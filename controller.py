from threading import Thread
import time

import model

class Controller:
    def __init__(self, model: model.Model = model.Model()):
        self.model = model
        self.endpoints_filtered = []
        self.set_endpoint_filter(None)

        self.testing = False
        self.progress = None
        self.testing_thread = None

    def add_endpoint(self, endpoint: model.Endpoint):
        self.model.add_endpoint(endpoint)
        self.filter()

    def remove_endpoint(self, endpoint: model.Endpoint):
        self.model.remove_endpoint(endpoint)
        self.filter()

    def set_endpoint_filter(self, filters):
        self.endpoint_filter = filters
        self.filter()

    def filter(self):
        if self.endpoint_filter is None:
            self.endpoints_filtered = self.model.endpoints
            return

        def filt(endpoint: model.Endpoint):
            return (self.endpoint_filter.url in endpoint.url and self.endpoint_filter.get == endpoint.get and self.endpoint_filter.post == endpoint.post)

        self.endpoints_filtered = list(filter(filt, self.model.endpoints))

    def endpoints(self):
        return self.endpoints_filtered

    def open(self, filename: str):
        print("Controller: opening")
        self.model = model.Model.load(filename)
        self.set_endpoint_filter(None)
    
    def save(self, filename: str):
        print("Controller: saving")
        self.model.save(filename)

    def tests(self):
        self.progress = 0
        while self.progress < 1 and self.testing:
            self.progress += 0.01
            time.sleep(0.1)

    def start_testing(self):
        self.testing = True
        self.testing_thread = Thread(target=Controller.tests, args=(self, ))
        self.testing_thread.start()

    def cancel_testing(self):
        self.testing = False
        if self.testing_thread is not None:
            self.testing_thread.join(3)
    
    def cleanup(self):
        self.cancel_testing()
