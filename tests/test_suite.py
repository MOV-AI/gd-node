from threading import Thread
from unittest.mock import MagicMock, patch
import unittest
import time
import os

from dal.utils.redis_mocks import fake_redis, FakeAsyncPool

test_dir = os.path.dirname(__file__)


@patch("gd_node.node.signal.signal", new=MagicMock)
class TestSuite(unittest.TestCase):

    @fake_redis("dal.movaidb.database.Connection", recording_dir=test_dir)
    @fake_redis("dal.plugins.persistence.redis.redis.Connection", recording_dir=test_dir)
    @patch("dal.movaidb.database.aioredis.ConnectionsPool", FakeAsyncPool)
    def test_disable_callbacks_on_transition(self):
        # We must import here to make sure the mocks are activated first
        from dal.movaidb.database import Redis
        Redis() # start up the singleton
        from dal.models.scopestree import scopes
        from gd_node.node import ARGS, GDNode

        #scope = scopes(workspace="global")

        callback_data = {"Callback": {"hello": {"Code": "open('/tmp/output', 'w').write('hello')"}}}
        #scope.write(callback_data, scope="Callback", ref="hello", version="__UNVERSIONED__")

        callback_data = {"Callback": {"transition": {"Code": "gd.oport['end'].send()"}}}
        #scope.write(callback_data, scope="Callback", ref="transition", version="__UNVERSIONED__")

        node_data = {
            "Node": {
                "Test Node 1": {
                    "Info": "Node for testing",
                    "Label": "test_node_1",
                    "Launch": True,
                    "PackageDepends": "",
                    "Path": "",
                    "Persistent": False,
                    "PortsInst": {
                        "Port1": {
                            "Message": "ContextClientIn",
                            "In": {
                                "in": {
                                    "Callback": "hello",
                                    "Parameter": {"Namespace": "navigation"},
                                }
                            },
                            "Package": "movai_msgs",
                            "Template": "MovAI/ContextClient",
                        },
                        "transition_port": {
                            "Message": "ContextClientIn",
                            "In": {
                                "in": {
                                    "Callback": "transition",
                                    "Parameter": {"Namespace": "calibration"},
                                }
                            },
                            "Package": "movai_msgs",
                            "Template": "MovAI/ContextClient",
                        },
                        "end": {
                            "Message": "Transition",
                            "Out": {"out": {"Message": "movai_msgs/Transition"}},
                            "Package": "movai_msgs",
                            "Template": "MovAI/TransitionFor",
                        },
                    },
                    "Remappable": True,
                    "Type": "MovAI/State",
                    "User": "",
                    "Version": "",
                    "VersionDelta": {},
                }
            }
        }
        #scope.write(node_data, scope="Node", ref="Test Node 1", version="__UNVERSIONED__")

        args = ARGS()
        args.verbose = True
        args.develop = False
        args.name = "Test Node 1"
        args.inst = "Test Inst 1"
        args.flow = "Test Flow 1"
        args.params = ""
        args.message = "None"

        node_thread = Thread(target=GDNode, args=(args, []), daemon=True)
        node_thread.start()

        time.sleep(3)
        if os.path.exists("/tmp/output"):
            os.remove("/tmp/output")

        redisc = Redis()
        redisc.db_local.publish("Var:context,ID:navigation_TX,Parameter:", "_id status")

        time.sleep(0.5)

        assert os.path.exists("/tmp/output")
        os.remove("/tmp/output")

        # start the transition, which should disable all other callbacks
        redisc.db_local.publish("Var:context,ID:calibration_TX,Parameter:", "_id result")

        assert not os.path.exists("/tmp/output")
        # trigger the file creation callback again
        redisc.db_local.publish("Var:context,ID:navigation_TX,Parameter:", "_id status")

        time.sleep(3)

        assert not os.path.exists("/tmp/output")


if __name__ == "__main__":
    unittest.main()
