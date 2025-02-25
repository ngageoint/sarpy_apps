"""
A general use class for metaicon and metaviewer functionality, intended to be
used only by extension.
"""

__author__ = "Thomas McCullough"
__classification__ = "UNCLASSIFIED"

#import tkinter
import logging

#from tk_builder.panels.image_panel import ImagePanel
#from tk_builder.image_reader import CanvasImageReader
from tk_builder.widgets.derived_widgets import PopupWindow

from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader, \
    DerivedCanvasImageReader
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
#from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon

#logger = logging.getLogger(__name__)
#logging.basicConfig(filename='widget.log', encoding='utf-8', level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
import sys
import os
directory = os.path.dirname(os.path.abspath(sys.argv[0])) 
#print("Current dir", directory)
parent_directory = os.getcwd()
#print("Parent dir", parent_directory)
classes_dir = 'supporting_classes'
metaicon_dir = 'metaicon'
full_class_path = os.path.join(parent_directory, classes_dir)
#print("Full path for classes", full_class_path)
metaicon_path = os.path.join(full_class_path, metaicon_dir)
#print("Metaicon path", metaicon_path)
sys.path.append(full_class_path)
from metaicon.metaicon import MetaIcon


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
        print("I am in WidgetWithMetadata")
        self.logger = logging.getLogger('WidgetWithMetadata')
        self.logger.setLevel('INFO')
        self.logger.info("WidgetWithMetadata __init__")
        self.metaicon_popup_panel = PopupWindow(master)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)

        self.metaviewer_popup_panel = PopupWindow(master)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)

        self.image_panel = image_panel

    def metaicon_popup(self):
        self.logger.info("metaicon_popup")
        self.metaicon_popup_panel.popup_callback()

    def metaviewer_popup(self):
        self.logger.info("metaviewer_popup")
        self.metaviewer_popup_panel.popup_callback()

    def populate_metaicon_from_reader(self, image_reader):
        """
        Populate the metaicon from the given reader.

        Parameters
        ----------
        image_reader : None|CanvasImageReader
        """
        self.logger.info("populate_metaicon_from_reader")
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

        self.logger.info("In populate_metaicon in WidgetWithMetadata {self.image_panel}")
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
        self.logger.info("In populate_metaviewer_from_reader in WidgetWithMetadata {image_reader}")

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
        self.logger.info("In populate_metaviewer in WidgetWithMetadata {self.image_panel}")

        if self.image_panel is None:
            self.populate_metaviewer_from_reader(None)
        else:
            self.populate_metaviewer_from_reader(self.image_panel.image_reader)


