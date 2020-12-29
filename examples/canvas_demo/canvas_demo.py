import os

import tkinter
from tkinter.filedialog import askopenfilename
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.utils.geometry_utils.kml_util import KmlUtil
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.base_elements import StringDescriptor, IntegerDescriptor, TypedDescriptor
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader

import sarpy.geometry.point_projection as point_projection
import sarpy.geometry.geocoords as geocoords
import sarpy.visualization.remap as remap

import numpy

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class CanvasDemoButtonPanel(WidgetPanel):
    _widget_list = ("fname_select",
                    "rect_select",
                    "draw_line_w_drag",
                    "draw_line_w_click",
                    "draw_arrow_w_drag",
                    "draw_arrow_w_click",
                    "draw_rect_w_drag",
                    "draw_rect_w_click",
                    "draw_polygon_w_click",
                    "draw_point",
                    "edit",
                    "color_selector",
                    "remap_dropdown",
                    )
    fname_select = widget_descriptors.ButtonDescriptor("fname_select")  # type: basic_widgets.Button
    rect_select = widget_descriptors.ButtonDescriptor("rect_select")  # type: basic_widgets.Button
    draw_line_w_drag = widget_descriptors.ButtonDescriptor("draw_line_w_drag")  # type: basic_widgets.Button
    draw_line_w_click = widget_descriptors.ButtonDescriptor("draw_line_w_click")  # type: basic_widgets.Button
    draw_arrow_w_drag = widget_descriptors.ButtonDescriptor("draw_arrow_w_drag")  # type: basic_widgets.Button
    draw_arrow_w_click = widget_descriptors.ButtonDescriptor("draw_arrow_w_click")  # type: basic_widgets.Button
    draw_rect_w_drag = widget_descriptors.ButtonDescriptor("draw_rect_w_drag")  # type: basic_widgets.Button
    draw_rect_w_click = widget_descriptors.ButtonDescriptor("draw_rect_w_click")  # type: basic_widgets.Button
    draw_polygon_w_click = widget_descriptors.ButtonDescriptor("draw_polygon_w_click")  # type: basic_widgets.Button
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

    fname = StringDescriptor(
        'fname', default_value='None', docstring='')  # type: str
    selection_rect_id = IntegerDescriptor(
        'selection_rect_id', docstring='')  # type: int
    image_reader = TypedDescriptor(
        'image_reader', ComplexImageReader, docstring='')  # type: ComplexImageReader

    def __init__(self):
        self.shapes_in_selector = []


class CanvasDemo(WidgetPanel):
    _widget_list = ("button_panel", "canvas_demo_image_panel", "pyplot_panel")
    button_panel = widget_descriptors.PanelDescriptor("button_panel", CanvasDemoButtonPanel)   # type: CanvasDemoButtonPanel
    pyplot_panel = widget_descriptors.PyplotImagePanelDescriptor("pyplot_panel")   # type: PyplotImagePanel
    canvas_demo_image_panel = widget_descriptors.ImagePanelDescriptor("canvas_demo_image_panel")   # type: ImagePanel

    def __init__(self, primary):
        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.variables = AppVariables()

        self.init_w_horizontal_layout()
        primary_frame.pack(fill=tkinter.BOTH, expand=1)
        self.button_panel.pack(fill=tkinter.X, expand=False)
        self.pyplot_panel.pack(expand=True)
        self.canvas_demo_image_panel.pack(expand=True)

        # define panels widget_wrappers in primary frame
        self.button_panel.set_spacing_between_buttons(0)
        # bind events to callbacks here
        self.button_panel.fname_select.config(command=self.callback_initialize_canvas_image)
        self.button_panel.rect_select.config(command=self.callback_set_to_select)

        self.button_panel.draw_line_w_drag.config(command=self.callback_draw_line_w_drag)
        self.button_panel.draw_line_w_click.config(command=self.callback_draw_line_w_click)
        self.button_panel.draw_arrow_w_drag.config(command=self.callback_draw_arrow_w_drag)
        self.button_panel.draw_arrow_w_click.config(command=self.callback_draw_arrow_w_click)
        self.button_panel.draw_rect_w_drag.config(command=self.callback_draw_rect_w_drag)
        self.button_panel.draw_rect_w_click.config(command=self.callback_draw_rect_w_click)
        self.button_panel.draw_polygon_w_click.config(command=self.callback_draw_polygon_w_click)
        self.button_panel.draw_point.config(command=self.callback_draw_point)
        self.button_panel.edit.config(command=self.callback_edit)
        self.button_panel.color_selector.config(command=self.callback_activate_color_selector)
        self.button_panel.remap_dropdown.on_selection(self.callback_remap)

        self.canvas_demo_image_panel.canvas.on_left_mouse_click(self.callback_handle_canvas_left_mouse_click)
        self.canvas_demo_image_panel.canvas.on_left_mouse_release(self.callback_handle_canvas_left_mouse_release)

    def callback_save_kml(self):
        kml_save_fname = tkinter.filedialog.asksaveasfilename(initialdir=os.path.expanduser("~/Downloads"))

        kml_util = KmlUtil()

        canvas_shapes = self.canvas_demo_image_panel.canvas.variables.shape_ids
        for shape_id in canvas_shapes:
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

                if shape_id == self.canvas_demo_image_panel.canvas.variables.zoom_rect_id:
                    pass
                elif shape_type == self.canvas_demo_image_panel.canvas.variables.select_rect_id:
                    pass
                elif shape_type == self.canvas_demo_image_panel.canvas.SHAPE_TYPES.POINT:
                    kml_util.add_point(str(shape_id), xy_point_list[0])
                elif canvas_shapes == self.canvas_demo_image_panel.canvas.SHAPE_TYPES.LINE:
                    kml_util.add_linestring(str(shape_id), xy_point_list)
                elif shape_type == self.canvas_demo_image_panel.canvas.SHAPE_TYPES.POLYGON:
                    kml_util.add_polygon(str(shape_id), xy_point_list)
                elif shape_type == self.canvas_demo_image_panel.canvas.SHAPE_TYPES.RECT:
                    kml_util.add_polygon(str(shape_id), xy_point_list)
        kml_util.write_to_file(kml_save_fname)

    def callback_handle_canvas_left_mouse_click(self, event):
        self.canvas_demo_image_panel.canvas.callback_handle_left_mouse_click(event)
        current_shape = self.canvas_demo_image_panel.canvas.variables.current_shape_id
        if current_shape:
            self.variables.shapes_in_selector.append(current_shape)
            self.variables.shapes_in_selector = sorted(list(set(self.variables.shapes_in_selector)))

    def callback_handle_canvas_left_mouse_release(self, event):
        self.canvas_demo_image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.canvas_demo_image_panel.canvas.variables.select_rect_id == self.canvas_demo_image_panel.canvas.variables.current_shape_id:
            self.update_selection()

    def callback_edit(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_edit_shape(select_closest_first=True)

    def callback_activate_color_selector(self):
        self.canvas_demo_image_panel.canvas.activate_color_selector()

    def callback_draw_line_w_drag(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_line_by_dragging()

    def callback_draw_line_w_click(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_line_by_clicking()

    def callback_draw_arrow_w_drag(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_arrow_by_dragging()

    def callback_draw_arrow_w_click(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_arrow_by_clicking()

    def callback_draw_rect_w_drag(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_rect()

    def callback_draw_rect_w_click(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_rect_by_clicking()

    def callback_draw_polygon_w_click(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()

    def callback_draw_point(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_draw_point()

    def callback_set_to_select(self):
        self.canvas_demo_image_panel.canvas.set_current_tool_to_selection_tool()

    # define custom callbacks here
    def callback_remap(self):
        self.update_selection()

    def update_selection(self):
        remap_dict = {entry: entry for entry in remap.get_remap_list()}
        selection = self.button_panel.remap_dropdown.get()
        self.variables.image_reader.set_remap_type(remap_dict[selection])
        image_data = self.canvas_demo_image_panel.canvas.get_image_data_in_canvas_rect_by_id(
            self.canvas_demo_image_panel.canvas.variables.select_rect_id)
        self.pyplot_panel.update_image(image_data)
        self.canvas_demo_image_panel.canvas.update_current_image()

    def callback_initialize_canvas_image(self):
        image_file_extensions = ['*.nitf', '*.NITF']
        ftypes = [
            ('image files', image_file_extensions),
            ('All files', '*'),
        ]
        new_fname = askopenfilename(initialdir=os.path.expanduser("~"), filetypes=ftypes)
        if new_fname:
            self.variables.fname = new_fname
            self.variables.image_reader = ComplexImageReader(new_fname)
            self.canvas_demo_image_panel.set_image_reader(self.variables.image_reader)


def main():
    root = tkinter.Tk()
    app = CanvasDemo(root)
    root.mainloop()


if __name__ == '__main__':
    main()
