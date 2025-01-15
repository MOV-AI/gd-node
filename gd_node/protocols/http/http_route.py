from typing import Any

from aiohttp import web

from gd_node.callback import GD_Callback


class HttpRoute:

    """Http endpoints

    Args:
        _node_name: Name of the node instance
        _port_name: Name of the port
        _topic: Not used
        _message: Url rule
        _callback: Name of the callback to be executed
    """

    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _params: dict,
        _update: bool,
        **_ignore
    ):
        """Init"""
        from gd_node.protocol import TransportHttp, Transports
        transport: TransportHttp = Transports.get("Http")
        assert transport is not None and transport._instance is not None
        app = transport._instance.app

        self.node_name = _node_name
        self.port_name = _port_name
        self.topic = _params.get("Endpoint", _message)

        self.reply = None
        self.callback = GD_Callback(_callback, self.node_name, self.port_name, _update)
        self.callback.user.globals.update({"app": app, "web": web})

        # add http route
        HTTP.app.add_routes(
            [
                web.get(self.topic, self.run_callback),
                web.post(self.topic, self.run_callback),
            ]
        )

    async def run_callback(self, request: web.Request) -> web.Response:
        """http handler"""
        body = None
        if request.has_body:
            body = await request.json()
        setattr(request, "body", body)
        self.callback.execute(request)
        if self.reply in ["", None]:
            raise web.HTTPNotImplemented()
        return self.reply

    def send(self, msg: Any):
        """prepare reply"""
        self.reply = msg
