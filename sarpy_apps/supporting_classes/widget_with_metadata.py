"""
A general use generally abstract class for metaicon and metaviewer functionality.
"""

__author__ = "Thomas McCullough"
__classification__ = "UNCLASSIFIED"

import tkinter

from tk_builder.image_reader import CanvasImageReader

from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader, \
    DerivedCanvasImageReader
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon


class WidgetWithMetadata(object):
    """
    Common use framework for handling metaicon and metaviewer functionality.
    """

    def __init__(self, master):
        """

        Parameters
        ----------
        master : tkinter.Tk|tkinter.Toplevel
        """

        self.metaicon_popup_panel = tkinter.Toplevel(master)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)
        self.metaicon.hide_on_close()
        self.metaicon_popup_panel.withdraw()

        self.metaviewer_popup_panel = tkinter.Toplevel(master)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)
        self.metaviewer.hide_on_close()
        self.metaviewer_popup_panel.withdraw()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.deiconify()

    def metaicon_popup(self):
        self.metaicon_popup_panel.deiconify()

    def populate_metaicon(self, image_reader, the_index):
        """
        Populate the metaicon.

        Parameters
        ----------
        image_reader : CanvasImageReader
        the_index : int
        """

        if image_reader is None:
            self.metaicon.make_empty()

        if isinstance(image_reader, ComplexCanvasImageReader):
            self.metaicon.create_from_reader(image_reader.base_reader, index=the_index)
        elif isinstance(image_reader, DerivedCanvasImageReader):
            self.metaicon.create_from_reader(image_reader.base_reader, index=the_index)
        else:
            self.metaicon.make_empty()

    def populate_metaviewer(self, image_reader):
        """
        Populate the metaviewer.

        Parameters
        ----------
        image_reader : CanvasImageReader
        """

        if image_reader is None:
            self.metaviewer.empty_entries()

        if isinstance(image_reader, (ComplexCanvasImageReader, DerivedCanvasImageReader)):
            self.metaviewer.populate_from_reader(image_reader.base_reader)
        else:
            self.metaviewer.empty_entries()
