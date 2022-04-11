"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

   Maintainers:
   - Tiago Teixeira (tiago.teixeira@mov.ai) - 2020

   Module that implements the Asynchronous Http Server
"""

import asyncio

import aiohttp_cors
from aiohttp import web

try:
    from movai_core_enterprise.models.layout import Layout

    enterprise = True
except ImportError:
    enterprise = False

from movai_core_shared.logger import Log

LOGGER = Log.get_logger("http.mov.ai")


class HTTP:
    """Holder for app"""

    app = ""


# @TODO: pass HttpMessage to the callback
# @TODO: define message structure


class CreateServer:
    """Class that creates a aiohttp server with support
    for http and websockets

    Args:
        _hostname: Name of the server host
        _port: Port of the server
    """

    def __init__(
        self, _node_name: str, _hostname: str, _port: int, *, middleware
    ) -> None:
        """Init"""
        self.hostname = _hostname
        self.port = _port
        self.node_name = _node_name
        self.api_version = "/api/v1/"

        auth_whitelist = (
            r"/$",
            r"/token-auth/$",
            r"/token-refresh/$",
            r"/token-verify/$",
            r"/static/(.*)",
            r"{api_version}apps/(.*)".format(api_version=self.api_version),
        )

        HTTP.app = web.Application(
            middlewares=[
                # Todo: add middlewere or use the backend functions
                # JWTMiddleware(JWT_SECRET_KEY, auth_whitelist).middleware,
                # save_node_type,
                # remove_flow_exposed_port_links,
                # redirect_not_found
            ]
        )
        HTTP.app["connections"] = set()
        HTTP.app["sub_connections"] = set()
        aiohttp_cors.setup(
            HTTP.app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )

    def start(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.run())

    async def run(self):
        """
        Keep the server running
        """
        runner = web.AppRunner(HTTP.app)
        await runner.setup()
        site = web.TCPSite(runner, self.hostname, self.port)
        await site.start()
        LOGGER.info(
            "Http/websockets server listenning on %s %s", self.hostname, self.port
        )
