from functools import partial
from concurrent import futures

import re
import json
import requests
from http import HTTPStatus

import model

from imgui_bundle import hello_imgui
log = hello_imgui.log
LogLevel = hello_imgui.LogLevel


def str_to_dict(text: str) -> dict[str, str]:
    to_ret = {}
    for line in text.splitlines(False):
        if (ind := line.find(':')) >= 0:
            to_ret[line[:ind]] = line[ind + 2:]  # skip over semicolon and space
    return to_ret


def match_errors(text: str) -> bool:
    static = match_errors
    if not hasattr(static, 'errors'):  # fill with fuzzdb/regex/errors.txt
        errors = open("./fuzzdb/regex/errors.txt", "r")
        static.errors = '|'.join(map(lambda s: f"({re.escape(s.strip())})", errors.readlines()))
    return re.search(static.errors, text) is not None


def response_convert(response: requests.Response) -> model.HTTPResponse:
    body_json = False
    try:
        json.loads(response.text)
        body_json = True
    except Exception:
        pass
    headers = ""
    for k, v in response.headers.items():
        headers += f"{k}: {v}\n"
    
    return model.HTTPResponse(HTTPStatus(response.status_code), headers, response.text, body_json, response.cookies)


class Controller:
    def __init__(self, model: model.Model = model.Model([], []), thread_pool: futures.ThreadPoolExecutor = futures.ThreadPoolExecutor(4)):
        self.model = model
        self.thread_pool = thread_pool

        self.endpoints_filtered = []
        self.set_endpoint_filter(None)

        self.results_filtered = []
        self.set_result_filter(None)

        self.in_progress = False
        self.progress = None
        self.testing_thread = None

    def add_endpoint(self, endpoint: model.Endpoint):
        self.model.add_endpoint(endpoint)
        self.filter_endpoints()

    def remove_endpoint(self, endpoint: model.Endpoint):
        self.model.remove_endpoint(endpoint)
        self.filter_endpoints()

    def set_endpoint_filter(self, filter: model.EndpointFilter):
        self.endpoint_filter = filter
        self.filter_endpoints()

    def filter_endpoints(self):
        if self.endpoint_filter is None:
            self.endpoints_filtered = self.model.endpoints
            return

        self.endpoints_filtered = list(filter(
            partial(model.EndpointFilter.use, self.endpoint_filter),
            self.model.endpoints))

    def endpoints(self):
        return self.endpoints_filtered

    def set_result_filter(self, filter: model.TestResultFilter):
        self.result_filter = filter
        self.filter_results()

    def filter_results(self):
        if self.result_filter is None:
            self.results_filtered = self.model.results
            return

        self.results_filtered = list(filter(
            partial(model.TestResultFilter.use, self.result_filter),
            self.model.results))

    def test_results(self):
        return self.results_filtered

    def open(self, filename: str):
        log(LogLevel.info, f"Loading file: {filename}")
        self.model = model.Model.load(filename)
        self.set_endpoint_filter(None)
        self.set_result_filter(None)
    
    def save(self, filename: str):
        log(LogLevel.info, f"Saving to file: {filename}")
        self.model.save(filename)

    def make_request(self, endpoint: model.Endpoint) -> requests.Response:
        headers = str_to_dict(endpoint.interaction.request.headers)
        if endpoint.http_type() == model.HTTPType.GET:
            return requests.get(endpoint.url, endpoint.interaction.request.body, headers=headers, cookies=endpoint.interaction.request.cookies)
        if endpoint.http_type() == model.HTTPType.POST:
            return requests.post(endpoint.url, endpoint.interaction.request.body, headers=headers, cookies=endpoint.interaction.request.cookies)
        if endpoint.http_type() == model.HTTPType.PUT:
            return requests.put(endpoint.url, endpoint.interaction.request.body, headers=headers, cookies=endpoint.interaction.request.cookies)
        if endpoint.http_type() == model.HTTPType.DELETE:
            return requests.delete(endpoint.url, endpoint.interaction.request.body, headers=headers, cookies=endpoint.interaction.request.cookies)

    def basic_test(self, endpoint: model.Endpoint) -> model.TestResult:
        def value_lower(t):
            (k, v) = t
            return (k, v.lower())

        ret = None

        try:
            response = self.make_request(endpoint)
            model_http_response = response_convert(response)
            expected_response_header_set = set(map(value_lower, str_to_dict(endpoint.interaction.response.headers).items()))  # response headers but values are lowercase
            response_header_set = set(map(value_lower, response.headers.items()))  # response headers but values are lowercase

            verdict = "Got expected response"
            severity = model.Severity.OK

            if match_errors(model_http_response.body):
                verdict = "Found errors in response"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body_json != model_http_response.body_json:
                verdict = "Unmatched body type"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body != "" and endpoint.interaction.response.body != model_http_response.body:
                verdict = "Unmatched body"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.http_status != HTTPStatus(response.status_code):
                verdict = "Unmatched return status"
                severity = model.Severity.DANGER
            # checks if expected response cookies are subset of received
            elif not set(endpoint.interaction.response.cookies).issubset(set(response.cookies)):
                verdict = "Unmatched cookies"
                severity = model.Severity.DANGER
            # checks if expected response headers are subset of received
            elif not expected_response_header_set.issubset(response_header_set):
                verdict = "Unmatched headers"
                severity = model.Severity.DANGER

            ret = model.TestResult(endpoint, severity, verdict,
                                   response.elapsed, model_http_response)
        except requests.ConnectTimeout as error:
            ret = model.TestResult(endpoint, model.Severity.WARNING, "Connection timeout",
                                   response.elapsed, error=error)
        except requests.ConnectionError as error:
            ret = model.TestResult(endpoint, model.Severity.WARNING, "Connection error",
                                   response.elapsed, error=error)
        except requests.HTTPError as error:
            ret = model.TestResult(endpoint, model.Severity.CRITICAL, "HTTP error",
                                   response.elapsed, error=error)
        except Exception as error:
            ret = model.TestResult(endpoint, model.Severity.DANGER, "Unknown error",
                                   response.elapsed, error=error)
        
        return ret

    def run_basic_tests(self):
        self.in_progress = True
        self.progress = 0
        count = len(self.model.endpoints)

        thrs = []
        results = []
        for endpoint in self.model.endpoints:
            log(LogLevel.info, f"Starting test for {endpoint.url} {endpoint.http_type()}")
            thrs.append(self.thread_pool.submit(Controller.basic_test, self, endpoint))

        for thr in thrs:
            results.append(thr.result())
            self.progress += 1 / count

        self.model.results = results
        self.progress = 1
        self.in_progress = False
        self.filter_results()

    def start_basic_testing(self):
        self.testing_thread = self.thread_pool.submit(Controller.run_basic_tests, self)

    def cancel_testing(self):
        if not self.in_progress:
            return
        self.thread_pool.shutdown(cancel_futures=True)
        self.in_progress = False
        log(LogLevel.info, "Testing canceled")
    
    def cleanup(self):
        self.cancel_testing()
