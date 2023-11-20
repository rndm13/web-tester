import unittest
from web_tester import controller


class TestController(unittest.TestCase):
    def test_match_errors(self):
        self.assertFalse(controller.match_errors("Successfully processed input!!!!!!"))
        self.assertTrue(controller.match_errors("Died on line 64"))
        self.assertTrue(controller.match_errors("Fatal error: server cannot be a teapot"))
