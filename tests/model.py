import unittest
from web_tester import model


class TestPartialDict(unittest.TestCase):
    def test_enabled_only(self):
        element = model.PartialDictionary.Element
        pd = model.PartialDictionary([
            element("key", "value", True),
            element("test", "no", False),
            element("a", "b", True)])

        self.assertEqual(pd.get(), {"key": "value", "a": "b"})

    def test_from_str(self):
        element = model.PartialDictionary.Element
        pd = model.PartialDictionary([
            element("key", "value", True),
            element("a", "b", True)])

        text = """
               key: value
               a: b
               """

        self.assertEqual(pd.get(), model.PartialDictionary.from_str(text).get())

    def test_from_dict(self):
        element = model.PartialDictionary.Element
        pd = model.PartialDictionary([
            element("key", "value", True),
            element("a", "b", True)])

        dictionary = {
            "key": "value",
            "a": "b",
        }

        self.assertEqual(pd.get(), model.PartialDictionary.from_dict(dictionary).get())
