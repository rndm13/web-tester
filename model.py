import validators
import json

from enum import Enum, StrEnum
from http import HTTPStatus
import requests

import _pickle as pickle

from imgui_bundle import imgui_color_text_edit as ed
TextEditor = ed.TextEditor

import datetime


class HTTPType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HTTPRequest:
    def __init__(self, http_type: HTTPType, headers: str = "", body: str = "", body_json: bool = False, cookies: dict[str, str] = {}):
        self.http_type = http_type
        self.headers = headers
        self.body = body
        self.body_json = body_json
        self.cookies = cookies

    def validate(self):
        if self.body_json:
            try:
                json.loads(self.body)
            except Exception as ex:
                return str(ex)
        return ""


class HTTPResponse:
    def __init__(self, http_status: HTTPStatus, headers: str = "", body: str = "", body_json: bool = False, cookies: dict[str, str] = {}):
        self.http_status = http_status
        self.headers = headers
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
                 response: HTTPResponse):
        self.request = request
        self.response = response

    def validate(self) -> str:
        ret = self.request.validate()
        if ret != "":
            return ret
        ret = self.response.validate()
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

    def use(self, endp: Endpoint) -> bool:
        ret = True
        if self.url is not None:
            ret &= self.url in endp.url
        if self.http_type is not None:
            ret &= self.http_type == endp.http_type()
        return ret


class Severity(Enum):
    OK = 0,
    WARNING = 1,
    DANGER = 2,
    CRITICAL = 3

    def __str__(self) -> str:
        strs = {0: "Ok", 1: "Warning", 2: "Danger", 3: "Critical"}
        return strs[self.value[0]]


class TestResult:
    def __init__(self, endpoint: Endpoint, severity: Severity, verdict: str, response: requests.Response = None, error=None) -> ():
        self.endpoint = endpoint
        self.severity = severity
        self.verdict = verdict

        self.response = None
        if response is not None:
            body_json = False
            try:
                json.loads(response.content)
                body_json = True
            except Exception:
                pass
            headers = ""
            for k, v in response.headers.items():
                headers += f"{k}: {v}\n"

            self.response = HTTPResponse(HTTPStatus(response.status_code), headers, response.content, body_json, response.cookies)

        self.error = error

    def color(self) -> list[int]:
        if self.severity == Severity.OK:
            return [0, 255, 0, 255]
        if self.severity == Severity.WARNING:
            return [0, 0, 255, 255]
        if self.severity == Severity.DANGER:
            return [255, 255, 0, 255]
        if self.severity == Severity.CRITICAL:
            return [255, 0, 0, 255]


class TestResultFilter:
    def __init__(self, url: str, http_type: HTTPType, min_severity: int) -> ():
        self.url = url
        self.http_type = http_type
        self.min_severity = min_severity

    def use(self, tr: TestResult) -> bool:
        ret = tr.severity.value[0] >= self.min_severity
        if self.url is not None:
            ret &= self.url in tr.endpoint.url
        if self.http_type is not None:
            ret &= self.http_type == tr.endpoint.http_type()
        
        return ret


class Model:
    def __init__(self, endpoints: list[Endpoint] = [], results: list[TestResult] = []):
        self.endpoints = endpoints
        self.results = results

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
    ec = Endpoint('https://example.com/some/action', Interaction(HTTPRequest(HTTPType.GET), HTTPResponse(HTTPStatus.OK)))
    return ec
