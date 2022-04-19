"""Unit Test for GD_Callback

Attributes:
    CB_DICT (dict): Tested callback
"""
import types
import unittest
from dal.scopes import Callback
from gd_node.callback import GD_Callback, UserFunctions

CB_DICT = {
    "Callback": {
        "test_GD_Callback": {
            "Code": "print(msg)\n" "test().assertEqual(3, math.sqrt(9))",
            "Info": "This is a Callback created to " "perform Unittest",
            "Message": "std_msgs.msg/String",
            "Py3Lib": {
                "math": {"Module": "math"},
                "test": {"Class": "TestCase", "Module": "unittest"},
            },
            "Version": "0.0.0",
            "VersionDelta": {},
        }
    }
}


class TestGDCallback(unittest.TestCase):
    """Test class for the GD_Callback"""

    def setUp(self):
        """Setup all needed data"""
        cb = Callback("test_GD_Callback", new=True)
        cb.Message = "std_msgs.msg/String"
        cb.Version = "0.0.0"
        cb.Info = "This is a Callback created to perform Unittest"
        cb.Code = "print(msg)\ntest().assertEqual(3, math.sqrt(9))"
        cb.add("Py3Lib", "math", Module="math")
        cb.add("Py3Lib", "test", Module="unittest", Class="TestCase")

    def tearDown(self):
        """Delete previously created data"""
        Callback("test_GD_Callback").remove()

    def test_init(self):
        """Test the initialization of a GD_Callback"""

        # instantiate the class
        test_cb = GD_Callback("test_GD_Callback", "fake_node", "fake_port", False)

        # check if the instance was created and the code is the same
        self.assertIsInstance(test_cb.callback, Callback)
        self.assertEqual(test_cb.callback.get_dict(), CB_DICT)

        # check the compiled code
        self.assertIsInstance(test_cb.compiled_code, types.CodeType)

        # check user class
        self.assertIsInstance(test_cb.user, UserFunctions)

    def test_execute(self):
        """Test the execution of the callback code"""

        test_cb = GD_Callback("test_GD_Callback", "fake_node", "fake_port", False)
        test_cb.execute("Unit TEST Says HELLO")

    def test_update(self):
        """Delete previously created data"""
        test_cb = GD_Callback("test_GD_Callback", "fake_node", "fake_port", False)

        # change the Code in db and check the if the new version is diferent
        cb = Callback("test_GD_Callback")
        cb.Code = "print(msg)\ntest().assertNotEqual(4, math.sqrt(9))"

        self.assertNotEqual(test_cb.callback.get_dict(), CB_DICT)


if __name__ == "__main__":
    unittest.main()
