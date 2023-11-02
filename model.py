import validators
import json

from enum import StrEnum
from http import HTTPStatus

import _pickle as pickle

from imgui_bundle import imgui_color_text_edit as ed
TextEditor = ed.TextEditor


class HTTPType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HTTPRequest:
    def __init__(self, http_type: HTTPType, header: str = "", body: str = "", body_json: bool = False, cookies: dict[str, str] = {}):
        self.http_type = http_type
        self.header = header
        self.body = body
        self.body_json = body_json
        self.cookies = cookies

    def validate(self):
        if self.body_json:
            try:
                json.loads(self.text)
            except Exception as ex:
                return str(ex)
        return ""


class HTTPResponse:
    def __init__(self, http_status: HTTPStatus, header: str = "", body: str = "", body_json: bool = False, cookies: dict[str, str] = {}):
        self.http_status = http_status
        self.header = header
        self.body = body
        self.body_json = body_json
        self.cookies = cookies
        
    def validate(self):
        if self.body_json:
            try:
                json.loads(self.text)
            except Exception as ex:
                return str(ex)
        return ""


class Interaction:
    def __init__(self,
                 request: HTTPRequest,
                 expected_response: HTTPResponse):
        self.request = request
        self.expected_response = expected_response

    def validate(self) -> str:
        ret = self.request.validate()
        if ret != "":
            return ret
        ret = self.expected_response.validate()
        if ret != "":
            return ret
        return ""

    def http_type(self) -> HTTPType:
        return self.request.http_type.value


class Endpoint:
    def __init__(self, url: str, interaction: Interaction) -> ():
        self.url = url
        self.interaction = interaction

    def http_type(self) -> str:
        return self.interaction.request.http_type.value

    def validate(self) -> str:
        if not validators.url(self.url):
            return "endpoint url must be a ... url?!?!"
        
        return self.interaction.validate()


class EndpointFilter:
    def __init__(self, url: str, http_type: HTTPType) -> ():
        self.url = url
        self.http_type = http_type

    def get_filter(self, endp: Endpoint) -> bool:
        ret = True
        if self.url is not None:
            ret &= self.url in endp.url
        if self.http_type is not None:
            ret &= self.http_type in endp.http_type
        return ret


class Model:
    def __init__(self, endpoints: list[Endpoint] = []):
        self.endpoints = endpoints

    def add_endpoint(self, endpoint: Endpoint):
        return self.endpoints.append(endpoint)

    def remove_endpoint(self, endpoint: Endpoint):
        return self.endpoints.remove(endpoint)

    def save(self, filename: str):
        with open(filename, 'wb') as output:
            return pickle.dump(self, output, -1)

    @staticmethod
    def load(filename: str):
        with open(filename, 'rb') as input:
            return pickle.load(input)


def example_endpoint() -> Endpoint:
    ec = Endpoint('https://example.com/some/action', Interaction(HTTPRequest(HTTPType.GET), HTTPRequest(HTTPStatus.OK)))
    return ec
