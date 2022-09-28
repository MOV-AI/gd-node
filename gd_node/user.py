"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

    Module to store and give access to GD_Node
    Iports, Oports and Parameters during runtime
"""
from gd_node.shared import Shared


class GD_User:

    """User class

    Attributes:
        iport (dict): Input ports of the node
        name (str): Name of the node instance
        oport (dict): Output ports of the node
        params (dict): Parameters of the node instance
    """

    name = ""
    template = ""
    iport = {}
    oport = {}
    params = {}
    shared = Shared()

    @classmethod
    def send(cls, port, msg=""):
        """Making send function easy to write"""
        cls.oport[port].send(msg)
