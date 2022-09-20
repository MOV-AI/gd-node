"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

   Module that implements all the tranports and protocols
   currently supported by the GD_Node
"""
from typing import Any

from dal.classes.protocols import redissub as RedisSub

import gd_node.protocols.http.http_route
import gd_node.protocols.http.web_socket
import gd_node.protocols.base as Base
import gd_node.protocols.http as Http
import gd_node.protocols.ros1 as ROS1
import gd_node.protocols.movai as MovAI

from gd_node.user import GD_User as gd


class TransportsProvider:
    def __init__(self):
        self._transports = {}
        self._transports_inst = {}
        self._callbacks = {}

    def register(self, key, builder):
        self._transports[key] = builder

    def create(self, key, **kwargs):
        builder = self._transports.get(key)
        if not builder:
            raise ValueError(key)
        self._transports_inst[key] = builder(**kwargs)
        return self._transports_inst[key]

    def get(self, key, **kwargs):
        trans_inst = self._transports_inst.get(key)
        if not trans_inst:
            trans_inst = self.create(key, **kwargs)
        return trans_inst

    def register_event(self, key, callback):
        self._callbacks[key] = callback

    def on_shutdown(self, **kwargs):
        callback = self._callbacks.get("on_shutdown")
        if callable(callback):
            callback(**kwargs)

    def start(self, **kwargs):
        for transport_name in self._transports:
            try:
                self._transports[transport_name].start()
            except AttributeError as e:
                pass

    def shutdown(self):
        # disable all callback events
        self._callbacks.clear()
        for transport_name in self._transports:
            try:
                self._transports[transport_name].shutdown()
            except AttributeError as e:
                pass


class TransportROS1:
    def __init__(self):
        self._instance = None

    def __call__(self, inst_name, remaps, **_ignore):
        if not self._instance:
            self._instance = ROS1.ROS1(
                inst_name, remaps, shutdown=Transports.on_shutdown
            )
            self._instance.init_node()
        return self._instance

    def shutdown(self):
        if self._instance:
            self._instance.shutdown("Node %s required shutdown." % gd.name)


class TransportRedis:
    def __init__(self):
        self._instance = None

    def __call__(self, inst_name, remaps, **_ignore):
        if not self._instance:
            self._instance = None
        return self._instance


class TransportHttp:
    def __init__(self):
        self._instance = None

    def __call__(self, node_name, **_ignore):
        if not self._instance:
            port = gd.params.get("_port", 5000)
            self._instance = Http.CreateServer(node_name, "0.0.0.0", port)
        return self._instance


class TransportROS2:
    def __init__(self):
        self._instance = None

    def __call__(self, inst_name, **_ignore):
        import gd_node.protocols.ros2 as ROS2

        if not self._instance:
            self._instance = ROS2.ROS2_INIT(inst_name)
        return self._instance

    def shutdown(self):
        if self._instance:
            self._instance.shutdown("Node %s required shutdown." % gd.name)


class TransportSocketIO:
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignore):
        if not self._instance:
            self._instance = None
        return self._instance


Transports = TransportsProvider()
Transports.register("ROS1", TransportROS1())
Transports.register("Redis", TransportRedis())
Transports.register("Http", TransportHttp())
Transports.register("ROS2", TransportROS2())
Transports.register("SocketIO", TransportSocketIO())


class PortsProvider:
    """Class to help create ports instances"""

    def __init__(self):
        self.debug = False
        self._ports = {}
        self._instances = []
        self._callbacks = {}

    def register(self, key, builder):
        self._ports[key] = builder

    def create(self, key, **kwargs):
        builder = self._ports.get(key)
        if not builder:
            print("ValueError: ", key)
            return None
        inst = builder(**kwargs)
        self._instances.append(inst)
        return inst

    def register_event(self, key, callback):
        self._callbacks[key] = callback

    def on_shutdown(self, **kwargs):
        callback = self._callbacks.get("on_shutdown")
        if callable(callback):
            callback(**kwargs)

    def shutdown(self):
        # disable all callback events
        self._callbacks.clear()
        for instance in self._instances:
            try:
                instance.shutdown()
            except AttributeError as e:
                pass


class IportRos1Sub:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = ROS1.ROS1_Subscriber(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class IportRos1Service:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = ROS1.ROS1_ServiceServer(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        self._instance.unregister("Node %s required shutdown." % gd.name)


class IportRos1Action:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        kwargs["_topic"] = kwargs["_topic"].rpartition("/")[0]
        self._instance = ROS1.ROS1_ActionServer(**kwargs)
        gd.iport[name] = self._instance


class IportRos1ActionClient:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        port = kwargs["_port"]
        self._instance = ROS1.ROS1_Subscriber(**kwargs)
        gd.iport[port + "@" + name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()
            del self._instance


class IportRos1Timer:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        gd.iport[name] = ROS1.ROS1_Timer(**kwargs)


class IportRos1Tf:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = ROS1.ROS1_TFSubscriber(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class IportRos1TopicHz:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = ROS1.ROS1_TopicHz(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class IportVarSub:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        gd.iport[name] = RedisSub.Var_Subscriber(**kwargs)


class IportHttpRoute:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = gd_node.protocols.http.http_route.HttpRoute(**kwargs)
        # gd.oport['reply@' + name] = Http.HttpRouteReply()
        gd.oport["reply@" + name + "/data_in"] = self._instance
        gd.iport[name] = self._instance


class IportWebSocket:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = gd_node.protocols.http.web_socket.WebSocketSub(**kwargs)
        gd.oport["reply@" + name + "/data_in"] = self._instance
        gd.iport[name] = self._instance


class IportMovaiExit:
    def __init__(self, **kwargs):
        self._instance = MovAI.Exit(**kwargs)

    def shutdown(self):
        if self._instance:
            self._instance.execute()


class IportMovaiInit:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = MovAI.Init(**kwargs)
        gd.iport[name] = self._instance


class IportMovaiTransition:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = MovAI.TransitionIn(**kwargs)
        gd.iport[name] = self._instance


class IportMovaiDependency:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        kwargs["update"] = False
        self._instance = Base.BaseIport(**kwargs)
        gd.iport[name] = self._instance


class IportMovaiSM:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = MovAI.StateMachineProtocol(**kwargs)
        gd.iport[name] = self._instance


class IportMovaiContextClient:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = MovAI.ContextClientIn(**kwargs)
        gd.iport[name] = self._instance


class IportMovaiContextServer:
    def __init__(self, **kwargs):
        name = kwargs["_port_name"]
        self._instance = MovAI.ContextServerIn(**kwargs)
        gd.iport[name] = self._instance


class IportRos2Sub:
    def __init__(self, **kwargs):
        import gd_node.protocols.ros2 as ROS2

        name = kwargs["_port_name"]
        self._instance = ROS2.ROS2_Subscriber(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        if self._instance:
            pass
            # self._instance.unregister()


class IportRos2ServiceServer:
    def __init__(self, **kwargs):
        import gd_node.protocols.ros2 as ROS2

        name = kwargs["_port_name"]
        self._instance = ROS2.ROS2_ServiceServer(**kwargs)
        gd.iport[name] = self._instance

    def shutdown(self):
        if self._instance:
            pass
            # self._instance.unregister()


Iport = PortsProvider()
Iport.register("ROS1/Subscriber", IportRos1Sub)
Iport.register("ROS1/Service", IportRos1Service)
Iport.register("ROS1/Action", IportRos1Action)
Iport.register("ROS1/ActionClient", IportRos1ActionClient)
Iport.register("ROS1/Timer", IportRos1Timer)
Iport.register("ROS1/TF", IportRos1Tf)
Iport.register("ROS1/TopicHz", IportRos1TopicHz)
Iport.register("Redis/VarSubscriber", IportVarSub)
Iport.register("AioHttp/Http", IportHttpRoute)
Iport.register("AioHttp/Websocket", IportWebSocket)
Iport.register("MovAI/Exit", IportMovaiExit)
Iport.register("MovAI/Init", IportMovaiInit)
Iport.register("MovAI/Transition", IportMovaiTransition)
Iport.register("MovAI/Dependency", IportMovaiDependency)
Iport.register("MovAI/StateMachine", IportMovaiSM)
Iport.register("MovAI/ContextClientIn", IportMovaiContextClient)
Iport.register("MovAI/ContextServerIn", IportMovaiContextServer)
Iport.register("ROS2/Subscriber", IportRos2Sub)
Iport.register("ROS2/ServiceServer", IportRos2ServiceServer)


class OportRos1Pub:
    def __init__(self, name, topic, message, **_ignore):
        self._instance = ROS1.ROS1_Publisher(topic, message)
        gd.oport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class OportRos1ServiceClient:
    def __init__(self, name, topic, message, **_ignore):
        message = message.rsplit("Request")[0]
        self._instance = ROS1.ROS1_ServiceClient(topic, message)
        gd.oport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class OportRos1ActionClient:
    def __init__(self, name, topic, message, **_ignore):
        _topic, _, port = topic.rpartition("/")

        if port == "goal":
            gd.oport["goal@" + name] = ROS1.ROS1_ActionClient(
                _topic, message.rsplit("Goal")[0]
            )
        if port == "cancel":
            gd.oport["cancel@" + name] = ROS1.ROS1_Publisher(topic, message)


class OportRos1DynReconfigure:
    def __init__(self, name, topic, message, **_ignore):
        self._instance = ROS1.ROS1_DynReconfigure(topic, message)
        gd.oport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class OportRos1Tf:
    def __init__(self, name, topic, message, _params, **_ignore):
        self._instance = ROS1.ROS1_TFBroadcaster(topic, message, _params)
        gd.oport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class OportRos1Parameter:
    def __init__(self, name, topic, message, _params, **_ignore):
        self._instance = ROS1.ROS1_Parameter(topic, message, _params)
        gd.oport[name] = self._instance


class OportRos1Bag:
    def __init__(self, name, topic, message, **_ignore):
        self._instance = ROS1.ROS1_Bag(topic, message)
        gd.oport[name] = self._instance

    def shutdown(self):
        if self._instance:
            self._instance.unregister()


class OportRos2Pub:
    def __init__(self, name, topic, message, _params, **_ignore):
        import gd_node.protocols.ros2 as ROS2

        self._instance = ROS2.ROS2_Publisher(topic, message)
        gd.oport[name] = self._instance


class OportRos2ServiceClient:
    def __init__(self, name, topic, message, _params, **_ignore):
        import gd_node.protocols.ros2 as ROS2

        self._instance = ROS2.ROS2_ServiceClient(topic, message)
        gd.oport[name] = self._instance


class OportMovaiContextClient:
    def __init__(self, node_name, name, topic, message, _params, **_ignore):
        gd.oport[name] = MovAI.ContextClientOut(node_name, name, _params)


class OportMovaiContextServer:
    def __init__(self, node_name, name, topic, message, _params, **_ignore):
        gd.oport[name] = MovAI.ContextServerOut(node_name, name, _params)


class OportMovaiTransition:
    def __init__(self, name, node_name, flow_name, **_ignore):
        gd.oport[name] = MovAI.Transition(node_name, name, flow_name)


class OportMovaiDepends:
    def __init__(self, name, node_name, **_ignore):
        gd.oport[name] = Base.BaseOport()


Oport = PortsProvider()
Oport.register("ROS1/Publisher", OportRos1Pub)
Oport.register("ROS1/Service", OportRos1ServiceClient)
Oport.register("ROS1/Action", OportRos1ActionClient)
Oport.register("ROS1/Reconfigure", OportRos1DynReconfigure)
Oport.register("ROS1/Bag", OportRos1Bag)
Oport.register("ROS1/TF", OportRos1Tf)
Oport.register("ROS1/ParameterServer", OportRos1Parameter)
Oport.register("MovAI/Transition", OportMovaiTransition)
Oport.register("MovAI/Depends", OportMovaiDepends)
Oport.register("MovAI/ContextClientOut", OportMovaiContextClient)
Oport.register("MovAI/ContextServerOut", OportMovaiContextServer)
Oport.register("ROS2/Publisher", OportRos2Pub)
Oport.register("ROS2/ServiceClient", OportRos2ServiceClient)


class Params(object):

    """Makes GD_Node parameters accessible in all callbacks

    Args:
        _name: Name of the parameter
        _value: Value of the parameter
    """

    def __init__(self, _name: str, _value: Any) -> None:
        """Init"""
        gd.params[_name] = _value
