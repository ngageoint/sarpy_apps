import os

import tkinter
from tkinter.filedialog import askopenfilename
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_canvas_panel import ImageCanvasPanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, StringTupleDescriptor
from tk_builder.widgets.image_canvas import TOOLS
from tk_builder.widgets import widget_descriptors
from tk_builder.image_readers.image_reader import ImageReader
from sarpy_apps.apps.taser.panels.taser_button_panel import TaserButtonPanel
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.quad_pol_image_reader import QuadPolImageReader


class AppVariables(object):
    fnames = StringTupleDescriptor(
        'fnames', default_value='None', docstring='')  # type: [str]
    remap_type = StringDescriptor(
        'remap_type', default_value='density', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', ImageReader, docstring='')  # type: ImageReader


class Taser(WidgetPanel):
    _widget_list = ("button_panel", "taser_image_panel", "pyplot_panel")
    button_panel = widget_descriptors.PanelDescriptor("button_panel", TaserButtonPanel)         # type: TaserButtonPanel
    taser_image_panel = widget_descriptors.ImageCanvasPanelDescriptor("taser_image_panel")         # type: ImageCanvasPanel
    pyplot_panel = widget_descriptors.PanelDescriptor("pyplot_panel", PyplotImagePanel)         # type: PyplotImagePanel

    def __init__(self, primary):
        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.variables = AppVariables()

        self.init_w_horizontal_layout()

        # define panels widget_wrappers in primary frame
        self.button_panel.set_spacing_between_buttons(0)
        self.taser_image_panel.set_canvas_size(700, 400)

        # need to pack both primary frame and self, since this is the main app window.
        primary_frame.pack()
        self.pack()

        # bind events to callbacks here
        self.button_panel.single_channel_fname_select.on_left_mouse_click(self.callback_select_single_channel_file)
        self.button_panel.quad_pole_fname_select.on_left_mouse_click(self.callback_select_quadpole_files)
        self.button_panel.remap_dropdown.on_selection(self.callback_remap)
        self.button_panel.zoom_in.on_left_mouse_click(self.callback_set_to_zoom_in)
        self.button_panel.zoom_out.on_left_mouse_click(self.callback_set_to_zoom_out)
        self.button_panel.pan.on_left_mouse_click(self.callback_set_to_pan)
        self.button_panel.rect_select.on_left_mouse_click(self.callback_set_to_select)

        self.taser_image_panel.canvas.on_left_mouse_release(self.callback_left_mouse_release)

    def callback_left_mouse_release(self, event):
        self.taser_image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.taser_image_panel.canvas.variables.current_tool == TOOLS.SELECT_TOOL:
            self.taser_image_panel.canvas.zoom_to_selection((0, 0, self.taser_image_panel.canvas.variables.canvas_width, self.taser_image_panel.canvas.variables.canvas_height))
            self.display_canvas_rect_selection_in_pyplot_frame()

    # noinspection PyUnusedLocal
    def callback_set_to_zoom_in(self, event):
        self.taser_image_panel.canvas.set_current_tool_to_zoom_in()

    # noinspection PyUnusedLocal
    def callback_set_to_zoom_out(self, event):
        self.taser_image_panel.canvas.set_current_tool_to_zoom_out()

    # noinspection PyUnusedLocal
    def callback_set_to_pan(self, event):
        self.taser_image_panel.canvas.set_current_tool_to_pan()
        self.taser_image_panel.canvas.hide_shape(self.taser_image_panel.canvas.variables.zoom_rect_id)

    # noinspection PyUnusedLocal
    def callback_set_to_select(self, event):
        self.taser_image_panel.canvas.set_current_tool_to_selection_tool()

    # define custom callbacks here
    # noinspection PyUnusedLocal
    def callback_remap(self, event):
        remap_dict = {"density": "density",
                      "brighter": "brighter",
                      "darker": "darker",
                      "high contrast": "highcontrast",
                      "linear": "linear",
                      "log": "log",
                      "pedf": "pedf",
                      "nrl": "nrl"}
        selection = self.button_panel.remap_dropdown.get()
        remap_type = remap_dict[selection]
        self.variables.image_reader.remap_type = remap_type
        self.display_canvas_rect_selection_in_pyplot_frame()
        self.taser_image_panel.canvas.update_current_image()

    # noinspection PyUnusedLocal
    def callback_select_single_channel_file(self, event):
        image_file_extensions = ['*.nitf', '*.NITF']
        ftypes = [
            ('image files', image_file_extensions),
            ('All files', '*'),
        ]
        new_fname = askopenfilename(initialdir=os.path.expanduser("~"), filetypes=ftypes)
        if new_fname:
            self.variables.fnames = [new_fname]
            self.variables.image_reader = ComplexImageReader(new_fname)
            self.taser_image_panel.set_image_reader(self.variables.image_reader)

    # noinspection PyUnusedLocal
    def callback_select_quadpole_files(self, event):
        image_file_extensions = ['*.nitf', '*.NITF']
        ftypes = [
            ('image files', image_file_extensions),
            ('All files', '*'),
        ]
        n_files = 4
        polarization_states = ['H:H', "H:V", "V:H", "V:V"]
        fnames = []
        for i in range(n_files):
            message = "please select " + polarization_states[i] + " file."
            new_fname = askopenfilename(initialdir=os.path.expanduser("~"), filetypes=ftypes, title=message)
            if new_fname:
                fnames.append(new_fname)
        self.variables.fnames = fnames
        self.variables.image_reader = QuadPolImageReader(self.variables.fnames)
        self.taser_image_panel.set_image_reader(self.variables.image_reader)

    def display_canvas_rect_selection_in_pyplot_frame(self):
        image_data = self.taser_image_panel.canvas.get_image_data_in_canvas_rect_by_id(self.taser_image_panel.canvas.variables.select_rect_id)
        self.pyplot_panel.update_image(image_data)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = Taser(root)
    root.mainloop()
