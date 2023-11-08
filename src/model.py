from typing import Union
import validators
import json
import datetime

from enum import Enum, StrEnum
from http import HTTPStatus

import _pickle as pickle

from imgui_bundle import imgui_color_text_edit as ed, hello_imgui
TextEditor = ed.TextEditor
log = hello_imgui.log
LogLevel = hello_imgui.LogLevel


class HTTPType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class RequestBodyType(StrEnum):
    JSON = "JSON"
    RAW = "RAW"
    ORIGIN = "ORIGIN"


class HTTPRequest:
    def __init__(self, http_type: HTTPType, body_type: RequestBodyType = RequestBodyType.ORIGIN, body: Union[str, dict[str, str]] = None, headers: str = "", cookies: dict[str, str] = {}):
        self.http_type = http_type
        self.body_type = body_type
        self.body = body
        if self.body is None:
            match self.body_type:
                case RequestBodyType.ORIGIN:
                    self.body = {}
                case RequestBodyType.JSON | RequestBodyType.RAW:
                    self.body = ""
        self.headers = headers
        self.cookies = cookies
        self.prettify()

    def validate(self) -> str:
        match self.body_type:
            case RequestBodyType.JSON:
                try:
                    json.loads(self.body)
                except Exception as ex:
                    return f"failed to validate json: {str(ex)}"
        return ""

    def prettify(self) -> ():
        try:
            match self.body_type:
                case RequestBodyType.JSON:
                    json_data = json.loads(self.body)
                    self.body = json.dumps(json_data, indent=4)
        except Exception as e:
            log(LogLevel.warning, f"Failed to prettify json: {str(e)}")


class ResponseBodyType(StrEnum):
    JSON = "JSON"
    HTML = "HTML"
    RAW = "RAW"


class HTTPResponse:
    def __init__(self, http_status: HTTPStatus, body_type: ResponseBodyType = ResponseBodyType.JSON, body: Union[str, dict[str, str]] = "", headers: str = "", cookies: dict[str, str] = {}):
        self.http_status = http_status
        self.body_type = body_type
        self.body = body
        self.headers = headers
        self.cookies = cookies
        self.prettify()
        
    def validate(self) -> str:
        match self.body_type:
            case ResponseBodyType.JSON:
                try:
                    json.loads(self.body)
                except Exception as ex:
                    return f"failed to validate json: {str(ex)}"

        return ""

    def prettify(self) -> ():
        try:
            match self.body_type:
                case ResponseBodyType.JSON:
                    json_data = json.loads(self.body)
                    self.body = json.dumps(json_data, indent=4)
        except Exception as e:
            log(LogLevel.warning, f"Failed to prettify json: {str(e)}")


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


class Wordlist:
    wordlists = {}  # NOTE: doesn't get saved in files

    def __init__(self, filename: str):
        self.filename = filename

    def get(self) -> list[str]:
        if self.filename not in Wordlist.wordlists:
            file = open(self.filename, "r")
            Wordlist.wordlists[self.filename] = list(map(lambda s: s.strip(), file.readlines()))
        return Wordlist.wordlists[self.filename]

    @classmethod
    def unload(cls, filename: str) -> ():
        cls.wordlists.pop(filename)


class FuzzTest:
    def __init__(self, count: int = 10):
        self.count = count


class SQLInjectionTest:
    def __init__(self, count: int = 10, wordlist: Wordlist = Wordlist('./fuzzdb/attack/sql-injection/detect/GenericBlind.txt')):
        self.count = count
        self.wordlist = wordlist

    def wordlist(self):
        return self.wordlist.get()


class Endpoint:
    def __init__(self, url: str, interaction: Interaction, max_wait_time: int = 10,
                 match_test: bool = True, fuzz_test: FuzzTest = FuzzTest(), sqlinj_test: SQLInjectionTest = None) -> ():
        self.url = url
        self.interaction = interaction
        self.max_wait_time = max_wait_time
        self.match_test = match_test
        self.fuzz_test = fuzz_test
        self.sqlinj_test = sqlinj_test

    def http_type(self) -> str:
        return self.interaction.request.http_type.value

    def test_types(self) -> str:
        results = []

        if self.match_test:
            results.append("Match")
        if self.fuzz_test is not None:
            results.append("Fuzz")
        if self.sqlinj_test is not None:
            results.append("SQL")

        return ', '.join(results)

    def validate(self) -> str:
        if not validators.url(self.url):
            return "endpoint url must be a ... url?!?!"

        if not self.match_test and self.fuzz_test is None and self.sqlinj_test is None:
            return "must select at least one type of testing"
        
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
    OK = 0
    WARNING = 1
    DANGER = 2
    CRITICAL = 3

    def __str__(self) -> str:
        strs = {0: "Ok", 1: "Warning", 2: "Danger", 3: "Critical"}
        return strs[self.value]


class TestResult:
    def __init__(self,
                 endpoint: Endpoint, severity: Severity, verdict: str, elapsed_time: datetime.time,
                 diff_request: HTTPRequest = None, response: HTTPResponse = None, error=None) -> ():
        self.endpoint = endpoint
        self.severity = severity
        self.verdict = verdict
        self.elapsed_time = elapsed_time
        self.response = response
        self.error = error

        self.diff_request = diff_request
        if self.diff_request is None:
            self.diff_request = self.endpoint.interaction.request

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
        ret = tr.severity.value >= self.min_severity
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
