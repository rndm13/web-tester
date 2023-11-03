from functools import partial

from threading import Thread
import requests

import model


class Controller:
    def __init__(self, model: model.Model = model.Model()):
        self.model = model
        self.endpoints_filtered = []
        self.set_endpoint_filter(None)

        self.in_progress = False
        self.progress = None
        self.testing_thread = None

    def add_endpoint(self, endpoint: model.Endpoint):
        self.model.add_endpoint(endpoint)
        self.filter()

    def remove_endpoint(self, endpoint: model.Endpoint):
        self.model.remove_endpoint(endpoint)
        self.filter()

    def set_endpoint_filter(self, filter: model.EndpointFilter):
        self.endpoint_filter = filter
        self.filter()

    def filter(self):
        if self.endpoint_filter is None:
            self.endpoints_filtered = self.model.endpoints
            return

        self.endpoints_filtered = list(filter(
            partial(model.EndpointFilter.use, self.endpoint_filter),
            self.model.endpoints))

    def endpoints(self):
        return self.endpoints_filtered

    def open(self, filename: str):
        self.model = model.Model.load(filename)
        self.set_endpoint_filter(None)
    
    def save(self, filename: str):
        self.model.save(filename)

    def basic_tests(self):
        self.in_progress = True
        self.progress = 0
        count = len(self.model.endpoints)
        for endpoint in self.model.endpoints:
            # if endpoint.get:
            #     requests.get(endpoint.url, endpoint.get_interaction.get_request())

            self.progress += 1 / count
        self.progress = 1
        self.in_progress = False

    def start_basic_testing(self):
        self.testing_thread = Thread(target=Controller.basic_tests, args=(self, ))
        self.testing_thread.start()

    def cancel_testing(self):
        self.in_progress = False
        if self.testing_thread is not None:
            self.testing_thread.join(3)
    
    def cleanup(self):
        self.cancel_testing()
