# -*- coding: utf-8 -*-
"""
This module provides a tool for doing some basic validation for a CPHD file.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Valkyrie Systems Corporation"

import contextlib
import io
import logging
import os

import plotly.offline
import tkinter
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import showinfo
from tkinter.scrolledtext import ScrolledText

from tk_builder.base_elements import StringDescriptor, TypedDescriptor
from tk_builder.file_filters import create_filter_entry, all_files
from tk_builder.logger import TextHandler
from tk_builder.panel_builder import WidgetPanel, WidgetPanelNoLabel
from tk_builder.widgets.basic_widgets import Label, CheckButton, Text, Button
from tk_builder.widgets.widget_descriptors import LabelDescriptor, CheckButtonDescriptor, \
    TextDescriptor, ButtonDescriptor

from sarpy_apps.supporting_classes import cphd_plotting
from sarpy_apps.supporting_classes.file_filters import cphd_files
from sarpy_apps.supporting_classes.image_reader import CPHDTypeCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

import sarpy.consistency.cphd_consistency
from sarpy.io.phase_history.base import CPHDTypeReader
from sarpy.io.general.base import SarpyIOError
import tempfile


class _Buttons(WidgetPanelNoLabel):
    """
    The panel of buttons for validation tasks.
    """

    _widget_list = (
        ('plot_image_area_label', 'plot_image_area_button'),
        ('plot_vector_power_label', 'plot_vector_power_button'),
    )

    plot_image_area_label = LabelDescriptor(
        'plot_image_area_label', default_text='Plot ImageArea and Boresights',
        docstring='')  # type: Label
    plot_image_area_button = ButtonDescriptor(
        'plot_image_area_button', default_text='CPHD ImageArea Plot',
        docstring='')  # type: Button
    plot_vector_power_label = LabelDescriptor(
        'plot_vector_power_label', default_text='Plot CPHD Vector Power',
        docstring='')  # type: Label
    plot_vector_power_button = ButtonDescriptor(
        'plot_vector_power_button', default_text='CPHD Vector Power Plot',
        docstring='')  # type: Button

    def __init__(self, parent):
        """

        Parameters
        ----------
        parent
        """

        WidgetPanelNoLabel.__init__(self, parent)
        self.init_w_rows()


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', CPHDTypeCanvasImageReader, docstring='')  # type: CPHDTypeCanvasImageReader


class ValidationTool(tkinter.PanedWindow, WidgetWithMetadata):
    _widget_list = ("button_panel", "text_log_widget")
    button_panel = TypedDescriptor(
        'button_panel', _Buttons, docstring='the button panel')  # type: _Buttons
    text_log_widget = TypedDescriptor(
        'text_log_widget', ScrolledText, docstring='the log display')  # type: ScrolledText

    def __init__(self, primary, reader=None, **kwargs):
        """

        Parameters
        ----------
        primary : tkinter.Toplevel|tkinter.Tk
        reader : None|str|CPHDTypeReader|CPHDTypeCanvasImageReader
        """

        self.variables = AppVariables()

        if 'sashrelief' not in kwargs:
            kwargs['sashrelief'] = tkinter.RIDGE
        if 'orient' not in kwargs:
            kwargs['orient'] = tkinter.VERTICAL

        tkinter.PanedWindow.__init__(self, primary, **kwargs)
        WidgetWithMetadata.__init__(self, primary)
        self.pack(expand=tkinter.TRUE, fill=tkinter.BOTH)

        # handle packing manually
        self.button_panel = _Buttons(self)
        self.add(self.button_panel, width=700, height=100, padx=5, pady=5, sticky=tkinter.NSEW)

        # create the scrolled text widget for logging output
        self.text_log_widget = ScrolledText(self)  # TODO: other configuration?
        self.add(self.text_log_widget, width=700, height=400, padx=5, pady=5, sticky=tkinter.NSEW)

        # set the logging handler for the validation logger to log to our widget
        self.log_handler = TextHandler(self.text_log_widget)  # type: TextHandler
        self.log_handler.setFormatter(logging.Formatter('%(levelname)s:%(asctime)s - %(message)s', '%Y-%m-%dT%H:%M:%S'))
        # attach this handler to the validation logger
        self.logger = logging.getLogger('validation')
        self.logger.setLevel('INFO')
        self.logger.addHandler(self.log_handler)

        self.set_title()

        # define menus
        self.menu_bar = tkinter.Menu()
        # file menu
        self.file_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open CPHD", command=self.callback_select_file)
        self.file_menu.add_command(label="Open Directory", command=self.callback_select_directory)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save Log", command=self.save_log)
        self.file_menu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        self.metadata_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.metadata_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        self.metadata_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Metadata", menu=self.metadata_menu)

        self.master.config(menu=self.menu_bar)

        # set the callbacks for the button panel
        self.button_panel.plot_image_area_button.config(command=self.callback_plot_image_area)
        self.button_panel.plot_vector_power_button.config(command=self.callback_plot_vector_power)

        self.update_reader(reader)

    def _verify_reader(self):
        # type: () -> bool
        if self.variables.image_reader is not None:
            return True

        showinfo('No CPHD selected', message='First, select a CPHD for this functionality.')
        return False

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "CPHD Validation Tool"
        else:
            the_title = "CPHD Viewer for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self.master.destroy()

    def save_log(self):
        if self.variables.image_reader is None or self.log_handler is None:
            return

        save_fname = asksaveasfilename(
            initialdir=self.variables.browse_directory,
            title="Save validation log output to location?",
            initialfile='{}.validation.txt'.format(os.path.splitext(self.variables.image_reader.file_name)[0]),
            filetypes=[create_filter_entry('Log files', '.log .txt'), all_files])
        if save_fname is None or save_fname in ['', ()]:
            return
        if os.path.splitext(save_fname)[1] == '':
            save_fname += '.validation.txt'
        self.log_handler.save_to_file(save_fname)

    def perform_basic_validation(self):
        if self.variables.image_reader is None:
            return

        fname = self.variables.image_reader.base_reader.file_name
        self.logger.info('Starting validation for {}\n'.format(fname))
        cphd_con = sarpy.consistency.cphd_consistency.CphdConsistency.from_file(fname)
        cphd_con.check()
        with contextlib.redirect_stdout(io.StringIO()) as buffered_stdout:
            cphd_con.print_result(color=False)
        if buffered_stdout.getvalue():
            self.logger.info(buffered_stdout.getvalue())
        else:
            self.logger.info('***{} appears to be valid***'.format(fname))
        self.logger.info('Completed validation for {}\n'.format(fname))
        return

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|CPHDTypeReader|CPHDTypeCanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
            the_reader = CPHDTypeCanvasImageReader(the_reader)

        if isinstance(the_reader, CPHDTypeReader):
            the_reader = CPHDTypeCanvasImageReader(the_reader)

        if not isinstance(the_reader, CPHDTypeCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        # update the reader
        self.variables.image_reader = the_reader
        self.set_title()
        # refresh appropriate GUI elements
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.log_handler.clear()
        # perform the initial validation
        self.logger.info(
            'Preparing validation for file {}\n'.format(
                os.path.abspath(self.variables.image_reader.file_name)))
        self.perform_basic_validation()

    def _disconnect_logging(self):
        if self.log_handler is None:
            return

        logger = logging.getLogger('validation')
        logger.removeHandler(self.log_handler)
        self.log_handler = None

    def callback_select_file(self):
        fname = askopenfilename(initialdir=self.variables.browse_directory, filetypes=[cphd_files])
        if fname is None or fname in ['', ()]:
            return

        try:
            the_reader = CPHDTypeCanvasImageReader(fname)
        except SarpyIOError:
            showinfo('Opener not found',
                     message='File {} was not successfully opened as a CPHD type.'.format(fname))
            return
        self.update_reader(the_reader, update_browse=os.path.split(fname)[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return

        try:
            the_reader = CPHDTypeCanvasImageReader(dirname)
        except SarpyIOError:
            showinfo('Opener not found',
                     message='Directory {} was not successfully opened as a CPHD type.'.format(dirname))
            return
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def callback_plot_image_area(self):
        """
        Enable the plot metadata analysis
        """

        if not self._verify_reader():
            return

        reader = self.variables.image_reader.base_reader
        fig = cphd_plotting.plot_image_area(reader)
        dir_name = tempfile.mkdtemp()
        temp_file = os.path.join(dir_name, 'temp-plot.html')
        plotly.offline.plot(fig, filename=temp_file)

    def callback_plot_vector_power(self):
        """
        Enable the vector power visualization
        """

        if not self._verify_reader():
            return

        reader = self.variables.image_reader.base_reader
        root = tkinter.Toplevel(self.master)
        cphd_plotting.CphdVectorPower(root, reader)

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon_from_reader(self.variables.image_reader)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer_from_reader(self.variables.image_reader)

    def destroy(self):
        self._disconnect_logging()
        # noinspection PyBroadException
        try:
            super(ValidationTool, self).destroy()
        except Exception:
            pass


def main(reader=None):
    """
    Main method for initializing the tool

    Parameters
    ----------
    reader : None|str|CPHDTypeReader|CPHDTypeCanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = ValidationTool(root, reader=reader)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the validation tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None,  nargs='?',
        help='The path to the optional CPHD file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
