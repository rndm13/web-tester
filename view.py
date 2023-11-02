from functools import partial
import copy

from controller import Controller
import model

from imgui_bundle import imgui, immapp, imgui_color_text_edit as ed, portable_file_dialogs as pfd
TextEditor = ed.TextEditor


class EndpointInput(object):
    editor = TextEditor()
    validation = ""
        
    @classmethod
    def render_ed(cls, label: str, text: str, size: imgui.ImVec2 = (0, 0), language: TextEditor.LanguageDefinition = None) -> str:
        if language is None:
            changed, i = imgui.input_text_multiline("", text, size)
            return i
            
        cls.editor.set_language_definition(language)
        cls.editor.set_text(text)
        cls.editor.render(label, False, size, False)
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + 4)
        return cls.editor.get_text()

    @classmethod
    def request_input(cls, request: model.HTTPRequest):
        if imgui.begin_tab_bar("Request"):
            tab, _ = imgui.begin_tab_item("Header")
            if tab:
                request.header = cls.render_ed(
                        "Header",
                        request.header,
                        (-1, 250))
                imgui.end_tab_item()

            tab, _ = imgui.begin_tab_item("Body")
            if tab:
                _, request.body_json = imgui.checkbox("JSON", request.body_json)

                language = None
                if request.body_json:
                    language = cls.editor.LanguageDefinition.json()

                request.body = cls.render_ed(
                    "Body",
                    request.body,
                    (-1, 250),
                    language)

                imgui.end_tab_item()

            tab, _ = imgui.begin_tab_item("Cookies")
            if tab:
                if imgui.button("Add new cookie!"):
                    request.cookies["New"] = "Cookie"

                i = 0  # For button ids
                to_remove = None  # on delete button click
                if imgui.begin_table("Cookies", 3, View.table_flags, (0, 250)):
                    imgui.table_header("Key")
                    imgui.table_header("Value")
                    imgui.table_header("Actions")

                    for k, v in request.cookies.items():
                        imgui.push_id(i + 0)

                        imgui.table_next_column()
                        imgui.set_next_item_width(-1)
                        changed, t_k = imgui.input_text("", k)
                        if changed:
                            request.cookies.pop(k)
                            k = t_k
                            request.cookies[k] = v

                        imgui.pop_id()
                        imgui.push_id(i + 1)
                        
                        imgui.table_next_column()
                        imgui.set_next_item_width(-1)
                        changed, t_v = imgui.input_text("", v)
                        if changed:
                            request.cookies[k] = t_v

                        imgui.pop_id()
                        imgui.push_id(i + 2)

                        imgui.table_next_column()
                        if imgui.button("Delete", (-1, 0)):
                            to_remove = k

                        imgui.pop_id()
                        i += 3
                    if to_remove is not None:
                        request.cookies.pop(to_remove)

                    imgui.end_table()

                imgui.end_tab_item()

            imgui.end_tab_bar()

    @classmethod
    def edit(cls, endpoint: model.Endpoint, label: str) -> bool:
        if endpoint is None:
            return False

        request = endpoint.interaction.request
        response = endpoint.interaction.expected_response

        ret = False

        if not imgui.is_popup_open(label):
            imgui.open_popup(label)
        if imgui.begin_popup_modal(label):
            changed, endpoint.url = imgui.input_text("URL", endpoint.url)
            
            imgui.text("HTTP Types")
            for v in model.HTTPType:
                imgui.same_line()
                s = imgui.radio_button(str(v), request.http_type == v)
                if s:
                    request.http_type = v

            cls.request_input(request)
            
            # changed, endpoint.get = imgui.checkbox("GET", endpoint.get)
            # if endpoint.get and imgui.tree_node("GET request"):
            #     endpoint.get_interaction.request.render_ed(EndpointInput.editor, "GET request")
            #     imgui.tree_pop()
            #
            # changed, endpoint.post = imgui.checkbox("POST", endpoint.post)
            # if endpoint.post and imgui.tree_node("POST request"):
            #     endpoint.post_interaction.request.render_ed(EndpointInput.editor, "POST request")
            #     imgui.tree_pop()

            if imgui.button("Save", (50, 30)):
                EndpointInput.validation = endpoint.validate()
                if EndpointInput.validation == "":
                    ret = True

            if EndpointInput.validation != "":
                imgui.text_colored(imgui.ImVec4(255, 0, 0, 255), f"Failed to validate input:\n{EndpointInput.validation}")
            imgui.end_popup()

        return ret


class EndpointFilterInput:
    def __init__(self, parent, filt: model.EndpointFilter = model.EndpointFilter("", None)):
        self.controller = parent.controller
        self.filt = filt
        self.spec_type = False

    def gui(self) -> bool:
        _, self.filt.url = imgui.input_text("URL", self.filt.url)

        changed, self.spec_type = imgui.checkbox("Specify http types?", self.spec_type)
        if changed:
            if self.spec_type:
                self.filt.http_type = model.HTTPType.GET
            else:
                self.filt.http_type = None

        if self.spec_type:
            for v in model.HTTPType:
                imgui.same_line()
                s = imgui.radio_button(str(v), self.filt.http_type == v)
                if s:
                    self.filt.http_type = v


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

            imgui.text(f"(FPS: {round(1 / imgui.get_io().delta_time, 1)})")

            imgui.end_menu_bar()

        if self.file_save is not None and self.file_save.ready():
            if self.file_save.result() is not None:
                self.controller.save(self.file_save.result())
                self.file_save = None

        if self.file_open is not None and self.file_open.ready():
            if self.file_open.result() is not None and len(self.file_open.result()) > 0:
                self.controller.open(self.file_open.result()[0])
                self.file_open = None

    def gui(self):
        imgui.begin("Tests", 0, imgui.WindowFlags_.menu_bar)

        self.menu()

        if imgui.button("Add endpoint", (0, 30)):
            self.endpoint_add = model.example_endpoint()
            
        if EndpointInput.edit(self.endpoint_add, "Add endpoint"):
            self.controller.add_endpoint(self.endpoint_add)
            self.endpoint_add = None

        imgui.same_line()

        if imgui.button("Search endpoints", (0, 30)):
            self.endpoint_filter = EndpointFilterInput(self)
        
        if self.endpoint_filter is not None:
            if imgui.tree_node_ex("Filter", imgui.TreeNodeFlags_.default_open):
                self.endpoint_filter.gui()

                if imgui.button("Filter", (100, 30)):
                    self.controller.set_endpoint_filter(copy.deepcopy(self.endpoint_filter.filt))
                imgui.same_line()
                if imgui.button("Cancel", (100, 30)):
                    self.endpoint_filter = None

                imgui.tree_pop()

        self.endpoint_table()

        if EndpointInput.edit(self.endpoint_edit, "Edit endpoint"):
            self.endpoint_edit = None

        if self.controller.model.endpoints != []:
            if not self.controller.in_progress:
                if imgui.button("Test", (50, 30)):
                    self.controller.start_basic_testing()
            else:
                if imgui.button("Cancel", (50, 30)):
                    self.controller.cancel_testing()

        imgui.end()

    def endpoint_table(self):

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
                imgui.text(ep.http_type())
                
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


class StatusBar:
    def __init__(self, parent):
        self.controller = parent.controller
    
    def gui(self):
        if self.controller.progress is not None:
            imgui.begin("Status Bar")
            if not self.controller.in_progress:
                imgui.text("Stopped")
            else:
                imgui.text("|/-\\"[round(imgui.get_time() / (1 / 8)) & 3])
                imgui.same_line()
                imgui.text("Running")
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
