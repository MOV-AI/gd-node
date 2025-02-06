from dal.utils.callback import Callback, UserFunctions
from dal.scopes.statemachine import SMVars
from dal.movaidb import MovaiDB

from movai_core_shared.exceptions import DoesNotExist

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


class GD_Callback(Callback):
    def set_transitioning(self):
        gd.is_transitioning = True


class GD_UserFunctions(UserFunctions):
    def load_classes(self, _node_name, _port_name, _user):
        # Enhance the globals environment with gd-node and
        # movai-core-enterprise classes
        super().load_classes(_node_name, _port_name, _user)

        self.globals["gd"] = gd

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
            self.globals["SM"] = UserSM
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
