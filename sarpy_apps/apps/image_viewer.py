# -*- coding: utf-8 -*-
"""
This module provides a general SAR image viewer tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")

import os

import tkinter
from tkinter import ttk
from tkinter.filedialog import askopenfilenames, askdirectory

from tk_builder.base_elements import StringDescriptor, TypedDescriptor
from tk_builder.image_reader import CanvasImageReader
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets.basic_widgets import Frame

from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader, \
    DerivedCanvasImageReader, CPHDTypeCanvasImageReader, CRSDTypeCanvasImageReader, \
    GeneralCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.io.general.base import BaseReader
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.product.base import SIDDTypeReader
from sarpy.io.phase_history.base import CPHDTypeReader
from sarpy.io.received.base import CRSDTypeReader
from sarpy.io import open as open_general


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', CanvasImageReader, docstring='')  # type: CanvasImageReader


class ImageViewer(Frame, WidgetWithMetadata):
    def __init__(self, primary, reader=None, **kwargs):
        """

        Parameters
        ----------
        primary : tkinter.Toplevel|tkinter.Tk
        reader
        kwargs
        """

        self.root = primary
        Frame.__init__(self, primary, **kwargs)
        WidgetWithMetadata.__init__(self, primary)
        self.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.primary = tkinter.PanedWindow(self, sashrelief=tkinter.RIDGE, orient=tkinter.HORIZONTAL)

        self.variables = AppVariables()

        self.image_panel = ImagePanel(self.primary, borderwidth=0)  # type: ImagePanel
        self.primary.add(
            self.image_panel, width=400, height=700, padx=5, pady=5, sticky=tkinter.NSEW,
            stretch=tkinter.FIRST)

        self.pyplot_panel = PyplotImagePanel(self.primary)  # type: PyplotImagePanel
        self.primary.add(
            self.pyplot_panel, width=400, height=700, padx=5, pady=5, sticky=tkinter.NSEW)

        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.set_title()

        # define menus
        self.menu_bar = tkinter.Menu()
        # file menu
        self.file_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open Image", command=self.callback_select_files)
        self.file_menu.add_command(label="Open Directory", command=self.callback_select_directory)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        self.metadata_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.metadata_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        self.metadata_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        self._valid_data_shown = tkinter.IntVar(self, value=0)
        self.metadata_menu.add_checkbutton(
            label='ValidData', variable=self._valid_data_shown, command=self.show_valid_data)
        # ensure menus cascade
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Metadata", menu=self.metadata_menu)

        self.root.config(menu=self.menu_bar)

        # hide extraneous tool elements
        self.image_panel.hide_tools('shape_drawing')
        self.image_panel.hide_shapes()

        # bind canvas events for proper functionality
        # this makes for bad performance on a larger image - do not activate
        # self.image_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)
        self.image_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        self.image_panel.canvas.bind('<<RemapChanged>>', self.handle_remap_change)
        self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)

        self.update_reader(reader, update_browse=None)

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Image Viewer"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Image Viewer, Multiple Files"
        else:
            the_title = "Image Viewer for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self.primary.destroy()
        self.root.destroy()

    def show_valid_data(self):
        if self.variables.image_reader is None or \
                not isinstance(self.variables.image_reader, SICDTypeCanvasImageReader):
            return

        the_value = self._valid_data_shown.get()
        if the_value == 1:
            # we just checked on
            sicd = self.variables.image_reader.get_sicd()
            if sicd.ImageData.ValidData is not None:
                self.image_panel.canvas.show_valid_data(sicd.ImageData.ValidData.get_array(dtype='float64'))
        else:
            # we checked it off
            try:
                valid_data_id = self.image_panel.canvas.variables.get_tool_shape_id_by_name('VALID_DATA')
                self.image_panel.canvas.hide_shape(valid_data_id)
            except KeyError:
                pass

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

        full_image_width = self.image_panel.canvas.variables.state.canvas_width
        fill_image_height = self.image_panel.canvas.variables.state.canvas_height
        self.image_panel.canvas.zoom_to_canvas_selection((0, 0, full_image_width, fill_image_height))
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

    # noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.my_populate_metaicon()
        self.show_valid_data()

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|BaseReader|CanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
            the_reader = open_general(the_reader)

        if isinstance(the_reader, SICDTypeReader):
            the_reader = SICDTypeCanvasImageReader(the_reader)
        elif isinstance(the_reader, SIDDTypeReader):
            the_reader = DerivedCanvasImageReader(the_reader)
        elif isinstance(the_reader, CPHDTypeReader):
            the_reader = CPHDTypeCanvasImageReader(the_reader)
        elif isinstance(the_reader, CRSDTypeReader):
            the_reader = CRSDTypeCanvasImageReader(the_reader)
        elif isinstance(the_reader, BaseReader):
            the_reader = GeneralCanvasImageReader(the_reader)

        if not isinstance(the_reader, CanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_title()
        # refresh appropriate GUI elements
        self.pyplot_panel.make_blank()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.show_valid_data()

    def callback_select_files(self):
        fnames = askopenfilenames(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fnames is None or fnames in ['', ()]:
            return

        if len(fnames) > 1:
            the_reader = SICDTypeCanvasImageReader(fnames)
            self.update_reader(the_reader, update_browse=os.path.split(fnames[0])[0])
        else:
            self.update_reader(fnames[0], update_browse=os.path.split(fnames[0])[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        # NB: handle non-complex data possibilities here?
        the_reader = SICDTypeCanvasImageReader(dirname)
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def display_canvas_rect_selection_in_pyplot_frame(self):
        def get_extent(coords):
            left = min(coords[1::2])
            right = max(coords[1::2])
            top = max(coords[0::2])
            bottom = min(coords[0::2])
            return left, right, top, bottom

        threshold = self.image_panel.canvas.variables.config.select_size_threshold

        try:
            select_id = self.image_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
            if select_id is None:
                return
        except KeyError:
            return

        rect_coords = self.image_panel.canvas.get_shape_image_coords(select_id)
        extent = get_extent(rect_coords)

        if abs(extent[1] - extent[0]) < threshold or abs(extent[2] - extent[3]) < threshold:
            self.pyplot_panel.make_blank()
        else:
            image_data = self.image_panel.canvas.get_image_data_in_canvas_rect_by_id(select_id)
            if image_data is not None:
                self.pyplot_panel.update_image(image_data, extent=extent)
            else:
                self.pyplot_panel.make_blank()

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon(self.variables.image_reader)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer(self.variables.image_reader)


def main(reader=None):
    """
    Main method for initializing the aperture tool

    Parameters
    ----------
    reader : None|str|BaseReader|CanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = ImageViewer(root, reader=reader)
    root.geometry("1000x800")

    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the image viewer with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None, nargs='?',
        help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
