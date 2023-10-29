from functools import partial

from controller import Controller
from model import Endpoint

from imgui_bundle import imgui, immapp, imgui_color_text_edit as ed
TextEditor = ed.TextEditor


class EndpointInput:
    editor = TextEditor()
    validation = ""
        
    @staticmethod
    def edit(endpoint: Endpoint, label: str) -> bool:
        if endpoint is None:
            return False

        ret = False

        if not imgui.is_popup_open(label):
            imgui.open_popup(label)
        if imgui.begin_popup_modal(label):
            changed, endpoint.url = imgui.input_text("URL", endpoint.url)
            
            changed, endpoint.get = imgui.checkbox("GET", endpoint.get)
            if endpoint.get and imgui.tree_node("GET request"):
                endpoint.get_interaction.request.render_ed(EndpointInput.editor, "GET request")
                imgui.tree_pop()
            
            changed, endpoint.post = imgui.checkbox("POST", endpoint.post)
            if endpoint.post and imgui.tree_node("POST request"):
                endpoint.post_interaction.request.render_ed(EndpointInput.editor, "POST request")
                imgui.tree_pop()

            if imgui.button("Save"):
                EndpointInput.validation = endpoint.validate()
                if EndpointInput.validation == "":
                    ret = True

            if EndpointInput.validation != "":
                imgui.text_colored(imgui.ImVec4(255, 0, 0, 255), f"Failed to validate input:\n{EndpointInput.validation}")
            imgui.end_popup()

        return ret


class TestInputWindow:
    def __init__(self, parent):
        self.controller = parent.controller
        self.endpoint_add = None
        self.endpoint_edit = None
        self.validation = ""

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

        if imgui.button("Add endpoint"):
            self.endpoint_add = Endpoint()
            
        if EndpointInput.edit(self.endpoint_add, "Add endpoint"):
            self.controller.add_endpoint(self.endpoint_add)
            self.endpoint_add = None
            print("Added endpoint")

        i = 0  # For button ids
        if imgui.begin_table("Endpoints", 3, View.table_flags):
            imgui.table_header("URL")
            imgui.table_header("HTTP")
            imgui.table_header("Actions")

            for ep in self.controller.endpoints():
                imgui.table_next_column()
                imgui.text(ep.url)

                imgui.table_next_column()
                imgui.text(ep.http_types())
                
                imgui.table_next_column()
                imgui.push_id(i)
                if imgui.button("Edit"):
                    self.endpoint_edit = ep
                imgui.same_line()
                if imgui.button("Delete"):
                    self.controller.endpoints().remove(ep)
                imgui.pop_id()
                i += 1
            imgui.end_table()

        if EndpointInput.edit(self.endpoint_edit, "Edit endpoint"):
            self.endpoint_edit = None
            print("Added endpoint")

        imgui.end()


class View:
    table_flags = imgui.TableFlags_.scroll_y | imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_outer | imgui.TableFlags_.borders_v | imgui.TableFlags_.resizable | imgui.TableFlags_.reorderable | imgui.TableFlags_.hideable

    def __init__(self):
        self.controller = Controller()
        self.windows = [
            TestInputWindow(self)
        ]

    def run(self):
        immapp.run(
                gui_function=partial(View.gui, self),
                window_title="Web Tester",
                window_size_auto=True)

    def gui(self):
        for window in self.windows:
            window.gui()
