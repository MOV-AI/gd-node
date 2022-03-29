"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

    Module that implements specific Mov.AI protocol to deal with GD_Nodes
"""
import asyncio


from common_general.api.exceptions import TransitionException
from common_general.api.core.database import MovaiDB
from common_general.api.core.redis import RedisClient
from common_general.api.models.robot import Robot
from ..statemachine import SMVars, StateMachine
from ..callback import GD_Callback as Callback
from ..user import GD_User
from common_general.logger import StdoutLogger
from .base import BaseIport

LOGGER = StdoutLogger("spawner.mov.ai")

class Init(BaseIport):

    """Class that implements the init callback of the GD_Node

    Args:
            _node_name: Name of the node instance
            _iport_name: Name of the port
            _cb_name: Name of the callback to be executed
    """

    def __init__(self, _node_name: str, _port_name: str, _callback: str, **_ignore)-> None:
        """Init
        """
        super().__init__(_node_name, _port_name, None, None, _callback, False)
        self.register()
        self.callback('')

class Exit(BaseIport):

    """Class that implements the exit callback of the GD_Node

    Args:
            _node_name: Name of the node instance
            _iport_name: Name of the port
            _cb_name: Name of the callback to be executed
    """
    def __init__(self, _node_name: str, _port_name: str, _topic: str,
                 _message: str, _callback: str, **_ignore):
        """Init
        """
        super().__init__(_node_name, _port_name, _topic, _message, _callback, False)

    def execute(self):
        """Executes exit callback"""
        self.callback('')

        #deletes all vars
        #Var.delete_all(scope='Node', _node_name=GD_User.name)
        #for iport in GD_User.iport:
        #    Var.delete_all(scope='Callback', _node_name=GD_User.name, _port_name=iport)

    def unregister(self):
        pass


class StateMachineProtocol(BaseIport):
    """Class that implements a state machine inside a GD_Node"""

    def __init__(self, _node_name: str, _port_name: str, _topic: str,
                 _message: str, _callback: str, _params: dict, **_ignore):

        super().__init__(_node_name, _port_name, _topic, _message, _callback, False)

        self.current_state = None
        sm_id = _params.get('StateMachine', 'random_id')
        #sm_id = GD_User.params.get('movai_statemachine_name', 'random_id')

        print('')
        print('Initializing State Machine "%s":'%sm_id)

        self.sm_var = SMVars(_sm_name=sm_id, _node_name=_node_name)

        #instantiate all states in the sm and map them to callbacks to be executed
        state_machine = StateMachine(sm_id).get_dict()

        self.states = {}
        for state in state_machine['StateMachine'][sm_id]['State']:
            cb_name = state_machine['StateMachine'][sm_id]['State'][state].get('Callback', 'place_holder')
            callback = Callback(cb_name, _node_name, _port_name, True)
            callback.user.globals.update({"send": self.change_state})

            #Add parameters to Callback
            for param, value in state_machine['StateMachine'][sm_id]['State'][state].get('Parameter',{}).items():
                callback.user.globals.update({param: value['Value']})

            self.states.update({state: callback})
            print('\tState "%s" with callback "%s"'%(state, cb_name))

        self.transitions = {}
        #links = self.cache_dict["StateMachine"][self.name].get("Links", {})
        for link in state_machine['StateMachine'][sm_id]['Link']:
            link_from = state_machine['StateMachine'][sm_id]['Link'][link]['From']
            link_to = state_machine['StateMachine'][sm_id]['Link'][link]['To']
            link_to = link_to.split('/')[0]
            self.transitions.update({link_from: link_to})
            print('\tLink from "%s" to "%s"'%(link_from, link_to))

        #set the first state acording to start
        self.set_state(self.transitions.get('start/start/start')) #__start

        print('\tInitial state is:', self.current_state)
        self.sm_var.CURRENT_STATE = self.current_state

        #create a redis subscriber to the sm hash key
        self.loop = asyncio.get_event_loop()
        sub_dict = {'Name':'node', 'ID':_node_name + '@' + sm_id, 'Parameter':'*'}
        self.loop.create_task(self.register_sub(self.loop, 'Var', self.callback, **sub_dict))

        #TODO Possible minimum rate implemented with timer

    async def register_sub(self, loop, scope, callback, **sub_dict):
        databases = await RedisClient.get_client()
        MovaiDB(db='local', loop=loop, databases=databases).subscribe_by_args(scope, callback, **sub_dict)

    def callback(self, msg)-> None: #the redis subscriber callback
        """Executes the callback if port is enabled"""
        if self.enabled:
            self.run()

    def change_state(self, port):
        """Change from current state to next one according to port called"""
        new_state = self.transitions.get(self.current_state + '/' + port + '/out')
        if new_state:
            print('Called exit "%s", transitioning to state "%s"'%(port, new_state))
            self.set_state(new_state)
        else:
            print('Exit port "%s" from state "%s" does not exist or is unconnected'%(port, self.current_state))
            #raise DoesNotExist('Called exit port %s from state %s does not exist or is unconnected'%(port, self.current_state))

    def run(self):
        """Executes the callback of the current state"""
        if self.enabled:
            self.states.get(self.current_state).execute('')

    def set_state(self, state):
        """Sets the current state"""
        self.current_state = state
        self.sm_var.CURRENT_STATE = state #this will trigger the execution

    def get_state(self):
        """Returns the current state"""
        return self.current_state

class TransitionIn(BaseIport):

    """Class that implements the transition callback of the state GD_Node

    Args:
            _node_name: Name of the node instance
            _iport_name: Name of the port
            _cb_name: Name of the callback to be executed
    """

    def __init__(self, _node_name: str, _port_name: str, _callback: str, _data, **_ignore)-> None:
        """Init
        """
        super().__init__(_node_name, _port_name, None, None, _callback, False)
        self.register()
        self.callback(_data)


class Transition:

    """

    Method for changing between GD_Nodes

    Args:
            _node_name: Name of the node instance
            _oport_name: Name of the port

    """

    def __init__(self, _node_name: str, _oport_name: str, _flow_name: str)-> None:
        """Init"""
        self.robot = Robot()
        self.node_name = _node_name
        self.port_name = _oport_name
        self.flow_name = _flow_name

    def send(self, msg=None)->None:
        """Send function"""

        self.robot.send_cmd(command='TRANS', node=self.node_name, port=self.port_name,
            data=msg, flow=self.flow_name)

        for iport in GD_User.iport:
            try:
                GD_User.iport[iport].unregister()
            except AttributeError:
                pass
        raise TransitionException

class ContextMsg:
    """Message for Context
        data -> dictionary of full context table
        changed -> dictionary only of values changed
    """
    def __init__(self, id={}, data={}, changed={}):
        self.data = data
        self.changed = changed
        self.id = id

class ContextClientIn(BaseIport):

    """Class that implements the Client Context comunication in the GD_Node
       Is subscribed to a redis hash (param)

    Args:
            _node_name: Name of the node instance
            _iport_name: Name of the port
            _cb_name: Name of the callback to be executed
    """
    def __init__(self, _node_name: str, _port_name: str, _topic: str,
                 _message: str, _callback: str, _params: dict, _update: bool, **_ignore):
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update)

        self.stack = _params.get('Namespace', '')

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.register_sub())

    async def register_sub(self) -> None:
        """Subscribe to key."""
        pattern = {'Var':{'context':{'ID':{self.stack+'_TX':{'Parameter':'**'}}}}}
        databases = await RedisClient().get_client()
        await MovaiDB('local', loop=self.loop, databases=databases).subscribe_channel(pattern, self.callback)

    def callback(self, msg):
        """Executes callback"""
        key = msg[0].decode('utf-8')
        changed_fields = list(msg[1].split(' '))

        dict_key = MovaiDB().keys_to_dict([(key, '')])
        full_table = MovaiDB('local').get_hash(dict_key)

        changed = {item:full_table[item] for item in changed_fields}

        _id = full_table.pop('_id')
        changed.pop('_id')

        msg = ContextMsg(id=_id, data=full_table, changed=changed)
        super().callback(msg)

class ContextServerIn(BaseIport):

    """Class that implements the Server Context comunication in the GD_Node
       Is subscribed to a redis hash (param)

    Args:
            _node_name: Name of the node instance
            _iport_name: Name of the port
            _cb_name: Name of the callback to be executed
    """
    def __init__(self, _node_name: str, _port_name: str, _topic: str,
                 _message: str, _callback: str, _params: dict, _update: bool, **_ignore):
        """Init"""
        super().__init__(_node_name, _port_name, _topic, _message, _callback, _update)

        self.stack = _params.get('Namespace', '')

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.register_sub())

    async def register_sub(self) -> None:
        """Subscribe to key."""
        pattern = {'Var':{'context':{'ID':{self.stack+'_RX':{'Parameter':'**'}}}}}
        databases = await RedisClient().get_client()
        await MovaiDB('local', loop=self.loop, databases=databases).subscribe_channel(pattern, self.callback)

    def callback(self, msg):
        """Executes callback"""
        key = msg[0].decode('utf-8')
        changed_fields = list(msg[1].split(' '))

        dict_key = MovaiDB().keys_to_dict([(key, '')])
        full_table = MovaiDB('local').get_hash(dict_key)

        changed = {item:full_table[item] for item in changed_fields}

        _id = full_table.pop('_id')
        changed.pop('_id')

        msg = ContextMsg(id=_id, data=full_table, changed=changed)
        super().callback(msg)


class ContextClientOut:
    """Class that implements Client Context comunication in the GD_Node"""

    def __init__(self, _node_name: str, _oport_name: str, _params: dict)-> None:
        """Init"""

        self.stack = _params.get('Namespace', '')
        self._node_name = _node_name

    def send(self, msg):
        """Send function"""

        if not isinstance(msg, dict):
            raise Exception('Wrong message type, this should be a dictionary')

        msg.update({'_id': self._node_name})
        to_send = {'Var':{'context':{'ID':{self.stack+'_RX':{'Parameter':msg}}}}}
        MovaiDB('local').hset_pub(to_send)

class ContextServerOut:
    """Class that implements Client Context comunication in the GD_Node"""

    def __init__(self, _node_name: str, _oport_name: str, _params: dict)-> None:
        """Init"""
        self.stack = _params.get('Namespace', '')
        self._node_name = _node_name

    def send(self, msg):
        """Send function"""

        if not isinstance(msg, dict):
            raise Exception('Wrong message type, this should be a dictionary')
        msg.update({'_id': self._node_name})
        to_send = {'Var':{'context':{'ID':{self.stack+'_TX':{'Parameter':msg}}}}}
        MovaiDB('local').hset_pub(to_send)

#RX TX Transmit FROM this server, and Receive TO this server.
