from functools import partial
from imgui_bundle import imgui, immapp


class View:
    def run(self):
        immapp.run(
                gui_function=partial(View.gui, self),
                window_title="Music recommendation",
                window_size_auto=True)

    def gui(self):
        self.test()

    def test(self):
        imgui.begin("Test")
        imgui.text("Hello world!")
        imgui.end()
