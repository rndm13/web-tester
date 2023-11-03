from functools import partial

from threading import Thread
import requests

import model


class Controller:
    def __init__(self, model: model.Model = model.Model([], [])):
        self.model = model

        self.endpoints_filtered = []
        self.set_endpoint_filter(None)

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

    def test_results(self):
        return self.model.test_results

    def open(self, filename: str):
        self.model = model.Model.load(filename)
        self.set_endpoint_filter(None)
    
    def save(self, filename: str):
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
        for endpoint in self.model.endpoints:
            self.model.test_results.append(self.basic_test(endpoint))

            self.progress += 1 / count
        self.progress = 1
        self.in_progress = False

    def start_basic_testing(self):
        self.testing_thread = Thread(target=Controller.run_basic_tests, args=(self, ))
        self.testing_thread.start()

    def cancel_testing(self):
        self.in_progress = False
        if self.testing_thread is not None:
            self.testing_thread.join(3)
    
    def cleanup(self):
        self.cancel_testing()
