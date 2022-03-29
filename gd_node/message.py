"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020
"""
import re
import sys
import importlib
from typing import Any
from common_general.api.models.message import Message
from common_general.envvars import ROS2_PATH

ROS2_ONLY_ATTR = 'SLOT_TYPES' #Check in future updates

class GD_Message:

    """
    Class that imports and make available all Messages, Services
    and Actions for the GD_Node

    Args:
        _name: package/message_name
        _type: Available types are: msg, srv, action

    Raises:
        Exception: Message does not exist
    """

    def __init__(self, _name: str, _type='msg'): #_name includes _package for simplicity
        """Init
        """
        self.m = self.m_req = self.m_resp = None
        # it is has more than 1 '/', it shall blow
        module, name = _name.split('/')
        try:
            mod_obj = importlib.import_module(f"{module}.{_type}._{name}")
            self.m = getattr(mod_obj, name)
        except (ModuleNotFoundError, AttributeError):
            try:
                mod_obj = Message(module)
                msg = mod_obj.Msg[name]
                locals_dict = dict()
                exec(msg.Compiled, globals(), locals_dict)
                self.m = locals_dict[name]
                # also for services
                try:
                    self.m_req = locals_dict[name+'Request']
                    self.m_resp = locals_dict[name+'Response']
                except KeyError:
                    pass
            except Exception as e:   # pylint: disable=broad-except
                raise FileNotFoundError("Message does not exist") from e

    def get(self):
        """
        Method that returns the message

        Returns:
            TYPE: Any
        """
        return self.m

    def get_srv(self):
        """
        Method that returns the full service

        Returns:
            TYPE: Any
        """
        return self.m, self.m_req, self.m_resp


class GD_Message2:

    """
    Class that makes available all Messages and Services from ROS1, ROS2 and Redis to the GD_Node

    Args:
        _name: package/message_name
        _type: Available types are: msg, srv, action

    Raises:
        Exception: Message does not exist
    """

    def __init__(self):
        """Init"""

        self.ros_time_types = ['time', 'duration']
        self.ros_primitive_types = ['bool', 'byte', 'char', 'int8', 'uint8', 'int16',
                                    'uint16', 'int32', 'uint32', 'int64', 'uint64',
                                    'float32', 'float64', 'string']
        self.ros_header_types = ['Header', 'std_msgs/Header', 'roslib/Header']
        self.ros_binary_types_regexp = re.compile(r'(uint8|char)\[[^\]]*\]')
        self.list_brackets = re.compile(r'\[[^\]]*\]')


    def get_ros1_msg(self, _input: Any)->Any:
        """Returns a Ros1 msg class"""
        pass

    def get_ros1_srv(self):
        pass

    def get_ros2_msg(self, _input: Any)->Any:
        """Returns a Ros2 msg class. Accepts string with package/message
           and ROS1/ROS2 message class instance"""

        if isinstance(_input, str):
            pass
            #do the import
            return ''

        if hasattr(_input, ROS2_ONLY_ATTR):
            #its already a ros2 msg so just return it
            return _input

        #its a ros1 msg
        #ros1_msg_class = self._import_ros1_msg(_input._type) #wrong

        ros2_msg_class = self._import_ros2_msg(_input._type)

        return self._ros1_to_ros2(_input, ros2_msg_class())

    def get_ros2_srv(self, _input: Any)->Any:
        """Returns a Ros2 srv class. Accepts string with package/service
           and ROS1/ROS2 service Request/Responce class instance"""

        if isinstance(_input, str):
            return self._import_ros2_srv(_input)

        #Request and Response
        ros2_msg_class = self._import_ros2_srv(_input._type)
        return self._ros1_to_ros2(_input, ros2_msg_class())

    def _import_ros1_msg(self, _input: str):
        """Imports and returns a Ros1 message class"""
        module, msg_name = _input.split('/')
        vars()['msg_mod'] = importlib.import_module(module +'.msg._'+ msg_name)
        message_class = getattr(msg_mod, msg_name)
        return message_class

    def _import_ros2_msg(self, _input: str):
        """Imports and returns a Ros2 message class"""
        module, msg_name = _input.split('/')

        path_backup = sys.path
        msg_mod = importlib.import_module(module) #Try with vars only

        sys.path.insert(1, ROS2_PATH)

        importlib.reload(msg_mod)
        importlib.reload(msg_mod.msg)

        message_class = getattr(msg_mod.msg, msg_name)

        sys.path = path_backup
        return message_class

    def _import_ros2_srv(self, _input: str):
        """Imports and returns a Ros2 service class"""
        module, srv_name = _input.split('/')

        path_backup = sys.path
        msg_mod = importlib.import_module(module)
        msg_mod_srv = importlib.import_module(module+'.srv')

        sys.path.insert(1, ROS2_PATH)

        importlib.reload(msg_mod)
        importlib.reload(msg_mod_srv)

        if _input.endswith('Request'):
            main_class = getattr(msg_mod_srv, srv_name.rsplit('Request', 1)[0])
            message_class = getattr(main_class, 'Request')

        elif _input.endswith('Response'):
            main_class = getattr(msg_mod_srv, srv_name.rsplit('Response', 1)[0])
            message_class = getattr(main_class, 'Response')
        else:
            message_class = getattr(msg_mod_srv, srv_name)

        sys.path = path_backup
        return message_class


    def _ros1_to_ros2(self, ros1_msg, ros2_msg):
        """Passses the elements of a Ros1 message class to a Ros2 message class"""
        message_fields = zip(ros1_msg.__slots__, ros1_msg._slot_types)
        for field_name, field_type in message_fields:
            field_value = getattr(ros1_msg, field_name)

            #TODO test Byte special case missing, need example

            if field_type in self.ros_time_types: #Time
                #sec, nanosec in ros2...
                setattr(getattr(ros2_msg, field_name), 'secs', getattr(field_value, 'secs'))
                setattr(getattr(ros2_msg, field_name), 'nsecs', getattr(field_value, 'nsecs'))

            elif field_type in self.ros_primitive_types:
                ros2_msg_type = type(getattr(ros2_msg, field_name))
                setattr(ros2_msg, field_name, ros2_msg_type(field_value))

            elif self.list_brackets.search(field_type) is not None: #List
                setattr(ros2_msg, field_name, field_value)

            else:
                self._ros1_to_ros2(field_value, getattr(ros2_msg, field_name))

        return ros2_msg

    def _ros2_to_ros1(self, ros2_msg, ros1_msg):
        """Passses the elements of a Ros2 message class to a Ros1 message class"""
        message_fields = ros2_msg.get_fields_and_field_types() #returns a dict
        for field_name, field_type in message_fields.items():
            field_value = getattr(ros2_msg, field_name)
