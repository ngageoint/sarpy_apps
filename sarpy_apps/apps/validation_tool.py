# -*- coding: utf-8 -*-
"""
This module provides a tool for doing some basic validation for a SICD file.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

import logging
import os

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

from sarpy_apps.apps.aperture_tool import RegionSelection
from sarpy_apps.apps.local_support_tool import LocalFrequencySupportTool
from sarpy_apps.apps.full_support_tool import FullFrequencySupportTool
from sarpy_apps.apps.rcs_tool import RCSTool
from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.visualization.kmz_product_creation import create_kmz_view
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.complex.sicd import SICDReader
from sarpy.consistency.sicd_consistency import check_file
from sarpy.io.general.base import SarpyIOError


class _Feedback(WidgetPanel):
    _widget_list = (
        ('title_label', ),
        ('acceptable_label', 'acceptable_button'),
        ('feedback_label', 'feedback_text'),
        ('cancel_button', 'submit_button'))

    title_label = LabelDescriptor(
        'title_label', default_text='',
        docstring='The overall title')  # type: Label
    acceptable_label = LabelDescriptor(
        'acceptable_label', default_text='acceptable?', docstring='')  # type: Label
    acceptable_button = CheckButtonDescriptor(
        'acceptable_button', docstring='')  # type: CheckButton
    feedback_label = LabelDescriptor(
        'feedback_label', default_text='feedback', docstring='')  # type: Label
    feedback_text = TextDescriptor(
        'feedback_text', docstring='The widget to provide log information')  # type: Text
    cancel_button = ButtonDescriptor(
        'cancel_button', default_text='Cancel', docstring='')  # type: Button
    submit_button = ButtonDescriptor(
        'submit_button', default_text='Submit', docstring='')  # type: Button

    def __init__(self, root, title_text):
        """

        Parameters
        ----------
        root : tkinter.Toplevel
        title_text : str
        """

        WidgetPanel.__init__(self, root)
        self.init_w_rows()
        self.title_label.set_text(title_text)


class FeedbackPopup(object):
    """
    Class enabling feedback from validation steps
    """

    def __init__(self, primary, title_text):
        self.use_feedback = True  # type: bool
        self.acceptable = False  # type: bool
        self.feedback_text = ''  # type: str

        self.root = tkinter.Toplevel(primary)
        self.widget = _Feedback(self.root, title_text)
        self.widget.set_text('Feedback')

        # label appearance
        self.widget.title_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.widget.acceptable_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.widget.feedback_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)

        # set up callbacks
        self.widget.cancel_button.config(command=self.callback_cancel)
        self.widget.submit_button.config(command=self.callback_submit)

    def callback_cancel(self):
        self.use_feedback = False
        self.root.destroy()

    def callback_submit(self):
        self.use_feedback = True
        self.acceptable = self.widget.acceptable_button.instate(['selected'])
        self.feedback_text = self.widget.feedback_text.get('1.0', 'end-1c')
        self.root.destroy()


class _Buttons(WidgetPanelNoLabel):
    """
    The panel of buttons for validation tasks.
    """

    _widget_list = (
        ('local_fs_label', 'local_fs_button'),
        ('full_fs_label', 'full_fs_button'),
        ('sign_label', 'sign_button'),
        ('noise_label', 'noise_button'),
        ('geolocation_label', 'geolocation_button'))

    local_fs_label = LabelDescriptor(
        'local_fs_label', default_text='Perform local frequency support analysis',
        docstring='')  # type: Label
    local_fs_button = ButtonDescriptor(
        'local_fs_button', default_text='Frequency Support Tool',
        docstring='')  # type: Button

    full_fs_label = LabelDescriptor(
        'full_fs_label', default_text='Perform full image frequency analysis',
        docstring='')  # type: Label
    full_fs_button = ButtonDescriptor(
        'full_fs_button', default_text='Frequency Analysis Tool',
        docstring='')  # type: Button

    sign_label = LabelDescriptor(
        'sign_label', default_text='Perform Fourier analysis',
        docstring='')  # type: Label
    sign_button = ButtonDescriptor(
        'sign_button', default_text='Aperture Tool',
        docstring='')  # type: Button

    noise_label = LabelDescriptor(
        'noise_label', default_text='Perform noise analysis',
        docstring='')  # type: Label
    noise_button = ButtonDescriptor(
        'noise_button', default_text='RCS Tool',
        docstring='')  # type: Button

    geolocation_label = LabelDescriptor(
        'geolocation_label', default_text='Perform basic geolocation analysis',
        docstring='')  # type: Label
    geolocation_button = ButtonDescriptor(
        'geolocation_button', default_text='Create kmz',
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
        'image_reader', SICDTypeCanvasImageReader, docstring='')  # type: SICDTypeCanvasImageReader


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
        reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
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
        self.add(self.button_panel, width=700, height=300, padx=5, pady=5, sticky=tkinter.NSEW)

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
        self.file_menu.add_command(label="Open Image", command=self.callback_select_file)
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
        self.button_panel.local_fs_button.config(command=self.callback_local_fs)
        self.button_panel.full_fs_button.config(command=self.callback_full_fs)
        self.button_panel.sign_button.config(command=self.callback_sign)
        self.button_panel.noise_button.config(command=self.callback_noise)
        self.button_panel.geolocation_button.config(command=self.callback_geolocation)

        self.update_reader(reader)

    def _verify_reader(self):
        # type: () -> bool
        if self.variables.image_reader is not None:
            return True

        showinfo('No complex image selected', message='First, select a complex image for this functionality.')
        return False

    def _get_and_log_feedback(self, title_text):
        # type: (str) -> None
        feedback = FeedbackPopup(self.master, title_text)
        feedback.root.grab_set()
        feedback.root.wait_window()
        if not feedback.use_feedback:
            return

        feedback_text = feedback.feedback_text.strip()
        if feedback_text != '':
            feedback_text += '\n'
        if feedback.acceptable:
            self.logger.info('{} acceptable\n{}'.format(title_text, feedback_text))
        else:
            self.logger.error('{} unacceptable\n{}'.format(title_text, feedback_text))

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

        the_reader = self.variables.image_reader.base_reader
        if isinstance(the_reader, SICDReader):
            msg_id = 'SICD structure for file {}'.format(the_reader.file_name)
            self.logger.info('Starting validation of {}'.format(msg_id))
            # noinspection PyUnresolvedReferences
            result = check_file(the_reader.nitf_details)
            if result:
                self.logger.info('***{} appears to be valid***'.format(msg_id))
            self.logger.info('Completed validation for {}\n'.format(msg_id))
        else:
            # noinspection PyUnresolvedReferences
            the_sicds = the_reader.get_sicds_as_tuple()
            for the_index, the_sicd in enumerate(the_sicds):
                msg_id = 'SICD structure at index {}'.format(the_index) if len(the_sicds) > 1 else 'SICD structure'
                self.logger.info('Starting validation of {}'.format(msg_id))
                result = the_sicd.is_valid(recursive=True, stack=False)  # this implicitly logs things of note
                if result:
                    self.logger.info('***{} appears to be valid***'.format(msg_id))
                self.logger.info('Completed validation for {}\n'.format(msg_id))

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
        fname = askopenfilename(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fname is None or fname in ['', ()]:
            return

        try:
            the_reader = SICDTypeCanvasImageReader(fname)
        except SarpyIOError:
            showinfo('Opener not found',
                     message='File {} was not successfully opened as a SICD type.'.format(fname))
            return
        self.update_reader(the_reader, update_browse=os.path.split(fname)[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return

        try:
            the_reader = SICDTypeCanvasImageReader(dirname)
        except SarpyIOError:
            showinfo('Opener not found',
                     message='Directory {} was not successfully opened as a SICD type.'.format(dirname))
            return
        self.update_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def callback_local_fs(self):
        """
        Enable the local frequency support analysis
        """

        if not self._verify_reader():
            return

        # create a complex image reader - don't pass the same one around, so no hidden state
        reader = SICDTypeCanvasImageReader(self.variables.image_reader.base_reader)
        # open the frequency support tool based on this reader
        root = tkinter.Toplevel(self.master)  # create a new toplevel with its own mainloop, so it's blocking
        tool = LocalFrequencySupportTool(root, reader=reader)
        root.grab_set()
        root.wait_window()

        self._get_and_log_feedback('Local Frequency Support (DeltaKCOAPoly)')

    def callback_full_fs(self):
        """
        Enable the full image frequency analysis
        """

        if not self._verify_reader():
            return

        # create a complex image reader - don't pass the same one around, so no hidden state
        reader = SICDTypeCanvasImageReader(self.variables.image_reader.base_reader)
        # open the frequency support tool based on this reader
        root = tkinter.Toplevel(self.master)  # create a new toplevel with its own mainloop, so it's blocking
        tool = FullFrequencySupportTool(root, reader=reader)
        root.grab_set()
        root.wait_window()

        self._get_and_log_feedback('Full Image Frequency Support')

    def callback_sign(self):
        """
        Enable Fourier sign analysis
        """

        if not self._verify_reader():
            return

        # create a complex image reader - don't pass the same one around, so no hidden state
        reader = SICDTypeCanvasImageReader(self.variables.image_reader.base_reader)
        # open the aperture tool based on this reader
        root = tkinter.Toplevel(self.master)  # create a new toplevel with its own mainloop, so it's blocking
        tool = RegionSelection(root, reader=reader)
        root.grab_set()
        root.wait_window()

        self._get_and_log_feedback('Fourier Sign')

    def callback_noise(self):
        """
        Enable noise analysis
        """

        if not self._verify_reader():
            return

        # create a complex image reader - don't pass the same one around, so no hidden state
        reader = SICDTypeCanvasImageReader(self.variables.image_reader.base_reader)
        # open the rcs tool based on this reader
        root = tkinter.Toplevel()  # create a new toplevel with its own mainloop, so it's blocking
        tool = RCSTool(root, reader=reader)
        root.grab_set()
        root.wait_window()

        self._get_and_log_feedback('Noise Value')

    def callback_geolocation(self):
        """
        Enable basic geolocation comparison
        """

        if not self._verify_reader():
            return

        # find a place to save the overlay, then produce it
        initialdir, fstem = os.path.split(os.path.abspath(self.variables.image_reader.file_name))
        dirname = askdirectory(initialdir=initialdir, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return

        fstem_part = os.path.splitext(fstem)[0]
        kmz_file_stem = 'View-{}'.format(fstem_part)
        showinfo('KMZ creation',
                 message='This may be somewhat time consuming.\n'
                         'KMZ file(s) being created in directory {}\n'
                         'The created filename will begin with {}\n'
                         'Once the file(s) are created, review and provide feedback.'.format(dirname, kmz_file_stem))
        create_kmz_view(
            self.variables.image_reader.base_reader, dirname,
            inc_scp=True, inc_collection_wedge=True,
            file_stem=kmz_file_stem, pixel_limit=3072)
        showinfo('KMZ creation complete',
                 message='KMZ file(s) created in directory {}\n'
                         'The created filename(s) begin with {}\n'
                         'Review and provide feedback.'.format(dirname, kmz_file_stem))

        self._get_and_log_feedback('Geolocation')

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
    reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
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
        help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
