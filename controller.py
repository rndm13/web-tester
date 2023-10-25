# import wfuzz
import validators
import json

from enum import StrEnum
from imgui_bundle import imgui_color_text_edit as ed
TextEditor = ed.TextEditor


class HttpType(StrEnum):
    GET = "GET"
    POST = "POST"


class EdType(StrEnum):
    JSON = "JSON"
    HTML = "HTML"


class EdText:
    def __init__(self, type: EdType, text: str):
        self.type = type
        self.text = text

    def render_ed(self, editor: TextEditor, label: str):
        editor.set_text(self.text)
        if self.type == EdType.JSON:
            editor.set_language_definition(TextEditor.LanguageDefinition.json())
        if self.type == EdType.HTML:
            editor.set_language_definition(None)
        editor.render(label)
        self.text = editor.get_text()

    def validate(self) -> str:
        if self.type == EdType.JSON:
            try:
                json.loads(self.text)
            except Exception as ex:
                return str(ex)
        return ""
        

JSONExample = EdText(EdType.JSON, """
{
    "json": "example",
    "isjson": true
}""")


class Interaction:
    def __init__(self, type: HttpType, request: EdText = JSONExample, response: EdText = JSONExample):
        self.type = type
        self.request = request
        self.response = response

    def validate(self):
        ret = self.request.validate()
        if ret != "":
            return ret
        ret = self.response.validate()
        if ret != "":
            return ret
        return ""


class Endpoint:
    def __init__(self, url: str = "https://example.com/some-action",
                 get: bool = False, get_interaction: Interaction = Interaction(HttpType.GET),
                 post: bool = False, post_interaction: Interaction = Interaction(HttpType.POST)):
        self.url = url
        self.get = get
        self.get_interaction = get_interaction
        self.post = post
        self.post_interaction = post_interaction

    def http_types(self) -> str:
        ret = ""
        if self.get:
            ret += "GET "
        if self.post:
            ret += "POST "
        
        if ret == "":
            ret = "None"

        return ret

    def validate(self) -> str:
        if not validators.url(self.url):
            return "endpoint url must be a ... url?!?!"
        
        if not (self.get or self.post):
            return "endpoint must have at least a single http request"
        
        ret = self.get_interaction.validate()
        if ret != "":
            return ret
        
        ret = self.post_interaction.validate()
        if ret != "":
            return ret

        return ""


class Controller:
    def __init__(self, endpoints: list[Endpoint] = []):
        self.endpoints = endpoints

    def add_endpoint(self, endpoint: Endpoint):
        self.endpoints.append(endpoint)
