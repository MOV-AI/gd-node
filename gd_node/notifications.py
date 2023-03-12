"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Moawiya Mograbi (moawiya@mov.ai) - 2023

    An interface to notification of Message Server
"""


from movai_core_shared.core.message_client import MessageClient
from movai_core_shared.envvars import MESSAGE_SERVER_BIND_ADDR
from movai_core_shared.consts import NOTIFICATIONS_HANDLER_MSG_TYPE
import jsonpickle


class Notify:
    """Message Server Notifications Handler interface"""

    @classmethod
    def email(self, recipients: list, body: str, subject: str = "", attachment: str = ""):
        """sends an email through Message Server client, by sending smtp
        notification to the MessageServer with the needed information
        using zmq socket (MessageClient)

        Arguments:
            - recipients(list): list includes the recipients emails that we want
                                to send to.
            - body(str): the body of the email.
            - subject(str): the subject of the email.
            - attachment(str): path of the zip attachment we want to send.
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

        client = MessageClient(MESSAGE_SERVER_BIND_ADDR)
        client.send_request(NOTIFICATIONS_HANDLER_MSG_TYPE, data)
