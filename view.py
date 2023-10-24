from functools import partial
from imgui_bundle import imgui, immapp
from controller import (Controller, EndPoint)


class TestInput:
    def __init__(self, parent):
        self.controller = parent.controller
        self.endpoint = EndPoint("https://example.com/some-action/")
        self.validation = ""
        self.http_type = 0

    def gui(self):
        imgui.begin("Test input selection")
        if imgui.tree_node("About"):
            imgui.text("""
Hello!
This is a window where you specify all http endpoints for your site or web api.
You can set which http requests to make, input payload templates and output examples.
Here you can also choose for which security vulnerabilities to test for and what should be servers response.
                       """)
            imgui.tree_pop()
        
        changed, self.endpoint.url = imgui.input_text("URL", self.endpoint.url)
        
        imgui.text(f"{self.endpoint.http_types()}: ")
        imgui.same_line()
        if imgui.tree_node("Http types"):
            changed, self.endpoint.get = imgui.checkbox("GET", self.endpoint.get)
            changed, self.endpoint.post = imgui.checkbox("POST", self.endpoint.post)
            imgui.tree_pop()

        if imgui.button("Add endpoint"):
            self.validation = self.endpoint.validate()
            if self.validation == "":
                self.controller.add_endpoint(self.endpoint)

        if self.validation != "":
            imgui.text_colored(imgui.ImVec4(255, 0, 0, 255), f"Failed to validate input:\n{self.validation}")

        imgui.end()


class View:
    def __init__(self):
        self.controller = Controller()
        self.windows = [
            TestInput(self)
        ]

    def run(self):
        immapp.run(
                gui_function=partial(View.gui, self),
                window_title="Web Tester",
                window_size_auto=True)

    def gui(self):
        for window in self.windows:
            window.gui()
