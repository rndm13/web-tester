from functools import partial

from threading import Thread
import requests

import model

from imgui_bundle import hello_imgui
log = hello_imgui.log
LogLevel = hello_imgui.LogLevel


class Controller:
    def __init__(self, model: model.Model = model.Model([], [])):
        self.model = model

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
            self.results_filtered = self.model.test_results
            return

        self.results_filtered = list(filter(
            partial(model.TestResultFilter.use, self.result_filter),
            self.model.test_results))

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

    def basic_test(self, endpoint: model.Endpoint) -> model.TestResult:
        try:
            response = None
            if endpoint.http_type() == model.HTTPType.GET:
                response = requests.get(endpoint.url, endpoint.interaction.request.body, headers=endpoint.interaction.request.headers, cookies=endpoint.interaction.request.cookies)
            if endpoint.http_type() == model.HTTPType.POST:
                response = requests.post(endpoint.url, endpoint.interaction.request.body, headers=endpoint.interaction.request.headers, cookies=endpoint.interaction.request.cookies)
            if endpoint.http_type() == model.HTTPType.PUT:
                response = requests.put(endpoint.url, endpoint.interaction.request.body, headers=endpoint.interaction.request.headers, cookies=endpoint.interaction.request.cookies)
            if endpoint.http_type() == model.HTTPType.DELETE:
                response = requests.delete(endpoint.url, endpoint.interaction.request.body, headers=endpoint.interaction.request.headers, cookies=endpoint.interaction.request.cookies)
            return model.TestResult(endpoint, model.Severity.OK,
                                    "Ended with no error", response)
        except requests.ConnectTimeout as error:
            return model.TestResult(endpoint, model.Severity.WARNING,
                                    "Connection timeout", error=error)
        except requests.ConnectionError as error:
            return model.TestResult(endpoint, model.Severity.WARNING,
                                    "Connection error", error=error)
        except requests.HTTPError as error:
            return model.TestResult(endpoint, model.Severity.CRITICAL,
                                    "HTTP error", error=error)
        except Exception as error:
            return model.TestResult(endpoint, model.Severity.DANGER,
                                    "Unknown error", error=error)

    def run_basic_tests(self):
        self.in_progress = True
        self.progress = 0
        count = len(self.model.endpoints)
        test_results = []
        for endpoint in self.model.endpoints:
            log(LogLevel.info, f"Starting test for {endpoint.url} {endpoint.http_type()}")
            result = self.basic_test(endpoint)
            test_results.append(result)

            self.progress += 1 / count
        self.progress = 1
        self.in_progress = False
        self.model.test_results = test_results

    def start_basic_testing(self):
        self.testing_thread = Thread(target=Controller.run_basic_tests, args=(self, ))
        self.testing_thread.start()

    def cancel_testing(self):
        self.in_progress = False
        if self.testing_thread is not None:
            self.testing_thread.join(3)
        log(LogLevel.info, "Testing canceled")
    
    def cleanup(self):
        self.cancel_testing()
