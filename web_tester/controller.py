from typing import Callable

from functools import partial
import string
import rstr
import random
from copy import deepcopy

from concurrent import futures

import re
import json
import requests
from http import HTTPStatus

from . import model
from . import reports

from imgui_bundle import hello_imgui
log = hello_imgui.log
LogLevel = hello_imgui.LogLevel


def match_errors(text: str) -> bool:
    static = match_errors
    if not hasattr(static, 'errors'):  # fill with fuzzdb/regex/errors.txt
        file = open("./fuzzdb/regex/errors.txt", "r")
        static.errors = '|'.join(map(lambda s: f"({re.escape(s.strip())})", file.readlines()))
        file.close()
    ret = re.search(f"\\b({static.errors})\\b", text)
    # log(LogLevel.debug, str(ret))
    return ret is not None


def response_convert(response: requests.Response) -> model.HTTPResponse:
    body_type = model.ResponseBodyType.HTML
    try:  # check if body is json perchance
        json.loads(response.text)
        body_type = model.ResponseBodyType.JSON
    except Exception:
        pass

    headers = model.PartialDictionary.from_dict(response.headers)
    cookies = model.PartialDictionary.from_dict(response.cookies)
    
    return model.HTTPResponse(HTTPStatus(response.status_code), body_type, response.text, headers, cookies)


def fuzz_json(json_body, rand=lambda: rstr.rstr(string.printable)):
    body = deepcopy(json_body)

    if isinstance(body, dict):
        for k, v in body.items():
            body[k] = fuzz_json(v, rand)
        return body
    if isinstance(body, list):
        for item in body:
            item = fuzz_json(item, rand)
    if isinstance(body, str):
        return rand()
    if isinstance(body, int):
        return round(random.random() * 100) - 50
    if isinstance(body, float):
        return random.random() * 100 - 50
    if isinstance(body, bool):
        return random.random() >= 0.5

    return body


class Controller:
    def __init__(self, model: model.Model = model.Model([], []), thread_pool: futures.ThreadPoolExecutor = futures.ThreadPoolExecutor()):
        self.model = model
        self.thread_pool = thread_pool

        self.endpoints_filtered = []
        self.set_endpoint_filter(None)

        self.results_filtered = []
        self.set_result_filter(None)

        self.in_progress = False
        self.progress = None

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
        try:
            log(LogLevel.info, f"Loading file: {filename}")
            self.model = model.Model.load(filename)
            self.set_endpoint_filter(None)
            self.set_result_filter(None)
        except Exception as e:
            log(LogLevel.error, f"Failed loading file {str(e)}")
    
    def save(self, filename: str):
        try:
            log(LogLevel.info, f"Saving to file: {filename}")
            self.model.save(filename)
        except Exception as e:
            log(LogLevel.error, f"Failed saving to file {str(e)}")

    def export(self, filename: str):
        if self.model.results == []:
            log(LogLevel.warning, "No results to export")
            return

        try:
            log(LogLevel.info, f"Exporting results to file: {filename}")
            reports.export_test_results(filename, self.model.results)

        except Exception as e:
            log(LogLevel.error, f"Failed exporting to file: {str(e)}")

    def make_request(self, endpoint: model.Endpoint, request: model.HTTPRequest = None) -> requests.Response:
        if request is None:
            request = endpoint.interaction.request
        
        if endpoint.http_type() == model.HTTPType.GET:
            return requests.get(endpoint.url, data=request.get_body(), headers=request.headers.get(),
                                cookies=request.cookies.get(), timeout=endpoint.max_wait_time)
        if endpoint.http_type() == model.HTTPType.POST:
            return requests.post(endpoint.url, data=request.get_body(), headers=request.headers.get(),
                                 cookies=request.cookies.get(), timeout=endpoint.max_wait_time)
        if endpoint.http_type() == model.HTTPType.PUT:
            return requests.put(endpoint.url, data=request.get_body(), headers=request.headers.get(),
                                cookies=request.cookies.get(), timeout=endpoint.max_wait_time)
        if endpoint.http_type() == model.HTTPType.DELETE:
            return requests.delete(endpoint.url, data=request.get_body(), headers=request.headers.get(),
                                   cookies=request.cookies.get(), timeout=endpoint.max_wait_time)

    def handle_request(self, endpoint: model.Endpoint, handler: Callable[[requests.Response], model.TestResult], diff_request: model.HTTPRequest = None) -> model.TestResult:
        if diff_request is None:
            diff_request = endpoint.interaction.request

        try:
            response = self.make_request(endpoint, diff_request)
            log(LogLevel.info, f"Got response from {endpoint.url} {endpoint.http_type()}")

            return handler(response)
        except requests.ConnectTimeout as error:
            log(LogLevel.error, f"Connection timeout for {endpoint.url} {endpoint.http_type()}")
            return model.TestResult(endpoint, model.Severity.CRITICAL, "Connection timeout (exceeded max set for endpoint)",
                                    None, error=error, diff_request=diff_request)
        except requests.ConnectionError as error:
            log(LogLevel.error, f"Connection error for {endpoint.url} {endpoint.http_type()}")
            return model.TestResult(endpoint, model.Severity.WARNING, "Connection error",
                                    None, error=error, diff_request=diff_request)
        except requests.HTTPError as error:
            log(LogLevel.error, f"HTTP error for {endpoint.url} {endpoint.http_type()}")
            return model.TestResult(endpoint, model.Severity.DANGER, "HTTP error",
                                    None, error=error, diff_request=diff_request)
        except Exception as error:
            log(LogLevel.error, f"Unknown error for {endpoint.url} {endpoint.http_type()}")
            return model.TestResult(endpoint, model.Severity.WARNING, "Unknown error",
                                    None, error=error, diff_request=diff_request)

    def match_test(self, endpoint: model.Endpoint, override_cookies: model.PartialDictionary = None) -> model.TestResult:
        def value_lower(t):
            (k, v) = t
            return (k, v.lower())

        request = deepcopy(endpoint.interaction.request)

        if override_cookies is not None:
            request.cookies = deepcopy(override_cookies)

        def handle_response(response: requests.Response):
            model_http_response = response_convert(response)
            expected_response_header_set = set(map(value_lower, endpoint.interaction.response.headers.get().items()))  # response headers but values are lowercase
            response_header_set = set(map(value_lower, response.headers.items()))  # response headers but values are lowercase

            verdict = "Got expected response"
            severity = model.Severity.OK
            
            # if specified status isn't client error we check for errors in response
            if not endpoint.interaction.response.http_status.is_client_error and match_errors(model_http_response.body):
                verdict = "Found errors in response"
                severity = model.Severity.CRITICAL
            elif model_http_response.http_status.is_server_error:
                verdict = "Server error in status found"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body_type != model_http_response.body_type:
                verdict = "Unmatched body type"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body != "" and endpoint.interaction.response.body != model_http_response.body:
                verdict = "Unmatched body"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.http_status != HTTPStatus(response.status_code):
                verdict = "Unmatched return status"
                severity = model.Severity.DANGER
            # checks if expected response cookies are subset of received
            elif not set(endpoint.interaction.response.cookies.get()).issubset(set(response.cookies)):
                verdict = "Unmatched cookies"
                severity = model.Severity.DANGER
            # checks if expected response headers are subset of received
            elif not expected_response_header_set.issubset(response_header_set):
                verdict = "Unmatched headers"
                severity = model.Severity.DANGER

            return model.TestResult(endpoint, severity, verdict,
                                    response.elapsed, request, model_http_response)
    
        return self.handle_request(endpoint, handle_response, request)

    def fuzz_test(self, endpoint: model.Endpoint, override_cookies: model.PartialDictionary = None) -> model.TestResult:
        request = deepcopy(endpoint.interaction.request)

        # generating request body
        match request.body_type:
            case model.RequestBodyType.FORM_DATA:
                for elem in request.body.elements:  # should be a dictionary
                    if elem.enabled:
                        elem.value = rstr.rstr(string.printable)

            case model.RequestBodyType.RAW:
                request.body = rstr.rstr(string.printable)

            case model.RequestBodyType.JSON:
                # log(LogLevel.warning, "Proper json fuzzing not implemented right now")
                request.body = json.dumps(fuzz_json(json.loads(request.body)))
                # request.body = rstr.rstr(string.printable)

        if override_cookies is not None:
            request.cookies = deepcopy(override_cookies)

        def handle_response(response: requests.Response):
            model_http_response = response_convert(response)

            verdict = "Got expected response"
            severity = model.Severity.OK
            
            # if status isn't client error we check for errors in response
            if not model_http_response.http_status.is_client_error and match_errors(model_http_response.body):
                verdict = "Found non-client errors in response"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body_type != model_http_response.body_type:
                verdict = "Unmatched body type"
                severity = model.Severity.CRITICAL
            elif model_http_response.http_status.is_server_error:
                verdict = "Server error in status found"
                severity = model.Severity.CRITICAL

            return model.TestResult(endpoint, severity, verdict,
                                    response.elapsed, request, model_http_response)

        return self.handle_request(endpoint, handle_response, request)

    def sqlinj_test(self, endpoint: model.Endpoint, override_cookies: model.PartialDictionary = None) -> model.TestResult:
        request = deepcopy(endpoint.interaction.request)

        # generating request body
        wordlist = endpoint.sqlinj_test.wordlist.get()
        match request.body_type:
            case model.RequestBodyType.FORM_DATA:
                for elem in request.body.elements:  # should be a dictionary
                    if elem.enabled:
                        elem.value = wordlist[random.randint(0, len(wordlist) - 1)]
            case model.RequestBodyType.RAW:
                request.body = wordlist[random.randint(0, len(wordlist) - 1)]
            case model.RequestBodyType.JSON:
                request.body = json.dumps(fuzz_json(json.loads(request.body), lambda: wordlist[random.randint(0, len(wordlist) - 1)]))

        if override_cookies is not None:
            request.cookies = deepcopy(override_cookies)

        def handle_response(response: requests.Response):
            model_http_response = response_convert(response)

            verdict = "Got expected response"
            severity = model.Severity.OK
            
            # if status isn't client error we check for errors in response
            if not model_http_response.http_status.is_client_error and match_errors(model_http_response.body):
                verdict = "Found non-client errors in response"
                severity = model.Severity.CRITICAL
            elif endpoint.interaction.response.body_type != model_http_response.body_type:
                verdict = "Unmatched body type"
                severity = model.Severity.CRITICAL
            elif model_http_response.http_status.is_server_error:
                verdict = "Server error in status found"
                severity = model.Severity.CRITICAL

            return model.TestResult(endpoint, severity, verdict,
                                    response.elapsed, request, model_http_response)

        return self.handle_request(endpoint, handle_response, request)

    def run_default_tests(self):
        self.in_progress = True
        self.progress = 0

        thrs = []
        results = []
        for endpoint in self.model.enabled_endpoints():
            if endpoint.match_test:
                log(LogLevel.info, f"Starting match test for {endpoint.url} {endpoint.http_type()}")
                thrs.append(self.thread_pool.submit(Controller.match_test, self, endpoint))
            if endpoint.fuzz_test is not None:
                for i in range(0, endpoint.fuzz_test.count):
                    log(LogLevel.info, f"Starting fuzz test for {endpoint.url} {endpoint.http_type()}")
                    thrs.append(self.thread_pool.submit(Controller.fuzz_test, self, endpoint))
            if endpoint.sqlinj_test is not None:
                for i in range(0, endpoint.sqlinj_test.count):
                    log(LogLevel.info, f"Starting SQL injection test for {endpoint.url} {endpoint.http_type()}")
                    thrs.append(self.thread_pool.submit(Controller.sqlinj_test, self, endpoint))

        count = len(thrs)
        for thr in thrs:
            try:
                results.append(thr.result(timeout=None))
                self.progress += 1 / count
            except Exception as error:
                log(LogLevel.error, error)

        self.model.results = results
        self.progress = 1
        self.in_progress = False
        self.filter_results()

    def run_dynamic_tests(self):
        self.in_progress = True
        self.progress = 0

        results = []
        
        max_count = 0

        for endpoint in self.model.enabled_endpoints():
            if endpoint.match_test:
                max_count += 1
            if endpoint.fuzz_test is not None:
                max_count += endpoint.fuzz_test.count
            if endpoint.sqlinj_test is not None:
                max_count += endpoint.sqlinj_test.count

        cookies = model.PartialDictionary()
        if self.model.dynamic_options.use_initial_values:
            cookies = self.model.dynamic_options.initial_cookies

        for endpoint in self.model.enabled_endpoints():
            if endpoint.match_test:
                log(LogLevel.info, f"Starting match test for {endpoint.url} {endpoint.http_type()}")
                results.append(self.match_test(endpoint, cookies))
                if results[-1].severity == model.Severity.OK:
                    cookies = model.PartialDictionary.merge(cookies, results[-1].response.cookies)
                self.progress += 1 / max_count
            if endpoint.fuzz_test is not None:
                for i in range(0, endpoint.fuzz_test.count):
                    log(LogLevel.info, f"Starting fuzz test for {endpoint.url} {endpoint.http_type()}")
                    results.append(self.fuzz_test(endpoint, cookies))
                    if results[-1].severity == model.Severity.OK:
                        cookies = model.PartialDictionary.merge(cookies, results[-1].response.cookies)
                    self.progress += 1 / max_count
            if endpoint.sqlinj_test is not None:
                for i in range(0, endpoint.sqlinj_test.count):
                    log(LogLevel.info, f"Starting SQL injection test for {endpoint.url} {endpoint.http_type()}")
                    results.append(self.sqlinj_test(endpoint, cookies))
                    if results[-1].severity == model.Severity.OK:
                        cookies = model.PartialDictionary.merge(cookies, results[-1].response.cookies)
                    self.progress += 1 / max_count

        self.model.results = results
        self.progress = 1
        self.in_progress = False
        self.filter_results()

    def start_testing(self):
        if self.model.dynamic_options is not None:
            self.thread_pool.submit(Controller.run_dynamic_tests, self)
        else:
            self.thread_pool.submit(Controller.run_default_tests, self)

    def cancel_testing(self):
        if not self.in_progress:
            return

        # log(LogLevel.debug, str(self.thread_pool._threads))
        # for thr in self.thread_pool._threads:
        #     thr.join(timeout=0)

        self.thread_pool.shutdown(cancel_futures=True)
        self.thread_pool = futures.ThreadPoolExecutor()
            
        self.in_progress = False
        log(LogLevel.info, "Testing canceled")
    
    def cleanup(self):
        self.cancel_testing()
