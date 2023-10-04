"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

   Module that implements the ROS1 protocol
"""
import asyncio
import importlib
import os
import sys
from typing import Any

import actionlib
import rosgraph
import rosnode
import rosparam
import rospy
from dynamic_reconfigure.client import Client as DynClient
from geometry_msgs.msg import Pose

from gd_node.callback import GD_Callback as Callback
from gd_node.message import GD_Message
from gd_node.user import GD_User

from gd_node.protocols.base import BaseIport


class ROS1:

    """
    ROS transport class.

    Serves as init for all the ROS based protocols. Creates a thread with the ropy.init_node

    Args:
        _node_name: Name of the node instance running
    """

    def __init__(self, _node_name: str, _remaps: list, *, shutdown=None):
        """ROS1 Init"""
        self.node_name = _node_name
        self.remaps = _remaps
        self.cb_shutdown = shutdown
        # maybe launch this in a thread executor
        try:
            self.loop = asyncio.get_event_loop()
        except Exception as e:
            self.loop = asyncio.new_event_loop()

    def init_node(self) -> None:
        """node launch"""
        # self.loop.run_until_complete(self.launch_ros_node())
        self.loop.create_task(self._launch_ros_node())

    async def _launch_ros_node(self):
        await self.loop.run_in_executor(None, self.launch_ros_node)

    def launch_ros_node(self):
        """async launch"""
        rospy.init_node(self.node_name, argv=self.remaps, disable_signals=True, disable_rosout=True)
        rospy.on_shutdown(self.on_shutdown)

    def on_shutdown(self):
        if callable(self.cb_shutdown):
            self.cb_shutdown()

    def shutdown(self, message=None):
        # remove on_shutdown event
        rospy.on_shutdown(lambda: None)
        rospy.signal_shutdown(message)

    @staticmethod
    def is_init(node_name: str) -> bool:
        """Checks if the node is successfully registered on the ros master

        Returns:
            bool: Node is initiated
        """
        sys.stderr = open(os.devnull, "w")  # just to ignore stupid prints
        try:
            ping = rosnode.rosnode_ping(node_name, max_count=1)
        except Exception as e:
            print("[ERROR] Roscore is needed and seems to not be running")
            sys.exit(0)
        sys.stderr = sys.__stderr__
        return ping

    @staticmethod
    def clean_parameter_server() -> None:
        """Cleans all the params in the parameter server except the default ones"""
        default_params = ["/rosdistro", "/rosversion", "/run_id"]  #'/roslaunch/uris/*'
        params = rospy.get_param_names()

        for param in [param for param in params if param not in default_params]:
            if "roslaunch/uris/" not in param:
                try:
                    rospy.delete_param(param)
                except KeyError:
                    print('Could not delete param "%s"' % param)

    @staticmethod
    def rosnode_cleanup() -> None:
        """Clean up stale node registration information on the ROS Master.
        Adapted from ronode.rosnode_cleanup"""
        pinged, unpinged = rosnode.rosnode_ping_all()
        if unpinged:
            master = rosgraph.Master("/rosnode")
            rosnode.cleanup_master_blacklist(master, unpinged)


##############################            IPORTS                   ###############################

class ROS1IportBase(BaseIport):
    """
    A base class for all of the ROS IPORTS
    """
    MAX_RETRIES = 100

    def callback(self, msg: Any) -> None:
        """Callback function for all the ROS IPORTS"""
        for _ in range(self.MAX_RETRIES):
            if self._gd_node.RUNNING and self.enabled:
                self.cb.execute(msg)
                return
            # if the port isn't initiated after 10 seconds it means it's disabled
            rospy.timer.sleep(0.1)

class ROS1_Subscriber(ROS1IportBase):

    """ROS Subscriber class. Implementation of the rospy.Subscriber

    Args:
        _node_name: Name of the node instance running
        _port_name: Name of the port
        _topic: ROS topic to subscribe
        _message: Ros Message
        _callback: Name of the callback to be executed

    """

    # __slots__ = ['node_name', 'port_name', 'topic', 'msg', 'cb', 'sub']
    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _update: bool,
        _gd_node: Any = None,
        **_
    ) -> None:
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)
        self._gd_node = _gd_node

        self.msg = GD_Message(_message, _type="msg").get()
        self.sub = rospy.Subscriber(self.topic, self.msg, self.callback)


    def unregister(self) -> None:
        """Unregisters the subscriber"""
        super().unregister()
        if self.sub is not None:
            self.sub.unregister()
            self.sub = None

    def register(self) -> None:
        """Registers the subscriber"""
        super().register()
        if self.sub is None:
            self.sub = rospy.Subscriber(self.topic, self.msg, self.callback)


####################################################


class ROS1_ServiceServer(ROS1IportBase):

    """ROS Service Server class. Implementation of the rospy.Service

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
        _gd_node: Any = None,
        **_ignore
    ) -> None:
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)
        _message = _message.rsplit("Request")[0]
        self.srv = GD_Message(_message, _type="srv").get()

        reply_key = "reply@" + self.port_name

        # initialize the oport needed for the reply
        self.reply = ROS1_ServiceServerReply()
        GD_User.oport[reply_key] = self.reply
        self.sub = rospy.Service(self.topic, self.srv, self.callback)

    def callback(self, msg: Any) -> Any:
        """Callback of the ROS Service Server protocol.

        Args:
            msg: ROS Service Request message

        Returns:
            Any: ROS service response message
        """
        super().callback(msg)
        if self.enabled:
            return self.reply.msg
        return None

    def get_response(self):
        """Returns the Service Response Class"""
        return self.srv._response_class  # pylint: disable=W0212

    def unregister(self, message: str = None):
        super().unregister()
        if self.sub is not None:
            self.sub.shutdown(message)
            self.sub = None


class ROS1_ServiceServerReply:

    """Class to provive a way of sending the response of a service server."""

    # stupid oport class just for the user to reply in a service server with oport['name'].send(msg)

    def __init__(self) -> None:
        self.msg = None

    def send(self, msg: Any) -> None:
        """Send function"""
        self.msg = msg


####################################################


class ROS1_Timer(ROS1IportBase):

    """ROS Timer class. Implementation of the rospy.Timer

    Args:
        _node_name: Name of the node instance running
        _port_name: Name of the port
        _topic: Not Used
        _message: Period of trigger
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
        _gd_node: Any = None,
        **_ignore
    ) -> None:
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)

        self.duration = 1 / float(_params.get("Frequency", 10))
        self.oneshot = _params.get("Oneshot", False)

        self.timer = rospy.Timer(rospy.Duration(self.duration), self.callback, oneshot=self.oneshot)
        # timer need to start unregistered to start counting when enabled
        self.unregister()

    def unregister(self) -> None:
        """Shutdown the timer"""
        super().unregister()
        self.timer.shutdown()

    def register(self) -> None:
        """Registers the timer"""
        super().register()
        if self.timer._shutdown:
            self.timer = rospy.Timer(
                rospy.Duration(self.duration), self.callback, oneshot=self.oneshot
            )


####################################################


class ROS1_TFSubscriber(ROS1IportBase):
    """Subscriber of ROS TF. Implementation of tf.TransformListener"""

    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _params: dict,
        _update: bool,
        _gd_node: Any = None,
        **_ignore
    ) -> None:
        globals()["tf"] = importlib.import_module("tf")
        globals()["tf2_ros"] = importlib.import_module("tf2_ros")
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)

        self.parent_frame = _params["Parent"]
        self.child_frame = _params["Child"]
        self.duration = 1 / float(_params.get("Frequency", 30))
        self.listener = tf.TransformListener()

        self.timer = rospy.Timer(rospy.Duration(self.duration), self.callback)

    def callback(self, msg: Any) -> None:
        try:
            msg = self.listener.lookupTransform(
                "/" + self.parent_frame, "/" + self.child_frame, rospy.Time(0)
            )
            (pos, rot) = msg
            data = Pose()
            data.position.x, data.position.y, data.position.z = pos[0], pos[1], pos[2]
            (
                data.orientation.x,
                data.orientation.y,
                data.orientation.z,
                data.orientation.w,
            ) = (rot[0], rot[1], rot[2], rot[3])
            super().callback(data)
            self.listener._buffer.clear()
        except tf2_ros.TransformException:
            pass
            # print('No transformation available yet')


####################################################

# This will not be used for now and is not up to date!
class ROS1_ActionServer(ROS1IportBase):
    def __init__(
        self,
        _node_name: str,
        _port_name: str,
        _topic: str,
        _message: str,
        _callback: str,
        _update: bool,
        _gd_node: Any = None,
        **_ignore
    ) -> None:
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)
        reply_key = "reply@" + self.topic

        module, msg_name = _message.split("/")
        vars()["msg_mod"] = importlib.import_module(module + ".msg._" + msg_name)

        GD_User.oport[reply_key] = ROS1_ActionServerReply(self.port_name, self)
        self.cb = Callback(_callback, self.node_name, self.port_name, True)
        self._as = actionlib.SimpleActionServer(
            self.topic,
            eval("msg_mod" + "." + msg_name),
            execute_cb=self.callback,
            auto_start=False,
        )
        self._as.start()

    def callback(self, msg):
        self.cb.execute(msg)

    def send_result(self, msg):  # sends the result....
        self._as.set_succeeded(msg)

    def send_feedback(self, msg):  # sends the feedback
        self._as.publish_feedback(msg)


class ROS1_ActionServerReply:
    def __init__(self, _port_name: str, iport: ROS1_ActionServer) -> None:
        self.port_name = _port_name
        self.iport = iport
        self.msg = None

    def send(self, msg: Any) -> None:
        self.msg = msg
        self.iport.send_result(msg)


class ROS1_ActionServerFeedback:
    def __init__(self, **_iport) -> None:
        self.port_name = _iport["Name"]
        self.msg = None

    def send(self, msg: Any) -> None:
        self.msg = msg
        GD_User.iport[self.port_name].send_feedback(msg)


class RostopicHzMsg:

    """Message for Rostopic Hz info

    rate -> average rate

    min -> minimun rate

    max -> maximun rate

    std_dev -> standard deviation

    window -> window size (number of samples)

    """

    def __init__(self, rate=0.0, min=0.0, max=0.0, std_dev=0.0, window=1):

        self.rate = rate

        self.min = min

        self.max = max

        self.std_dev = std_dev

        self.window = window


class ROS1_TopicHz(ROS1IportBase):

    """ROS1 Frequency Subscriber class. Implementation of the rostopic.ROSTopicHz class

    Args:

        _node_name: Name of the node instance running

        _port_name: Name of the port

        _topic: ROS topic to subscribe

        _message: Ros Message

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
        _gd_node: Any = None,
        **_ignore
    ) -> None:

        """Init"""

        import rostopic

        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update, _gd_node=_gd_node)

        self.msg = rospy.AnyMsg

        self.topic = "/" + _topic

        self.window_size = _params.get("WindowSize", -1)

        self.duration = 1 / _params.get("Frequency", 1)

        self.rostopic_hz = rostopic.ROSTopicHz(self.window_size)

        self.sub = rospy.Subscriber(
            self.topic, self.msg, self.rostopic_hz.callback_hz, callback_args=self.topic
        )

        self.timer = rospy.Timer(rospy.Duration(self.duration), self.callback)

    def callback(self, msg: Any) -> None:

        """Callback"""

        res = self.rostopic_hz.get_hz(self.topic)

        if res:

            data = RostopicHzMsg(*res)

        else:

            data = RostopicHzMsg()

        super().callback(data)

    def unregister(self) -> None:

        """Unregisters the subscriber"""

        super().unregister()

        self.timer.shutdown()

        if self.sub is not None:

            self.sub.unregister()

            self.sub = None

    def register(self) -> None:

        """Registers the subscriber"""

        super().register()

        if self.sub is None:

            self.sub = rospy.Subscriber(self.topic, self.msg, self.callback)

        if self.timer._shutdown:

            self.timer = rospy.Timer(rospy.Duration(self.duration), self.callback)


##############################            OPORTS                   ########################################################


class ROS1_Publisher:
    """ROS Publisher class. Implementation of the rospy.Publisher

    Args:
        _topic: ROS topic to publish
        _message: ROS message
    """

    def __init__(self, _topic: str, _message: Any, _params: dict = None, _gd_node=None) -> None:
        """Init"""

        self.msg = GD_Message(_message).get()
        self._gd_node = _gd_node
        params = {"queue_size": 1}
        if _params is not None:
            params.update(_params)
        self.pub = rospy.Publisher(_topic, self.msg, **params)

    def send(self, msg: Any) -> None:
        """Send function

        Args:
            msg: ROS Message
        """
        if not self._gd_node or self._gd_node.RUNNING:
            # publish only when Node is actually still running
            self.pub.publish(msg)

    def unregister(self):
        if self.pub:
            self.pub.unregister()


####################################################


class ROS1_ServiceClient:

    """ROS Service Client class.
    Implementation of the rospy.ServiceProxy

    Args:
        _topic: ROS topic to call service
        _service: ROS Service
    """

    def __init__(self, _topic: str, _service: Any):
        """Init"""
        self.topic = _topic
        self.srv = GD_Message(_service, _type="srv").get()
        self.pub = rospy.ServiceProxy(_topic, self.srv)

    def send(self, srv: Any) -> Any:
        """Send function

        Args:
            srv: ROS Service request message

        Returns:
            Any: ROS Service response message

        """
        response = self.pub(srv)
        return response

    def wait_for_service(self, timeout=10):
        """Wait until a service becomes available.
        A ROSException is raised if the timeout is exceeded"""
        rospy.wait_for_service(self.topic, timeout=timeout)

    def get_request(self):
        """Returns the Service Request Class"""
        return self.srv._request_class  # pylint: disable=W0212

    def unregister(self):
        if self.pub:
            self.pub.close()


####################################################


class ROS1_ActionClient:

    """ROS Action Client class.
    Implementation of the actionlib.SimpleActionClient

    Args:
        _topic: ROS topic to call actionlib
        _message: ROS Action Message
    """

    def __init__(self, _topic: str, _message: Any):
        """Init"""
        module, msg_name = _message.split("/")
        msg_mod = importlib.import_module(module + ".msg._" + msg_name)
        self.action = getattr(msg_mod, msg_name)

        goal_msg = msg_name.replace("Action", "Goal")
        msg_mod_goal = importlib.import_module(module + ".msg._" + goal_msg)
        self.goal = getattr(msg_mod_goal, goal_msg)

        msg_mod_cancel = importlib.import_module("actionlib_msgs.msg._GoalID")
        self.cancel = getattr(msg_mod_cancel, "GoalID")

        self.client = actionlib.SimpleActionClient(_topic, self.action)

    def send(self, msg: Any):
        """Send function

        Args:
            msg: ROS Action Goal Message
        """
        self.client.send_goal(msg)

    def get_goal(self):
        """Returns the Goal Message of the Action"""
        return self.goal

    def get_cancel(self):
        """Returns the Cancel Message of the Action"""
        return self.cancel


####################################################


class ROS1_DynReconfigure:

    """Implementation of ROS Dynamic Reconficure Client

    Args:
       _topic: Description
       _message: Nothing for now
    """

    def __init__(self, _topic: str, _message: str) -> None:
        """Init"""
        self.mapping = {}
        self.topic = _topic

    def send(self, msg: dict, topic: str = None, timeout=0.5):
        """Send function for ROS Dynamic Reconfigure

        Args:
            msg: Dictionary with params and values to reconfigure
        """
        topic = self.topic if topic is None else topic
        client = self.mapping.get(topic)
        if not client:
            client = DynClient(topic, timeout=timeout, config_callback=None)
            self.mapping[topic] = client

        client.update_configuration(msg)

    def access_dynclient(self, msg: dict, topic: str = None, timeout=0.5):

        topic = self.topic if topic is None else topic

        client = self.mapping.get(topic)

        if not client:

            client = DynClient(topic, timeout=timeout, config_callback=None)

            self.mapping[topic] = client

    def unregister(self):
        """Close all connections to server"""
        for _, client in self.mapping.items():
            client.close()


class ROS1_Bag:
    """ROS Bag class. Implementation of the rosbag

    Args:
        _topic: ROS topic to publish
        _message: ROS message
    """

    def __init__(self, _topic: str, _message: Any) -> None:
        """Init"""
        import rosbag, datetime

        try:
            name = _topic.split("/")[1]
        except:
            name = _topic.replace("/", "_")
        date = datetime.datetime.now()
        date.strftime("_%Y_%m_%d::%H_%M_%S")
        if not os.path.exists("rosbags"):
            os.makedirs("rosbags")
        name = "rosbags/" + name + date.strftime("_%Y_%m_%d::%H_%M_%S") + ".bag"
        self.bag = rosbag.Bag(name, mode="w")

    def send(self, msg: Any, topic: str) -> None:
        """Send function

        Args:
            topic: ROS topic to save the published message
            msg: ROS Message
        """
        self.bag.write(topic, msg)

    def unregister(self):
        if self.bag:
            self.bag.close()


####################################################


class ROS1_TFBroadcaster:

    """ROS TF broadcaster class.
    Implementation of the tf.TransformBroadcaster().sendTransform

    Args:
        _params: Parent and Child frames
        _message: ROS Pose Message
    """

    def __init__(self, _topic: str, _message: Any, _params: dict):
        """Init"""
        globals()["tf"] = importlib.import_module("tf")
        globals()["tf2_ros"] = importlib.import_module("tf2_ros")

        self._topic1 = _params["Child"]
        self._topic2 = _params["Parent"]
        self.broadcaster = tf.TransformBroadcaster()

    def send(self, msg, *, child=None, parent=None):
        """Send function

        Args:
            msg: ROS Pose Message
        """
        if child is not None:
            self._topic1 = child
        if parent is not None:
            self._topic2 = parent
        pos = (msg.position.x, msg.position.y, msg.position.z)
        ori = (
            msg.orientation.x,
            msg.orientation.y,
            msg.orientation.z,
            msg.orientation.w,
        )

        self.broadcaster.sendTransform(pos, ori, rospy.Time.now(), self._topic1, self._topic2)

    def unregister(self):
        self.broadcaster = None


class ROS1_Parameter:

    """ROS Parameter Server write class.
    Implementation of rosparam upload_params

    Args:
        _params: Namespace
        _message: python dict
    """

    def __init__(self, _topic: str, _message: Any, _params: dict):
        """Init"""
        self.namespace = _params.get("Namespace", "")

    def send(self, msg: dict):
        """Send function

        Args:
            msg: dict of key value parameters
        """
        if not isinstance(msg, dict):
            raise Exception("Wrong message type, it should be a dictionary")
        rosparam.upload_params(self.namespace, msg, False)
