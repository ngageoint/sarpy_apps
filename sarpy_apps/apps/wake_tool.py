# -*- coding: utf-8 -*-
"""
This module provides a version of the wake tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import os
import tkinter
from tkinter import ttk
from tkinter.filedialog import askopenfilenames, askdirectory
import numpy

from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from tk_builder.base_elements import StringDescriptor, TypedDescriptor, IntegerDescriptor
from tk_builder.panel_builder import WidgetPanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.widgets.image_canvas import ShapeTypeConstants

from sarpy.compliance import string_types
from sarpy.io.complex.base import SICDTypeReader


######
# Panel definitions

class ButtonPanel(WidgetPanel):
    _widget_list = ("line_draw", "point_draw")
    line_draw = widget_descriptors.ButtonDescriptor(
        "line_draw", default_text="line")  # type: basic_widgets.Button
    point_draw = widget_descriptors.ButtonDescriptor(
        "point_draw", default_text="point")  # type:  basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(1, column_widths=8, row_heights=5)


class InfoPanel(WidgetPanel):
    _widget_list = (
        "canvas_distance_label", "canvas_distance_val",
        "pixel_distance_label", "pixel_distance_val",
        "geo_distance_label", "geo_distance_val")

    canvas_distance_label = widget_descriptors.LabelDescriptor(
        "canvas_distance_label", default_text="canvas distance:")  # type: basic_widgets.Label
    pixel_distance_label = widget_descriptors.LabelDescriptor(
        "pixel_distance_label", default_text="pixel distance:")  # type: basic_widgets.Label
    geo_distance_label = widget_descriptors.LabelDescriptor(
        "geo_distance_label", default_text="geo distance:")  # type: basic_widgets.Label

    canvas_distance_val = widget_descriptors.EntryDescriptor(
        "canvas_distance_val", default_text="")  # type: basic_widgets.Entry
    pixel_distance_val = widget_descriptors.EntryDescriptor(
        "pixel_distance_val", default_text="")  # type: basic_widgets.Entry
    geo_distance_val = widget_descriptors.EntryDescriptor(
        "geo_distance_val", default_text="")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=2, column_widths=[20, 10], row_heights=5)

        self.canvas_distance_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.pixel_distance_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.geo_distance_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)

        self.canvas_distance_val.config(state='disabled')
        self.pixel_distance_val.config(state='disabled')
        self.geo_distance_val.config(state='disabled')


class SidePanel(WidgetPanel):
    _widget_list = ("buttons", "info_panel")
    buttons = widget_descriptors.PanelDescriptor(
        "buttons", ButtonPanel, default_text="")    # type: ButtonPanel
    info_panel = widget_descriptors.PanelDescriptor(
        "info_panel", InfoPanel, default_text="")  # type: InfoPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()


#######
# Main App

class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The initial opening directory. This will get updated on chosen file.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', SICDTypeCanvasImageReader, docstring='')  # type: SICDTypeCanvasImageReader
    arrow_id = IntegerDescriptor(
        'arrow_id', docstring='')  # type: int
    point_id = IntegerDescriptor(
        'point_id', docstring='')  # type: int
    horizontal_line_id = IntegerDescriptor(
        'horizontal_line_id', docstring='')  # type: int
    line_width = IntegerDescriptor(
        'line_width', default_value=3, docstring='')  # type: int
    horizontal_line_width = IntegerDescriptor(
        'horizontal_line_width', default_value=3, docstring='')  # type: int
    horizontal_line_color = StringDescriptor(
        'horizontal_line_color', default_value='green',
        docstring='A hexidecimal or named color.')  # type: str


class WakeTool(WidgetPanel, WidgetWithMetadata):
    """
    Tool that displays information based on a line and point drawn on an image.  Information pertains
    to the direction of the line and distance from the point to the line.
    """

    def __init__(self, primary):
        """

        Parameters
        ----------
        primary : tkinter.Toplevel|tkinter.Tk
        """

        self.root = primary
        self.primary_frame = basic_widgets.Frame(primary)
        WidgetPanel.__init__(self, self.primary_frame)
        WidgetWithMetadata.__init__(self, primary)
        self.image_panel = ImagePanel(self.primary_frame)  # type: ImagePanel
        self.side_panel = SidePanel(self.primary_frame)  # type: SidePanel
        self.variables = AppVariables()
        self.set_title()

        self.image_panel.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.TRUE)
        self.side_panel.pack(expand=tkinter.FALSE)
        self.primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        # set up event listeners
        self.side_panel.buttons.line_draw.config(command=self.arrow_draw_command)
        self.side_panel.buttons.point_draw.config(command=self.draw_point_command)

        self.image_panel.canvas.variables.state.line_width = self.variables.line_width
        # hide unnecessary tools
        self.image_panel.hide_tools(['shape_drawing', 'select'])
        self.image_panel.hide_shapes()

        # define menus
        menubar = tkinter.Menu()
        # file menu
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.callback_select_files)
        filemenu.add_command(label="Open Directory", command=self.callback_select_directory)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Metadata", menu=popups_menu)

        # handle packing
        primary.config(menu=menubar)

        # bind useful events from our canvas
        self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.callback_index_changed)
        # refreshed the canvas

        self.image_panel.canvas.bind('<<ShapeCoordsFinalized>>', self.callback_shape_edited)
        # a shape is finished drawing (i.e. changed)

        self.image_panel.canvas.bind('<<ShapeCoordsEdit>>', self.callback_shape_edited)
        # a shape is edited

        self.image_panel.canvas.bind('<<ShapeCreate>>', self.callback_shape_create)
        # a new shape is created

        self.image_panel.canvas.bind('<<ShapeDelete>>', self.callback_shape_delete)
        # a shape is deleted

    # callbacks for direct use
    def exit(self):
        self.root.destroy()

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Wake Tool"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Wake Tool, Multiple Files"
        else:
            the_title = "Wake Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def callback_select_files(self):
        fnames = askopenfilenames(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fnames is None or fnames in ['', ()]:
            return

        if len(fnames) == 1:
            the_reader = SICDTypeCanvasImageReader(fnames[0])
        else:
            the_reader = SICDTypeCanvasImageReader(fnames)
        self.update_reader(the_reader, update_browse=os.path.split(fnames[0])[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return

        the_reader = SICDTypeCanvasImageReader(dirname)
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    # callbacks for canvas event bindings
    # noinspection PyUnusedLocal
    def callback_index_changed(self, event):
        """
        Callback that our index has changed - should have refreshed the canvas shapes already.

        Parameters
        ----------
        event
        """

        if self.variables.arrow_id is not None:
            self.image_panel.canvas.delete_shape(self.variables.arrow_id)
        if self.variables.point_id is not None:
            self.image_panel.canvas.delete_shape(self.variables.point_id)
        self.update_distance()
        self.my_populate_metaicon()

    def callback_shape_edited(self, event):
        """
        Callback for a shape having coordinates edited.

        Parameters
        ----------
        event
        """

        if (event.y == ShapeTypeConstants.ARROW and event.x == self.variables.arrow_id) or \
                (event.y == ShapeTypeConstants.POINT and event.x == self.variables.point_id):
            self.update_distance()

    def callback_shape_create(self, event):
        """
        Handle a shape creation.

        Parameters
        ----------
        event
        """

        if event.y == ShapeTypeConstants.ARROW:
            if self.variables.arrow_id is None:
                self.variables.arrow_id = event.x
            elif self.variables.arrow_id == event.x:
                pass  # I don't know how this would happen
            else:
                old_arrow = self.variables.arrow_id
                self.variables.arrow_id = event.x
                self.image_panel.canvas.delete_shape(old_arrow)  # this should never happen
        elif event.y == ShapeTypeConstants.POINT:
            if self.variables.point_id is None:
                self.variables.point_id = event.x
            elif self.variables.point_id == event.x:
                pass  # how?
            else:
                old_point = self.variables.point_id
                self.variables.arrow_id = event.x
                self.image_panel.canvas.delete_shape(old_point)  # this should never happen

    def callback_shape_delete(self, event):
        """
        Handle a shape deletion.

        Parameters
        ----------
        event
        """

        if event.y == ShapeTypeConstants.ARROW and \
                self.variables.arrow_id == event.x:
            self.variables.arrow_id = None
        elif event.y == ShapeTypeConstants.POINT and \
                self.variables.point_id == event.x:
            self.variables.point_id = None
        elif event.y == ShapeTypeConstants.LINE and \
                self.variables.horizontal_line_id == event.x:
            self.variables.horizontal_line_id = None
        self.update_distance()

    # methods used in callbacks
    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : str|SICDTypeReader|SICDTypeCanvasImageReader
        update_browse : None|str
        """

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, string_types):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, string_types):
            the_reader = SICDTypeCanvasImageReader(the_reader)

        if isinstance(the_reader, SICDTypeReader):
            the_reader = SICDTypeCanvasImageReader(the_reader)

        if not isinstance(the_reader, SICDTypeCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        # refresh appropriate GUI elements
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        # initialize our shape tracking
        self.variables.point_id = None
        self.variables.arrow_id = None
        self.variables.horizontal_line_id = None
        self.set_title()

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.image_panel.canvas.variables.canvas_image_object is None or \
                self.image_panel.canvas.variables.canvas_image_object.image_reader is None:
            image_reader = None
            the_index = None
        else:
            image_reader = self.image_panel.canvas.variables.canvas_image_object.image_reader
            the_index = self.image_panel.canvas.get_image_index()
        self.populate_metaicon(image_reader, the_index)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.image_panel.canvas.variables.canvas_image_object is None:
            image_reader = None
        else:
            image_reader = self.image_panel.canvas.variables.canvas_image_object.image_reader
        self.populate_metaviewer(image_reader)

    def arrow_draw_command(self):
        """
        Callback for drawing/editing the arrow.
        """

        if self.variables.arrow_id not in self.image_panel.canvas.variables.vector_objects:
            self.variables.arrow_id = None
        self.image_panel.canvas.set_current_tool_to_draw_arrow(self.variables.arrow_id)

    def draw_point_command(self):
        """
        Callback for drawing/editing the point.
        """

        if self.variables.point_id not in self.image_panel.canvas.variables.vector_objects:
            self.variables.point_id = None
        self.image_panel.canvas.set_current_tool_to_draw_point(self.variables.point_id)

    def update_distance(self):
        """
        Handles the case that we have modified the line or the point coordinates.
        This also handles the creation/editing of the horizontal line.
        """

        if self.variables.point_id is None or self.variables.arrow_id is None:
            if self.variables.horizontal_line_id is not None:
                self.image_panel.canvas.delete_shape(self.variables.horizontal_line_id)
            self.side_panel.info_panel.canvas_distance_val.set_text("")
            self.side_panel.info_panel.pixel_distance_val.set_text("")
            self.side_panel.info_panel.geo_distance_val.set_text("")
            return

        # calculate horizontal line segment
        point_x, point_y = self.image_panel.canvas.get_shape_canvas_coords(self.variables.point_id)
        line_slope, line_intercept = self.get_line_slope_and_intercept()
        end_x = (point_y - line_intercept) / line_slope
        end_y = point_y
        horizontal_line_coords = (point_x, point_y, end_x, end_y)
        # save last object selected on canvas (either the point or the line)
        last_shape_id = self.image_panel.canvas.current_shape_id
        if self.variables.horizontal_line_id is None:
            self.variables.horizontal_line_id = self.image_panel.canvas.create_new_line(
                horizontal_line_coords,
                increment_color=False,
                fill=self.variables.horizontal_line_color,
                width=self.variables.horizontal_line_width)
        else:
            self.image_panel.canvas.modify_existing_shape_using_canvas_coords(
                self.variables.horizontal_line_id, horizontal_line_coords)
        # set current object ID back to what it was after drawing the horizontal line
        self.image_panel.canvas.current_shape_id = last_shape_id
        canvas_distance = self.image_panel.canvas.get_canvas_line_length(self.variables.horizontal_line_id)
        pixel_distance = self.image_panel.canvas.get_image_line_length(self.variables.horizontal_line_id)
        geo_distance = self.calculate_wake_distance()
        self.side_panel.info_panel.canvas_distance_val.set_text("{:.2f}".format(canvas_distance))
        self.side_panel.info_panel.pixel_distance_val.set_text("{:.2f}".format(pixel_distance))
        self.side_panel.info_panel.geo_distance_val.set_text("{:.2f}".format(geo_distance))

    def calculate_wake_distance(self):
        horizontal_line_image_coords = self.image_panel.canvas.get_vector_object(
            self.variables.horizontal_line_id).image_coords
        sicd_meta = self.variables.image_reader.get_sicd()
        points = numpy.asarray(numpy.reshape(horizontal_line_image_coords, (2, 2)))
        ecf_ground_points = sicd_meta.project_image_to_ground(points)
        return float(numpy.linalg.norm(ecf_ground_points[0, :] - ecf_ground_points[1, :]))

    def get_line_slope_and_intercept(self):
        line_coords = self.image_panel.canvas.coords(self.variables.arrow_id)

        line_x1, line_x2 = line_coords[0], line_coords[2]
        line_y1, line_y2 = line_coords[1], line_coords[3]

        line_slope = (line_y2 - line_y1)/(line_x2 - line_x1)
        line_intercept = line_y1 - line_slope * line_x1
        return line_slope, line_intercept


def main(reader=None):
    """
    Main method for initializing the tool

    Parameters
    ----------
    reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = WakeTool(root)
    root.geometry("1000x800")
    if reader is not None:
        app.update_reader(reader)

    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the wake tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
