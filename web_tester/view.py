import copy

from .controller import Controller
from . import model
from http import HTTPStatus

from imgui_bundle import imgui, hello_imgui, imgui_color_text_edit as ed, portable_file_dialogs as pfd
TextEditor = ed.TextEditor
log = hello_imgui.log
LogLevel = hello_imgui.LogLevel


class Editors:
    editors = {}

    @classmethod
    def get_editor(cls, label: str) -> TextEditor:
        if cls.editors.get(label) is None:
            cls.editors[label] = TextEditor()
        return cls.editors[label]

    @classmethod
    def render_ed(cls, label: str, text: str, size: imgui.ImVec2 = (0, 0), language: TextEditor.LanguageDefinition = None) -> (bool, str):
        if language is None:
            changed, text = imgui.input_text_multiline("", text, size)
            return changed, text
            
        editor = cls.get_editor(label)
        editor.set_language_definition(language)

        if editor.is_text_changed() or editor.get_text() != text:
            editor.set_text(text)

        editor.render(label, False, size, False)

        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + 4)
        return editor.is_text_changed(), editor.get_text()


def dict_input(form: dict[str, str]):
    if imgui.button("Add"):
        i = 1
        while f"key_{i}" in form:
            i += 1
        form[f"key_{i}"] = "value"

    i = 0  # For button ids
    to_remove = None  # on delete button click
    if imgui.begin_table("Cookies", 3, View.table_flags, (0, 250)):
        imgui.table_setup_scroll_freeze(0, 1)
        imgui.table_setup_column("Key", imgui.TableColumnFlags_.none)
        imgui.table_setup_column("Value", imgui.TableColumnFlags_.none)
        imgui.table_setup_column("Actions", imgui.TableColumnFlags_.none)
        imgui.table_headers_row()
        
        changed_key = False
        old_key = ""
        new_key = ""
        changed_key_value = ""

        for k, v in form.items():
            if imgui.table_next_column():
                imgui.push_id(i + 0)

                imgui.set_next_item_width(-1)
                changed_key, new_key = imgui.input_text("", k)
                if changed_key:
                    old_key = k
                    changed_key_value = v

                imgui.pop_id()

            if imgui.table_next_column():
                imgui.push_id(i + 1)
                
                imgui.set_next_item_width(-1)
                changed, val = imgui.input_text("", v)
                if changed:
                    form[k] = val

                imgui.pop_id()

            if imgui.table_next_column():
                imgui.push_id(i + 2)

                if imgui.button("Delete", (-1, 0)):
                    to_remove = k

                imgui.pop_id()
            i += 3

        if to_remove is not None:
            form.pop(to_remove)

        if changed_key:
            form.pop(old_key)
            form[new_key] = changed_key_value

        imgui.end_table()


def read_only_dict(form: dict[str, str]):
    i = 0  # For button ids
    if imgui.begin_table("Cookies", 2, View.table_flags, (0, 250)):
        imgui.table_setup_scroll_freeze(0, 1)
        imgui.table_setup_column("Key", imgui.TableColumnFlags_.none)
        imgui.table_setup_column("Value", imgui.TableColumnFlags_.none)
        imgui.table_headers_row()

        for k, v in form.items():
            if imgui.table_next_column():
                imgui.push_id(i + 0)
                imgui.set_next_item_width(-1)
                imgui.input_text("", k, imgui.InputTextFlags_.read_only)

                imgui.pop_id()
            
            if imgui.table_next_column():
                imgui.push_id(i + 1)
                imgui.set_next_item_width(-1)
                imgui.input_text("", v, imgui.InputTextFlags_.read_only)

                imgui.pop_id()
            i += 2

        imgui.end_table()


def request_body_input(request: model.HTTPRequest):
    if request.http_type == model.HTTPType.DELETE:
        request.body = None
        imgui.text("DELETE requests don't have body")

    imgui.text("Type")  # type selection
    for v in model.RequestBodyType:
        imgui.same_line()
        s = imgui.radio_button(str(v), request.body_type == v)
        if s:
            request.body_type = v

    match request.body_type:
        case model.RequestBodyType.ORIGIN:
            if type(request.body) is not dict:
                request.body = {}
            dict_input(request.body)
        case model.RequestBodyType.JSON | model.RequestBodyType.RAW:
            if type(request.body) is not str:
                request.body = ""

            language = None
            if request.body_type == model.RequestBodyType.JSON:
                language = TextEditor.LanguageDefinition.json()

            imgui.push_id(0)
            changed, request.body = Editors.render_ed(
                "Request body",
                request.body,
                (-1, 250),
                language)

            if changed:
                request.prettify()

            imgui.pop_id()

def request_input(request: model.HTTPRequest):
    if imgui.begin_tab_bar("Request"):
        if imgui.begin_tab_item("Body")[0]:
            request_body_input(request)
            imgui.end_tab_item()
        if imgui.begin_tab_item("Cookies")[0]:
            dict_input(request.cookies)
            imgui.end_tab_item()

        if imgui.begin_tab_item("Headers")[0]:
            imgui.push_id(1)
            _, request.headers = Editors.render_ed(
                    "Request headers",
                    request.headers,
                    (-1, 250))
            imgui.pop_id()
            imgui.end_tab_item()

        imgui.end_tab_bar()

def response_input(response: model.HTTPResponse):
    cur_resp = list(HTTPStatus).index(response.http_status)
    changed, cur_resp = imgui.combo(
            label="Expected response",
            current_item=cur_resp,
            items=list(map(lambda x: f"{x.value} | {x.phrase}", HTTPStatus)))
    if changed:
        response.http_status = list(HTTPStatus)[cur_resp]

    if imgui.begin_tab_bar("Response"):
        if imgui.begin_tab_item("Body")[0]:
            imgui.text("Type")  # type selection
            for v in model.ResponseBodyType:
                imgui.same_line()
                s = imgui.radio_button(str(v), response.body_type == v)
                if s:
                    response.body_type = v

            language = None
            if response.body_type == model.ResponseBodyType.JSON:
                language = TextEditor.LanguageDefinition.json()

            imgui.push_id(0)
            changed, response.body = Editors.render_ed(
                "Response body",
                response.body,
                (-1, 250),
                language)

            if changed:
                response.prettify()

            imgui.pop_id()
            imgui.end_tab_item()

        if imgui.begin_tab_item("Cookies")[0]:
            dict_input(response.cookies)
            imgui.end_tab_item()

        if imgui.begin_tab_item("Headers")[0]:
            imgui.push_id(1)
            _, response.headers = Editors.render_ed(
                    "Response headers",
                    response.headers,
                    (-1, 250))
            imgui.pop_id()
            imgui.end_tab_item()

        imgui.end_tab_bar()

def read_only_request_body(request: model.HTTPRequest):
    if request.http_type == model.HTTPType.DELETE:
        request.body = None
        imgui.text("DELETE requests don't have body")

    imgui.text(f"Type: {request.body_type.name}")

    match request.body_type:
        case model.RequestBodyType.ORIGIN:
            if type(request.body) is not dict:
                request.body = {}
            read_only_dict(request.body)
        case model.RequestBodyType.JSON | model.RequestBodyType.RAW:
            if type(request.body) is not str:
                request.body = ""

            language = None
            match request.body_type:
                case model.ResponseBodyType.JSON:
                    language = TextEditor.LanguageDefinition.json()

            imgui.push_id(0)
            Editors.render_ed(
                "RO Request body",
                request.body,
                (-1, 250),
                language)

            imgui.pop_id()


def read_only_request(request: model.HTTPRequest):
    if request is None:
        return False

    ret = False

    if not imgui.is_popup_open("Request"):
        imgui.open_popup("Request")
    if imgui.begin_popup_modal("Request"):
        if imgui.begin_tab_bar("Request"):
            if imgui.begin_tab_item("Body")[0]:
                read_only_request_body(request)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Cookies")[0]:
                read_only_dict(request.cookies)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Headers")[0]:
                imgui.push_id(1)
                Editors.render_ed(
                        "RO Request headers",
                        request.headers,
                        (-1, 250))
                imgui.pop_id()
                imgui.end_tab_item()

            imgui.end_tab_bar()

            if imgui.button("Close"):
                ret = True

        imgui.end_popup()
    
    return ret

def read_only_response(response: model.HTTPResponse) -> bool:
    if response is None:
        return False

    ret = False

    if not imgui.is_popup_open("Response"):
        imgui.open_popup("Response")
    if imgui.begin_popup_modal("Response"):
        imgui.text(f"HTTP Status: {response.http_status.value} | {response.http_status.phrase}")

        if imgui.begin_tab_bar("Response"):
            if imgui.begin_tab_item("Body")[0]:
                imgui.text(f"Type: {response.body_type}")

                language = None
                match response.body_type:
                    case model.ResponseBodyType.JSON:
                        language = TextEditor.LanguageDefinition.json()

                imgui.push_id(0)
                Editors.render_ed(
                    "RO Response body",
                    response.body,
                    (-1, 250),
                    language)

                imgui.pop_id()

                imgui.end_tab_item()

            if imgui.begin_tab_item("Cookies")[0]:
                read_only_dict(response.cookies)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Headers")[0]:
                imgui.push_id(1)
                Editors.render_ed(
                        "RO Response headers",
                        response.headers,
                        (-1, 250))
                imgui.pop_id()
                imgui.end_tab_item()

            imgui.end_tab_bar()

            if imgui.button("Close"):
                ret = True

        imgui.end_popup()
    
    return ret


def fuzz_test(endpoint: model.Endpoint):
    if endpoint.interaction.request.http_type == model.HTTPType.DELETE:
        endpoint.fuzz_test = None
        return

    changed, fuzz_test = imgui.checkbox("Fuzz tests", endpoint.fuzz_test is not None)
    if changed:
        if fuzz_test:
            endpoint.fuzz_test = model.FuzzTest()
        else:
            endpoint.fuzz_test = None
    if fuzz_test:
        imgui.same_line()
        if imgui.tree_node("Details"):
            imgui.push_id(0)
            changed, endpoint.fuzz_test.count = imgui.input_int("Test count", endpoint.fuzz_test.count)
            if changed:
                endpoint.fuzz_test.count = max(1, endpoint.fuzz_test.count)
            imgui.pop_id()
            imgui.tree_pop()


def sqlinj_test(endpoint: model.Endpoint) -> ():
    static = sqlinj_test
    if not hasattr(static, "sqlinj_file_open"):
        static.sqlinj_file_open = None

    if endpoint.interaction.request.http_type == model.HTTPType.DELETE:
        endpoint.sqlinj_test = None
        return

    changed, test = imgui.checkbox("SQL injection tests", endpoint.sqlinj_test is not None)
    if changed:
        if test:
            endpoint.sqlinj_test = model.SQLInjectionTest()
        else:
            endpoint.sqlinj_test = None
    if test:
        imgui.same_line()
        if imgui.tree_node("Details"):
            imgui.push_id(0)
            changed, endpoint.sqlinj_test.count = imgui.input_int("Test count", endpoint.sqlinj_test.count)
            if changed:
                endpoint.sqlinj_test.count = max(1, endpoint.sqlinj_test.count)
            imgui.pop_id()

            imgui.push_id(1)
            imgui.input_text("Wordlist file", endpoint.sqlinj_test.wordlist.filename, imgui.InputTextFlags_.read_only)
            imgui.pop_id()

            imgui.same_line()
            if imgui.button("Open different"):
                static.sqlinj_file_open = pfd.open_file("Open a wordlist", "./fuzzdb/", ["*"])

            if static.sqlinj_file_open is not None and static.sqlinj_file_open.ready():
                if static.sqlinj_file_open.result() is not None and static.sqlinj_file_open.result() != []:  # can open multiple files
                    endpoint.sqlinj_test.wordlist = model.Wordlist(static.sqlinj_file_open.result()[0])
                    static.sqlinj_file_open = None

            imgui.tree_pop()


def endpoint_vulnerabilities_input(endpoint: model.Endpoint):
    _, endpoint.match_test = imgui.checkbox("Basic input/output match test", endpoint.match_test)
    imgui.push_id("fuzz_test")
    fuzz_test(endpoint)
    imgui.pop_id()
    imgui.push_id("sqlinj_test")
    sqlinj_test(endpoint)
    imgui.pop_id()


def edit_endpoint(endpoint: model.Endpoint, label: str) -> bool:
    static = edit_endpoint
    if not hasattr(static, "validation"):
        static.validation = ""

    if endpoint is None:
        return False

    request = endpoint.interaction.request
    response = endpoint.interaction.response

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

        if imgui.tree_node("Request"):
            request_input(request)
            imgui.tree_pop()

        if imgui.tree_node("Expected Response"):
            response_input(response)
            imgui.tree_pop()

        endpoint_vulnerabilities_input(endpoint)

        changed, endpoint.max_wait_time = imgui.input_int("Max wait time (seconds)", endpoint.max_wait_time)
        if changed:
            endpoint.max_wait_time = max(1, endpoint.max_wait_time)
        
        if imgui.button("Save", (50, 30)):
            static.validation = endpoint.validate()
            if static.validation == "":
                ret = True

        if static.validation != "":
            imgui.text_colored(imgui.ImVec4(255, 0, 0, 255), f"Failed to validate input:\n{static.validation}")
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


class TestResultFilterInput:
    def __init__(self, parent, filt: model.TestResultFilter = model.TestResultFilter("", None, 0)):
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

        _, self.filt.min_severity = imgui.combo(
            label="Min severity",
            current_item=self.filt.min_severity,
            items=list(map(lambda x: x.name, model.Severity)))


class TestInputWindow:
    def __init__(self, parent):
        self.controller = parent.controller

        self.endpoint_filter = None
        self.endpoint_add = None
        self.endpoint_edit = None
        self.validation = ""

    def gui(self):
        if imgui.button("Add Test", (0, 30)):
            self.endpoint_add = model.example_endpoint()
            
        if edit_endpoint(self.endpoint_add, "Add Test"):
            self.controller.add_endpoint(self.endpoint_add)
            self.endpoint_add = None

        imgui.same_line()

        if imgui.button("Filter Tests", (0, 30)):
            self.endpoint_filter = EndpointFilterInput(self)
        
        if self.endpoint_filter is not None:
            if imgui.tree_node_ex("Filter", imgui.TreeNodeFlags_.default_open):
                self.endpoint_filter.gui()

                if imgui.button("Filter", (100, 30)):
                    self.controller.set_endpoint_filter(copy.deepcopy(self.endpoint_filter.filt))
                imgui.same_line()
                if imgui.button("Cancel", (100, 30)):
                    self.endpoint_filter = None
                    self.controller.set_endpoint_filter(self.endpoint_filter)

                imgui.tree_pop()

        self.endpoint_table()

        if edit_endpoint(self.endpoint_edit, "Editing Test"):
            self.endpoint_edit = None

        if self.controller.model.endpoints != []:
            if not self.controller.in_progress:
                if imgui.button("Test", (50, 30)):
                    self.controller.start_testing()
            else:
                if imgui.button("Cancel", (50, 30)):
                    self.controller.cancel_testing()

    def endpoint_table(self):
        i = 0  # For button ids
        if imgui.begin_table("Tests", 4, View.table_flags, (0, 250)):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("URL", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("HTTP", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Test types", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Actions", imgui.TableColumnFlags_.none)
            imgui.table_headers_row()

            for ep in self.controller.endpoints():
                if imgui.table_next_column():
                    imgui.push_id(i + 0)
                    imgui.set_next_item_width(-1)
                    imgui.input_text("", ep.url, imgui.InputTextFlags_.read_only)
                    imgui.pop_id()

                if imgui.table_next_column():
                    imgui.text(ep.http_type())
                
                if imgui.table_next_column():
                    imgui.text(ep.test_types())
                
                if imgui.table_next_column():
                    imgui.push_id(i + 1)
                    width = imgui.get_column_width()
                    if imgui.button("Edit", (width / 2 - 5, 0)):
                        self.endpoint_edit = ep
                    imgui.same_line()
                    if imgui.button("Delete", (width / 2 - 5, 0)):
                        self.controller.remove_endpoint(ep)
                    imgui.pop_id()
                i += 2
            imgui.end_table()


class TestResultsWindow:
    def __init__(self, parent):
        self.controller = parent.controller

        self.endpoint_edit = None
        self.request_details = None
        self.response_details = None

        self.result_filter = None

    def results_table(self):
        i = 0  # For button ids
        if imgui.begin_table("Results", 6, View.table_flags, (0, -1)):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("URL", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Severity", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Verdict", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Response", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Elapsed time", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Error", imgui.TableColumnFlags_.none)
            imgui.table_headers_row()

            for tr in self.controller.test_results():
                if imgui.table_next_column():
                    imgui.push_id(i + 0)
                    imgui.input_text("", tr.endpoint.url, imgui.InputTextFlags_.read_only)
                    imgui.pop_id()

                    imgui.same_line()
                    imgui.text(tr.endpoint.http_type())

                    imgui.same_line()
                    imgui.push_id(i + 1)
                    if imgui.button("Edit"):
                        self.endpoint_edit = tr.endpoint
                    imgui.pop_id()

                    if id(tr.endpoint.interaction.request) != id(tr.diff_request):
                        imgui.push_id(i + 2)
                        imgui.same_line()
                        if imgui.button("Request details"):
                            self.request_details = tr.diff_request
                        imgui.pop_id()
                      
                if imgui.table_next_column():
                    imgui.text_colored(tr.color(), str(tr.severity))
                  
                if imgui.table_next_column():
                    imgui.text(tr.verdict)
                  
                if imgui.table_next_column():
                    if tr.response is None:
                        imgui.text("None")
                    else:
                        imgui.push_id(i + 3)
                        if imgui.button("Details", (-1, 0)):
                            self.response_details = tr.response
                        imgui.pop_id()

                if imgui.table_next_column():
                    imgui.text(str(tr.elapsed_time))
  
                if imgui.table_next_column():
                    imgui.push_id(i + 4)
                    imgui.set_next_item_width(-1)
                    imgui.input_text("", str(tr.error), imgui.InputTextFlags_.read_only)
                    imgui.pop_id()
                i += 5
            imgui.end_table()

            if read_only_response(self.response_details):
                self.response_details = None
            if read_only_request(self.request_details):
                self.request_details = None
            if edit_endpoint(self.endpoint_edit, "Editing endpoint"):
                self.endpoint_edit = None

    def gui(self):
        if self.controller.model.endpoints != []:
            if not self.controller.in_progress:
                if imgui.button("Test", (50, 30)):
                    self.controller.start_testing()
            else:
                if imgui.button("Cancel", (50, 30)):
                    self.controller.cancel_testing()

            imgui.same_line()

            if imgui.button("Filter Results", (0, 30)):
                self.result_filter = TestResultFilterInput(self)
        
        if self.result_filter is not None:
            if imgui.tree_node_ex("Filter", imgui.TreeNodeFlags_.default_open):
                self.result_filter.gui()

                if imgui.button("Filter", (100, 30)):
                    self.controller.set_result_filter(copy.deepcopy(self.result_filter.filt))
                imgui.same_line()
                if imgui.button("Cancel", (100, 30)):
                    self.result_filter = None
                    self.controller.set_result_filter(self.result_filter)

                imgui.tree_pop()

        self.results_table()
        

class View:
    table_flags = imgui.TableFlags_.scroll_y | imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_outer | imgui.TableFlags_.borders_v | imgui.TableFlags_.resizable | imgui.TableFlags_.reorderable | imgui.TableFlags_.hideable

    def __init__(self, controller: Controller = Controller()):
        self.controller = controller
        self.tests = TestInputWindow(self)
        self.results = TestResultsWindow(self)

        self.file_save = None
        self.file_open = None
        self.file_export = None

    def status_bar(self):
        if self.controller.in_progress:
            imgui.text("|/-\\"[round(imgui.get_time() / (1 / 8)) & 3])  # spinner
            imgui.same_line()
            imgui.set_cursor_pos_x(20)
            imgui.text("Running")
            imgui.same_line()
            imgui.progress_bar(self.controller.progress, (1000, 15))

    def menu(self):
        if imgui.begin_menu("File"):
            if imgui.menu_item("Save", "Ctrl+S", False)[0]:
                self.file_save = pfd.save_file("Select where to save", "", ["*.wt"])

            if imgui.menu_item("Open", "Ctrl+O", False)[0]:
                self.file_open = pfd.open_file("Open a save", "", ["*.wt"])

            imgui.separator()
            
            if imgui.menu_item("Export results", "", False, self.controller.model.results != [])[0]:
                self.file_export = pfd.save_file("Select where to export", "", ["*.docx"])

            imgui.end_menu()

        if self.file_save is not None and self.file_save.ready():
            if self.file_save.result() is not None and self.file_save.result() != "":
                self.controller.save(self.file_save.result())
                self.file_save = None

        if self.file_open is not None and self.file_open.ready():
            if self.file_open.result() is not None and self.file_open.result() != []:  # can open multiple files
                self.controller.open(self.file_open.result()[0])
                self.file_open = None

        if self.file_export is not None and self.file_export.ready():
            if self.file_export.result() is not None and self.file_export.result() != "":
                self.controller.export(self.file_export.result())
                self.file_export = None

    def app_menu(self):
        pass

    def run(self):
        runner_params = hello_imgui.RunnerParams()

        runner_params.app_window_params.window_title = "Web Tester"
        runner_params.imgui_window_params.menu_app_title = "Web Tester"
        runner_params.app_window_params.restore_previous_geometry = True

        runner_params.imgui_window_params.show_status_fps = False
        runner_params.imgui_window_params.show_status_bar = True
        runner_params.callbacks.show_status = lambda: self.status_bar()

        runner_params.imgui_window_params.show_menu_bar = True  # We use the default menu of Hello ImGui
        runner_params.callbacks.show_menus = lambda: self.menu()
        runner_params.callbacks.show_app_menu_items = lambda: self.app_menu()

        # First, tell HelloImGui that we want full screen dock space (this will create "MainDockSpace")
        runner_params.imgui_window_params.default_imgui_window_type = \
            hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
        # Set the default layout (this contains the default DockingSplits and DockableWindows)
        runner_params.docking_params = self.layout()

        # Part 3: Run the app
        hello_imgui.run(runner_params)

    def splits(self) -> list[hello_imgui.DockingSplit]:
        split_main_misc = hello_imgui.DockingSplit()
        split_main_misc.initial_dock = "MainDockSpace"
        split_main_misc.new_dock = "MiscSpace"
        split_main_misc.direction = imgui.Dir_.right
        split_main_misc.ratio = 0.25

        splits = [split_main_misc]
        return splits

    def windows(self) -> list[hello_imgui.DockableWindow]:
        test_w = hello_imgui.DockableWindow()
        test_w.label = "Test input window"
        test_w.dock_space_name = "MainDockSpace"
        test_w.gui_function = lambda: self.tests.gui()

        result_w = hello_imgui.DockableWindow()
        result_w.label = "Test results window"
        result_w.dock_space_name = "MainDockSpace"
        result_w.gui_function = lambda: self.results.gui()

        logs_w = hello_imgui.DockableWindow()
        logs_w.label = "Logs"
        logs_w.dock_space_name = "MiscSpace"
        logs_w.gui_function = hello_imgui.log_gui

        return [
            test_w,
            result_w,
            logs_w,
        ]

    def layout(self) -> hello_imgui.DockingParams:
        docking_params = hello_imgui.DockingParams()
        docking_params.layout_name = "Default"
        docking_params.docking_splits = self.splits()
        docking_params.dockable_windows = self.windows()
        return docking_params

    def cleanup(self):
        self.controller.cleanup()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()
