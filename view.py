from functools import partial
import copy

from controller import Controller
from model import Endpoint

from imgui_bundle import imgui, immapp, imgui_color_text_edit as ed, portable_file_dialogs as pfd
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

            if imgui.button("Save", (30, 30)):
                EndpointInput.validation = endpoint.validate()
                if EndpointInput.validation == "":
                    ret = True

            if EndpointInput.validation != "":
                imgui.text_colored(imgui.ImVec4(255, 0, 0, 255), f"Failed to validate input:\n{EndpointInput.validation}")
            imgui.end_popup()

        return ret


class EndpointFilter:
    def __init__(self, parent):
        self.controller = parent.controller

        self.url = ""
        self.get = True
        self.post = False

    def gui(self) -> bool:
        _, self.url = imgui.input_text("URL", self.url)
        _, self.get = imgui.checkbox("GET", self.get)
        _, self.post = imgui.checkbox("POST", self.post)


class TestInputWindow:
    def __init__(self, parent):
        self.controller = parent.controller

        self.endpoint_filter = None
        self.endpoint_add = None
        self.endpoint_edit = None
        self.validation = ""

        self.file_save = None
        self.file_open = None

    def menu(self):
        if imgui.begin_menu_bar():

            if imgui.begin_menu("File"):

                if imgui.button("Save"):
                    self.file_save = pfd.save_file("Select where to save", "", ["*.wt"])

                if imgui.button("Open"):
                    self.file_open = pfd.open_file("Open a save", "", ["*.wt"])

                imgui.end_menu()

            if imgui.begin_menu("About"):
                imgui.text("""
    Hello!
    This is a window where you specify all http endpoints for your site or web api.
    You can set which http requests to make, input payload templates and output examples.
    Here you can also choose for which security vulnerabilities to test for and what should be servers response.
                           """)

                imgui.end_menu()

            imgui.end_menu_bar()
            
        if self.file_save is not None and self.file_save.ready():
            if self.file_save.result() is not None:
                self.controller.save(self.file_save.result())
                self.file_save = None

        if self.file_open is not None and self.file_open.ready():
            if self.file_open.result() is not None:
                self.controller.open(self.file_open.result()[0])
                self.file_open = None

    def gui(self):
        imgui.begin("Tests", 0, imgui.WindowFlags_.menu_bar)

        self.menu()

        if imgui.button("Add endpoint", (0, 30)):
            self.endpoint_add = Endpoint()
            
        if EndpointInput.edit(self.endpoint_add, "Add endpoint"):
            self.controller.add_endpoint(self.endpoint_add)
            self.endpoint_add = None

        imgui.same_line()

        if imgui.button("Search endpoints", (0, 30)):
            self.endpoint_filter = EndpointFilter(self)
        
        if self.endpoint_filter is not None:
            if imgui.tree_node_ex("Filter", imgui.TreeNodeFlags_.default_open):
                self.endpoint_filter.gui()

                if imgui.button("Filter", (100, 30)):
                    self.controller.set_endpoint_filter(copy.deepcopy(self.endpoint_filter))
                imgui.same_line()
                if imgui.button("Cancel", (100, 30)):
                    self.endpoint_filter = None

                imgui.tree_pop()

        i = 0  # For button ids
        if imgui.begin_table("Endpoints", 3, View.table_flags, (0, 300)):
            imgui.table_header("URL")
            imgui.table_header("HTTP")
            imgui.table_header("Actions")

            for ep in self.controller.endpoints():
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.input_text("", ep.url, imgui.InputTextFlags_.read_only)

                imgui.table_next_column()
                imgui.text(ep.http_types())
                
                imgui.table_next_column()
                imgui.push_id(i)
                width = imgui.get_column_width()
                if imgui.button("Edit", (width / 2 - 5, 0)):
                    self.endpoint_edit = ep
                imgui.same_line()
                if imgui.button("Delete", (width / 2 - 5, 0)):
                    self.controller.remove_endpoint(ep)
                imgui.pop_id()
                i += 1
            imgui.end_table()

        if EndpointInput.edit(self.endpoint_edit, "Edit endpoint"):
            self.endpoint_edit = None

        if imgui.button("Test", (50, 30)):
            self.controller.start_testing()
        
        if self.controller.testing and imgui.button("Cancel", (50, 30)):
            self.controller.cancel_testing()

        imgui.end()


class StatusBar:
    def __init__(self, parent):
        self.controller = parent.controller
    
    def gui(self):
        if self.controller.progress is not None:
            imgui.begin("Status Bar")
            imgui.progress_bar(self.controller.progress)
            imgui.end()


class View:
    table_flags = imgui.TableFlags_.scroll_y | imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_outer | imgui.TableFlags_.borders_v | imgui.TableFlags_.resizable | imgui.TableFlags_.reorderable | imgui.TableFlags_.hideable

    def __init__(self):
        self.controller = Controller()
        self.tests = TestInputWindow(self)
        self.status_bar = StatusBar(self)

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def run(self):
        immapp.run(
                gui_function=partial(View.gui, self),
                window_title="Web Tester",
                window_size_auto=True,
                window_restore_previous_geometry=True)

    def gui(self):
        self.tests.gui()
        self.status_bar.gui()

    def cleanup(self):
        self.controller.cleanup()
