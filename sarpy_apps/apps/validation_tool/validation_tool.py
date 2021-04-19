# -*- coding: utf-8 -*-
"""
This module provides a tool for doing some basic validation for a SICD file.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

import logging
from logging import Handler
import os

import tkinter
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import showinfo
from tkinter.scrolledtext import ScrolledText

from tk_builder.base_elements import StringDescriptor, TypedDescriptor
from tk_builder.file_filters import create_filter_entry, all_files
from tk_builder.image_reader import ImageReader
from tk_builder.logger import TextHandler
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets

from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata


class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', ComplexImageReader, docstring='')  # type: ComplexImageReader


class ValidationTool(WidgetPanel, WidgetWithMetadata):
    _widget_list = ("image_panel", "pyplot_panel")  # TODO: fix this up...

    def __init__(self, primary):
        self.primary_frame = basic_widgets.Frame(primary)
        WidgetPanel.__init__(self, self.primary_frame)
        WidgetWithMetadata.__init__(self, primary)
        self.variables = AppVariables()

        # create the scrolled text widget for logging output, and corresponding logger handler
        self.text_log_widget = ScrolledText(self.primary_frame)  # type: ScrolledText
        # TODO: any other configuration for the log?
        self.log_handler = TextHandler(self.text_log_widget)  # type: TextHandler
        # attach this handler to the validation logger
        self.logger = logging.getLogger('validation')
        self.logger.addHandler(self.log_handler)

        self.init_w_horizontal_layout()  # TODO: handle packing manually...
        self.set_title()

        # TODO: here are the GUI elements to
        #   3.) button - Local frequency support analysis - open FrequencySupportTool.
        #   4.) button - Full frequency support analysis - this is still remaining. line 1677.
        #   5.) button - Sign verification - open ApertureTool. line 1656.
        #   6.) button - Noise comparison - open RCSTool. line 1914.
        #   7.) button - Geolocation comparison - create a kmz overlay somewhere. line 1630.

        # define menus
        menubar = tkinter.Menu()
        # file menu
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.callback_select_file)
        filemenu.add_command(label="Open Directory", command=self.callback_select_directory)
        filemenu.add_separator()
        filemenu.add_command(label="Save Log", command=self.save_log)
        filemenu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Metadata", menu=popups_menu)

        # handle packing
        self.primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        primary.config(menu=menubar)

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Validation Tool"
        else:
            the_title = "Image Viewer for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        # prompt to save any old log
        self.save_log()
        self.quit()

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

        self.logger.info('Starting validation of sicd structure(s)')
        the_reader = self.variables.image_reader.base_reader
        the_sicds = the_reader.get_sicds_as_tuple()
        for the_index, the_sicd in enumerate(the_sicds):
            msg_id = 'SICD structure at index {}'.format(the_index) if len(the_sicds) else 'SICD structure'
            self.logger.info('Starting validation of {}'.format(msg_id))
            result = the_sicd.is_valid(recursive=True, stack=False)  # this implicitly logs things of note
            if result:
                self.logger.info('***{} appears to be valid***'.format(msg_id))
            self.logger.info('Completed validation for {}\n'.format(msg_id))

    def update_reader(self, the_reader):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : ImageReader
        """

        # prompt to save any old log
        self.save_log()
        # update the reader
        self.variables.image_reader = the_reader
        self.set_title()
        # refresh appropriate GUI elements
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.logger.info('Preparing validation for file {}\n'.format(os.path.abspath(self.variables.image_reader.file_name)))
        self.perform_basic_validation()

    def _disconnect_logging(self):
        if self.log_handler is None:
            return

        logger = logging.getLogger('validation')
        logger.removeHandler(self.log_handler)
        self.log_handler = None

    def callback_select_file(self):
        fname = askopenfilename(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fname is None or fname in ['', ()]:
            return
        # update the default directory for browsing
        self.variables.browse_directory = os.path.split(fname)[0]

        try:
            the_reader = ComplexImageReader(fname)
        except IOError:
            showinfo('Opener not found',
                     message='File {} was not successfully opened as a SICD type.'.format(fname))
            return
        self.update_reader(the_reader)

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        # update the default directory for browsing
        self.variables.browse_directory = os.path.split(dirname)[0]
        try:
            the_reader = ComplexImageReader(dirname)
        except IOError:
            showinfo('Opener not found',
                     message='Directory {} was not successfully opened as a SICD type.'.format(dirname))
            return
        self.update_reader(the_reader)

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon(self.variables.image_reader, 0)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer(self.variables.image_reader)

    def destroy(self):
        self._disconnect_logging()
        try:
            super(ValidationTool, self).destroy()
        except Exception:
            pass

    def __del__(self):
        self.destroy()


def main():
    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = ValidationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
