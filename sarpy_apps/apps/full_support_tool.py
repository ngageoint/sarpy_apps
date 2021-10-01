# -*- coding: utf-8 -*-
"""
This module provides a full image frequency support visualization tool, intended
primarily for use in the validation tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

import logging
from typing import Optional
from tempfile import mkstemp
import os

import tkinter
from tkinter import ttk
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter.messagebox import showinfo

import numpy
from matplotlib import pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, \
    NavigationToolbar2Tk

from tk_builder.base_elements import TypedDescriptor, StringDescriptor
from tk_builder.image_reader import NumpyCanvasImageReader
from tk_builder.panel_builder import WidgetPanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets import widget_descriptors, basic_widgets

from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader, SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.compliance import int_func
from sarpy.io.complex.base import FlatSICDReader
from sarpy.processing.fft_base import fft_sicd, fft2_sicd, fftshift
from sarpy.processing.normalize_sicd import DeskewCalculator
from sarpy.io.complex.base import SICDTypeReader
from sarpy.compliance import string_types

logger = logging.getLogger(__name__)


def create_deskewed_transform(reader, dimension=0, suffix='.sarpy.cache'):
    """
    Performs the Fourier transform of the deskewed entirety of the given
    ComplexImageReader contents.

    Parameters
    ----------
    reader : SICDTypeCanvasImageReader
        The reader object.
    dimension : int
        One of [0, 1], which dimension to deskew along.
    suffix : None|str
        The suffix for the created file name (created using the tempfile module).

    Returns
    -------
    (str, numpy.ndarray, numpy.ndarray)
        A file name, numpy memmap of the given object, and mean along the given dimension.
        Care should be taken to ensure that the file is deleted when the usage is complete.
    """

    # set up a true file for the memmap
    # NB: it should be noted that the tempfile usage which clean themselves up
    #     cannot (as of 2021-04-23) be opened multiple times on Windows, which
    #     means that such a "file" cannot be used in conjunction with a numpy
    #     memmap.
    data_size = reader.data_size
    sicd = reader.get_sicd()
    _, file_name = mkstemp(suffix=suffix, text=False)
    logger.debug('Creating temp file % s' % file_name)
    # set up the memmap
    memmap = numpy.memmap(file_name, dtype='complex64', mode='r+', offset=0, shape=data_size)
    calculator = DeskewCalculator(
        reader.base_reader, dimension=dimension, index=reader.index,
        apply_deskew=True, apply_deweighting=False, apply_off_axis=False)
    mean_value = numpy.zeros((data_size[0], ), dtype='float64') if dimension == 0 else \
        numpy.zeros((data_size[1],), dtype='float64')

    # we'll proceed in blocks of approximately this number of pixels
    pixels_threshold = 2**20
    # is our whole reader sufficiently small to just do it all in one fell-swoop?
    if data_size[0]*data_size[1] <= 4*pixels_threshold:
        data = fftshift(fft2_sicd(calculator[:, :], sicd))
        memmap[:, :] = data
        mean_value[:] = numpy.mean(numpy.abs(data), axis=1-dimension)
        return file_name, memmap, mean_value

    # fetch full rows, and transform then shift along the row direction
    block_size = int_func(numpy.ceil(pixels_threshold/data_size[1]))
    start_col = 0
    while start_col < data_size[1]:
        end_col = min(start_col+block_size, data_size[1])
        data = fftshift(fft_sicd(calculator[:, start_col:end_col], 0, sicd), axes=0)
        memmap[:, start_col:end_col] = data
        if dimension == 0:
            mean_value += numpy.sum(numpy.abs(data), axis=1)
        start_col = end_col
    # fetch full columns, and transform then shift along the column direction
    block_size = int_func(numpy.ceil(pixels_threshold/data_size[0]))
    start_row = 0
    while start_row < data_size[0]:
        end_row = min(start_row+block_size, data_size[0])
        data = fftshift(fft_sicd(memmap[start_row:end_row, :], 1, sicd), axes=1)
        memmap[start_row:end_row, :] = data
        if dimension == 1:
            mean_value += numpy.sum(numpy.abs(data), axis=0)
        start_row = end_row

    if dimension == 0:
        mean_value /= data_size[1]
    else:
        mean_value /= data_size[0]
    return file_name, memmap, mean_value


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    remap_type = StringDescriptor(
        'remap_type', default_value='', docstring='')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', SICDTypeCanvasImageReader, docstring='')  # type: SICDTypeCanvasImageReader

    row_fourier_reader = TypedDescriptor(
        'row_fourier_reader', ComplexCanvasImageReader,
        docstring='The row deskewed fourier transformed reader')  # type: ComplexCanvasImageReader
    row_fourier_file = StringDescriptor(
        'row_fourier_file',
        docstring='The row deskewed fourier transformed reader file')  # type: Optional[str]
    # NB: we are saving this state in order to properly clean up
    column_fourier_reader = TypedDescriptor(
        'column_fourier_reader', ComplexCanvasImageReader,
        docstring='The column deskewed fourier transformed reader')  # type: ComplexCanvasImageReader
    column_fourier_file = StringDescriptor(
        'row_fourier_file',
        docstring='The column deskewed fourier transformed reader file')  # type: Optional[str]
    # NB: we are saving this state in order to properly clean up

    derived_row_weights = None  # the derived weights for the row
    scaled_row_mean = None  # the scaled mean Fourier transform of the row deskewed data
    derived_column_weights = None  # the derived weights for the column
    scaled_column_mean = None  # the scaled mean Fourier transform of the column deskewed data

    def __del__(self):
        # clean up files, because we might need to do so
        if self.row_fourier_file is not None \
                and os.path.exists(self.row_fourier_file):
            os.remove(self.row_fourier_file)
            logger.debug('(variables) Removing temp file % s' % self.row_fourier_file)
            self.row_fourier_file = None

        if self.column_fourier_file is not None and \
                os.path.exists(self.column_fourier_file):
            os.remove(self.column_fourier_file)
            logger.debug('(variables)  Removing temp file % s' % self.column_fourier_file)
            self.column_fourier_file = None


class FullFrequencySupportTool(WidgetPanel, WidgetWithMetadata):
    _widget_list = ("row_centered_image_panel", "column_centered_image_panel")
    row_centered_image_panel = widget_descriptors.ImagePanelDescriptor(
        "row_centered_image_panel")   # type: ImagePanel
    column_centered_image_panel = widget_descriptors.ImagePanelDescriptor(
        "column_centered_image_panel")   # type: ImagePanel

    def __init__(self, primary):
        self.root = primary
        self.primary_frame = basic_widgets.Frame(primary)
        self.variables = AppVariables()
        WidgetPanel.__init__(self, self.primary_frame)
        WidgetWithMetadata.__init__(self, primary)

        self.init_w_horizontal_layout()
        self.set_title()

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
        popups_menu.add_command(label="Weight Plots", command=self.create_weights_plot)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Metadata", menu=popups_menu)

        # handle packing
        self.primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        primary.config(menu=menubar)

        # hide extraneous tool elements
        self.row_centered_image_panel.hide_tools(['shape_drawing', 'select'])
        self.row_centered_image_panel.hide_shapes()
        self.row_centered_image_panel.hide_select_index()

        self.column_centered_image_panel.hide_tools(['shape_drawing', 'select'])
        self.column_centered_image_panel.hide_shapes()
        self.column_centered_image_panel.hide_select_index()

        # TODO: allow changing the image index somewhere?
        #   bind the handle_image_index_changed method

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Full Frequency Support Tool"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Full Frequency Support Tool, Multiple Files"
        else:
            the_title = "Full Frequency Support Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self._delete_files()
        self.root.destroy()

    def _delete_files(self):
        """
        This is a helper function for cleaning up our state.
        """

        if not hasattr(self, 'variables') or self.variables is None:
            return

        self.variables.row_fourier_reader = None
        self.variables.column_fourier_reader = None
        if self.variables.row_fourier_file is not None \
                and os.path.exists(self.variables.row_fourier_file):
            os.remove(self.variables.row_fourier_file)
            logger.debug('Removing temp file % s' % self.variables.row_fourier_file)

        if self.variables.column_fourier_file is not None and \
                os.path.exists(self.variables.column_fourier_file):
            os.remove(self.variables.column_fourier_file)
            logger.debug('Removing temp file % s' % self.variables.column_fourier_file)

        self.variables.row_fourier_file = None
        self.variables.column_fourier_file = None

    def _clear_display(self):
        """
        Clear the row and column Fourier transform displays
        """

        self._delete_files()
        junk_data = numpy.zeros((100, 100), dtype='uint8')
        self.row_centered_image_panel.set_image_reader(NumpyCanvasImageReader(junk_data))
        self.column_centered_image_panel.set_image_reader(NumpyCanvasImageReader(junk_data))

    def _calculate_fourier_data(self):
        def set_row_data():
            # calculate the fourier transform with deskew in the row direction
            row_file, row_memmap, row_mean_value = create_deskewed_transform(self.variables.image_reader, dimension=0)
            self.variables.row_fourier_file = row_file
            self.variables.row_fourier_reader = ComplexCanvasImageReader(
                FlatSICDReader(self.variables.image_reader.get_sicd(), row_memmap))
            self.row_centered_image_panel.set_image_reader(self.variables.row_fourier_reader)

            draw_deltak_lines(self.row_centered_image_panel.canvas, 'row')

            # rescale the row_mean_value so that the smoothed max value is essentially 1
            if row_mean_value.size < 200:
                the_max = numpy.amax(row_mean_value)
            else:
                the_size = int(numpy.ceil(row_mean_value.size/200.))
                smoothed = numpy.convolve(
                    row_mean_value, numpy.full((the_size, ), 1./the_size, dtype='float64'),
                    mode='valid')
                the_max = numpy.amax(smoothed)
            row_mean_value /= the_max
            self.variables.scaled_row_mean = row_mean_value
            # construct the proper weights and prepare information for weight plotting
            self.variables.derived_row_weights = the_sicd.Grid.Row.define_weight_function(populate=False)

        def set_col_data():
            # calculate the fourier transform with deskew in the column direction
            col_file, col_memmap, col_mean_value = create_deskewed_transform(self.variables.image_reader, dimension=1)
            self.variables.column_fourier_file = col_file
            self.variables.column_fourier_reader = ComplexCanvasImageReader(
                FlatSICDReader(self.variables.image_reader.get_sicd(), col_memmap))
            self.column_centered_image_panel.set_image_reader(self.variables.column_fourier_reader)

            draw_deltak_lines(self.column_centered_image_panel.canvas, 'column')

            # rescale the row_mean_value so that the smoothed max value is essentially 1
            if col_mean_value.size < 200:
                the_max = numpy.amax(col_mean_value)
            else:
                the_size = int(numpy.ceil(col_mean_value.size / 200.))
                smoothed = numpy.convolve(col_mean_value, numpy.full((the_size,), 1./the_size, dtype='float64'),
                                          mode='valid')
                the_max = numpy.amax(smoothed)
            col_mean_value /= the_max
            self.variables.scaled_column_mean = col_mean_value
            # construct the proper weights and prepare information for weight plotting
            self.variables.derived_column_weights = the_sicd.Grid.Col.define_weight_function(populate=False)

        def draw_deltak_lines(canvas, dimension):
            if dimension == 'row':
                # populate row as full bandwidth
                row_deltak1 = (row_count - 1)*(0.5 - 0.5*the_sicd.Grid.Row.SS*the_sicd.Grid.Row.ImpRespBW) + 1
                row_deltak2 = (row_count - 1)*(0.5 + 0.5*the_sicd.Grid.Row.SS*the_sicd.Grid.Row.ImpRespBW) + 1
                # calculate the column deltak1/deltak2 values
                col_deltak1 = (col_count - 1) * (0.5 + the_sicd.Grid.Col.SS*the_sicd.Grid.Col.DeltaK1) + 1
                col_deltak2 = (col_count - 1) * (0.5 + the_sicd.Grid.Col.SS*the_sicd.Grid.Col.DeltaK2) + 1
            elif dimension == 'column':
                # calculate the row deltak1/deltak2 values
                row_deltak1 = (row_count - 1)*(0.5 + the_sicd.Grid.Row.SS*the_sicd.Grid.Row.DeltaK1) + 1
                row_deltak2 = (row_count - 1)*(0.5 + the_sicd.Grid.Row.SS*the_sicd.Grid.Row.DeltaK2) + 1
                # populate column as full bandwidth
                col_deltak1 = (col_count - 1) * (0.5 - 0.5*the_sicd.Grid.Col.SS*the_sicd.Grid.Col.ImpRespBW) + 1
                col_deltak2 = (col_count - 1) * (0.5 + 0.5*the_sicd.Grid.Col.SS*the_sicd.Grid.Col.ImpRespBW) + 1
            else:
                raise ValueError('Unrecognized dimension argument `{}`'.format(dimension))

            # draw the row deltak1/deltak2 lines
            row_deltak1_id = canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, fill='red')
            canvas.modify_existing_shape_using_image_coords(
                row_deltak1_id, (row_deltak1, 0, row_deltak1, col_count))
            deltak2_id = canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, fill='red')
            canvas.modify_existing_shape_using_image_coords(
                deltak2_id, (row_deltak2, 0, row_deltak2, col_count))

            # draw the column deltak1/deltak2 lines
            col_deltak1_id = canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, fill='red')
            canvas.modify_existing_shape_using_image_coords(
                col_deltak1_id, (0, col_deltak1, row_count, col_deltak1))
            deltak2_id = canvas.create_new_line(
                (0, 0, 0, 0), make_current=False, increment_color=False, fill='red')
            canvas.modify_existing_shape_using_image_coords(
                deltak2_id, (0, col_deltak2, row_count, col_deltak2))

        # delete any previous state variables and clear displays
        self._clear_display()
        self.variables.scaled_row_mean = None
        self.variables.derived_row_weights = None
        self.variables.scaled_column_mean = None
        self.variables.derived_column_weights = None
        if self.variables.image_reader is None:
            return

        self.update_idletasks()
        the_sicd = self.variables.image_reader.get_sicd()
        row_count = the_sicd.ImageData.NumRows
        col_count = the_sicd.ImageData.NumCols

        set_row_data()
        self.update_idletasks()
        set_col_data()

    def create_weights_plot(self):
        """
        Create a matplotlib (using the user default backend) of the weight
        information.
        """

        if self.variables.image_reader is None or \
                self.variables.scaled_row_mean is None or \
                self.variables.scaled_column_mean is None:
            return  # nothing to be done currently

        the_sicd = self.variables.image_reader.get_sicd()
        fig, axs = pyplot.subplots(nrows=2, ncols=1)

        the_title = 'Weight information for file {}'.format(
            os.path.split(self.variables.image_reader.file_name)[1])
        fig.suptitle(the_title)

        # plot the row information
        axs[0].set_ylabel('Row Information')
        axs[0].set_xlabel('Krow (cycles/meter)')
        axs[0].plot(
            numpy.linspace(-0.5/the_sicd.Grid.Row.SS,
                           0.5/the_sicd.Grid.Row.SS,
                           self.variables.scaled_row_mean.size),
            self.variables.scaled_row_mean, 'b', lw=1, label='Observed Data')
        if self.variables.derived_row_weights is not None:
            axs[0].plot(numpy.linspace(-0.5*the_sicd.Grid.Row.ImpRespBW,
                                       0.5*the_sicd.Grid.Row.ImpRespBW,
                                       self.variables.derived_row_weights.size),
                        self.variables.derived_row_weights,
                        'g--', lw=3, label='Row Derived Weights')
        if the_sicd.Grid.Row.WgtFunct is not None:
            axs[0].plot(numpy.linspace(-0.5*the_sicd.Grid.Row.ImpRespBW,
                                       0.5*the_sicd.Grid.Row.ImpRespBW,
                                       the_sicd.Grid.Row.WgtFunct.size),
                        the_sicd.Grid.Row.WgtFunct,
                        'r:', lw=3, label='Row.WgtFunct')
        axs[0].set_xlim(min(-0.5/the_sicd.Grid.Row.SS, -0.5*the_sicd.Grid.Row.ImpRespBW),
                        max(0.5/the_sicd.Grid.Row.SS, 0.5*the_sicd.Grid.Row.ImpRespBW))
        axs[0].legend(loc='upper right')

        axs[1].set_ylabel('Column Information')
        axs[1].set_xlabel('Kcol (cycles/meter)')
        axs[1].plot(
            numpy.linspace(-0.5/the_sicd.Grid.Col.SS,
                           0.5/the_sicd.Grid.Col.SS,
                           self.variables.scaled_column_mean.size),
            self.variables.scaled_column_mean, 'b', lw=1, label='Observed Data')
        if self.variables.derived_column_weights is not None:
            axs[1].plot(numpy.linspace(-0.5*the_sicd.Grid.Col.ImpRespBW,
                                       0.5*the_sicd.Grid.Col.ImpRespBW,
                                       self.variables.derived_column_weights.size),
                        self.variables.derived_column_weights,
                        'g--', lw=3, label='Col Derived Weights')
        if the_sicd.Grid.Col.WgtFunct is not None:
            axs[1].plot(numpy.linspace(-0.5*the_sicd.Grid.Col.ImpRespBW,
                                       0.5*the_sicd.Grid.Col.ImpRespBW,
                                       the_sicd.Grid.Col.WgtFunct.size),
                        the_sicd.Grid.Col.WgtFunct,
                        'r:', lw=3, label='Col.WgtFunct')
        axs[1].set_xlim(min(-0.5/the_sicd.Grid.Col.SS, -0.5*the_sicd.Grid.Col.ImpRespBW),
                        max(0.5/the_sicd.Grid.Col.SS, 0.5*the_sicd.Grid.Col.ImpRespBW))
        axs[1].legend(loc='upper right')

        # create a toplevel, and put our figure inside it
        root = tkinter.Toplevel(self.root)

        root.wm_title("Embedding in Tk")

        canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, root)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        # grab the focus, so this is blocking
        root.grab_set()
        root.wait_window()

    def handle_image_index_changed(self):
        """
        Handle that the image index has changed.
        """

        self.my_populate_metaicon()
        self._calculate_fourier_data()

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
        self.row_centered_image_panel.canvas.current_tool = 'VIEW'
        self.row_centered_image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.variables.image_index = 0
        self.set_title()
        # refresh appropriate GUI elements
        self._calculate_fourier_data()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()

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

        the_reader = SICDTypeCanvasImageReader(dirname)
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon(self.variables.image_reader, self.variables.image_reader.index)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer(self.variables.image_reader)

    def __del__(self):
        self._delete_files()


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

    app = FullFrequencySupportTool(root)
    root.geometry("1000x1000")
    if reader is not None:
        app.update_reader(reader)

    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the full support frequency analysis tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
