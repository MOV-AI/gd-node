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

from movai_core_shared.logger import Log
from movai_core_shared.common.http_middlewares import (
    JWTMiddleware,
    apply_scope_contextmanagers,
    redirect_not_found,
)

from dal.data.shared.vault import JWT_SECRET_KEY
from dal.scopes.flow import delete_links_of_deleted_exposed_ports
from dal.scopes.node import save_node_type
from dal.utils import get_user_by_type_and_name


LOGGER = Log.get_logger("http.mov.ai")


class CreateServer:
    """Class that creates a aiohttp server with support
    for http and websockets

    Args:
        _hostname: Name of the server host
        _port: Port of the server
    """
    app: web.Application

    def __init__(self, _node_name: str, _hostname: str, _port: int, *, test=False) -> None:
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

        self.app = web.Application(
            middlewares=[
                JWTMiddleware(JWT_SECRET_KEY, get_user_by_type_and_name, auth_whitelist).middleware,
                apply_scope_contextmanagers("Flow", [delete_links_of_deleted_exposed_ports]),
                apply_scope_contextmanagers("Node", [save_node_type]),
                redirect_not_found,
            ]
        )
        self.app["connections"] = set()
        self.app["sub_connections"] = set()
        aiohttp_cors.setup(
            self.app,
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
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.hostname, self.port)
        await site.start()
        LOGGER.info("Http/websockets server listenning on %s %s", self.hostname, self.port)
