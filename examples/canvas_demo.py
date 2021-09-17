import os

import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename

import numpy

from tk_builder.base_elements import StringDescriptor, IntegerDescriptor, TypedDescriptor
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.utils.geometry_utils.kml_util import KmlUtil
from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.widgets.image_canvas import ShapeTypeConstants

from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader

import sarpy.geometry.point_projection as point_projection
import sarpy.geometry.geocoords as geocoords
import sarpy.visualization.remap as remap


__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class CanvasDemoButtonPanel(WidgetPanel):
    _widget_list = ("fname_select",
                    "rect_select",
                    "draw_line",
                    "draw_arrow",
                    "draw_rect",
                    "draw_polygon",
                    "draw_point",
                    "edit",
                    "color_selector",
                    "remap_dropdown",
                    )
    fname_select = widget_descriptors.ButtonDescriptor("fname_select")  # type: basic_widgets.Button
    rect_select = widget_descriptors.ButtonDescriptor("rect_select")  # type: basic_widgets.Button
    draw_line = widget_descriptors.ButtonDescriptor("draw_line")  # type: basic_widgets.Button
    draw_arrow = widget_descriptors.ButtonDescriptor("draw_arrow")  # type: basic_widgets.Button
    draw_rect = widget_descriptors.ButtonDescriptor("draw_rect")  # type: basic_widgets.Button
    draw_polygon = widget_descriptors.ButtonDescriptor("draw_polygon")  # type: basic_widgets.Button
    draw_point = widget_descriptors.ButtonDescriptor("draw_point")  # type: basic_widgets.Button
    color_selector = widget_descriptors.ButtonDescriptor("color_selector")      # type: basic_widgets.Button
    edit = widget_descriptors.ButtonDescriptor("edit")      # type: basic_widgets.Button
    remap_dropdown = widget_descriptors.ComboboxDescriptor("remap_dropdown")         # type: basic_widgets.Combobox

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(2, column_widths=20)

        self.remap_dropdown.update_combobox_values(["density",
                                                    "brighter",
                                                    "darker",
                                                    "high contrast",
                                                    "linear",
                                                    "log",
                                                    "pedf",
                                                    "nrl"])


class AppVariables(object):
    """
    The canvas demo app variables.
    """

    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'))  # type: str
    selection_rect_id = IntegerDescriptor(
        'selection_rect_id', docstring='')  # type: int
    image_reader = TypedDescriptor(
        'image_reader', ComplexCanvasImageReader, docstring='')  # type: ComplexCanvasImageReader

    def __init__(self):
        self.shapes_in_selector = []


class CanvasDemo(WidgetPanel):
    _widget_list = ("button_panel", "canvas_demo_image_panel", "pyplot_panel")
    button_panel = widget_descriptors.PanelDescriptor("button_panel", CanvasDemoButtonPanel)  # type: CanvasDemoButtonPanel
    pyplot_panel = widget_descriptors.PyplotImagePanelDescriptor("pyplot_panel")   # type: PyplotImagePanel
    canvas_demo_image_panel = widget_descriptors.ImagePanelDescriptor("canvas_demo_image_panel")   # type: ImagePanel

    def __init__(self, primary):
        primary_frame = basic_widgets.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.variables = AppVariables()

        self.init_w_horizontal_layout()
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.button_panel.pack(fill=tkinter.X, expand=tkinter.NO)
        self.pyplot_panel.pack(expand=tkinter.YES)
        self.canvas_demo_image_panel.pack(expand=tkinter.YES)

        # bind events to callbacks here
        self.button_panel.fname_select.config(command=self.callback_initialize_canvas_image)
        self.button_panel.rect_select.config(command=self.callback_set_to_select)

        self.button_panel.draw_line.config(command=self.callback_draw_line)
        self.button_panel.draw_arrow.config(command=self.callback_draw_arrow)
        self.button_panel.draw_rect.config(command=self.callback_draw_rect)
        self.button_panel.draw_polygon.config(command=self.callback_draw_polygon)
        self.button_panel.draw_point.config(command=self.callback_draw_point)
        self.button_panel.edit.config(command=self.callback_edit)
        self.button_panel.color_selector.config(command=self.callback_activate_color_selector)
        self.button_panel.remap_dropdown.on_selection(self.callback_remap)

        self.canvas_demo_image_panel.canvas.on_left_mouse_click(self.callback_handle_canvas_left_mouse_click)
        self.canvas_demo_image_panel.canvas.on_left_mouse_release(self.callback_handle_canvas_left_mouse_release)

    def callback_save_kml(self):
        kml_save_fname = asksaveasfilename(initialdir=os.path.expanduser("~/Downloads"))

        kml_util = KmlUtil()

        for shape_id in self.canvas_demo_image_panel.canvas.variables.shape_ids:
            image_coords = self.canvas_demo_image_panel.canvas.get_shape_image_coords(shape_id)
            shape_type = self.canvas_demo_image_panel.canvas.get_shape_type(shape_id)
            if image_coords:
                sicd_meta = self.canvas_demo_image_panel.canvas.variables.canvas_image_object.reader_object.sicdmeta
                image_points = numpy.zeros((int(len(image_coords)/2), 2))
                image_points[:, 0] = image_coords[0::2]
                image_points[:, 1] = image_coords[1::2]

                ground_points_ecf = point_projection.image_to_ground(image_points, sicd_meta)
                ground_points_latlon = geocoords.ecf_to_geodetic(ground_points_ecf)

                world_y_coordinates = ground_points_latlon[:, 0]
                world_x_coordinates = ground_points_latlon[:, 1]

                xy_point_list = [(x, y) for x, y in zip(world_x_coordinates, world_y_coordinates)]

                if shape_id == self.canvas_demo_image_panel.canvas.variables.zoom_rect.uid:
                    pass
                elif shape_type == self.canvas_demo_image_panel.canvas.variables.select_rect.uid:
                    pass
                elif shape_type == ShapeTypeConstants.POINT:
                    kml_util.add_point(str(shape_id), xy_point_list[0])
                elif shape_type == ShapeTypeConstants.LINE:
                    kml_util.add_linestring(str(shape_id), xy_point_list)
                elif shape_type == ShapeTypeConstants.POLYGON:
                    kml_util.add_polygon(str(shape_id), xy_point_list)
                elif shape_type == ShapeTypeConstants.RECT:
                    kml_util.add_polygon(str(shape_id), xy_point_list)
        kml_util.write_to_file(kml_save_fname)

    def callback_handle_canvas_left_mouse_click(self, event):
        self.canvas_demo_image_panel.canvas.callback_handle_left_mouse_click(event)
        current_shape = self.canvas_demo_image_panel.canvas.current_shape_id
        if current_shape:
            self.variables.shapes_in_selector.append(current_shape)
            self.variables.shapes_in_selector = sorted(list(set(self.variables.shapes_in_selector)))

    def callback_handle_canvas_left_mouse_release(self, event):
        self.canvas_demo_image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.canvas_demo_image_panel.canvas.variables.select_rect.uid == self.canvas_demo_image_panel.canvas.current_shape_id:
            self.update_selection()

    def callback_edit(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_edit_shape(select_closest_first=True)

    def callback_activate_color_selector(self):
        self.canvas_demo_image_panel.canvas.activate_color_selector()

    def callback_draw_line(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_line()

    def callback_draw_arrow(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_arrow()

    def callback_draw_rect(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_rect()

    def callback_draw_polygon(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_polygon()

    def callback_draw_point(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_point()

    def callback_set_to_select(self):
        self.canvas_demo_image_panel.canvas.current_tool = 'SELECT'

    # define custom callbacks here
    def callback_remap(self):
        self.update_selection()

    def update_selection(self):
        remap_dict = {entry[0]: entry[1] for entry in remap.get_remap_list()}
        selection = self.button_panel.remap_dropdown.get()
        self.variables.image_reader.set_remap_type(remap_dict[selection])
        image_data = self.canvas_demo_image_panel.canvas.get_image_data_in_canvas_rect_by_id(
            self.canvas_demo_image_panel.canvas.variables.select_rect.uid)
        self.pyplot_panel.update_image(image_data)
        self.canvas_demo_image_panel.canvas.update_current_image()

    def callback_initialize_canvas_image(self):
        image_file_extensions = ['*.nitf', '*.NITF', '*.ntf', '*.NTF']
        ftypes = [
            ('NITF files', image_file_extensions),
            ('All files', '*'),
        ]
        new_fname = askopenfilename(initialdir=self.variables.browse_directory, filetypes=ftypes)
        if new_fname:
            self.variables.browse_directory = os.path.split(new_fname)[0]
            self.variables.image_reader = ComplexCanvasImageReader(new_fname)
            self.canvas_demo_image_panel.set_image_reader(self.variables.image_reader)


def main():
    root = tkinter.Tk()
    app = CanvasDemo(root)
    root.mainloop()


if __name__ == '__main__':
    main()
