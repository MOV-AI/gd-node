import uuid

from movai_core_shared.consts import DEFAULT_CALLBACK

from dal.models.widget import Widget

from gd_node.protocols.http import LOGGER


class MovaiWidget(object):
    def __init__(self, name, uid, _type="widgets"):
        self.name = name
        self.type = _type
        try:
            self.obj = Widget(self.name)
        except Exception as e:
            LOGGER.error(
                "COULD NOT GET WIDGET OBJECT, ARE YOU SURE THIS WIDGET EXISTS? %s", e
            )
            self.obj = None
        if uid:
            self.uid = uid
        else:
            self.uid = uuid.uuid4().hex

    def is_supported(self, node, user=None):
        node_test = None
        supported = False
        templates = ["widget", "MovAI/WidgetAio"]
        try:
            node_test = Node(node)
        except Exception as e:
            LOGGER.error("is_supported %s", e)
            return supported

        try:
            for ports_inst in node_test.PortsInst:
                if (
                    ports_inst == self.name
                    and node_test.PortsInst[ports_inst].Template in templates
                ):
                    supported = {
                        "main": {
                            "callback": node_test.PortsInst[ports_inst]
                            .In["data_in"]
                            .Callback,
                            "message": node_test.PortsInst[ports_inst]
                            .In["data_in"]
                            .Message,
                        },
                        "listener": {"callback": False, "message": []},
                        "name": self.name,
                        "general": self.get_general(),
                        "settings": self.user_settings(user),
                    }
                    if "sub" in node_test.PortsInst[ports_inst].In:
                        if (
                            not node_test.PortsInst[ports_inst].In["sub"].Callback
                            == DEFAULT_CALLBACK
                        ):
                            supported["listener"]["callback"] = (
                                node_test.PortsInst[ports_inst].In["sub"].Callback
                            )
                        supported["listener"]["message"] = (
                            node_test.PortsInst[ports_inst].In["sub"].Message
                        )

                    supported["parameters"] = self.get_defaults()
                    break
        except Exception as e:
            LOGGER.error("is_supported %s", e)
        return supported

    def user_settings(self, user):
        parameters = {}
        if user:
            try:
                user_db = User(user)
                if self.name in user_db.Application:
                    instance = user_db.Application[self.name]
                    if hasattr(instance, "Parameter"):
                        for key in instance.Parameter:
                            LOGGER.debug(
                                "THE USER PARAMETER %s %s %s",
                                key,
                                user,
                                instance.Parameter[key].Value,
                            )
                            parameters[key] = instance.Parameter[key].Value
            except Exception as e:
                LOGGER.error("user_settings %s", e)
        return parameters

    def get_general(self):
        to_return = {}
        try:
            ref_map = {
                "applications": {
                    "class": Layout,
                    "fields": {"Icon": "icon", "Info": "description"},
                },
                "widgets": {
                    "class": Widget,
                    "fields": {"Icon": "icon", "Info": "description"},
                },
            }
            ref_obj = ref_map[self.type]
            ref_class = ref_obj["class"](self.name)
            for field in ref_obj["fields"]:
                to_return[ref_obj["fields"][field]] = getattr(ref_class, field)
        except Exception as e:
            LOGGER.error(e)
        return to_return

    def get_defaults(self):
        to_return = []

        if self.obj:
            for key in self.obj.Parameter:
                to_return.append(
                    {
                        "value": self.obj.Parameter[key].Value,
                        "type": self.obj.Parameter[key].Type,
                        "name": key,
                    }
                )
        else:
            LOGGER.error("Widget object could not be found!")
        return to_return
