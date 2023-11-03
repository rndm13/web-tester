import copy

from controller import Controller
import model
from http import HTTPStatus

from imgui_bundle import imgui, hello_imgui, imgui_color_text_edit as ed, portable_file_dialogs as pfd
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
    def cookies(cls, cookies: dict[str, str]):
        if imgui.button("Add new cookie!"):
            i = 1
            while f"key_{i}" in cookies:
                i += 1
            cookies[f"key_{i}"] = "value"

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

            for k, v in cookies.items():
                imgui.push_id(i + 0)

                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                changed_key, new_key = imgui.input_text("", k)
                if changed_key:
                    old_key = k
                    changed_key_value = v

                imgui.pop_id()
                imgui.push_id(i + 1)
                
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                changed, val = imgui.input_text("", v)
                if changed:
                    cookies[k] = val

                imgui.pop_id()
                imgui.push_id(i + 2)

                imgui.table_next_column()
                if imgui.button("Delete", (-1, 0)):
                    to_remove = k

                imgui.pop_id()
                i += 3

            if to_remove is not None:
                cookies.pop(to_remove)

            if changed_key:
                cookies.pop(old_key)
                cookies[new_key] = changed_key_value

            imgui.end_table()

    @classmethod
    def read_only_cookies(cls, cookies: dict[str, str]):
        i = 0  # For button ids
        if imgui.begin_table("Cookies", 2, View.table_flags, (0, 250)):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("Key", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Value", imgui.TableColumnFlags_.none)
            imgui.table_headers_row()

            for k, v in cookies.items():
                imgui.push_id(i + 0)

                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.input_text("", k, imgui.InputTextFlags_.read_only)

                imgui.pop_id()
                imgui.push_id(i + 1)
                
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.input_text("", v, imgui.InputTextFlags_.read_only)

                imgui.pop_id()
                i += 2

            imgui.end_table()


    @classmethod
    def request_input(cls, request: model.HTTPRequest):
        if imgui.begin_tab_bar("Request"):
            if imgui.begin_tab_item("Body")[0]:
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

            if imgui.begin_tab_item("Cookies")[0]:
                cls.cookies(request.cookies)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Headers")[0]:
                request.headers = cls.render_ed(
                        "Headers",
                        request.headers,
                        (-1, 250))
                imgui.end_tab_item()

            imgui.end_tab_bar()

    @classmethod
    def response_input(cls, response: model.HTTPResponse):
        cur_resp = list(HTTPStatus).index(response.http_status)
        changed, cur_resp = imgui.combo(
                label="Expected response",
                current_item=cur_resp,
                items=list(map(lambda x: f"{x.value} | {x.phrase}", HTTPStatus)))
        if changed:
            response.http_status = list(HTTPStatus)[cur_resp]

        if imgui.begin_tab_bar("Response"):
            if imgui.begin_tab_item("Body")[0]:
                _, response.body_json = imgui.checkbox("JSON", response.body_json)

                language = None
                if response.body_json:
                    language = cls.editor.LanguageDefinition.json()

                response.body = cls.render_ed(
                    "Body",
                    response.body,
                    (-1, 250),
                    language)

                imgui.end_tab_item()

            if imgui.begin_tab_item("Cookies")[0]:
                cls.cookies(response.cookies)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Headers")[0]:
                response.headers = cls.render_ed(
                        "Headers",
                        response.headers,
                        (-1, 250))
                imgui.end_tab_item()

            imgui.end_tab_bar()

    @classmethod
    def read_only_response(cls, response: model.HTTPResponse) -> bool:
        if response is None:
            return False

        ret = False

        if not imgui.is_popup_open("Response"):
            imgui.open_popup("Response")
        if imgui.begin_popup_modal("Response"):
            imgui.text(f"HTTP Status: {response}")

            if imgui.begin_tab_bar("Response"):
                if imgui.begin_tab_item("Body")[0]:
                    imgui.checkbox("JSON", response.body_json)

                    language = None
                    if response.body_json:
                        language = cls.editor.LanguageDefinition.json()

                    cls.render_ed(
                        "Body",
                        response.body,
                        (-1, 250),
                        language)

                    imgui.end_tab_item()

                if imgui.begin_tab_item("Cookies")[0]:
                    cls.read_only_cookies(response.cookies)
                    imgui.end_tab_item()

                if imgui.begin_tab_item("Headers")[0]:
                    cls.render_ed(
                            "Headers",
                            response.headers,
                            (-1, 250))
                    imgui.end_tab_item()

                imgui.end_tab_bar()

                if imgui.button("Close"):
                    ret = True

            imgui.end_popup()
        
        return ret

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

            if imgui.tree_node("Request"):
                cls.request_input(request)
                imgui.tree_pop()

            if imgui.tree_node("Expected Response"):
                cls.response_input(response)
                imgui.tree_pop()
            
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

    def gui(self):
        if imgui.button("Add Test", (0, 30)):
            self.endpoint_add = model.example_endpoint()
            
        if EndpointInput.edit(self.endpoint_add, "Add Test"):
            self.controller.add_endpoint(self.endpoint_add)
            self.endpoint_add = None

        imgui.same_line()

        if imgui.button("Search Tests", (0, 30)):
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

        if EndpointInput.edit(self.endpoint_edit, "Edit Test"):
            self.endpoint_edit = None

        if self.controller.model.endpoints != []:
            if not self.controller.in_progress:
                if imgui.button("Test", (50, 30)):
                    self.controller.start_basic_testing()
            else:
                if imgui.button("Cancel", (50, 30)):
                    self.controller.cancel_testing()

    def endpoint_table(self):

        i = 0  # For button ids
        if imgui.begin_table("Tests", 3, View.table_flags, (0, 250)):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("URL", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("HTTP", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Actions", imgui.TableColumnFlags_.none)
            imgui.table_headers_row()

            for ep in self.controller.endpoints():
                imgui.push_id(i + 0)
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.input_text("", ep.url, imgui.InputTextFlags_.read_only)
                imgui.pop_id()

                imgui.table_next_column()
                imgui.text(ep.http_type())
                
                imgui.table_next_column()
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

        self.response_details = None

    def results_table(self):
        i = 0  # For button ids
        if imgui.begin_table("Results", 7, View.table_flags, (0, 250)):
            imgui.table_setup_scroll_freeze(0, 1)
            imgui.table_setup_column("URL", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("HTTP", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Severity", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Verdict", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Response", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Error", imgui.TableColumnFlags_.none)
            imgui.table_setup_column("Actions", imgui.TableColumnFlags_.none)
            imgui.table_headers_row()

            for tr in self.controller.test_results():
                color = tr.color()

                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.push_id(i + 0)
                imgui.input_text("", tr.endpoint.url, imgui.InputTextFlags_.read_only)
                imgui.pop_id()

                imgui.table_next_column()
                imgui.text_colored(color, tr.endpoint.http_type())
                  
                imgui.table_next_column()
                imgui.text_colored(color, str(tr.severity))
                  
                imgui.table_next_column()
                imgui.text_colored(color, tr.verdict)
                  
                imgui.table_next_column()
                if tr.response is None:
                    imgui.text_colored(color, "None")
                else:
                    if imgui.button("Details"):
                        self.response_details = tr.response
  
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                imgui.push_id(i + 1)
                imgui.input_text("", str(tr.error), imgui.InputTextFlags_.read_only)
                imgui.pop_id()
                  
                # imgui.push_id(i + 1)
                imgui.table_next_column()
                imgui.text_colored(color, "TODO!")
                # imgui.pop_id()
                i += 2
            imgui.end_table()

            if EndpointInput.read_only_response(self.response_details):
                self.response_details = None

    def gui(self):
        if self.controller.model.endpoints != []:
            if not self.controller.in_progress:
                if imgui.button("Test", (50, 30)):
                    self.controller.start_basic_testing()
            else:
                if imgui.button("Cancel", (50, 30)):
                    self.controller.cancel_testing()

        self.results_table()
        

class View:
    table_flags = imgui.TableFlags_.scroll_y | imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_outer | imgui.TableFlags_.borders_v | imgui.TableFlags_.resizable | imgui.TableFlags_.reorderable | imgui.TableFlags_.hideable

    def __init__(self, controller: Controller = Controller()):
        self.controller = controller
        self.tests = TestInputWindow(self)
        self.results = TestResultsWindow(self)

        self.file_save = None
        self.file_open = None

    def status_bar(self):
        if self.controller.in_progress:
            imgui.text("|/-\\"[round(imgui.get_time() / (1 / 8)) & 3])
            imgui.same_line()
            imgui.set_cursor_pos_x(20)
            imgui.text("Running")
            imgui.progress_bar(self.controller.progress)

    def menu(self):
        if imgui.begin_menu("File"):
            if imgui.menu_item("Save", "Ctrl+S", False)[0]:
                self.file_save = pfd.save_file("Select where to save", "", ["*.wt"])

            if imgui.menu_item("Open", "Ctrl+O", False)[0]:
                self.file_open = pfd.open_file("Open a save", "", ["*.wt"])
            imgui.end_menu()

        if imgui.begin_menu("Test"):
            if imgui.menu_item("Basic tests", "", False)[0]:
                self.controller.start_basic_testing()
            imgui.end_menu()

        if self.file_save is not None and self.file_save.ready():
            if self.file_save.result() is not None and self.file_save.result() != "":
                self.controller.save(self.file_save.result())
                self.file_save = None

        if self.file_open is not None and self.file_open.ready():
            if self.file_open.result() is not None and self.file_open.result() != []:  # can open multiple files
                self.controller.open(self.file_open.result()[0])
                self.file_open = None

    def app_menu(self):
        imgui.text("Hello!\nI should probably add about here or something...")
        pass

    def run(self):
        runner_params = hello_imgui.RunnerParams()

        runner_params.app_window_params.window_title = "Web Tester"
        runner_params.imgui_window_params.menu_app_title = "Web Tester"
        runner_params.app_window_params.restore_previous_geometry = True

        runner_params.imgui_window_params.show_status_bar = True
        runner_params.callbacks.show_status = lambda: self.status_bar()

        # runner_params.im_gui_window_params.show_status_fps = False

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
