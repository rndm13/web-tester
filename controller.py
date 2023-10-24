# import wfuzz
import validators


class EndPoint:
    def __init__(self, url: str = "https://example.com/some-action", get: bool = False, post: bool = False):
        self.url = url
        self.get = get
        self.post = post

    def http_types(self) -> str:
        ret = ""
        if self.get:
            ret += "GET "
        if self.post:
            ret += "POST "
        
        if ret == "":
            ret = "None"

        return ret

    def validate(self) -> str:
        if not validators.url(self.url):
            return "endpoint url must be a ... url?!?!"
        return ""


class Controller:
    def __init__(self):
        self.end_points = []

    def add_endpoint(self, endpoint: EndPoint):
        self.end_points.append(endpoint)
