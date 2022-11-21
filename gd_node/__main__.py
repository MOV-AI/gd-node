#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Manuel Silva (manuel.silva@mov.ai) - 2020
   - Tiago Paulino (tiago@mov.ai) - 2020

    This is the GD_Node
"""
import argparse
from gd_node.node import GDNode


def main():
    parser = argparse.ArgumentParser(description="Launch GD_Node")
    parser.add_argument(
        "-n", "--name", help="GD_Node template name", type=str, required=True, metavar=""
    )
    parser.add_argument(
        "-i", "--inst", help="GD_Node instance name", type=str, required=True, metavar=""
    )
    parser.add_argument(
        "-p",
        "--params",
        help='GD_Node instance parameters "param_name:=param_value,..."',
        type=str,
        metavar="",
    )
    parser.add_argument(
        "-f", "--flow", help="Flow name where GD_Node is running", type=str, metavar=""
    )
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    parser.add_argument("-m", "--message", help="Message to pass to state", type=str, metavar="")
    parser.add_argument(
        "-d",
        "--develop",
        help="Development mode enables real-time callback update",
        action="store_true",
    )

    ARGS, UNKNOWN = parser.parse_known_args()

    GDNode(ARGS, UNKNOWN)


if __name__ == "__main__":
    main()
