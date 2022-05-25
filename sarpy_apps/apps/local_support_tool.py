# -*- coding: utf-8 -*-
"""
This module provides a local frequency support visualization tool, intended primarily
for use in the validation tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import os
from typing import Union
import numpy

import tkinter
from tkinter import ttk
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter.messagebox import showinfo

from tk_builder.base_elements import TypedDescriptor, IntegerDescriptor, StringDescriptor
from tk_builder.image_reader import NumpyCanvasImageReader
from tk_builder.panels.image_panel import ImagePanel

from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.complex.utils import get_physical_coordinates
from sarpy.visualization.remap import NRL
from sarpy.processing.sicd.fft_base import fft2_sicd, fftshift


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    remap_type = StringDescriptor(
        'remap_type', default_value='', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', SICDTypeCanvasImageReader, docstring='')  # type: SICDTypeCanvasImageReader
    row_line_low = IntegerDescriptor(
        'row_line_low',
        docstring='The id of the frequency_panel of the lower row bandwidth line.')  # type: Union[None, int]
    row_line_high = IntegerDescriptor(
        'row_line_high',
        docstring='The id of the frequency_panel of the upper row bandwidth line.')  # type: Union[None, int]
    col_line_low = IntegerDescriptor(
        'col_line_low',
        docstring='The id of the frequency_panel of the lower column bandwidth line.')  # type: Union[None, int]
    col_line_high = IntegerDescriptor(
        'col_line_high',
        docstring='The id of the frequency_panel of the upper column bandwidth line.')  # type: Union[None, int]
    row_deltak1 = IntegerDescriptor(
        'row_deltak1',
        docstring='The id of the frequency_panel of the row deltak1 line.')  # type: Union[None, int]
    row_deltak2 = IntegerDescriptor(
        'row_deltak2',
        docstring='The id of the frequency_panel of the row deltak2 line.')  # type: Union[None, int]
    col_deltak1 = IntegerDescriptor(
        'col_deltak1',
        docstring='The id of the frequency_panel of the column deltak1.')  # type: Union[None, int]
    col_deltak2 = IntegerDescriptor(
        'col_deltak2',
        docstring='The id of the frequency_panel of the column deltak2.')  # type: Union[None, int]


class LocalFrequencySupportTool(tkinter.PanedWindow, WidgetWithMetadata):
    def __init__(self, primary, reader=None, **kwargs):
        """

        Parameters
        ----------
        primary : tkinter.Tk|tkinter.Toplevel
        reader : None|str|SICDTypeReader|SICDTypeImageCanvasReader
        kwargs
        """

        self.root = primary
        self.variables = AppVariables()
        self.phase_remap = NRL()

        if 'sashrelief' not in kwargs:
            kwargs['sashrelief'] = tkinter.RIDGE
        if 'orient' not in kwargs:
            kwargs['orient'] = tkinter.HORIZONTAL

        tkinter.PanedWindow.__init__(self, primary, **kwargs)

        self.image_panel = ImagePanel(self, borderwidth=0)  # type: ImagePanel
        self.add(
            self.image_panel, width=400, height=700, padx=5, pady=5, sticky=tkinter.NSEW,
            stretch=tkinter.FIRST)
        WidgetWithMetadata.__init__(self, primary, self.image_panel)

        self.frequency_panel = ImagePanel(self, borderwidth=0)  # type: ImagePanel
        self.add(
            self.frequency_panel, width=400, height=700, padx=5, pady=5, sticky=tkinter.NSEW)
        self.pack(fill=tkinter.BOTH, expand=tkinter.YES)

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

        # handle packing
        self.root.config(menu=self.menu_bar)

        # hide extraneous tool elements
        self.image_panel.hide_tools('shape_drawing')
        self.image_panel.hide_shapes()
        self.frequency_panel.hide_tools(['shape_drawing', 'select'])
        self.frequency_panel.hide_shapes()
        self.frequency_panel.hide_select_index()

        # bind canvas events for proper functionality
        self.image_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)
        self.image_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)

        self.update_reader(reader)

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Frequency Support Tool"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Frequency Support Tool, Multiple Files"
        else:
            the_title = "Frequency Support Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self.root.destroy()

    def show_valid_data(self):
        if self.variables.image_reader is None:
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

    def set_default_selection(self):
        """
        Sets the default selection on the currently selected image.
        """

        if self.variables.image_reader is None:
            return

        # get full image size
        full_rows = self.variables.image_reader.full_image_ny
        full_cols = self.variables.image_reader.full_image_nx
        default_size = 512
        middle = (
            max(0, int(0.5*(full_rows - default_size))),
            max(0, int(0.5*(full_cols - default_size))),
            min(full_rows, int(0.5*(full_rows + default_size))),
            min(full_cols, int(0.5*(full_cols + default_size))))
        self.image_panel.canvas.zoom_to_full_image_selection((0, 0, full_rows, full_cols))
        # set selection rectangle
        self.image_panel.canvas.current_tool = 'SELECT'
        select = self.image_panel.canvas.variables.get_tool_shape_by_name('SELECT')
        self.image_panel.canvas.modify_existing_shape_using_image_coords(select.uid, middle)
        self.handle_selection_change(None)

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
        self.update_displayed_selection()

    # noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.populate_metaicon()
        self.set_default_selection()
        self.show_valid_data()

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
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
        self.set_title()
        # refresh appropriate GUI elements
        self.set_default_selection()
        self.populate_metaicon()
        self.populate_metaviewer()
        self.show_valid_data()

    def callback_select_files(self):
        fnames = askopenfilenames(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fnames is None or fnames in ['', ()]:
            return

        if len(fnames) == 1:
            the_reader = SICDTypeCanvasImageReader(fnames[0])
        else:
            the_reader = SICDTypeCanvasImageReader(fnames)

        if the_reader is None:
            showinfo('Opener not found',
                     message='File {} was not successfully opened as a SICD type '
                             'file.'.format(fnames))
            return
        self.update_reader(the_reader, update_browse=os.path.split(fnames[0])[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        # update the default directory for browsing
        self.variables.browse_directory = os.path.split(dirname)[0]
        the_reader = SICDTypeCanvasImageReader(dirname)
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def _initialize_bandwidth_lines(self):
        if self.variables.row_line_low is None or \
                self.frequency_panel.canvas.get_vector_object(self.variables.row_line_low) is None:
            self.variables.row_deltak1 = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='red')
            self.variables.row_deltak2 = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='red')
            self.variables.col_deltak1 = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='red')
            self.variables.col_deltak2 = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='red')

            self.variables.row_line_low = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='blue', regular_options={'dash': (3, )})
            self.variables.row_line_high = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='blue', regular_options={'dash': (3, )})
            self.variables.col_line_low = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='blue', regular_options={'dash': (3, )})
            self.variables.col_line_high = self.frequency_panel.canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, color='blue', regular_options={'dash': (3, )})

        else:
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_deltak1, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_deltak2, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_deltak1, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_deltak2, (0, 0, 0, 0))

            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_line_low, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_line_high, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_line_low, (0, 0, 0, 0))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_line_high, (0, 0, 0, 0))

    def update_displayed_selection(self):
        def get_extent(coords):
            return min(coords[0::2]), max(coords[0::2]), min(coords[1::2]), max(coords[1::2])

        def draw_row_delta_lines():
            deltak1 = (row_count - 1)*(0.5 + the_sicd.Grid.Row.SS*the_sicd.Grid.Row.DeltaK1) + 1
            deltak2 = (row_count - 1)*(0.5 + the_sicd.Grid.Row.SS*the_sicd.Grid.Row.DeltaK2) + 1

            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_deltak1, (deltak1, 0, deltak1, col_count))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_deltak2, (deltak2, 0, deltak2, col_count))

        def draw_col_delta_lines():
            deltak1 = (col_count - 1)*(0.5 + the_sicd.Grid.Col.SS*the_sicd.Grid.Col.DeltaK1) + 1
            deltak2 = (col_count - 1)*(0.5 + the_sicd.Grid.Col.SS*the_sicd.Grid.Col.DeltaK2) + 1

            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_deltak1, (0, deltak1, row_count, deltak1))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_deltak2, (0, deltak2, row_count, deltak2))

        def draw_row_bandwidth_lines():
            # noinspection PyBroadException
            try:
                delta_kcoa_center = the_sicd.Grid.Row.DeltaKCOAPoly(row_phys, col_phys)
            except Exception:
                delta_kcoa_center = 0.0

            row_bw_low = (row_count - 1)*(
                    0.5 + the_sicd.Grid.Row.SS*(delta_kcoa_center - 0.5*the_sicd.Grid.Row.ImpRespBW)) + 1
            row_bw_high = (row_count - 1)*(
                    0.5 + the_sicd.Grid.Row.SS*(delta_kcoa_center + 0.5*the_sicd.Grid.Row.ImpRespBW)) + 1

            row_bw_low = (row_bw_low % row_count)
            row_bw_high = (row_bw_high % row_count)

            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_line_low, (row_bw_low, 0, row_bw_low, col_count))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.row_line_high, (row_bw_high, 0, row_bw_high, col_count))

        def draw_col_bandwidth_lines():
            # noinspection PyBroadException
            try:
                delta_kcoa_center = the_sicd.Grid.Col.DeltaKCOAPoly(row_phys, col_phys)
            except Exception:
                delta_kcoa_center = 0.0

            col_bw_low = (col_count - 1) * (
                    0.5 + the_sicd.Grid.Col.SS*(delta_kcoa_center - 0.5*the_sicd.Grid.Col.ImpRespBW)) + 1
            col_bw_high = (col_count - 1) * (
                    0.5 + the_sicd.Grid.Col.SS*(delta_kcoa_center + 0.5*the_sicd.Grid.Col.ImpRespBW)) + 1

            col_bw_low = (col_bw_low % col_count)
            col_bw_high = (col_bw_high % col_count)

            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_line_low, (0, col_bw_low, row_count, col_bw_low))
            self.frequency_panel.canvas.modify_existing_shape_using_image_coords(
                self.variables.col_line_high, (0, col_bw_high, row_count, col_bw_high))

        threshold = self.image_panel.canvas.variables.config.select_size_threshold
        select_id = self.image_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
        rect_coords = self.image_panel.canvas.get_shape_image_coords(select_id)
        extent = get_extent(rect_coords)  # left, right, bottom, top
        row_count = extent[1] - extent[0]
        col_count = extent[3] - extent[2]

        the_sicd = self.variables.image_reader.get_sicd()
        row_phys, col_phys = get_physical_coordinates(
            the_sicd, 0.5*(extent[0]+extent[1]), 0.5*(extent[2]+extent[3]))

        if row_count < threshold or col_count < threshold:
            junk_data = numpy.zeros((100, 100), dtype='uint8')
            self.frequency_panel.set_image_reader(NumpyCanvasImageReader(junk_data))
            self._initialize_bandwidth_lines()
        else:
            image_data = self.variables.image_reader.base_reader[extent[0]:extent[1], extent[2]:extent[3]]
            if image_data is not None:
                self.frequency_panel.set_image_reader(
                    NumpyCanvasImageReader(self.phase_remap(fftshift(fft2_sicd(image_data, the_sicd)))))
                self._initialize_bandwidth_lines()
                draw_row_delta_lines()
                draw_col_delta_lines()
                draw_row_bandwidth_lines()
                draw_col_bandwidth_lines()
            else:
                junk_data = numpy.zeros((100, 100), dtype='uint8')
                self.frequency_panel.set_image_reader(NumpyCanvasImageReader(junk_data))
                self._initialize_bandwidth_lines()


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

    app = LocalFrequencySupportTool(root, reader=reader)
    root.geometry("1000x1000")
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the local support frequency analysis tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None, nargs='?',
        help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
