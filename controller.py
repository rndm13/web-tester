# import wfuzz
import model


class Controller:
    def __init__(self, model: model.Model = model.Model()):
        self.model = model

    def add_endpoint(self, endpoint: model.Endpoint):
        self.model.add_endpoint(endpoint)

    def endpoints(self):
        return self.model.endpoints
