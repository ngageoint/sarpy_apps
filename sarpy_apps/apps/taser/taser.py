import os

import tkinter
from tkinter.filedialog import askopenfilenames

from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, StringTupleDescriptor
from tk_builder.widgets.image_canvas import TOOLS
from tk_builder.widgets import widget_descriptors
from tk_builder.image_readers.image_reader import ImageReader
from tk_builder.widgets import basic_widgets
from tk_builder.panels.image_panel import ToolConstants

from sarpy_apps.supporting_classes.image_reader import ComplexImageReader, QuadPolImageReader
import sarpy.visualization.remap as remap

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class TaserButtonPanel(WidgetPanel):
    _widget_list = ("fname_select",
                    "rect_select",
                    "remap_dropdown")
    fname_select = widget_descriptors.ButtonDescriptor("fname_select")  # type: basic_widgets.Button
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

        # bind events to callbacks here
        self.button_panel.fname_select.config(command=self.callback_select_files)
        self.button_panel.remap_dropdown.on_selection(self.callback_remap)
        self.button_panel.rect_select.config(command=self.callback_set_to_select)

        self.taser_image_panel.canvas.on_left_mouse_release(self.callback_left_mouse_release)
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.button_panel.pack(fill=tkinter.X, expand=tkinter.NO)
        self.taser_image_panel.resizeable = True

    def callback_left_mouse_release(self, event):
        self.taser_image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.taser_image_panel.canvas.variables.current_tool == TOOLS.SELECT_TOOL:
            full_image_width = self.taser_image_panel.canvas.variables.canvas_width
            fill_image_height = self.taser_image_panel.canvas.variables.canvas_height
            self.taser_image_panel.canvas.zoom_to_canvas_selection((0, 0, full_image_width, fill_image_height))
            self.display_canvas_rect_selection_in_pyplot_frame()

    # noinspection PyUnusedLocal
    def callback_set_to_select(self):
        self.taser_image_panel.current_tool = ToolConstants.SELECT_TOOL

    # define custom callbacks here
    # noinspection PyUnusedLocal
    def callback_remap(self, event):
        remap_dict = {entry: entry for entry in remap.get_remap_list()}
        selection = self.button_panel.remap_dropdown.get()
        remap_type = remap_dict[selection]
        self.variables.image_reader.set_remap_type(remap_type)
        self.display_canvas_rect_selection_in_pyplot_frame()
        self.taser_image_panel.canvas.update_current_image()

    def callback_select_files(self):
        image_file_extensions = ['*.nitf', '*.ntf', '*.NITF', '*.NTF']
        ftypes = [
            ('image files', image_file_extensions),
            ('All files', '*')]

        fnames = askopenfilenames(initialdir=os.path.expanduser("~"), filetypes=ftypes)

        # TODO: handle non-complex data possibilities here
        if fnames:
            if len(fnames) == 1:
                self.variables.image_reader = ComplexImageReader(fnames[0])
            else:
                self.variables.image_reader = QuadPolImageReader(fnames)
            self.taser_image_panel.set_image_reader(self.variables.image_reader)

    def display_canvas_rect_selection_in_pyplot_frame(self):
        image_data = self.taser_image_panel.canvas.get_image_data_in_canvas_rect_by_id(
            self.taser_image_panel.canvas.variables.select_rect_id)
        self.pyplot_panel.update_image(image_data)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = Taser(root)
    root.mainloop()
