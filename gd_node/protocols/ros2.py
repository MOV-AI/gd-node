"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020
"""
import asyncio
import importlib
import sys
from typing import Any
import rclpy

from movai_core_shared.envvars import ROS2_PATH

from gd_node.message import GD_Message2
from gd_node.user import GD_User

from gd_node.protocols.base import BaseIport

# Initialization, Shutdown, and Spinning
# http://docs.ros2.org/latest/api/rclpy/api/init_shutdown.html


class ROS2:
    node = ""


class ROS2_INIT:
    def __init__(self, _node_name):
        rclpy.init(args=None)
        ROS2.node = rclpy.create_node(_node_name)

    def shutdown(self, message=None):
        # remove on_shutdown event
        ROS2.node.destroy_node()
        rclpy.shutdown()


class ROS2Async:
    """Run ROS2 node asynchronous"""

    def __init__(self, *, shutdown=None):
        """ROS2 Init"""

        self.cb_shutdown = shutdown
        # maybe launch this in a thread executor
        try:
            self.loop = asyncio.get_event_loop()
        except Exception as e:
            self.loop = asyncio.new_event_loop()

    def run_node(self) -> None:
        """Node spin"""
        self.loop.create_task(self._run_ros_node())

    async def _run_ros_node(self):
        await self.loop.run_in_executor(None, self.run_ros_node)

    def run_ros_node(self):
        """Async launch"""
        while rclpy.ok():
            rclpy.spin_once(ROS2.node)


class ROS2_Subscriber(BaseIport):
    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _update: bool,
        **_ignore
    ) -> None:

        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update)

        self.topic = _topic

        path_backup = sys.path

        module, msg_name = _message.split("/")
        msg_mod = importlib.import_module(module)

        sys.path.insert(1, ROS2_PATH)
        importlib.reload(msg_mod)
        importlib.reload(msg_mod.msg)

        self.msg = getattr(msg_mod.msg, msg_name)

        self.sub = ROS2.node.create_subscription(
            self.msg, self.topic, self.callback, 10
        )  # QOS profile
        self.sub  # prevent unused variable warning

        sys.path = path_backup
        importlib.reload(msg_mod)
        importlib.reload(msg_mod.msg)

    def unregister(self) -> None:
        """Unregisters the subscriber -> Needs testing"""
        super().unregister()
        self.sub.destoy()
        self.sub = None

    def register(self) -> None:
        """Registers the subscriber"""
        super().register()
        if self.sub is None:
            self.sub = ROS2.node.create_subscription(
                self.msg, self.topic, self.callback, 10
            )
            self.sub  # prevent unused variable warning


class Ros2Srv:
    """Service message container to pass to callback"""

    def __init__(self, request=None, response=None):
        self.request = request
        self.response = response


class ROS2_ServiceServer(BaseIport):

    """ROS2 Service Server class. Implementation of the rclpy.node.create_service

    Args:
        _node_name: Name of the node instance running
        _port_name: Name of the port
        _topic: ROS service topic
        _message: Ros Service
        _callback: Name of the callback to be executed
    """

    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _update: bool,
        **_ignore
    ) -> None:
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update)

        _message = _message.rsplit("Request")[0]  # Do we need this?
        self.gd_message = GD_Message2()
        self.msg = self.gd_message.get_ros2_srv(_message)

        self.srv = ROS2.node.create_service(self.msg, _topic, self.callback)

        reply_key = "reply@" + self.port_name

        # initialize the oport needed for the reply
        self.reply = ROS2_ServiceServerReply()
        GD_User.oport[reply_key] = self.reply

    def callback(self, request: Any, response: Any) -> Any:
        """Callback of the ROS Service Server protocol.
        Args:
            msg: ROS Service Request message

        Returns:
            Any: ROS service response message
        """

        msg = Ros2Srv(request, response)

        if self.enabled:
            super().callback(msg)
            return self.reply.msg
        return response

    def unregister(self, message: str = None):
        super().unregister()
        # self.srv.shutdown(message) ?
        # self.srv = None


class ROS2_ServiceServerReply:

    """Class to provive a way of sending the response of a service server.
    E.g: gd.oport['reply@iport_name'].send(msg)"""

    def __init__(self) -> None:
        self.msg = None

    def send(self, msg: Any) -> None:
        """Send function"""
        self.msg = msg


class ROS2_Publisher:
    def __init__(self, _topic: str, _message: Any):

        self.gd_message = GD_Message2()

        path_backup = sys.path

        module, msg_name = _message.split("/")
        msg_mod = importlib.import_module(module)

        sys.path.insert(1, ROS2_PATH)
        importlib.reload(msg_mod)
        importlib.reload(msg_mod.msg)

        msg = getattr(msg_mod.msg, msg_name)

        self.pub = ROS2.node.create_publisher(msg, _topic, 10)

        sys.path = path_backup
        importlib.reload(msg_mod)
        importlib.reload(msg_mod.msg)

    def send(self, msg):
        """Send method"""
        msg = self.gd_message.get_ros2_msg(msg)  # if msg is ros1 converts to ros2
        self.pub.publish(msg)


class ROS2_ServiceClient:

    """ROS2 Service Client class.
    Implementation of the rclpy.ServiceProxy

    Args:
        _topic: ROS topic to call service
        _message: ROS Service
    """

    def __init__(self, _topic: str, _message: Any):
        """Init"""
        self.gd_message = GD_Message2()
        msg = self.gd_message.get_ros2_srv(_message)

        self.client = ROS2.node.create_client(msg, _topic)

    def send(self, msg: Any) -> Any:
        """Send function

        Args:
            msg: ROS Service request message

        Returns:
            Any: ROS Service response message

        """
        msg = self.gd_message.get_ros2_srv(msg)

        # future = self.client.call_async(msg)
        future = self.client.call(msg)

        # rclpy.spin_until_future_complete(ROS2.node, future)

        # if future.result() is not None:
        #    return future.result()

        # return future.exception()
        return future

    def unregister(self):
        """Unregister"""
        if self.client:
            self.client.destroy()
