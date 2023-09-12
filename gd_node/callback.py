"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020
"""
import copy
import importlib
import time
from typing import Any
from os import getenv

from movai_core_shared.logger import Log, LogAdapter
from movai_core_shared.exceptions import DoesNotExist, TransitionException
from movai_core_shared.consts import USER_LOG_TAG

# Imports from DAL

from dal.movaidb import MovaiDB
from dal.models.callback import Callback

from dal.models.lock import Lock
from dal.models.container import Container
from dal.models.nodeinst import NodeInst
from dal.scopes.package import Package
from dal.models.ports import Ports
from dal.models.var import Var
from dal.models.scopestree import ScopesTree, scopes

from dal.scopes.configuration import Configuration
from dal.scopes.fleetrobot import FleetRobot
from dal.scopes.message import Message
from dal.scopes.robot import Robot
from dal.scopes.statemachine import StateMachine, SMVars

from gd_node.user import GD_User as gd

try:

    from movai_core_enterprise.message_client_handlers.alerts import Alerts
    from movai_core_enterprise.models.annotation import Annotation
    from movai_core_enterprise.models.graphicasset import GraphicAsset
    from movai_core_enterprise.models.graphicscene import GraphicScene
    from movai_core_enterprise.models.layout import Layout
    from movai_core_enterprise.scopes.task import Task
    from movai_core_enterprise.models.taskentry import TaskEntry
    from movai_core_enterprise.models.tasktemplate import TaskTemplate
    from movai_core_enterprise.message_client_handlers.metrics import Metrics

    enterprise = True
except ImportError:
    enterprise = False

LOGGER = LogAdapter(Log.get_logger("spawner.mov.ai"))


class GD_Callback:
    """Callback class used by GD_Node to execute code

    Args:
        _cb_name: The name of the callback
        _node_name: The name of the node instance
        _port_name: The name of the input port
        _update: Real time update of the callback code
    """

    _robot = None
    _scene = None

    def __init__(
        self, _cb_name: str, _node_name: str, _port_name: str, _update: bool = False
    ) -> None:
        """Init"""
        self.name = _cb_name
        self.node_name = _node_name
        self.port_name = _port_name
        self.updated_globals = {}

        self.callback = ScopesTree().from_path(_cb_name, scope="Callback")

        self.compiled_code = compile(self.callback.Code, _cb_name, "exec")
        self.user = UserFunctions(
            _cb_name,
            _node_name,
            _port_name,
            self.callback.Py3Lib,
            self.callback.Message,
        )
        self.count = 0

        self._debug = eval(getenv("DEBUG_CB", "False"))

    def execute(self, msg: Any = None) -> None:
        """Executes the code

        Args:
            msg: Message received in the callback
        """

        self.user.globals.update({"msg": msg})
        self.user.globals.update({"count": self.count})
        globais = copy.copy(self.user.globals)
        self.start(self.compiled_code, globais)
        self.count += 1
        self.updated_globals = globais
        if (
            "response" in globais
            and isinstance(globais["response"], dict)
            and "status_code" in globais["response"]
        ):
            self.updated_globals["status_code"] = globais["response"]["status_code"]

    def start(self, code, globais):
        """Executes the code

        Args:
            msg: Message received in the callback
        """
        try:
            t_init = time.perf_counter()
            if self._debug:
                import linecache

                linecache.cache[self.name] = (
                    len(self.callback.Code),
                    None,
                    self.callback.Code.splitlines(True),
                    self.name,
                )
            exec(code, globais)
            t_delta = time.perf_counter() - t_init
            if t_delta > 0.5:
                LOGGER.info(
                    f"{self.node_name}/{self.port_name}/{self.callback.Label} took: {t_delta}"
                )
        except TransitionException:
            LOGGER.debug("Transitioning...")
            gd.is_transitioning = True
        except Exception as e:
            LOGGER.error(str(e), node=self.node_name, callback=self.name)


class UserFunctions:
    """Class that provides functions to the callback execution"""

    def __init__(
        self,
        _cb_name: str,
        _node_name: str,
        _port_name: str,
        _libraries: list,
        _message: str,
        _user="SUPER",
    ) -> None:
        """Init"""

        self.globals = {"gd": gd, "run": self.run}
        self.cb_name = _cb_name
        self.node_name = _node_name
        # self.globals['redis_sub'] = GD_Message('movai_msgs/redis_sub', _type='msg').get()

        for lib in _libraries:
            try:
                mod = importlib.import_module(_libraries[lib].Module)
                try:
                    self.globals[lib] = getattr(mod, _libraries[lib].Class)
                except TypeError:  # Class is not defined
                    self.globals[lib] = mod
            except Exception as e:
                raise Exception(
                    f"Import {lib} in callback {_cb_name} of node {_node_name} was not found"
                ) from e

        if GD_Callback._robot is None:
            GD_Callback._robot = Robot()

        _robot_id = GD_Callback._robot.name

        if GD_Callback._scene is None:
            scene_name = GD_Callback._robot.Status.get("active_scene")
            if scene_name:
                try:
                    GD_Callback._scene = scopes.from_path(scene_name, scope="GraphicScene")
                except:
                    LOGGER.error(f'Scene "{scene_name}" was not found')

        class UserVar(Var):
            """Class for user to set and get vars"""

            def __init__(self, scope: str = "Node", robot_name=_robot_id):
                super().__init__(
                    scope=scope,
                    _robot_name=robot_name,
                    _node_name=_node_name,
                    _port_name=_port_name,
                )

        class UserLock(Lock):
            """Class for user to use locks"""

            def __init__(self, name, **kwargs):
                kwargs.update({"_node_name": _node_name, "_robot_name": _robot_id})
                super().__init__(name, **kwargs)

        class UserSM(SMVars):
            """Class for user to set and get state machine vars"""

            sm_ports = None

            def __init__(self, sm_name: str):
                if UserSM.sm_ports is None:
                    UserSM.sm_ports = {}
                    sm_ports_dict = MovaiDB().search(
                        {
                            "Node": {
                                gd.template: {
                                    "PortsInst": {"*": {"Template": "MovAI/StateMachine"}}
                                }
                            }
                        }
                    )
                    for port in sm_ports_dict:
                        for name in MovaiDB().keys_to_dict([(port, "")])["Node"][gd.template][
                            "PortsInst"
                        ]:
                            sm_params = MovaiDB().get_hash(
                                {
                                    "Node": {
                                        gd.template: {
                                            "PortsInst": {name: {"In": {"in": {"Parameter": ""}}}}
                                        }
                                    }
                                },
                                search=False,
                            )
                            sm_id = sm_params.get("StateMachine", "random_id")
                            UserSM.sm_ports.update({name: sm_id})

                sm_id = UserSM.sm_ports.get(sm_name)
                if not sm_id:
                    raise DoesNotExist("State Machine %s not found for this node" % sm_name)
                super().__init__(_sm_name=sm_id, _node_name=_node_name)

        if _user == "SUPER":
            logger = Log.get_callback_logger("GD_Callback", self.node_name, self.cb_name)
            self.globals.update(
                {
                    "scopes": scopes,
                    "Package": Package,
                    "Message": Message,
                    "Ports": Ports,
                    "StateMachine": StateMachine,  # TODO implement model
                    "Var": UserVar,
                    "Robot": GD_Callback._robot,
                    "FleetRobot": FleetRobot,
                    "logger": logger,
                    "PortName": _port_name,
                    "SM": UserSM,
                    "Callback": Callback,
                    "Lock": UserLock,
                    "print": self.user_print,
                    "Scene": GD_Callback._scene,
                    "NodeInst": NodeInst,
                    "Container": Container,
                    "Configuration": Configuration,
                }
            )
            if enterprise:
                metrics = Metrics()
                self.globals.update(
                    {
                        "Alerts": Alerts,
                        "Annotation": Annotation,
                        "GraphicAsset": GraphicAsset,
                        "GraphicScene": GraphicScene,
                        "Layout": Layout,
                        "metrics": metrics,
                        "Task": Task,
                        "TaskEntry": TaskEntry,
                        "TaskTemplate": TaskTemplate,
                    }
                )

    def user_print(self, *args):
        """Method to redirect the print function into logger"""
        to_send = " ".join([str(arg) for arg in args])
        LOGGER.debug(to_send, node=self.node_name, callback=self.cb_name)

    def run(self, cb_name, msg):
        """Run another callback from a callback"""
        callback = scopes.from_path(cb_name, scope="Callback")
        compiled_code = compile(callback.Code, cb_name, "exec")
        user = UserFunctions("", "", "", callback.Py3Lib, callback.Message)

        user.globals.update({"msg": msg})
        globais = user.globals

        exec(compiled_code, globais)
