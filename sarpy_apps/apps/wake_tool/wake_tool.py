import tkinter
from sarpy_apps.apps.wake_tool.panels.side_panel import SidePanel
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets.image_canvas import TOOLS
from tk_builder.panel_builder import WidgetPanel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, IntegerDescriptor
from tk_builder.widgets import widget_descriptors
import numpy as np


class AppVariables(object):
    image_fname = StringDescriptor(
        'image_fname', default_value='None', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', ComplexImageReader, docstring='')  # type: ComplexImageReader
    arrow_id = IntegerDescriptor(
        'arrow_id', docstring='')  # type: int
    point_id = IntegerDescriptor(
        'point_id', docstring='')  # type: int
    horizontal_line_id = IntegerDescriptor(
        'horizontal_line_id', docstring='')  # type: int
    line_width = IntegerDescriptor(
        'line_width', default_value=3, docstring='')  # type: int
    horizontal_line_width = IntegerDescriptor(
        'horizontal_line_width', default_value=2, docstring='')  # type: int
    horizontal_line_color = StringDescriptor(
        'horizontal_line_color', default_value='green',
        docstring='A hexidecimal or named color.')  # type: str


class WakeTool(WidgetPanel):
    """
    Tool that displays information based on a line and point drawn on an image.  Information pertains
    to the direction of the line and distance from the point to the line.
    """
    _widget_list = ("side_panel", "image_panel")
    side_panel = widget_descriptors.PanelDescriptor(
        "side_panel", SidePanel, default_text="wake tool controls")      # type: SidePanel
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")  # type: ImagePanel

    def __init__(self, primary):
        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_vertical_layout()
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.variables = AppVariables()

        self.side_panel.set_spacing_between_buttons(0)

        # set up event listeners
        self.side_panel.buttons.line_draw.config(command=self.line_draw_command)
        self.side_panel.buttons.point_draw.config(command=self.draw_point_command)

        self.image_panel.canvas.variables.line_width = self.variables.line_width
        self.image_panel.canvas.on_left_mouse_click(self.callback_handle_left_mouse_click)
        self.image_panel.canvas.on_left_mouse_motion(self.callback_on_left_mouse_motion)

        self.side_panel.pack(fill=tkinter.X, expand=tkinter.NO, side="top")
        self.side_panel.do_not_expand()
        self.side_panel.fill_x(False)
        self.side_panel.file_selector.set_fname_filters([("*.NITF", ".nitf")])
        self.side_panel.file_selector.select_file.config(command=self.select_file_command)
        self.image_panel.canvas.update_outer_axes_on_zoom = False

    def select_file_command(self):
        self.side_panel.file_selector.select_file_command()
        if self.side_panel.file_selector.fname:
            self.variables.image_fname = self.side_panel.file_selector.fname
        self.variables.image_reader = ComplexImageReader(self.variables.image_fname)
        self.image_panel.set_image_reader(self.variables.image_reader)

    # noinspection PyUnusedLocal
    def line_draw_command(self):
        self.image_panel.canvas.set_current_tool_to_draw_arrow_by_dragging()
        self.image_panel.canvas.variables.current_shape_id = self.variables.arrow_id

    # noinspection PyUnusedLocal
    def draw_point_command(self):
        self.image_panel.canvas.set_current_tool_to_draw_point()
        self.image_panel.canvas.variables.current_shape_id = self.variables.point_id

    def callback_handle_left_mouse_click(self, event):
        # first do all the normal mouse click functionality of the canvas
        self.image_panel.canvas.callback_handle_left_mouse_click(event)
        # now set the object ID's accordingly, we do this so we don't draw multiple arrows or points
        if self.image_panel.canvas.variables.current_tool == TOOLS.DRAW_ARROW_BY_DRAGGING:
            self.variables.arrow_id = self.image_panel.canvas.variables.current_shape_id
        if self.image_panel.canvas.variables.current_tool == TOOLS.DRAW_POINT_BY_CLICKING:
            self.variables.point_id = self.image_panel.canvas.variables.current_shape_id
        if self.variables.point_id is not None and self.variables.arrow_id is not None:
            self.update_distance()

    def callback_on_left_mouse_motion(self, event):
        self.image_panel.canvas.callback_handle_left_mouse_motion(event)
        self.update_distance()

    def update_distance(self):
        if self.variables.point_id is not None and self.variables.arrow_id is not None:
            # calculate horizontal line segment
            point_x, point_y = self.image_panel.canvas.get_shape_canvas_coords(self.variables.point_id)
            line_slope, line_intercept = self.get_line_slope_and_intercept()
            end_x = (point_y - line_intercept) / line_slope
            end_y = point_y
            horizontal_line_coords = (point_x, point_y, end_x, end_y)
            # save last object selected on canvas (either the point or the line)
            last_shape_id = self.image_panel.canvas.variables.current_shape_id
            if self.variables.horizontal_line_id is None:
                self.variables.horizontal_line_id = \
                    self.image_panel.canvas.create_new_line(horizontal_line_coords,
                                                            fill=self.variables.horizontal_line_color,
                                                            width=self.variables.horizontal_line_width)
            else:
                self.image_panel.canvas.modify_existing_shape_using_canvas_coords(self.variables.horizontal_line_id, horizontal_line_coords)
            # set current object ID back to what it was after drawing the horizontal line
            self.image_panel.canvas.variables.current_shape_id = last_shape_id
            canvas_distance = self.image_panel.canvas.get_canvas_line_length(self.variables.horizontal_line_id)
            pixel_distance = self.image_panel.canvas.get_image_line_length(self.variables.horizontal_line_id)
            geo_distance = self.calculate_wake_distance()
            self.side_panel.info_panel.canvas_distance_val.set_text("{:.2f}".format(canvas_distance))
            self.side_panel.info_panel.pixel_distance_val.set_text("{:.2f}".format(pixel_distance))
            self.side_panel.info_panel.geo_distance_val.set_text("{:.2f}".format(geo_distance))

    def calculate_wake_distance(self):
        horizontal_line_image_coords = self.image_panel.canvas.get_vector_object(
            self.variables.horizontal_line_id).image_coords
        sicd_meta = self.variables.image_reader.base_reader.sicd_meta
        points = np.asarray(np.reshape(horizontal_line_image_coords, (2, 2)))
        ecf_ground_points = sicd_meta.project_image_to_ground(points)
        return float(np.linalg.norm(ecf_ground_points[0, :] - ecf_ground_points[1, :]))

    def get_line_slope_and_intercept(self):
        line_coords = self.image_panel.canvas.coords(self.variables.arrow_id)

        line_x1, line_x2 = line_coords[0], line_coords[2]
        line_y1, line_y2 = line_coords[1], line_coords[3]

        line_slope = (line_y2 - line_y1)/(line_x2 - line_x1)
        line_intercept = line_y1 - line_slope * line_x1
        return line_slope, line_intercept


if __name__ == '__main__':
    root = tkinter.Tk()
    app = WakeTool(root)
    root.geometry("1000x800")
    root.mainloop()
