"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

   Base classes for all protocols
"""

from typing import Any


from gd_node.callback import GD_Callback as Callback


class BaseIport:
    """Class with common methods for all the iports"""

    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        update: bool = True,
        _gd_node: Any = None,
        **_ignore
    ) -> None:

        self.node_name = _node_name
        self.port_name = _port_name
        self.topic = _topic
        self.enabled = False
        self.start_enabled = True
        self._gd_node = _gd_node
        self.cb = Callback(_callback, self.node_name, self.port_name, update)
        self.await_coro = None

    def callback(self, msg: Any) -> None:
        """Executes the callback if port is enabled"""
        # Todo: check if i cqn chqnge enabled to async event
        if self.enabled:
            self.cb.execute(msg)

    def unregister(self) -> None:
        """Disables the iport"""
        self.enabled = False

    def register(self) -> None:
        """Enables the iport"""
        self.enabled = True


class BaseOport:
    """Class with common methods for all the oports"""

    pass
