"""
A general use class for metaicon and metaviewer functionality, intended to be
used only by extension.
"""

__author__ = "Thomas McCullough"
__classification__ = "UNCLASSIFIED"

import tkinter

from tk_builder.panels.image_panel import ImagePanel
from tk_builder.image_reader import CanvasImageReader
from tk_builder.widgets.derived_widgets import PopupWindow

from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader, \
    DerivedCanvasImageReader
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon


class WidgetWithMetadata(object):
    """
    Common use framework for handling metaicon and metaviewer functionality.
    """

    def __init__(self, master, image_panel=None):
        """

        Parameters
        ----------
        master : tkinter.Tk|tkinter.Toplevel
        image_panel : None|ImagePanel
            An associated image panel
        """

        self.metaicon_popup_panel = PopupWindow(master)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)

        self.metaviewer_popup_panel = PopupWindow(master)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)

        self.image_panel = image_panel

    def metaicon_popup(self):
        self.metaicon_popup_panel.popup_callback()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.popup_callback()

    def populate_metaicon_from_reader(self, image_reader):
        """
        Populate the metaicon from the given reader.

        Parameters
        ----------
        image_reader : None|CanvasImageReader
        """

        if isinstance(image_reader, ComplexCanvasImageReader):
            self.metaicon.create_from_reader(image_reader.base_reader, index=image_reader.index)
        elif isinstance(image_reader, DerivedCanvasImageReader):
            self.metaicon.create_from_reader(image_reader.base_reader, index=image_reader.index)
        else:
            self.metaicon.make_empty()

    def populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.image_panel is None:
            self.populate_metaicon_from_reader(None)
        else:
            self.populate_metaicon_from_reader(self.image_panel.image_reader)

    def populate_metaviewer_from_reader(self, image_reader):
        """
        Populate the metaviewer from the given reader.

        Parameters
        ----------
        image_reader : None|CanvasImageReader
        """

        if image_reader is None:
            self.metaviewer.empty_entries()

        if isinstance(image_reader, (ComplexCanvasImageReader, DerivedCanvasImageReader)):
            self.metaviewer.populate_from_reader(image_reader.base_reader)
        else:
            self.metaviewer.empty_entries()

    def populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.image_panel is None:
            self.populate_metaviewer_from_reader(None)
        else:
            self.populate_metaviewer_from_reader(self.image_panel.image_reader)
