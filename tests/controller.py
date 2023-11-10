import unittest
from web_tester import controller
import requests


class TestController(unittest.TestCase):
    def test_str_to_dict(self):
        i = "key: value\n1234525: b\n:"
        o = {"key": "value", "1234525": "b", "": ""}
        self.assertEqual(controller.str_to_dict(i), o)

    def test_match_errors(self):
        self.assertFalse(controller.match_errors("Successfully processed input!!!!!!"))
        self.assertTrue(controller.match_errors("Died on line 64"))
        self.assertTrue(controller.match_errors("Fatal error: server cannot be a teapot"))
        
    def test_response_convert(self):  # requires internet connection
        r = requests.get("https://google.com/")
        response = controller.response_convert(r)
        self.assertEqual(response.validate(), "")
        self.assertEqual(response.body_type, controller.model.ResponseBodyType.HTML)
