import asyncio
import json
import sys
import uuid
from typing import Any

import aioredis
import yaml
from aiohttp import web, WSMsgType
from dal.movaidb import MovaiDB, RedisClient

from gd_node.callback import GD_Callback
from gd_node.protocols.http import HTTP, LOGGER


class WebSocketRedisSub:
    """API for dynamic subscriber to redis"""

    def __init__(self, _node_name: str, **_ignore):
        self.topic = "/ws/subscriber"
        self.node_name = _node_name

        self.databases = None
        self.connections = {}
        self.connection = None
        self.movaidb = MovaiDB()
        self.loop = asyncio.get_event_loop()

        # API available actions
        self.actions = {
            "subscribe": self.add_pattern,
            "unsubscribe": self.remove_pattern,
            "list": self.get_patterns,
            "execute": self.execute,
        }

        # Add API endpoint
        HTTP.app.add_routes([web.get(self.topic, self.handler)])

        # create database client
        self.loop.create_task(self.connect())

    async def connect(self):
        # create database client
        self.databases = await RedisClient.get_client()

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        """handle websocket connections"""

        ws_resp = web.WebSocketResponse()
        await ws_resp.prepare(request)

        self.connection = ws_resp
        HTTP.app["sub_connections"].add(ws_resp)

        # create uuid for the connection
        conn_id = uuid.uuid4().hex

        # acquire db connection
        _conn = await self.databases.slave_pubsub.acquire()
        conn = aioredis.Redis(_conn)
        if not conn:
            error = "could not acquire redis connection"
            LOGGER.error(error)
            await ws_resp.send_json({"event": "", "patterns": None, "error": error})

        # add connection
        self.connections.update({conn_id: {"conn": ws_resp, "subs": conn, "patterns": []}})

        # wait for messages
        async for ws_msg in ws_resp:
            if ws_msg.type == WSMsgType.TEXT:
                # message should be json
                try:
                    data = ws_msg.json()
                    LOGGER.info(data)
                    if "event" in data:
                        if data.get("event") == "execute":
                            _config = {
                                "conn_id": conn_id,
                                "conn": conn,
                                "callback": data.get("callback", None),
                                "func": data.get("func", None),
                                "data": data.get("data", None),
                            }
                        else:
                            _config = {
                                "conn_id": conn_id,
                                "conn": conn,
                                "_pattern": data.get("pattern", None),
                            }
                        await self.actions[data["event"]](**_config)
                    else:
                        error = "Not all required keys found"
                        LOGGER.error("ERROR: %s" % error)
                        output = {"event": None, "patterns": None, "error": error}
                        await ws_resp.send_json(output)
                except Exception as e:
                    error = "Request format unknown"
                    LOGGER.error(e)
                    output = {"event": None, "patterns": None, "error": str(e)}
                    await ws_resp.send_json(output)
            elif ws_msg.type == WSMsgType.ERROR:
                LOGGER.error("ws connection closed with exception %s" % ws_resp.exception())

        conn.close()
        await conn.wait_closed()
        HTTP.app["sub_connections"].remove(ws_resp)
        del self.connections[conn_id]
        return ws_resp

    def convert_pattern(self, _pattern: dict) -> str:
        try:
            pattern = _pattern.copy()
            scope = pattern.pop("Scope")
            search_dict = self.movaidb.get_search_dict(scope, **pattern)

            keys = []
            for elem in self.movaidb.dict_to_keys(search_dict, validate=False):
                key, _, _ = elem
                keys.append(key)
            return keys
        except Exception as e:
            LOGGER.error(f"caught Exception in convert_pattern: {e}")
            return ""

    async def add_pattern(self, conn_id, conn, _pattern, **ignore):
        """Add pattern to subscriber"""
        LOGGER.info(f"add_pattern{_pattern}")

        self.connections[conn_id]["patterns"].append(_pattern)
        key_patterns = []
        if isinstance(_pattern, list):
            for patt in _pattern:
                key_patterns.extend(self.convert_pattern(patt))
        else:
            key_patterns = self.convert_pattern(_pattern)
        keys = []
        tasks = []
        for key_pattern in key_patterns:
            pattern = "__keyspace@*__:%s" % (key_pattern)
            channel = await conn.psubscribe(pattern)
            self.loop.create_task(self.wait_message(conn_id, channel[0]))

            # add a new get_keys task
            tasks.append(self.get_keys(key_pattern))

        # wait for all get_keys tasks to run
        _values = await asyncio.gather(*tasks)

        for value in _values:
            for key in value:
                keys.append(key)

        # get all values
        values = await self.mget(keys)

        ws = self.connections[conn_id]["conn"]
        await ws.send_json({"event": "subscribe", "patterns": [_pattern], "value": values})

    async def remove_pattern(self, conn_id, conn, _pattern, **ignore):
        """Remove pattern from subscriber"""
        LOGGER.debug(f"removing pattern {_pattern} {conn}")
        if _pattern in self.connections[conn_id]["patterns"]:
            self.connections[conn_id]["patterns"].remove(_pattern)

        key_patterns = self.convert_pattern(_pattern)
        for key_pattern in key_patterns:
            pattern = "__keyspace@*__:%s" % (key_pattern)
            await conn.punsubscribe(pattern)

        ws = self.connections[conn_id]["conn"]
        await ws.send_json({"event": "unsubscribe", "patterns": [_pattern]})

    async def get_patterns(self, conn_id, conn, **ignore):
        """Get list of patterns"""

        output = {"event": "list", "patterns": self.connections[conn_id]["patterns"]}
        ws = self.connections[conn_id]["conn"]
        await ws.send_json(output)

    async def wait_message(self, conn_id, channel):
        """Receive messages from redis subscriber"""
        output = {"event": "unknown"}
        while await channel.wait_message():
            ws = self.connections[conn_id]["conn"]
            msg = await channel.get(encoding="utf-8")
            value = ""
            key = msg[0].decode("utf-8").split(":", 1)[1]
            # match the key triggerd with any patterns
            match_patterns = []
            for dict_pattern in self.connections[conn_id]["patterns"]:
                patterns = self.convert_pattern(dict_pattern)
                for pattern in patterns:
                    if all(piece in key for piece in pattern.split("*")):
                        match_patterns.append(dict_pattern)
            if msg[1] in ("set", "hset", "hdel"):
                key_in_dict = await self.get_value(key)
            else:
                key_in_dict = self.movaidb.keys_to_dict([(key, value)])
            output.update(
                {
                    "event": msg[1],
                    "patterns": match_patterns,
                    "key": key_in_dict,
                    "value": value,
                }
            )
            if not ws.closed:
                await ws.send_json(output)

    async def get_keys(self, pattern: str) -> list:
        """Get all redis keys in pattern"""
        _conn = self.databases.db_slave
        keys = await _conn.keys(pattern)

        # sort keys
        keys = [key.decode("utf-8") for key in keys]
        keys.sort(key=str.lower)
        keys = [key.encode("utf-8") for key in keys]

        return keys

    async def get_value(self, keys):
        """Get key value"""
        # TODO DEPRECATED NOT YET
        output = {}
        _conn = self.databases.db_slave
        key_values = []
        if not isinstance(keys, list):
            keys = [keys]
        tasks = []
        for key in keys:
            tasks.append(self.fetch_value(_conn, key))
        values = await asyncio.gather(*tasks)
        for key, value in values:
            if isinstance(key, bytes):
                key_values.append((key.decode("utf-8"), value))
            else:
                key_values.append((key, value))
        output = self.movaidb.keys_to_dict(key_values)
        return output

    async def fetch_value(self, _conn, key):
        # DEPRECATED
        type_ = await _conn.type(key)
        type_ = type_.decode("utf-8")
        if type_ == "string":
            value = await _conn.get(key)
            value = self.movaidb.decode_value(value)
        if type_ == "list":
            value = await _conn.lrange(key, 0, -1)
            value = self.movaidb.decode_list(value)
        if type_ == "hash":
            value = await _conn.hgetall(key)
            value = self.movaidb.decode_hash(value)
        try:  # Json cannot dump ROS Messages
            json.dumps(value)
        except Exception as e:
            LOGGER.error(
                f"failed dumping json, exception: {e}, \
                         trying yaml load ..."
            )
            try:
                value = yaml.load(str(value), Loader=yaml.SafeLoader)
            except Exception as e:
                LOGGER.error(f"failed loading yaml, exception: {e}")
                value = None
        return (key, value)

    async def mget(self, keys):
        """get values using redis mget"""
        _conn = self.databases.db_slave
        output = []
        values = []
        try:
            values = await _conn.mget(*keys)
        except Exception as e:
            LOGGER.info(e)

        for key, value in zip(keys, values):
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            if not value:
                # not a string
                value = await self.get_key_val(_conn, key)
            else:
                value = self.__decode_value("string", value)
            output.append((key, value))

        return self.movaidb.keys_to_dict(output)

    async def get_key_val(self, _conn, key):
        """get value by type"""
        type_ = await _conn.type(key)
        # get redis type
        type_ = type_.decode("utf-8")

        # get value by redis type
        if type_ == "string":
            value = await _conn.get(key)
        if type_ == "list":
            value = await _conn.lrange(key, 0, -1)
        if type_ == "hash":
            value = await _conn.hgetall(key)

        # return decode value
        return self.__decode_value(type_, value)

    def __decode_value(self, type_, value):
        """decode value by type"""
        if type_ == "string":
            value = self.movaidb.decode_value(value)
        if type_ == "list":
            value = self.movaidb.decode_list(value)
        if type_ == "hash":
            value = self.movaidb.sort_dict(self.movaidb.decode_hash(value))
        try:  # Json cannot dump ROS Messages
            json.dumps(value)
        except Exception as e:
            LOGGER.error(
                f"failed dumping json, exception: {e}, \
                         trying yaml load ..."
            )
            try:
                value = yaml.load(str(value), Loader=yaml.SafeLoader)
            except Exception as e:
                LOGGER.error(f"failed dumping json, exception: {e}")
                value = None
        return value

    async def execute(self, conn_id, conn, callback, data=None, **ignore):
        """
        event: execute
        execute specific callback
        Request implemented in Database.js
        """

        ws = self.connections[conn_id]["conn"]

        try:
            # get callback
            callback = GD_Callback(callback, self.node_name, "cloud", _update=False)

            # update callback with request data
            callback.user.globals.update({"msg": data, "response": {}})
            # execute callback
            callback.execute(data)

            # create response
            response = {"event": "execute", "result": None, "patterns": ["execute"]}
            _response = callback.updated_globals["response"]

            if isinstance(_response, dict):
                response.update(_response)
            else:
                response["result"] = _response

            # send response
            if not ws.closed:
                await ws.send_json(response)

        except Exception as _exception:
            LOGGER.error(f"exception caught {_exception}")
            error = f"{str(sys.exc_info()[1])} {sys.exc_info()}"
            if not ws.closed:
                await ws.send_json(
                    {
                        "event": "execute",
                        "callback": callback,
                        "result": None,
                        "error": error,
                    }
                )


class WebSocketSub:
    """Websocket subscriber"""

    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _params: dict,
        _update: bool,
        **_ignore,
    ):
        self.node_name = _node_name
        self.port_name = _port_name
        self.topic = "/ws/" + _params.get("Endpoint", _message)
        self.reply = None
        self.connection = None
        self.callback = GD_Callback(_callback, self.node_name, self.port_name, _update)
        # @TODO: this should go through the message
        self.callback.user.globals.update({"app": HTTP.app, "web": web})
        # register websocket endpoint
        HTTP.app.add_routes([web.get(self.topic, self.websocket_handler)])

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """handle websocket connections"""
        ws_resp = web.WebSocketResponse()
        await ws_resp.prepare(request)
        self.connection = ws_resp
        HTTP.app["connections"].add(ws_resp)
        # receive messages
        async for ws_msg in ws_resp:
            if ws_msg.type == WSMsgType.TEXT:
                self.run_callback(ws_msg)
                await ws_resp.send_json(self.reply)
            elif ws_msg.type == WSMsgType.ERROR:
                LOGGER.error("ws connection closed with exception %s", ws_resp.exception())
        HTTP.app["connections"].remove(ws_resp)
        return ws_resp

    def run_callback(self, msg: Any):
        """execute callback"""
        self.callback.user.globals.update({"app": HTTP.app, "req": msg})
        try:  # Ugly but native WS only handles strings, names arrays and Blobs
            data = msg.json()
        except Exception as e:
            LOGGER.warning(f"failed creating json, exception: {e}")
            data = msg.data
        self.callback.execute(data)

    def send(self, msg: Any, channel: str):
        """prepare reply"""
        self.reply = {"channel": msg}

    def broadcast(self, msg: Any, channel: str):
        """interface to call broadcast coroutine"""
        HTTP.app.loop.create_task(self._broadcast(msg, channel))

    async def _broadcast(self, msg: Any, channel: str):
        """coroutine to broadcast message to all connections"""
        message = {"channel": msg}
        for connection in HTTP.app["connections"]:
            await connection.send_json(message)
