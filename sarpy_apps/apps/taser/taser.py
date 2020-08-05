import os

import tkinter
from tkinter.filedialog import askopenfilename
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, StringTupleDescriptor
from tk_builder.widgets.image_canvas import TOOLS
from tk_builder.widgets import widget_descriptors
from tk_builder.image_readers.image_reader import ImageReader
from tk_builder.widgets import basic_widgets
from tk_builder.panels.image_panel import ToolConstants
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.quad_pol_image_reader import QuadPolImageReader


class TaserButtonPanel(WidgetPanel):
    _widget_list = ("single_channel_fname_select",
                    "quad_pole_fname_select",
                    "rect_select",
                    "remap_dropdown")
    single_channel_fname_select = widget_descriptors.ButtonDescriptor("single_channel_fname_select")  # type: basic_widgets.Button
    quad_pole_fname_select = widget_descriptors.ButtonDescriptor("quad_pole_fname_select")  # type: basic_widgets.Button
    rect_select = widget_descriptors.ButtonDescriptor("rect_select")  # type: basic_widgets.Button
    remap_dropdown = widget_descriptors.ComboboxDescriptor("remap_dropdown")         # type: basic_widgets.Combobox

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()
        self.remap_dropdown.update_combobox_values(["density",
                                                    "brighter",
                                                    "darker",
                                                    "high contrast",
                                                    "linear",
                                                    "log",
                                                    "pedf",
                                                    "nrl"])


class AppVariables(object):
    fnames = StringTupleDescriptor(
        'fnames', default_value='None', docstring='')  # type: [str]
    remap_type = StringDescriptor(
        'remap_type', default_value='density', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', ImageReader, docstring='')  # type: ImageReader


class Taser(WidgetPanel):
    _widget_list = ("button_panel", "taser_image_panel", "pyplot_panel")
    button_panel = widget_descriptors.PanelDescriptor("button_panel", TaserButtonPanel)   # type: TaserButtonPanel
    taser_image_panel = widget_descriptors.ImagePanelDescriptor("taser_image_panel")   # type: ImagePanel
    pyplot_panel = widget_descriptors.PanelDescriptor("pyplot_panel", PyplotImagePanel)   # type: PyplotImagePanel

    def __init__(self, primary):
        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.variables = AppVariables()

        self.init_w_horizontal_layout()

        # define panels widget_wrappers in primary frame
        self.button_panel.set_spacing_between_buttons(0)
        self.taser_image_panel.image_frame.outer_canvas.set_canvas_size(700, 400)

        # bind events to callbacks here
        self.button_panel.single_channel_fname_select.on_left_mouse_click(self.callback_select_single_channel_file)
        self.button_panel.quad_pole_fname_select.on_left_mouse_click(self.callback_select_quadpole_files)
        self.button_panel.remap_dropdown.on_selection(self.callback_remap)
        self.button_panel.rect_select.on_left_mouse_click(self.callback_set_to_select)

        self.taser_image_panel.image_frame.outer_canvas.canvas.on_left_mouse_release(self.callback_left_mouse_release)
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.button_panel.pack(fill=tkinter.X, expand=tkinter.NO)
        self.taser_image_panel.resizeable = True

    def callback_left_mouse_release(self, event):
        self.taser_image_panel.image_frame.outer_canvas.canvas.callback_handle_left_mouse_release(event)
        if self.taser_image_panel.image_frame.outer_canvas.canvas.variables.current_tool == TOOLS.SELECT_TOOL:
            full_image_width = self.taser_image_panel.image_frame.outer_canvas.canvas.variables.canvas_width
            fill_image_height = self.taser_image_panel.image_frame.outer_canvas.canvas.variables.canvas_height
            self.taser_image_panel.\
                image_frame.\
                outer_canvas.\
                canvas.zoom_to_selection((0, 0, full_image_width, fill_image_height))
            self.display_canvas_rect_selection_in_pyplot_frame()

    # noinspection PyUnusedLocal
    def callback_set_to_select(self, event):
        self.taser_image_panel.current_tool = ToolConstants.SELECT_TOOL

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
        self.taser_image_panel.image_frame.outer_canvas.canvas.update_current_image()

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
        image_data = self.taser_image_panel.image_frame.outer_canvas.canvas.get_image_data_in_canvas_rect_by_id(
            self.taser_image_panel.image_frame.outer_canvas.canvas.variables.select_rect_id)
        self.pyplot_panel.update_image(image_data)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = Taser(root)
    root.after(200, app.taser_image_panel.update_everything)
    root.mainloop()
