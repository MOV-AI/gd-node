"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020
"""
import ast
import asyncio
import pickle
import re
import signal
import time

import uvloop

from movai_core_shared.logger import Log
from movai_core_shared.consts import MOVAI_INIT, MOVAI_TRANSITION, MOVAI_CONTEXTCLIENTIN

# importing database profile automatically registers the database connections
from dal.movaidb import RedisClient
from dal.models.scopestree import scopes, ScopePropertyNode
from dal.models.var import Var


from gd_node.protocol import Iport, Oport, Transports
from gd_node.user import GD_User

LOGGER = Log.get_logger("spawner.mov.ai")

TIME_0 = time.time()


def CoreInterruptHandler(signalnum, *_):
    """Process interrupts"""
    # msg = "\nSignal (ID: {}) has been caught. Stopping GDNode...".format(signalnum)
    # LOGGER.info(msg)
    GDNode.RUNNING.set()


class GDNode:
    """GD_Node asynchronous class"""

    __DEFAULT_CALLBACK__ = "place_holder"
    RUNNING = None

    def __init__(self, args, unknown):
        self.debug = args.verbose
        self.develop = args.develop
        # if self.debug:
        #    Config().enable_console_debug()
        self.inst_name = args.inst
        self.node_name = args.name
        self.flow_name = args.flow

        self.loop = uvloop.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self.handle_exception)

        self.databases = None
        self.transports = {
            "ROS1": False,
            "ROS2": False,
            "Flask": False,
            "Redis": True,
            "Http": False,
        }
        self.launched_transports = []
        self.ports_params = {}
        self.loop.run_until_complete(self.main(args, unknown))

    def handle_exception(self, loop, context):
        msg = context.get("exception", context["message"])
        LOGGER.error(f"YEP SOU EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU")
        LOGGER.error(f"{self.inst_name}: {msg}")

    async def connect(self) -> None:
        """Connect to aioredis slave db"""
        self.databases = await RedisClient.get_client()
        # await self.databases.init_redis()

    def _stop(self):
        """stop node out of async loop"""
        type(self).RUNNING.set()

    async def stop(self) -> None:
        """Gracefully shutdown node"""
        LOGGER.info("Shutting down GD Node: %s" % self.inst_name)

        Iport.shutdown()
        Oport.shutdown()
        Transports.shutdown()

        await self.databases.shutdown()
        # Clean all vars related to this node
        Var.delete_all(scope="Node", _node_name=GD_User.name)
        for iport in GD_User.iport:
            Var.delete_all(scope="Callback", _node_name=GD_User.name, _port_name=iport)

        tasks = [
            task
            for task in asyncio.all_tasks(loop=self.loop)
            if task is not asyncio.current_task(loop=self.loop)
            and not task.done()
            and not task.cancelled()
        ]

        list(map(lambda task: task.cancel(), tasks))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    def initial_print(self, inst_name: str, template_name: str, inst_params: list):
        """Some inital debug prints"""
        to_send = '--- Starting GD_Node with Name "%s" and Template "%s"' % (
            inst_name,
            template_name,
        )
        LOGGER.info(to_send)
        # print('With parameters:')
        # for elem in inst_params:
        #    print(elem, ': ', inst_params[elem])
        # print('\n')

    async def init_transports(
        self,
        node_name: str,
        inst_name: str,
        ports_templates: dict,
        transports: dict,
        remaps: list,
    ):
        """Check all existing Transports allong ports and init them
        In case of ROS1 need to wait until node registers in master

        Args:
            ports_templates: Description
            transports: Description
        """
        for ports in ports_templates.values():
            for tranport_name in transports:
                for port in ports.In:
                    if tranport_name in ports.In[port].Transport:
                        transports[tranport_name] = True
                for port in ports.Out:
                    if tranport_name in ports.Out[port].Transport:
                        transports[tranport_name] = True
        for key in transports:
            if transports[key]:
                config = {
                    "node_name": node_name,
                    "inst_name": inst_name,
                    "remaps": remaps,
                }
                if self.debug:
                    print("Transport", key)
                    print("    ", config)
                Transports.get(key, **config)

        # Allow transports to trigger GD_Node shutdown
        # ex.: when a node is launched with the same name as a node already running
        # rospy triggers a request shutdown event
        Transports.register_event("on_shutdown", self._stop)

        if transports["ROS1"]:
            from .protocols.ros1 import ROS1

            while not ROS1.is_init(inst_name):
                await asyncio.sleep(0.01)
            # print("ROS1 Node %s registered successfully." % inst_name)

    async def init_oports(
        self, inst_name: str, ports_templates: dict, ports_inst: dict, flow_name: str
    ):
        """Init all the output ports

        Args:
            ports_templates: Description
            ports_inst: Description
        """

        for ports in ports_inst:
            template = ports_templates[ports_inst[ports].Template]
            for pout in ports_inst[ports].Out:

                transport = template.Out[pout].Transport
                protocol = template.Out[pout].Protocol
                message = ports_inst[ports].Out[pout].Message
                params = ports_inst[ports].Out[pout].Parameter or {}

                for param in params:
                    params[param] = self.ports_params.get(
                        "@" + param + "@" + pout + "@" + ports, params[param]
                    )

                key = transport + "/" + protocol

                config = {
                    "node_name": inst_name,
                    "name": ports,
                    "topic": inst_name + "/" + ports + "/" + pout,
                    "message": message,
                    "_params": params,
                    "flow_name": flow_name,
                    "_gd_node": self,
                }

                Oport.create(key, **config)

    async def init_iports(
        self,
        inst_name: str,
        ports_templates: dict,
        ports_inst: dict,
        init: bool = False,
        transition_data=None,
    ):
        """Init all the input ports

        Args:
            ports_templates: Description
            ports_inst: Description
            init: Description
        """
        ongoing_creations = []

        for ports in ports_inst:
            template = ports_templates[ports_inst[ports].Template]

            for i in ports_inst[ports].In:
                transport = template.In[i].Transport
                protocol = template.In[i].Protocol
                message = ports_inst[ports].In[i].Message
                # place_holder
                callback = ports_inst[ports].In[i].Callback or self.__DEFAULT_CALLBACK__
                params = ports_inst[ports].In[i].Parameter or {}

                for param in params:
                    params[param] = self.ports_params.get(
                        "@" + param + "@" + i + "@" + ports, params[param]
                    )

                _type = key = "/".join([transport, protocol])
                _port_name = ports  # "/".join([ports, i])
                _topic = "/".join([inst_name, ports, i])
                config = {
                    "_node_name": inst_name,
                    "_port_name": _port_name,
                    "_port": i,
                    "_type": _type,
                    "_topic": _topic,
                    "_message": message,
                    "_callback": callback,
                    "_params": params,
                    "_data": transition_data,
                    "_update": self.develop,
                    "_gd_node": self,
                }
                if (key in [MOVAI_INIT,MOVAI_TRANSITION]) == init:
                    port_instance = Iport.create(key, **config)
                    if key == MOVAI_CONTEXTCLIENTIN:
                        ongoing_creations.append(port_instance)

        while ongoing_creations:
            ongoing_creations = [port for port in ongoing_creations 
                                 if not port.is_port_fully_created()]
            if ongoing_creations:
                await asyncio.sleep(0.1)

    async def main(self, args, unknown) -> None:
        """Runs the main loop. Exiting stops GDNode"""
        try:
            type(self).RUNNING = asyncio.Event()
            # connect databases
            await self.connect()

            # self.robot = Robot()
            GD_User.name = self.inst_name
            GD_User.template = self.node_name

            self.node = scopes.from_path(self.node_name, scope="Node")

            # set db    client name
            # await self.databases.db_global.client_setname(self.robot.RobotName + '_' + self.inst_name)
            # await self.databases.db_slave.client_setname(self.inst_name)
            # await self.databases.db_local.client_setname(self.inst_name)

            inst_params = {}
            if args.params:
                parameters = args.params.split('"', 1)[1].rsplit('"', 1)[0]
                for param in parameters.split(";"):
                    key, value = param.split(":=")
                    try:
                        value = ast.literal_eval(value)
                    except:
                        pass
                    inst_params[key] = value

            self.initial_print(self.inst_name, self.node_name, inst_params)

            # params are available all over the node as gd.params['name']
            for param in self.node.Parameter:
                value = inst_params.get(param, self.node["Parameter"][param]["Value"])
                try:
                    if isinstance(value, ScopePropertyNode):
                        value = value.value
                    value = ast.literal_eval(value)
                except:
                    pass
                pattern = r"^@[a-zA-Z_0-9-.]+(@[a-zA-Z_0-9-]+)(@[a-zA-Z_0-9-.]+)$"
                if not re.match(pattern, param):
                    GD_User.params[param] = value
                else:
                    self.ports_params.update({param: value})

            node_ports = {}
            for ports in self.node.PortsInst:
                ports_name = self.node.PortsInst[ports].Template
                node_ports[ports_name] = scopes.from_path(ports_name, scope="Ports")

            # Transition message
            trans_msg = None
            if args.message is not None:
                temp_msg = eval(args.message)
                if temp_msg is not None:
                    trans_msg = pickle.loads(temp_msg)

            # Initialize each of the transports
            await self.init_transports(
                self.node_name, self.inst_name, node_ports, self.transports, unknown
            )

            # Then we start the oports
            await self.init_oports(self.inst_name, node_ports, self.node["PortsInst"], self.flow_name)

            # Init all the Iports
            await self.init_iports(
                self.inst_name,
                node_ports,
                self.node["PortsInst"],
                init=False,
                transition_data=trans_msg,
            )

            if self.transports["ROS1"]:
                # ros publishers sending stuff in the init need time to register..
                await asyncio.sleep(0.2)

            # Then we run the initial callback
            await self.init_iports(self.inst_name, node_ports, self.node["PortsInst"], init=True)
            if not GD_User.is_transitioning:

                # And finally we enable the iports
                for iport in GD_User.iport:
                    try:
                        if GD_User.iport[iport].start_enabled:
                            GD_User.iport[iport].register()
                    except AttributeError:
                        pass

                # Start servers only after all routes were added
                if self.transports["Http"]:
                    Transports.get("Http").start()

            start_time = time.time() - TIME_0

            LOGGER.info('Full time to init the GD_Node "%s": %s' % (self.inst_name, start_time))

            signal.signal(signal.SIGINT, CoreInterruptHandler)
            signal.signal(signal.SIGTERM, CoreInterruptHandler)
            await type(self).RUNNING.wait()

            await self.stop()
        except KeyboardInterrupt:
            LOGGER.warning(f"[KILLED] Node killed forcefully while being initialized. Instance: {self.inst_name} Node: {self.node_name}")
