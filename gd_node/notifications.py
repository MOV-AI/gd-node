"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Moawiya Mograbi (moawiya@mov.ai) - 2023

    An interface to notification of Message Server
"""


from movai_core_shared.core.message_client import MessageClient
from movai_core_shared.common.utils import is_manager
from movai_core_shared.consts import NOTIFICATIONS_HANDLER_MSG_TYPE
import re
import jsonpickle
from movai_core_shared.envvars import (
    MESSAGE_SERVER_LOCAL_ADDR,
    MESSAGE_SERVER_REMOTE_ADDR,
)
from dal.scopes.robot import Robot


# to make it an instance
def _inst(c):
    return c()


@_inst
class Notify:
    """Message Server Notifications Handler interface"""

    def __init__(self, path="/"):

        # remove multiple '/' together
        self._robot_id = Robot().name
        self._path = re.sub(r"/{2,}", r"/", path)
        self._local_client = MessageClient(MESSAGE_SERVER_LOCAL_ADDR, self._robot_id)
        if is_manager():
            self._remote_client = self._local_client
        else:
            self._remote_client = MessageClient(MESSAGE_SERVER_REMOTE_ADDR, self._robot_id)

    def email(self, recipients: list, body: str, subject: str = "", attachment: str = "", **kwargs):
        """sends an email through Message Server client, by sending smtp
        notification to the MessageServer with the needed information
        using zmq socket (MessageClient)

        Arguments:
            - recipients(list): list includes the recipients
                                emails that we want to send to.
            - body(str): the body of the email.
            - subject(str): the subject of the email.
            - attachment(str): path of the zip attachment we want to send.
            - kwargs: added in order to support old HealthNode functionality (will be deprecated)
        """
        attachment_data = ""
        if attachment:
            with open(attachment, "rb") as f:
                attachment_data = jsonpickle.encode(f.read())

        data = {
            "notification_type": "smtp",
            "recipients": recipients,
            "subject": subject,
            "body": body,
            "attachment_data": attachment_data,
        }

        return self._remote_client.send_request(NOTIFICATIONS_HANDLER_MSG_TYPE, data)

    # Notify['/path/to/endpoint']
    def __getitem__(self, item):
        if not isinstance(item, str):
            raise TypeError("key should be should be a str")

        return self.__class__(self._path + "/" + item)

    def post(self, **kwargs):
        if self._path.split("/")[-1] == "smtp":
            if "message" in kwargs:
                kwargs.update({"body": kwargs["message"]})
            return self.email(**kwargs)
        return {"result": "unsupported notification type"}

    # Notify.path.to.endpoint
    def __getattr__(self, attr):
        return self.__class__(self._path + "/" + attr)
