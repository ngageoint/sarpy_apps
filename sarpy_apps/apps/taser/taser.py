# -*- coding: utf-8 -*-
"""
This module provides a general viewer tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import os

import tkinter
from tkinter import ttk
from tkinter.filedialog import askopenfilenames, askdirectory

from tk_builder.base_elements import StringDescriptor, TypedDescriptor
from tk_builder.image_reader import ImageReader
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors, basic_widgets

from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.file_filters import common_use_collection


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    remap_type = StringDescriptor(
        'remap_type', default_value='density', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', ImageReader, docstring='')  # type: ImageReader


class Taser(WidgetPanel):
    _widget_list = ("taser_image_panel", "pyplot_panel")
    taser_image_panel = widget_descriptors.ImagePanelDescriptor("taser_image_panel")   # type: ImagePanel
    pyplot_panel = widget_descriptors.PanelDescriptor("pyplot_panel", PyplotImagePanel)   # type: PyplotImagePanel

    def __init__(self, primary):
        primary_frame = basic_widgets.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.variables = AppVariables()

        self.init_w_horizontal_layout()

        # define our meta icon and metaviewer popups
        self.metaicon_popup_panel = tkinter.Toplevel(self.master)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)
        self.metaicon_popup_panel.withdraw()

        self.metaviewer_popup_panel = tkinter.Toplevel(self.master)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)
        self.metaviewer_popup_panel.withdraw()

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
        menubar.add_cascade(label="Popups", menu=popups_menu)

        # handle packing
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        primary.config(menu=menubar)

        # hide extraneous tool elements
        self.taser_image_panel.hide_tools('shape_drawing')
        self.taser_image_panel.hide_shapes()

        # bind canvas events for proper functionality
        # this makes for bad performance on a larger image - do not activate
        # self.taser_image_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)
        self.taser_image_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        self.taser_image_panel.canvas.bind('<<RemapChanged>>', self.handle_remap_change)
        self.taser_image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)

    def exit(self):
        self.quit()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.deiconify()

    def metaicon_popup(self):
        self.metaicon_popup_panel.deiconify()

    # noinspection PyUnusedLocal
    def handle_selection_change(self, event):
        """
        Handle a change in the selection area.

        Parameters
        ----------
        event
        """

        if self.variables.image_reader is None:
            return

        full_image_width = self.taser_image_panel.canvas.variables.state.canvas_width
        fill_image_height = self.taser_image_panel.canvas.variables.state.canvas_height
        self.taser_image_panel.canvas.zoom_to_canvas_selection((0, 0, full_image_width, fill_image_height))
        self.display_canvas_rect_selection_in_pyplot_frame()

    # noinspection PyUnusedLocal
    def handle_remap_change(self, event):
        """
        Handle that the remap for the image canvas has changed.

        Parameters
        ----------
        event
        """
        if self.variables.image_reader is not None:
            self.display_canvas_rect_selection_in_pyplot_frame()

    #noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.populate_metaicon()

    def update_reader(self, the_reader):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : ImageReader
        """

        # change the tool to view
        self.taser_image_panel.canvas.set_current_tool_to_view()
        self.taser_image_panel.canvas.set_current_tool_to_view()
        # update the reader
        self.variables.image_reader = the_reader
        self.taser_image_panel.set_image_reader(the_reader)
        # refresh appropriate GUI elements
        self.pyplot_panel.make_blank()
        self.populate_metaicon()
        self.populate_metaviewer()

    def callback_select_files(self):
        fnames = askopenfilenames(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fnames is None or fnames in ['', ()]:
            return
        # update the default directory for browsing
        self.variables.browse_directory = os.path.split(fnames[0])[0]

        # TODO: handle non-complex data possibilities here
        if len(fnames) == 1:
            the_reader = ComplexImageReader(fnames[0])
        else:
            the_reader = ComplexImageReader(fnames)
        self.update_reader(the_reader)

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        # update the default directory for browsing
        self.variables.browse_directory = os.path.split(dirname)[0]
        # TODO: handle non-complex data possibilities here
        the_reader = ComplexImageReader(dirname)
        self.update_reader(the_reader)

    def display_canvas_rect_selection_in_pyplot_frame(self):
        def get_extent(coords):
            left = min(coords[1::2])
            right = max(coords[1::2])
            top = max(coords[0::2])
            bottom = min(coords[0::2])
            return left, right, top, bottom

        threshold = self.taser_image_panel.canvas.variables.config.select_size_threshold

        select_id = self.taser_image_panel.canvas.variables.select_rect.uid
        rect_coords = self.taser_image_panel.canvas.get_shape_image_coords(select_id)
        extent = get_extent(rect_coords)

        if abs(extent[1] - extent[0]) < threshold or abs(extent[2] - extent[3]) < threshold:
            self.pyplot_panel.make_blank()
        else:
            image_data = self.taser_image_panel.canvas.get_image_data_in_canvas_rect_by_id(select_id)
            if image_data is not None:
                self.pyplot_panel.update_image(image_data, extent=extent)
            else:
                self.pyplot_panel.make_blank()

    def populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.taser_image_panel.canvas.variables.canvas_image_object is None or \
                self.taser_image_panel.canvas.variables.canvas_image_object.image_reader is None:
            self.metaicon.make_empty()

        image_reader = self.taser_image_panel.canvas.variables.canvas_image_object.image_reader

        assert isinstance(image_reader, ComplexImageReader)  # TODO: handle other options
        self.metaicon.create_from_reader(image_reader.base_reader, index=self.taser_image_panel.canvas.get_image_index())

    def populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.taser_image_panel.canvas.variables.canvas_image_object is None or \
                self.taser_image_panel.canvas.variables.canvas_image_object.image_reader is None:
            self.metaviewer.empty_entries()

        image_reader = self.taser_image_panel.canvas.variables.canvas_image_object.image_reader

        assert isinstance(image_reader, ComplexImageReader)  # TODO: handle other options
        self.metaviewer.populate_from_reader(image_reader.base_reader)


def main():
    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('clam')

    app = Taser(root)
    root.mainloop()


if __name__ == '__main__':
    main()
