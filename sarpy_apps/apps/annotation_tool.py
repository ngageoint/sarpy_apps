"""
A tool for creating basic annotations on an image
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

import logging
from typing import Union, Sequence, Dict, List
from collections import defaultdict
import os

import tkinter
from tkinter import ttk, Button as tkButton, PanedWindow
from tkinter.messagebox import showinfo, askyesnocancel
from tkinter.colorchooser import askcolor
from tkinter.filedialog import askopenfilename, askdirectory, asksaveasfilename

from tk_builder.base_elements import StringDescriptor, BooleanDescriptor
from tk_builder.widgets.image_canvas_tool import ShapeTypeConstants
from tk_builder.image_reader import CanvasImageReader
from tk_builder.panels.image_panel import ImagePanel

from tk_builder.widgets.basic_widgets import Frame, Label, Entry, Button, \
    Combobox, Notebook
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling, TextWithScrolling
from tk_builder.widgets.widget_descriptors import LabelDescriptor, EntryDescriptor, TypedDescriptor

from sarpy_apps.supporting_classes.file_filters import common_use_collection, all_files, json_files
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader, \
    DerivedCanvasImageReader, CPHDTypeCanvasImageReader, CRSDTypeCanvasImageReader, \
    GeneralCanvasImageReader


from sarpy.annotation.base import FileAnnotationCollection, AnnotationFeature, GeometryProperties
from sarpy.geometry.geometry_elements import Point, LineString, LinearRing, \
    Polygon, basic_assemble_from_collection

from sarpy.io.general.base import BaseReader
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.product.base import SIDDTypeReader
from sarpy.io.phase_history.base import CPHDTypeReader
from sarpy.io.received.base import CRSDTypeReader
from sarpy.io import open as open_general


logger = logging.getLogger(__name__)


##############
# application variables which will serve as a common namespace and bookkeeping

class AppVariables(object):
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    unsaved_changes = BooleanDescriptor(
        'unsaved_changes', default_value=False,
        docstring='Are there unsaved annotation changes to be saved?')  # type: bool
    image_reader = TypedDescriptor(
        'image_reader', CanvasImageReader, docstring='')  # type: CanvasImageReader
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileAnnotationCollection,
        docstring='The file annotation collection.')  # type: FileAnnotationCollection
    annotation_file_name = StringDescriptor(
        'annotation_file_name',
        docstring='The path for the annotation results file.')  # type: str
    allow_multi_geometry = BooleanDescriptor(
        'allow_multi_geometry', default_value=True)  # type: bool

    def __init__(self):
        self._feature_to_canvas = {}  # a dictionary mapping feature.uid to shape ids on the canvas
        self._canvas_to_feature = {}  # a dictionary mapping canvas id to feature.uid
        self._canvas_to_geometry = {}  # a dictionary mapping canvas id to geometry.uid
        self._geometry_to_canvas = {}  # a dictionary mapping geometry.uid to canvas id
        self._geometry_type = {}  # dictionary mapping geometry.uid to shape type
        self._current_geometry_id = None
        self._current_feature_id = None

    @property
    def feature_to_canvas(self):
        # type: () -> Dict[str, List]
        """
        dict: The dictionary of feature_id to corresponding items on annotate canvas.
        """

        return self._feature_to_canvas

    @property
    def canvas_to_feature(self):
        # type: () -> Dict[int, str]
        """
        dict: The dictionary of annotate canvas id to feature_id.
        """

        return self._canvas_to_feature

    @property
    def canvas_to_geometry(self):
        # type: () -> Dict[int, str]
        """
        dict: The dictionary of annotate canvas id to geometry_id.
        """

        return self._canvas_to_geometry

    @property
    def geometry_to_canvas(self):
        # type: () -> Dict[str, int]
        """
        dict: The dictionary of geometry id to annotate canvas id.
        """

        return self._geometry_to_canvas

    @property
    def geometry_type(self):
        # type: () -> Dict[str, str]
        """
        dict: The dictionary of geometry id to shape type.
        """

        return self._geometry_type

    @property
    def current_canvas_id(self):
        """
        None|int: The current annotation feature id.
        """

        return self._canvas_to_geometry.get(self._current_geometry_id)

    @property
    def current_feature_id(self):
        """
        None|str: The current feature id.
        """

        return self._current_feature_id

    @property
    def current_geometry_id(self):
        """
        None|str: The current geometry id.
        """

        return self._current_geometry_id

    def get_canvas_shapes_for_feature(self, feature_id):
        """
        Gets the annotation shape ids associated with the given feature id.

        Parameters
        ----------
        feature_id : str

        Returns
        -------
        None|List[int]
        """

        return self._feature_to_canvas.get(feature_id, None)

    def get_feature_for_canvas(self, canvas_id):
        """
        Gets the feature id associated with the given canvas id.

        Parameters
        ----------
        canvas_id : int

        Returns
        -------
        None|str
        """

        return self._canvas_to_feature.get(canvas_id, None)

    def get_geometry_for_canvas(self, canvas_id):
        """
        Gets the geometry id associated with the given canvas id.

        Parameters
        ----------
        canvas_id : int

        Returns
        -------
        None|str
        """

        return self._canvas_to_geometry.get(canvas_id, None)

    def get_canvas_for_geometry(self, geometry_id):
        """
        Gets the canvas id associated with the given geometry id.

        Parameters
        ----------
        geometry_id : str

        Returns
        -------
        None|int
        """

        return self._geometry_to_canvas.get(geometry_id, None)

    def get_geometry_type(self, geometry_id):
        """
        Gets the shape type for the given geometry id.

        Parameters
        ----------
        geometry_id : str

        Returns
        -------
        None|str
        """

        return self._geometry_type.get(geometry_id, None)

    def reinitialize_features(self):
        """
        Reinitialize the feature tracking dictionaries. Note that this assumes that
        the context and annotate canvases have been reinitialized elsewhere.

        Returns
        -------
        None
        """

        self._feature_to_canvas = {}
        self._canvas_to_feature = {}
        self._canvas_to_geometry = {}
        self._geometry_to_canvas = {}
        self._geometry_type = {}
        self._current_geometry_id = None
        self._current_feature_id = None

    def initialize_feature_tracking(self, feature_id):
        """
        Helper function to initialize feature tracking for the given feature id.

        Parameters
        ----------
        feature_id : str
        """

        if feature_id in self._feature_to_canvas:
            raise KeyError('We are already tracking feature id {}'.format(feature_id))

        self._feature_to_canvas[feature_id] = []

    def set_canvas_tracking(self, canvas_id, feature_id, geometry_id, geometry_type):
        """
        Initialize feature tracking between the given feature id, the given annotate
        id, and the geometry properties.

        Parameters
        ----------
        feature_id : str
        canvas_id : int
        geometry_id : str
        geometry_type : str
        """

        if feature_id not in self._feature_to_canvas:
            self.initialize_feature_tracking(feature_id)

        # is the canvas id associated with another feature or geometry? It should not be.
        current_feature = self._canvas_to_feature.get(canvas_id, None)
        current_geometry = self._canvas_to_geometry.get(geometry_id, None)
        if current_feature is not None and current_feature != feature_id:
            raise ValueError(
                'canvas id {} is associated with feature id {},\n\t'
                'not {} as requested.'.format(canvas_id, current_feature, feature_id))
        if current_geometry is not None and current_geometry != geometry_id:
            raise ValueError(
                'canvas id {} is associated with geometry id {},\n\t'
                'not {} as requested.'.format(canvas_id, current_geometry, geometry_id))

        # is the geometry associated with another canvas id? it should not be.from
        current_canvas = self._geometry_to_canvas.get(geometry_id, None)
        if current_canvas is not None and current_canvas != canvas_id:
            raise ValueError(
                'geometry id {} is associated with canvas id {},\n\t'
                'not {} as requested.'.format(geometry_id, current_canvas, canvas_id))

        if current_feature is None:
            self._feature_to_canvas[feature_id].append(canvas_id)
            self._canvas_to_feature[canvas_id] = feature_id
        if current_geometry is None:
            self._canvas_to_geometry[canvas_id] = geometry_id
        if current_canvas is None:
            self._geometry_to_canvas[geometry_id] = canvas_id
            self._geometry_type[geometry_id] = geometry_type

    def delete_feature_from_tracking(self, feature_id, geometry_ids):
        """
        Remove the given feature from tracking. The associated annotate shape
        elements which should be deleted will be returned.

        Parameters
        ----------
        feature_id : str
        geometry_ids : List[str]

        Returns
        -------
        List[int]
            The list of annotate shape ids for deletion.
        """

        # dump the geometry ids
        for geom_id in geometry_ids:
            del self._geometry_to_canvas[geom_id]

        the_canvas_ids = self._feature_to_canvas.get(feature_id, None)
        if the_canvas_ids is None:
            return  # nothing being tracked - nothing to be done

        delete_shapes = []

        # for any shape not reassigned, set assignment to None
        for entry in the_canvas_ids:
            if entry not in self._canvas_to_feature:
                continue  # we've already actually deleted the shape
            associated_feat = self._canvas_to_feature[entry]
            if associated_feat is None:
                # this is marked for deletion, but deletion didn't happen
                delete_shapes.append(entry)
            elif associated_feat != feature_id:
                # reassigned to a different feature, do nothing
                continue
            else:
                # assign this tracking to None, to mark for deletion
                self._canvas_to_feature[entry] = None
                self._canvas_to_geometry[entry] = None
                delete_shapes.append(entry)
        # remove the feature from tracking
        del self._feature_to_canvas[feature_id]
        return delete_shapes

    def delete_geometry_from_tracking(self, geometry_id):
        """
        Remove the geometry id from tracking against the feature and canvas id.

        Parameters
        ----------
        geometry_id : str

        Returns
        -------
        None|int
            Any associated canvas id that must be deleted.
        """

        if geometry_id not in self._geometry_to_canvas:
            return

        canvas_id = self.get_canvas_for_geometry(geometry_id)
        feature_id = self.get_feature_for_canvas(canvas_id)

        if geometry_id in self._geometry_to_canvas:
            del self._geometry_to_canvas[geometry_id]
        if geometry_id in self._geometry_type:
            del self._geometry_type[geometry_id]

        if canvas_id is not None:
            del self._canvas_to_geometry[canvas_id]
            del self._canvas_to_feature[canvas_id]

        if feature_id is not None:
            try:
                self._feature_to_canvas[feature_id].remove(canvas_id)
            except ValueError:
                pass
        return canvas_id

    def delete_shape_from_tracking(self, canvas_id):
        """
        Remove the canvas id from tracking against the feature and geometry id.

        Parameters
        ----------
        canvas_id : int
        """

        if canvas_id not in self._canvas_to_feature:
            return

        # verify that association with None as feature.
        feat_id = self._canvas_to_feature.get(canvas_id, None)
        if feat_id is not None:
            raise ValueError(
                "We can't delete canvas id {}, because it is still associated "
                "with feature {}".format(canvas_id, feat_id))
        geom_id = self._canvas_to_geometry.get(canvas_id, None)
        if geom_id is not None:
            raise ValueError(
                "We can't delete canvas id {}, because it is still associated "
                "with geometry {}".format(canvas_id, geom_id))

        # actually remove the tracking entries
        del self._canvas_to_feature[canvas_id]
        del self._canvas_to_geometry[canvas_id]

    def get_current_annotation_object(self):
        """
        Gets the current annotation object

        Returns
        -------
        None|AnnotationFeature
        """

        if self._current_feature_id is None:
            return None
        return self.file_annotation_collection.annotations[self._current_feature_id]

    def get_current_geometry_properties(self):
        """
        Gets the current geometry properties object.

        Returns
        -------
        None|GeometryProperties
        """

        annotation = self.get_current_annotation_object()
        if annotation is None:
            return None

        if self._current_geometry_id is None:
            return None
        try:
            return annotation.properties.get_geometry_property(self._current_geometry_id)
        except KeyError:
            logger.warning('unknown geometry id {}, so no geometry can be returned'.format(self._current_geometry_id))
            return None


##############
# GUI Panel for viewing and manipulating the annotation details
#   this should probably have it's own top level

class NamePanel(Frame):
    """
    A simple panel for name display
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        app_variables : AppVariables
        """

        self.default_name = '<no name>'
        self._app_variables = app_variables  # type: AppVariables
        self.annotation_feature = None  # type: Union[None, AnnotationFeature]
        Frame.__init__(self, master, **kwargs)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.id_label = Label(self, text='ID:', width=12)  # type: Label
        self.id_label.grid(row=0, column=0, sticky='NW')
        self.id_value = Label(self, text='', width=12)  # type: Label
        self.id_value.grid(row=0, column=1, sticky='NEW')

        self.name_label = Label(self, text='Name:', width=12)  # type: Label
        self.name_label.grid(row=1, column=0, sticky='NW')
        self.name_value = Entry(self, text=self.default_name, width=12)  # type: Entry
        self.name_value.grid(row=1, column=1, sticky='NEW')

        self.grid_columnconfigure(1, weight=1)

        # setup the appearance of label
        self.id_value.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=3)
        self.update_annotation()

    def update_annotation(self):
        current_feature_id = self._app_variables.current_feature_id
        if self._app_variables.file_annotation_collection is None or current_feature_id is None:
            self.set_annotation_feature(None)
            return

        annotation = self._app_variables.file_annotation_collection.annotations[current_feature_id]
        self.set_annotation_feature(annotation)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        if annotation_feature is None:
            self._set_id_value(None)
            self._set_name_value(None)
        else:
            self._set_id_value(annotation_feature.uid)
            self._set_name_value(annotation_feature.get_name())

    def _set_id_value(self, value):
        if value is None:
            value = ''
        self.id_value.set_text(value)

    def _set_name_value(self, value):
        if value is None:
            value = self.default_name
        self.name_value.set_text(value)

    def _get_name_value(self):
        value = self.name_value.get().strip()
        return None if value in ['', self.default_name] else value

    def cancel(self):
        self.set_annotation_feature(self.annotation_feature)

    def save(self):
        if self.annotation_feature is None:
            return
        name_value = self._get_name_value()
        if name_value is not None and name_value != self.annotation_feature.get_name():
            self.annotation_feature.properties.name = name_value


class AnnotateButtons(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.delete_button = Button(self, text='Delete Shape')  # type: Button
        self.delete_button.pack(side=tkinter.LEFT, padx=3, pady=3)

        self.cancel_button = Button(self, text='Cancel')  # type: Button
        self.cancel_button.pack(side=tkinter.RIGHT, padx=3, pady=3)

        self.apply_button = Button(self, text='Apply')  # type: Button
        self.apply_button.pack(side=tkinter.RIGHT, padx=3, pady=3)


class AnnotateDetailsPanel(Frame):
    """
    A panel for displaying the basic details of the annotation
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        app_variables : AppVariables
        kwargs
        """

        self._app_variables = app_variables  # type: AppVariables
        self.annotation_feature = None  # type: Union[None, AnnotationFeature]
        self.directory_values = set()
        Frame.__init__(self, master, **kwargs)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.directory_label = Label(self, text='Directory:', width=12)  # type: Label
        self.directory_label.grid(row=0, column=0, sticky='NW', padx=5, pady=5)
        self.directory_value = Combobox(self, text='')  # type: Combobox
        self.directory_value.grid(row=0, column=1, sticky='NEW', padx=5, pady=5)

        self.description_label = Label(self, text='Description:', width=12)  # type: Label
        self.description_label.grid(row=1, column=0, sticky='NW', padx=5, pady=5)
        self.description_value = TextWithScrolling(self)  # type: TextWithScrolling
        self.description_value.frame.grid(row=1, column=1, sticky='NSEW', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.update_annotation_collection()

    @property
    def annotation_collection(self):
        """
        AnnotationCollection : the annotation collection
        """

        return self._app_variables.file_annotation_collection.annotations

    def _set_directory_values(self):
        self.directory_values = set()
        if self.annotation_collection is None:
            return

        for entry in self.annotation_collection.features:
            dir_value = entry.properties.directory
            if dir_value is not None:
                dir_parts = dir_value.split('/')
                root = ''
                for part in dir_parts:
                    element = root + part if root != '' else root + '/' + part
                    self.directory_values.add(element)

    def _set_directory(self, value):
        # type: (Union[None, str]) -> None
        self.directory_value.set_text('' if value is None else value)

    def _get_directory(self):
        # type: () -> str
        value = self.directory_value.get().strip()
        return None if value == '' else value

    def _set_description(self, value):
        # type: (Union[None, str]) -> None
        if value is None:
            value = ''
        self.description_value.set_value(value)

    def _get_description(self):
        # type: () -> Union[None, str]
        value = self.description_value.get_value().strip()
        return None if value == '' else value

    def update_annotation(self):
        annotation = self._app_variables.get_current_annotation_object()
        self.set_annotation_feature(annotation)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        if annotation_feature is None or annotation_feature.properties is None:
            self._set_directory(None)
            self._set_description(None)
            self.directory_value.update_combobox_values([])
            return

        self._set_directory_values()
        self.directory_value.update_combobox_values(sorted(list(self.directory_values)))

        properties = annotation_feature.properties
        self._set_directory(properties.directory)
        self._set_description(properties.description)

    def update_annotation_collection(self):
        self.update_annotation()

    def cancel(self):
        self.set_annotation_feature(self.annotation_feature)

    def save(self):
        if self.annotation_feature is None or self.annotation_feature.properties is None:
            return
        self.annotation_feature.properties.directory = self._get_directory()
        self.annotation_feature.properties.description = self._get_description()


class GeometryButtons(Frame):
    _shapes = ('point', 'line', 'rectangle', 'ellipse', 'polygon')

    def __init__(self, master, active_shapes=None, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        active_shapes : None|Sequence[str]
            The active shapes.
        """

        self.active_shapes = None
        Frame.__init__(self, master, **kwargs)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.label = Label(self, text='Add Geometry:')  # type: Label
        self.label.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.point = Button(self, text='Point')  # type: Button
        self.point.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.line = Button(self, text='Line')  # type: Button
        self.line.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.rectangle = Button(self, text='Rectangle')  # type: Button
        self.rectangle.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.ellipse = Button(self, text='Ellipse')  # type: Button
        self.ellipse.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.polygon = Button(self, text='Polygon')  # type: Button
        self.polygon.pack(side=tkinter.LEFT, padx=5, pady=5)

        self.set_active_shapes(active_shapes)

    def _check_shapes_list(self, shape_list):
        """
        Check the entries versus proper shape names.

        Parameters
        ----------
        shape_list : None|Sequence[str]

        Returns
        -------
        Sequence[str]
        """

        if shape_list is None:
            return self._shapes

        if isinstance(shape_list, str):
            shape_list = [shape_list, ]

        out_list = []
        for entry in shape_list:
            val = entry.lower().strip()
            if val in self._shapes:
                out_list.append(val)
            else:
                logger.warning('Got an invalid shape name `{}`. Skipping.'.format(entry))
        return out_list

    def set_active_shapes(self, shape_list=None):
        """
        Sets the collection of shapes which should be active.

        Parameters
        ----------
        shape_list : None|Sequence[str]
        """

        self.active_shapes = self._check_shapes_list(shape_list)
        missing = [entry for entry in self._shapes if entry not in self.active_shapes]
        if len(missing) > 0:
            self.disable_shapes(missing)

    def disable_shapes(self, shape_list=None):
        """
        Disable the shapes buttons.

        Parameters
        ----------
        shape_list : None|Sequence[str]
            Defaults to disabling all shapes.
        """

        shapes = self._check_shapes_list(shape_list)
        for name in shapes:
            getattr(self, name).state(['disabled'])

    def enable_shapes(self, shape_list=None):
        """
        Enable the provided shapes.

        Parameters
        ----------
        shape_list : None|Sequence[str]
            Defaults to enabling the active shapes.
        """

        shapes = self.active_shapes if shape_list is None else self._check_shapes_list(shape_list)
        for name in shapes:
            getattr(self, name).state(['!disabled'])


class GeometryPropertiesPanel(Frame):
    """
    A panel for displaying the basic geometry properties
    """
    uid_label = LabelDescriptor(
        'uid_label', default_text='UID:')  # type: Label
    uid_value = LabelDescriptor(
        'uid_value', default_text='')  # type: Label

    geom_type_label = LabelDescriptor(
        'geom_type_label', default_text='Type:')  # type: Label
    geom_type_value = LabelDescriptor(
        'geom_type_value', default_text='')  # type: Label

    name_label = LabelDescriptor(
        'name_label', default_text='Name:')  # type: Label
    name_value = EntryDescriptor(
        'name_value', default_text='<no name>')  # type: Entry

    color_label = LabelDescriptor(
        'color_label', default_text='Color:')  # type: Label
    color_button = TypedDescriptor(
        'color_button', tkButton,
        docstring='button to display the color choice, hence plain tk button')  # type: tkButton

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        app_variables : AppVariables
        kwargs
        """

        self._app_variables = app_variables  # type: AppVariables
        self.default_color = '#ff0066'
        self.default_name = '<NONE>'
        self.geometry_properties = None  # type: Union[None, GeometryProperties]
        self.color = None  # type: Union[None, str]

        Frame.__init__(self, master, **kwargs)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.uid_label = Label(self, text='Geo UID:')
        self.uid_label.grid(row=0, column=0, padx=3, pady=3, sticky='NW')
        self.uid_value = Label(self, text='')
        self.uid_value.grid(row=0, column=1, padx=3, pady=3, sticky='NEW')

        self.geom_type_label = Label(self, text='Shape Type:')
        self.geom_type_label.grid(row=1, column=0, padx=3, pady=3, sticky='NW')
        self.geom_type_value = Label(self, text='')
        self.geom_type_value.grid(row=1, column=1, padx=3, pady=3, sticky='NEW')

        self.name_label = Label(self, text='Geo Name:')
        self.name_label.grid(row=2, column=0, padx=3, pady=3, sticky='NW')
        self.name_value = Entry(self, text=self.default_name)
        self.name_value.grid(row=2, column=1, padx=3, pady=3, sticky='NEW')

        self.color_label = Label(self, text='Color:')
        self.color_label.grid(row=3, column=0, padx=3, pady=3, sticky='NW')
        self.color_button = tkButton(self, bg=self.default_color, text='', width=10, command=self.change_color)
        self.color_button.grid(row=3, column=1, padx=3, pady=3, sticky='NW')

        # setup the appearance of labels
        self.uid_value.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=3)
        self.grid_columnconfigure(1, weight=1)
        self.update_geometry_properties()

    def _reference_annotation_panel(self):
        geom_details_panel = self.master
        anno_tab_control = geom_details_panel.master
        return anno_tab_control.master

    def change_color(self):
        result = askcolor(color=self.color, title='Choose Color')

        # NB: this screws the focus up, for some reason
        ann_panel = self._reference_annotation_panel()
        ann_panel.master.lift()
        ann_panel.master.focus_set()

        if result is None:
            return
        self._set_color(result[1])

    def _set_uid_value(self, value):
        if value is None:
            value = ''
        self.uid_value.set_text(value)

    def _set_geom_type_value(self, value):
        if value is None:
            value = ''
        self.geom_type_value.set_text(value)

    def _set_name_value(self, value):
        if value is None:
            value = self.default_name
        self.name_value.set_text(value)

    def _get_name_value(self):
        value = self.name_value.get().strip()
        return None if value in ['', self.default_name] else value

    def _set_color(self, value):
        self.color = self.default_color if value is None else value
        self.color_button.configure(bg=self.color)

    def _get_color(self):
        return self.color

    def update_geometry_properties(self):
        geometry_properties = self._app_variables.get_current_geometry_properties()
        self.set_geometry_properties(geometry_properties)

    def set_geometry_properties(self, geometry_properties):
        """

        Parameters
        ----------
        geometry_properties : None|GeometryProperties
        """

        self.geometry_properties = geometry_properties
        if geometry_properties is None:
            self._set_uid_value(None)
            self._set_geom_type_value(None)
            self.default_name = '<NONE>'
            self._set_name_value(None)
            self._set_color(None)
        else:
            self._set_uid_value(geometry_properties.uid)
            geom_type = self._app_variables.get_geometry_type(geometry_properties.uid)
            self._set_geom_type_value(geom_type)
            self.default_name = '<{}>'.format(geom_type)
            self._set_name_value(geometry_properties.name)
            self._set_color(geometry_properties.color)

    def cancel(self):
        self.set_geometry_properties(self.geometry_properties)

    def save(self):
        if self.geometry_properties is None:
            return
        self.geometry_properties.name = self._get_name_value()
        self.geometry_properties.color = self._get_color()


class GeometryDetailsPanel(Frame):
    """
    A panel for displaying the basic geometry details
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        app_variables : AppVariables
        """

        self._app_variables = app_variables  # type: AppVariables
        self.annotation_feature = None  # type: Union[None, AnnotationFeature]

        Frame.__init__(self, master, **kwargs)
        self.geometry_buttons = GeometryButtons(
            self, active_shapes=None)  # type: GeometryButtons
        self.geometry_buttons.grid(row=0, column=0, columnspan=2, sticky='NEW', padx=3, pady=3)

        self.geometry_view = TreeviewWithScrolling(
            self, selectmode=tkinter.BROWSE)  # type: TreeviewWithScrolling
        self.geometry_view.heading('#0', text='Name')
        self.geometry_view.frame.grid(row=1, column=0, sticky='NSEW', padx=3, pady=3)
        # NB: reference the frame for packing, since it's already packed into a frame

        self.geometry_properties_panel = GeometryPropertiesPanel(
            self, app_variables)  # type: GeometryPropertiesPanel
        self.geometry_properties_panel.grid(row=1, column=1, sticky='NSEW', padx=3, pady=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.update_annotation()

        # configure the callback for treeview element selection
        self.geometry_view.bind('<<TreeviewSelect>>', self.geometry_selected_on_viewer)

    def _set_focus(self, uid):
        self.geometry_view.set_selection_with_expansion(uid)

    def _set_geometry_uid(self, uid):
        if uid == '':
            return

        current_id = self._app_variables.current_geometry_id
        self.geometry_properties_panel.update_geometry_properties()
        if current_id != uid:
            self._app_variables._current_geometry_id = uid
            self.emit_geometry_changed()

    def _get_name_string(self, properties):
        # type: (GeometryProperties) -> str
        name = properties.name if properties.name is not None else \
            '<{}>'.format(self._app_variables.get_geometry_type(properties.uid))
        return name

    def _render_entry(self, uid):
        properties = self.annotation_feature.get_geometry_property(uid)
        self.geometry_view.item(uid, text=self._get_name_string(properties))

    # noinspection PyUnusedLocal
    def geometry_selected_on_viewer(self, event):
        geometry_uid = self.geometry_view.focus()
        if geometry_uid == '':
            return

        self._set_geometry_uid(geometry_uid)

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.
        """

        self.geometry_view.delete(*self.geometry_view.get_children())

    def _fill_treeview(self):
        if self.annotation_feature is None or self.annotation_feature.geometry_count == 0:
            self._empty_entries()
            self.geometry_properties_panel.set_geometry_properties(None)
            return

        if self.annotation_feature.properties.geometry_properties is None:
            self._empty_entries()
            self.geometry_properties_panel.set_geometry_properties(None)
            showinfo(
                'No geometry properties defined',
                message='Feature id `{}` has no geometry properties,\n\t'
                        'but some geometry. '
                        'You cannot edit any details here.'.format(self.annotation_feature.uid))
            return

        if self.annotation_feature.geometry_count != len(self.annotation_feature.properties.geometry_properties):
            self._empty_entries()
            self.geometry_properties_panel.set_geometry_properties(None)
            showinfo(
                'geometry properties does not match geometry elements',
                message='Feature id `{}` has a mismatch between the geometry elements\n\t'
                        'and the defined geometry properties. '
                        'You cannot edit any details here.'.format(self.annotation_feature.uid))
            return

        current_choice = self._app_variables.current_geometry_id
        # there will be at least one by this point
        self._empty_entries()
        default_choice = None
        for properties in self.annotation_feature.properties.geometry_properties:
            if default_choice is None:
                default_choice = properties.uid
            name = self._get_name_string(properties)
            self.geometry_view.insert('', 'end', iid=properties.uid, text=name)

        self._set_focus(default_choice if current_choice is None else current_choice)

    def update_annotation(self):
        annotation_feature = self._app_variables.get_current_annotation_object()
        self.set_annotation_feature(annotation_feature)

    def update_geometry_properties(self):
        self.geometry_properties_panel.update_geometry_properties()
        if self._app_variables.current_geometry_id is not None:
            self._render_entry(self._app_variables.current_geometry_id)
            self._set_focus(self._app_variables.current_geometry_id)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        self._fill_treeview()
        if self.annotation_feature is not None:
            if self.annotation_feature.geometry_count == 0 or self._app_variables.allow_multi_geometry:
                self.geometry_buttons.enable_shapes()
            else:
                self.geometry_buttons.disable_shapes()

    def cancel(self):
        self.geometry_properties_panel.cancel()
        self._fill_treeview()

    def save(self):
        self.geometry_properties_panel.save()
        self._fill_treeview()

    def emit_geometry_changed(self):
        """
        Emit the <<GeometryPropertyChanged>> event.
        """

        self.event_generate('<<GeometryPropertyChanged>>')


class AnnotateTabControl(Frame):
    """
    A tab control panel which holds the feature details panels
    """

    def __init__(self, master, app_variables, **kwargs):
        self.app_variables = app_variables
        Frame.__init__(self, master, **kwargs)
        self.tab_control = Notebook(self)  # type: Notebook
        self.details_tab = AnnotateDetailsPanel(self, app_variables)
        self.geometry_tab = GeometryDetailsPanel(self, app_variables)

        self.tab_control.add(self.details_tab, text='Overall')
        self.tab_control.add(self.geometry_tab, text='Geometry')
        self.tab_control.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

    def update_geometry_properties(self):
        self.geometry_tab.update_geometry_properties()

    def update_annotation(self):
        self.details_tab.update_annotation()
        self.geometry_tab.update_annotation()

    def update_annotation_collection(self):
        self.details_tab.update_annotation_collection()
        self.geometry_tab.update_annotation()

    def cancel(self):
        self.details_tab.cancel()
        self.geometry_tab.cancel()

    def save(self):
        self.details_tab.save()
        self.geometry_tab.save()


class AnnotationPanel(Frame):
    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            tkinter.Tk|tkinter.TopLevel
        app_variables : AppVariables
        kwargs
        """

        self._app_variables = app_variables  # type: AppVariables
        Frame.__init__(self, master, **kwargs)
        self.pack(expand=tkinter.TRUE, fill=tkinter.BOTH)

        self.name_panel = NamePanel(self, app_variables)  # type: NamePanel
        self.name_panel.grid(row=0, column=0, sticky='NSEW')

        self.tab_panel = AnnotateTabControl(self, app_variables)  # type: AnnotateTabControl
        self.tab_panel.grid(row=1, column=0, sticky='NSEW')

        self.button_panel = AnnotateButtons(self)  # type: AnnotateButtons
        self.button_panel.grid(row=2, column=0, sticky='NSEW')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_geometry_properties(self):
        self.tab_panel.update_geometry_properties()

    def update_annotation(self):
        self.name_panel.update_annotation()
        self.tab_panel.update_annotation()

    def update_annotation_collection(self):
        """
        To be called when the annotation collection has been changed.
        """

        self.name_panel.update_annotation()
        self.tab_panel.update_annotation_collection()

    def cancel(self):
        self.name_panel.cancel()
        self.tab_panel.cancel()

    def save(self):
        self.name_panel.save()
        self.tab_panel.save()

    def hide_on_close(self):
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.master.withdraw()


##################
# Annotation collection panel for display and interaction

class AnnotationCollectionViewer(TreeviewWithScrolling):
    """
    A treeview for viewing and selecting form the annotation list.

    This does not modify the annotation collection itself, and maintains
    it's own parallel internal state which should be synced on changes using
    the provided methods.
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The tkinter master element
        app_variables : AppVariables
        kwargs
            Optional keywords for the treeview initialization
        """

        self._app_variables = app_variables  # type: AppVariables
        self._directory_structure = None
        self._element_association = None

        if 'selectmode' not in kwargs:
            kwargs['selectmode'] = tkinter.BROWSE
        TreeviewWithScrolling.__init__(self, master, **kwargs)
        self.heading('#0', text='Name')

        self.update_annotation_collection()

    @property
    def annotation_collection(self):
        """
        None|FileAnnotationCollection : The file annotation collection
        """

        return self._app_variables.file_annotation_collection

    def update_annotation_collection(self):
        """
        Should be called on an update of the annotation collection.
        """

        self._directory_structure = None
        self._element_association = None
        self._build_directory_structure()
        self._populate_tree()

    @staticmethod
    def _get_parent_direct(directory):
        """
        Gets the parent directory of the given directory.

        Parameters
        ----------
        directory : str

        Returns
        -------
        str
        """

        if directory == '':
            return ''
        return os.path.split(directory)[0]

    @staticmethod
    def _get_directory_value(annotation):
        """
        Gets the usable directory value.

        Parameters
        ----------
        annotation : AnnotationFeature

        Returns
        -------
        str
        """

        if annotation.properties is None:
            return ''

        dval = annotation.properties.directory
        return '' if dval is None else dval

    def _set_focus(self, the_id):
        self.set_selection_with_expansion(the_id)

    def _directory_definition_check(self, directory):
        """
        Verifies/defines that all parts of the directory are previously defined, and
        return the first element NOT defined.

        Parameters
        ----------
        directory

        Returns
        -------
        None|str
        """

        if directory == '':
            return
        parts = directory.split('/')

        first_not_defined = None
        root = ''

        for part in parts:
            direct_list = self._directory_structure[root]['directories']
            element = part if root == '' else root + '/' + part
            if element not in direct_list:
                if first_not_defined is None:
                    first_not_defined = element
            direct_list.append(element)
            root = element
        return first_not_defined

    def _is_empty(self, directory):
        """
        Checks if the given directory has an children at all.

        Parameters
        ----------
        directory : str

        Returns
        -------
        bool
        """

        state = self._directory_structure[directory]
        return len(state['directories']) == 0 and len(state['elements']) == 0

    def _directory_empty_check(self, directory):
        """
        Walks up the tree starting at directory to find the first empty
        directory. This will remove any empty directories from the state.

        Parameters
        ----------
        directory : str

        Returns
        -------
        None|str
        """

        root = directory
        first_empty = None
        while True:
            if not self._is_empty(root):
                return first_empty

            first_empty = root
            # this directory is totally empty, so delete it from the state
            del self._directory_structure[root]
            new_root, _ = os.path.split(root)
            if root == '':
                break

            # remove the empty directory from the parent
            self._directory_structure[new_root]['directories'].remove(root)
            root = new_root

        return first_empty

    def _build_directory_structure(self):
        def _default_value():
            return {'directories': [], 'elements': []}

        self._element_association = {}
        self._directory_structure = defaultdict(_default_value)

        if self.annotation_collection is None or self.annotation_collection.annotations is None:
            return

        # construct all the elements entries
        direct_set = set()
        for entry in self.annotation_collection.annotations:
            dval = self._get_directory_value(entry)
            direct_set.add(dval)
            if entry.uid not in self._directory_structure[dval]['elements']:
                self._directory_structure[dval]['elements'].append(entry.uid)
            self._element_association[entry.uid] = dval
        # populate all the directory information
        for entry in list(direct_set):
            self._directory_definition_check(entry)
        # now, sort all the directories lists
        for key, value in self._directory_structure.items():
            value['directories'] = sorted(value['directories'])

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of (re)initializing.

        Returns
        -------
        None
        """

        self.delete(*self.get_children())

    def _render_directory(self, directory, at_index='end'):
        if directory != '' and not self.exists(directory):
            stem, leaf = os.path.split(directory)
            self.insert(stem, at_index, directory, text=leaf)
        direct_info = self._directory_structure[directory]
        # render all the child directories
        for child_dir in direct_info['directories']:
            self._render_directory(child_dir)
        # render all the annotations
        for annotation_id in direct_info['elements']:
            self._render_annotation(annotation_id)

    def _render_annotation(self, the_id, at_index='end'):
        annotation = self.annotation_collection.annotations[the_id]
        parent = self._element_association[the_id]
        name = annotation.get_name()
        self.insert(parent, at_index, the_id, text=name)

    def _populate_tree(self):
        self._empty_entries()
        self._render_directory('')

    def rerender_directory(self, directory, maintain_focus=True):
        """
        Rerender everything below the given directory.

        Parameters
        ----------
        directory : str
        maintain_focus : bool
            maintain the current selection, if any?
        """

        selection = self.selection_get()
        # delete any children
        item = self.item(directory)
        self.delete(*item.get_children())
        self._render_directory(directory)
        if maintain_focus:
            self.set_selection_with_expansion(selection)

    def rerender_annotation(self, the_id, set_focus=False):
        """
        Rerender the given annotation.

        Parameters
        ----------
        the_id : str
        set_focus : bool
        """

        def update_state():
            self._element_association[the_id] = current_directory
            if the_id not in new_state['elements']:
                new_state['elements'].append(the_id)

        previous_directory = self._element_association.get(the_id, None)

        annotation = self.annotation_collection.annotations[the_id]

        current_directory = self._get_directory_value(annotation)
        new_state = self._directory_structure[current_directory]
        # verify the directory definition, and get any missing value parts
        missing_dir = self._directory_definition_check(current_directory)
        missing_parent = None if missing_dir is None else self._get_parent_direct(missing_dir)

        if previous_directory is None:
            # we have not previously rendered this annotation
            update_state()
            if missing_parent is None:
                self._render_annotation(the_id)
            else:
                self.rerender_directory(self._get_parent_direct(missing_dir), maintain_focus=True)
            return

        # delete the old element
        self.delete(the_id)

        if previous_directory != current_directory:
            # we have previously rendered this element in a different directory

            # update our previous treeview state
            previous_state = self._directory_structure[previous_directory]
            try:
                previous_state['elements'].remove(the_id)
            except ValueError:
                logger.warning(
                    'The internal annotation treeview appears to have an inconsistent state definition?')
                pass  # it was somehow in an inconsistent state

            # check for and eliminate empty directories above previous from the state
            remove_directory = self._directory_empty_check(previous_directory)
            if remove_directory is not None:
                # there is an empty directory, delete the whole thing from the treeview
                self.delete(remove_directory)

        # we update the new internal state
        update_state()

        # any necessary items are deleted from the tree, and the internal state has been update
        # render the new items
        if missing_parent is not None:
            self._render_directory(missing_parent)
        else:
            at_index = new_state['elements'].index(the_id) + len(new_state['directories'])
            self._render_annotation(the_id, at_index=at_index)

        if set_focus:
            self.set_selection_with_expansion(the_id)

    def delete_entry(self, the_id):
        """
        Removes the entry from the treeview and treeview metadata. This does not
        modify the underlying annotation collection, which should be done elsewhere.

        Parameters
        ----------
        the_id : str
        """

        directory = self._element_association.get(the_id, None)
        if directory is None:
            if self.exists(the_id):
                self.delete(the_id)
            return

        state = self._directory_structure[directory]
        try:
            state['elements'].remove(the_id)
        except ValueError:
            pass  # it was somehow in an old or inconsistent state

        remove_directory = self._directory_empty_check(directory)
        if remove_directory is not None and remove_directory != '':
            # there is an empty directory, delete the whole thing from the treeview
            self.delete(remove_directory)
        else:
            # delete the old element
            self.delete(the_id)

    def update_annotation(self):
        annotation_id = self._app_variables.current_feature_id
        if annotation_id is not None:
            self.rerender_annotation(annotation_id, set_focus=True)
        else:
            self.update_annotation_collection()


class AnnotationCollectionPanel(Frame):
    """
    Buttons for the annotation panel.
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
            The master widget
        app_variables : AppVariables
        kwargs
            keyword arguments passed through to the Frame constructor
        """

        Frame.__init__(self, master, **kwargs)

        self.button_panel = Frame(self, relief=tkinter.RIDGE, borderwidth=2)  # type: Frame
        self.new_button = Button(self.button_panel, text='New Annotation', width=28)  # type: Button
        self.new_button.grid(row=0, column=0, sticky='NW')
        self.edit_button = Button(self.button_panel, text='Edit Selected Annotation', width=28)  # type: Button
        self.edit_button.grid(row=1, column=0, sticky='NW')
        self.zoom_button = Button(self.button_panel, text='Zoom to Selected Annotation', width=28)  # type: Button
        self.zoom_button.grid(row=2, column=0, sticky='NW')
        self.move_button = Button(self.button_panel, text='Move Selected Annotation', width=28)  # type: Button
        self.move_button.grid(row=3, column=0, sticky='NW')
        self.button_panel.grid(row=0, column=0, sticky='NSEW')

        self.viewer = AnnotationCollectionViewer(self, app_variables)
        self.viewer.frame.grid(row=1, column=0, sticky='NSEW')
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_annotation_collection(self):
        """
        Should be called on an update of the annotation collection
        """

        self.viewer.update_annotation_collection()

    def update_annotation(self):
        self.viewer.update_annotation()


###################
# the main tool

class AnnotationTool(PanedWindow, WidgetWithMetadata):
    """
    The main annotation tool
    """
    _NEW_ANNOTATION_TYPE = AnnotationFeature
    _NEW_FILE_ANNOTATION_TYPE = FileAnnotationCollection

    def __init__(self, master, reader=None, annotation_collection=None, **kwargs):
        """

        Parameters
        ----------
        master
            tkinter.Tk|tkinter.TopLevel
        reader : None|str|BaseReader|GeneralCanvasImageReader
        annotation_collection : None|str|FileAnnotationCollection
        kwargs
        """

        self.variables = AppVariables()  # type: AppVariables

        if 'sashrelief' not in kwargs:
            kwargs['sashrelief'] = tkinter.RIDGE
        if 'orient' not in kwargs:
            kwargs['orient'] = tkinter.HORIZONTAL
        PanedWindow.__init__(self, master, **kwargs)
        WidgetWithMetadata.__init__(self, master)
        self.pack(expand=tkinter.TRUE, fill=tkinter.BOTH)

        self.image_panel = ImagePanel(self)
        self.image_panel.canvas.set_canvas_size(400, 500)
        self.add(
            self.image_panel, width=400, height=700, padx=3, pady=3, sticky='NSEW', stretch=tkinter.FIRST)

        self.collection_panel = AnnotationCollectionPanel(self, self.variables)

        self.add(self.collection_panel, width=200, height=700, padx=3, pady=3, sticky='NSEW')

        # file menu
        self.menu_bar = tkinter.Menu()
        self.file_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open Image", command=self.select_image_file)
        self.file_menu.add_command(label="Open Directory", command=self.select_image_directory)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Open Existing Annotation File", command=self.select_annotation_file)
        self.file_menu.add_command(label="Create New Annotation File", command=self.create_new_annotation_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save Annotation File", command=self.save_annotation_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit)
        # edit popup menu
        self.edit_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label='Replicate Selected', command=self.callback_replicate_feature)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label='Delete Selected', command=self.callback_delete_feature)
        # metadata popup menu
        self.metadata_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.metadata_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        self.metadata_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        self._valid_data_shown = tkinter.IntVar(self, value=0)
        self.metadata_menu.add_checkbutton(
            label='ValidData', variable=self._valid_data_shown, command=self.show_valid_data)
        # configure menubar
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menu_bar.add_cascade(label="Metadata", menu=self.metadata_menu)
        self.master.config(menu=self.menu_bar)

        # hide unwanted elements on the panel toolbars
        self.image_panel.hide_tools(['new_shape', 'select'])
        self.image_panel.hide_shapes()
        # disable tools until an image is selected
        self.image_panel.disable_tools()

        self.collection_panel.new_button.config(command=self.callback_new_annotation)
        self.collection_panel.edit_button.config(command=self.callback_popup_annotation)
        self.collection_panel.zoom_button.config(command=self.callback_zoom_to_feature)
        self.collection_panel.move_button.config(command=self.callback_move_feature)

        # set up context panel canvas event listeners
        self.image_panel.canvas.bind('<<ImageIndexPreChange>>', self.handle_image_index_prechange)
        self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)
        self.image_panel.canvas.bind('<<ShapeCreate>>', self.shape_create_on_canvas)
        self.image_panel.canvas.bind('<<ShapeCoordsFinalized>>', self.shape_finalized_on_canvas)
        self.image_panel.canvas.bind('<<ShapeDelete>>', self.shape_delete_on_canvas)
        self.image_panel.canvas.bind('<<ShapeSelect>>', self.shape_selected_on_canvas)

        # set up the label_panel viewer event listeners
        self.collection_panel.viewer.bind('<<TreeviewSelect>>', self.feature_selected_on_viewer)

        self.annotate_popup = tkinter.Toplevel(master)
        self.annotate = AnnotationPanel(self.annotate_popup, self.variables)
        self.annotate.hide_on_close()
        self.annotate_popup.withdraw()

        # bind actions/listeners from annotate popup
        self.annotate.tab_panel.geometry_tab.bind('<<GeometryPropertyChanged>>', self.geometry_selected_on_viewer)
        self.annotate.button_panel.delete_button.config(command=self.callback_delete_geometry)
        self.annotate.button_panel.cancel_button.config(command=self.callback_popup_cancel)
        self.annotate.button_panel.apply_button.config(command=self.callback_popup_apply)

        # bind the new geometry buttons explicitly
        self.annotate.tab_panel.geometry_tab.geometry_buttons.point.config(command=self.callback_new_point)
        self.annotate.tab_panel.geometry_tab.geometry_buttons.line.config(command=self.callback_new_line)
        self.annotate.tab_panel.geometry_tab.geometry_buttons.rectangle.config(command=self.callback_new_rect)
        self.annotate.tab_panel.geometry_tab.geometry_buttons.ellipse.config(command=self.callback_new_ellipse)
        self.annotate.tab_panel.geometry_tab.geometry_buttons.polygon.config(command=self.callback_new_polygon)

        self.set_reader(reader)
        self.set_annotations(annotation_collection)
        self.annotate.update_annotation_collection()

    @property
    def image_file_name(self):
        """
        None|str: The image file name.
        """

        if self.variables.image_reader is None:
            return None
        return self.variables.image_reader.file_name

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Annotation Tool"
        else:
            the_title = "Annotation Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        """
        The tool exit function
        """

        response = self._prompt_unsaved()
        if response:
            self.master.destroy()

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

    def set_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|BaseReader|GeneralCanvasImageReader
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

        if not isinstance(the_reader, GeneralCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        data_sizes = the_reader.base_reader.get_data_size_as_tuple()

        if len(data_sizes) > 1:
            rep_size = data_sizes[0]
            for entry in data_sizes:
                if rep_size != entry:
                    showinfo(
                        'Differing image sizes',
                        message='Annotation requires that all images in the reader have the same size. Aborting.')
                    return

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_title()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()

        self.set_annotations(None)
        self.show_valid_data()

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

    def _verify_image_selected(self, popup=True):
        """
        Verify that an image is selected. Deploy helpful popup if not.

        Parameters
        ----------
        popup : bool
            Should we deploy the popup?

        Returns
        -------
        bool
        """

        if self.image_file_name is None:
            if popup:
                showinfo('No Image Selected', message='First select an image file for annotation, using the file menu.')
            return False
        return True

    def _get_default_collection(self):
        return self._NEW_FILE_ANNOTATION_TYPE(image_file_name=self.image_file_name)

    def set_annotations(self, annotation_collection):
        if self.variables.image_reader is None:
            return  # nothing to be done

        annotation_filename = None
        if isinstance(annotation_collection, str):
            if not os.path.isfile(annotation_collection):
                showinfo(
                    'File does not exist',
                    message='Annotation file {} does not exist'.format(annotation_collection))
                annotation_collection = None
            else:
                try:
                    annotation_filename = annotation_collection
                    annotation_collection = self._NEW_FILE_ANNOTATION_TYPE.from_file(annotation_filename)
                except Exception as e:
                    showinfo('File Annotation Error',
                             message='Opening annotation file {} failed with error {}.'.format(
                                 annotation_filename, e))
                    return

        if annotation_collection is None:
            annotation_collection = self._get_default_collection()

        if not isinstance(annotation_collection, self._NEW_FILE_ANNOTATION_TYPE):
            raise TypeError(
                'annotation collection must be of type {}, got type {}'.format(
                    self._NEW_FILE_ANNOTATION_TYPE, type(annotation_collection)))

        # validate the the image selected matches the annotation image name
        _, image_fname = os.path.split(self.image_file_name)
        if annotation_collection.image_file_name != image_fname:
            showinfo('Image File Mismatch',
                     message='Warning! The annotation selected is indicated as applying\n'
                             'to image file {},\n'
                             'while the selected image file is\n'
                             '{}.'.format(annotation_collection.image_file_name, image_fname))

        # finish initialization
        self._initialize_annotation_file(annotation_filename, annotation_collection)

    def select_image_file(self):
        """
        Select the image callback.

        Returns
        -------
        None
        """

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        fname = askopenfilename(
            title='Select image file',
            initialdir=self.variables.browse_directory,
            filetypes=common_use_collection)

        if fname in ['', ()]:
            return

        self.set_reader(fname, update_browse=os.path.split(fname)[0])

    def select_image_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        # NB: handle non-complex data possibilities here?
        the_reader = SICDTypeCanvasImageReader(dirname)
        self.set_reader(the_reader, update_browse=os.path.split(dirname)[0])

    def select_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        browse_dir, image_fname = os.path.split(self.image_file_name)
        # guess at a sensible initial file name
        init_file = '{}.annotations.json'.format(image_fname)
        if not os.path.exists(os.path.join(browse_dir, init_file)):
            init_file = ''

        annotation_fname = askopenfilename(
            title='Select annotation file for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile=init_file,
            filetypes=[json_files, all_files])
        if annotation_fname in ['', ()]:
            return

        self.set_annotations(annotation_fname)

    def create_new_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        self.set_annotations(None)

    def set_current_geometry_id(self, geometry_id, check_popup=True):
        """
        Sets the current geometry id.

        Parameters
        ----------
        geometry_id : None|str
        check_popup : bool
            Should we update things in the associated annotation popup too?
            To avoid recursive loops.
        """

        if geometry_id is None:
            self.variables._current_geometry_id = None
            self.image_panel.canvas.current_shape_id = None
            return

        associated_canvas_id = self.variables.get_canvas_for_geometry(geometry_id)
        associated_feature_id = self.variables.get_feature_for_canvas(associated_canvas_id)
        current_feat_id = self.variables.current_feature_id
        if associated_feature_id != current_feat_id:
            self.set_current_feature_id(associated_feature_id, geometry_id=geometry_id)
            return

        self.variables._current_geometry_id = geometry_id
        self.image_panel.canvas.current_shape_id = associated_canvas_id
        if check_popup:
            self.annotate.update_geometry_properties()

    def set_current_feature_id(self, feature_id, geometry_id=None):
        """
        Sets the current feature id.

        Parameters
        ----------
        feature_id : None|str
        geometry_id : None|str
        """

        if (feature_id is None) or (feature_id not in self.variables.feature_to_canvas):
            self.variables._current_feature_id = None
            self.set_current_geometry_id(None)
            return

        self.variables._current_feature_id = feature_id
        self.variables._current_geometry_id = geometry_id
        self.collection_panel.update_annotation()
        self.annotate.update_annotation()

    def zoom_to_feature(self, feature_id):
        """
        Zoom the image viewer to encompass the selected feature.

        Parameters
        ----------
        feature_id : str
        """

        if feature_id is None:
            return

        feature = self.variables.file_annotation_collection.annotations[feature_id]
        bounding_box = feature.geometry.get_bbox()
        y_diff = max(bounding_box[2] - bounding_box[0], 100)
        x_diff = max(bounding_box[3] - bounding_box[1], 100)
        zoom_box = [
            bounding_box[0] - 0.5*y_diff,
            bounding_box[1] - 0.5*x_diff,
            bounding_box[2] + 0.5*y_diff,
            bounding_box[3] + 0.5*x_diff]
        self.image_panel.canvas.zoom_to_full_image_selection(zoom_box)

    def _check_current_shape_color(self):
        geometry_property = self.variables.get_current_geometry_properties()
        if geometry_property is None:
            return
        canvas_id = self.variables.get_canvas_for_geometry(geometry_property.uid)
        if canvas_id is None:
            return
        self.image_panel.canvas.change_shape_color(canvas_id, geometry_property.color)

    def _get_geometry_from_shape(self, shape_id):
        """
        Gets the geometry object for the given shape.

        Parameters
        ----------
        shape_id : int
            The annotation shape id.

        Returns
        -------
        Point|Line|Polygon
        """

        geometry_object = self.image_panel.canvas.get_geometry_for_shape(shape_id, coordinate_type='image')
        if isinstance(geometry_object, LinearRing):
            geometry_object = Polygon(coordinates=[geometry_object, ])  # use polygon for feature versus linear ring
        return geometry_object

    def _get_geometry_for_feature(self, feature_id):
        """
        Gets the geometry (possibly collection) for the feature.

        Parameters
        ----------
        feature_id : str

        Returns
        -------
        None|Geometry
        """

        canvas_ids = self.variables.get_canvas_shapes_for_feature(feature_id)
        if canvas_ids is None:
            return None
        elif len(canvas_ids) == 1:
            return self._get_geometry_from_shape(canvas_ids[0])
        else:
            return basic_assemble_from_collection(
                *[self._get_geometry_from_shape(entry) for entry in canvas_ids])

    def _create_shape_from_geometry(self, feature, the_geometry, geometry_properties):
        """
        Helper function for creating shapes on the annotation and context canvases
        from the given feature element.

        Parameters
        ----------
        feature : AnnotationFeature
            The feature, only used here for logging a failure.
        the_geometry : Point|LineString|Polygon
        geometry_properties : GeometryProperties

        Returns
        -------
        canvas_id : int
            The id of the element on the annotation canvas
        """

        def insert_point():
            # type: () -> (int, str)
            image_coords = the_geometry.coordinates[:2].tolist()
            # create the shape on the annotate panel
            canvas_id = self.image_panel.canvas.create_new_point(
                (0, 0), make_current=False, color=geometry_properties.color)
            self.image_panel.canvas.modify_existing_shape_using_image_coords(
                canvas_id, image_coords)
            return canvas_id, 'POINT'

        def insert_line():
            # type: () -> (int, str)
            image_coords = the_geometry.coordinates[:, :2].flatten().tolist()
            # create the shape on the annotate panel
            self.line = self.image_panel.canvas.create_new_line((0, 0, 0, 0), make_current=False,
                                                                color=geometry_properties.color)
            canvas_id = self.line
            self.image_panel.canvas.modify_existing_shape_using_image_coords(
                canvas_id, image_coords)
            return canvas_id, 'LINE'

        def insert_polygon():
            # type: () -> (int, str)

            # this will only render an outer ring
            image_coords = the_geometry.outer_ring.coordinates[:, :2].flatten().tolist()
            # create the shape on the annotate panel
            canvas_id = self.image_panel.canvas.create_new_polygon(
                (0, 0, 0, 0), make_current=False, color=geometry_properties.color)
            self.image_panel.canvas.modify_existing_shape_using_image_coords(canvas_id, image_coords)
            return canvas_id, 'POLYGON'

        self._modifying_shapes_on_canvas = True
        if isinstance(the_geometry, Point):
            annotate_shape_id, geom_type = insert_point()
        elif isinstance(the_geometry, LineString):
            annotate_shape_id, geom_type = insert_line()
        elif isinstance(the_geometry, Polygon):
            annotate_shape_id, geom_type = insert_polygon()
        else:
            showinfo(
                'Unhandled Geometry',
                message='Feature id {} has unsupported feature component of type {}\n'
                        'which will be omitted from display.\n'
                        'Any save of the annotation will not contain this feature.'.format(
                            feature.uid, type(the_geometry)))
            self._modifying_shapes_on_canvas = False
            return None

        self._modifying_shapes_on_canvas = False
        # set up the tracking for the new shapes
        self.variables.set_canvas_tracking(annotate_shape_id, feature.uid, geometry_properties.uid, geom_type)
        return annotate_shape_id

    def _insert_feature_from_file(self, feature):
        """
        This is creating all shapes from the given geometry. This short-circuits
        the event listeners, so must handle all tracking updates itself.

        Parameters
        ----------
        feature : AnnotationFeature
        """

        # initialize tracking
        self.variables.initialize_feature_tracking(feature.uid)

        if feature.geometry_count == 0:
            return  # nothing else to be done
        elif not feature.geometry.is_collection:
            # noinspection PyTypeChecker
            self._create_shape_from_geometry(
                feature, feature.geometry, feature.properties.geometry_properties[0])
        else:
            for geometry, geometry_property in zip(
                    feature.geometry.collection, feature.properties.geometry_properties):
                # noinspection PyTypeChecker
                self._create_shape_from_geometry(feature, geometry, geometry_property)

    def _update_feature_geometry(self, feature_id, set_focus=False):
        """
        Updates the entry in the file annotation list, because the geometry has
        somehow changed.

        Parameters
        ----------
        feature_id : str
        """

        geometry = self._get_geometry_for_feature(feature_id)

        annotation = self.variables.file_annotation_collection.annotations[feature_id]
        self.variables.file_annotation_collection.annotations[feature_id].geometry = geometry
        self.collection_panel.viewer.rerender_annotation(annotation.uid, set_focus=set_focus)
        self.annotate.update_annotation()
        self.variables.unsaved_changes = True

    def _add_shape_to_feature(self, feature_id, canvas_id, set_focus=False, set_current=False):
        """
        Add the newly created canvas shape to the given feature. This assumes
        it's not otherwise being tracked as part of another feature.

        Parameters
        ----------
        feature_id : str
        canvas_id : int
        set_focus : bool
            Set the focus on the given feature?
        set_current : bool
            Set this shape to be the current shape?
        """

        # NB: this assumes that the context shape has already been synced from
        # the event listener method
        # create a new geometry property with the given color
        vector_object = self.image_panel.canvas.get_vector_object(canvas_id)
        the_color = vector_object.color
        geometry_property = GeometryProperties(color=the_color)

        # append the newly created geometry property to the feature
        annotation = self.variables.file_annotation_collection.annotations[feature_id]
        annotation.properties.add_geometry_property(geometry_property)

        # update feature tracking
        self.variables.set_canvas_tracking(
            canvas_id, feature_id, geometry_property.uid, ShapeTypeConstants.get_name(vector_object.type))

        # update the entry of our annotation object
        self._update_feature_geometry(feature_id, set_focus=set_focus)
        if set_current:
            self.set_current_geometry_id(geometry_property.uid)
            self.collection_panel.update_annotation()
            self.annotate.update_annotation()

    def _empty_all_shapes(self):
        self._modifying_shapes_on_canvas = True
        self.image_panel.canvas.reinitialize_shapes()

        # reinitialize dictionary relating canvas shapes and annotation shapes
        self.variables.reinitialize_features()
        self._modifying_shapes_on_canvas = False

    def _initialize_geometry(self, annotation_file_name, annotation_collection):
        """
        Initialize the geometry elements from the annotation.

        Parameters
        ----------
        annotation_file_name : None|str
        annotation_collection : FileAnnotationCollection

        Returns
        -------
        None
        """

        # set our appropriate variables
        self.variables.annotation_file_name = annotation_file_name
        self.variables.file_annotation_collection = annotation_collection
        self.set_current_feature_id(None)

        self._modifying_shapes_on_canvas = True
        # dump all the old shapes
        self._empty_all_shapes()

        # populate all the shapes
        if annotation_collection.annotations is not None:
            for feature in annotation_collection.annotations.features:
                self._insert_feature_from_file(feature)
        self._modifying_shapes_on_canvas = False

    def _initialize_annotation_file(self, annotation_fname, annotation_collection):
        """
        The final initialization steps for the annotation file.

        Parameters
        ----------
        annotation_fname : None|str
        annotation_collection : FileLabelCollection
        """

        self._initialize_geometry(annotation_fname, annotation_collection)
        self.collection_panel.update_annotation_collection()
        self.annotate.update_annotation_collection()
        self.image_panel.enable_tools()
        self.variables.unsaved_changes = False

    def _delete_geometry(self, geometry_id):
        """
        Removes the given geometry.

        Parameters
        ----------
        geometry_id : str
        """

        if self.variables.current_geometry_id == geometry_id:
            self.set_current_geometry_id(None)

        canvas_id = self.variables.get_canvas_for_geometry(geometry_id)
        if canvas_id is not None:
            # get the feature and get rid of the geometry
            feature_id = self.variables.get_feature_for_canvas(canvas_id)
            feature = self.variables.file_annotation_collection.annotations[feature_id]
            feature.remove_geometry_element(geometry_id)
        # remove geometry from tracking
        canvas_id = self.variables.delete_geometry_from_tracking(geometry_id)
        # remove canvas id from tracking, and delete the shape
        if canvas_id is not None:
            self.variables.delete_shape_from_tracking(canvas_id)
            self.image_panel.canvas.delete_shape(canvas_id)

        self.collection_panel.update_annotation()
        self.annotate.update_annotation()

    def _delete_feature(self, feature_id):
        """
        Removes the given feature.

        Parameters
        ----------
        feature_id : str
        """

        if self.variables.current_feature_id == feature_id:
            self.set_current_feature_id(None)

        # remove feature from tracking, and get list of shapes to delete
        feature = self.variables.file_annotation_collection.annotations[feature_id]
        geometry_ids = [entry.uid for entry in feature.properties.geometry_properties]
        canvas_ids = self.variables.delete_feature_from_tracking(feature_id, geometry_ids)
        # delete the shapes - this will also remove from tracking
        for entry in canvas_ids:
            self.image_panel.canvas.delete_shape(entry)
        # delete from the treeview
        self.collection_panel.viewer.delete_entry(feature_id)
        self.variables.unsaved_changes = True
        # drop for the file annotation collection
        self.variables.file_annotation_collection.delete_annotation(feature_id)

        self.collection_panel.update_annotation_collection()
        self.annotate.update_annotation_collection()

    def _prompt_annotation_file_name(self):
        if self.image_file_name is not None:
            browse_dir, image_fname = os.path.split(self.image_file_name)
        else:
            browse_dir = self.variables.browse_directory
            image_fname = 'Unknown_Image'

        annotation_fname = asksaveasfilename(
            title='Select output annotation file name for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile='{}.annotation.json'.format(image_fname),
            filetypes=[json_files, all_files])

        if annotation_fname in ['', ()]:
            annotation_fname = None
        return annotation_fname

    def save_annotation_file(self):
        """
        Save the annotation file.
        """

        if self.variables.file_annotation_collection is None:
            self.variables.unsaved_changes = False
            return  # nothing to be done

        if self.variables.annotation_file_name is None:
            self.variables.annotation_file_name = self._prompt_annotation_file_name()
            if self.variables.annotation_file_name is None:
                return  # they didn't provide anything

        self.variables.file_annotation_collection.to_file(self.variables.annotation_file_name)
        self.variables.unsaved_changes = False

    def _prompt_unsaved(self):
        """
        Check for any unsaved changes, and prompt for action.

        Returns
        -------
        bool
            True if underlying action to continue, False if it should not.
        """

        if not self.variables.unsaved_changes:
            return True

        response = askyesnocancel(
            'Save Changes?',
            message='There are unsaved changes for your annotations. Do you want to save them?')
        if response is True:
            self.save_annotation_file()
        elif response is None:
            return False  # cancel
        return True

    def _set_focus_on_annotation_popup(self):
        self.annotate_popup.focus_set()
        self.annotate_popup.lift()

    def _set_focus_on_main(self):
        self.master.focus_set()
        self.master.lift()

    def callback_zoom_to_feature(self):
        """
        Handles pressing the zoom to feature button.
        """

        if self.variables.current_feature_id is None:
            return

        self.zoom_to_feature(self.variables.current_feature_id)

    def callback_move_feature(self):
        feature_id = self.variables.current_feature_id
        if feature_id is None:
            showinfo('No feature is selected', message="No feature is selected to delete.")
            return
        canvas_ids = self.variables.get_canvas_shapes_for_feature(feature_id)
        if canvas_ids is None or len(canvas_ids) == 0:
            return
        self.image_panel.canvas.set_current_tool('SHIFT_SHAPE', shape_ids=canvas_ids)

    def callback_replicate_feature(self):
        """
        Deletes the currently selected feature.
        """
        feature_id = self.variables.current_feature_id
        if feature_id is None:
            showinfo('No feature is selected', message="No feature is selected to replicate.")
            return

        feature = self.variables.get_current_annotation_object().replicate()
        # add the new feature to the file_annotation
        self.variables.file_annotation_collection.add_annotation(feature)
        # add the annotation to the canvas
        self._insert_feature_from_file(feature)
        # make this the current feature
        self.set_current_feature_id(feature.uid)

    def callback_delete_feature(self):
        """
        Deletes the currently selected feature.
        """

        feature_id = self.variables.current_feature_id
        if feature_id is None:
            showinfo('No feature is selected', message="No feature is selected to delete.")
            return

        response = askyesnocancel('Confirm deletion?', message='Confirm feature deletion.')
        if response is None or response is False:
            return

        self._delete_feature(feature_id)

    def callback_delete_geometry(self):
        """
        Deletes the currently selected geometry.
        """

        geometry_id = self.variables.current_geometry_id
        if geometry_id is None:
            showinfo('No geometry is selected', message="No geometry is selected to delete.")
            return

        response = askyesnocancel('Confirm deletion?', message='Confirm geometry deletion.')
        if response is None or response is False:
            return

        self._delete_geometry(geometry_id)

    def callback_new_annotation(self):
        if self.variables.file_annotation_collection is not None:
            # create a new feature and add it to tracking
            annotation = self._NEW_ANNOTATION_TYPE()
            self.variables.file_annotation_collection.add_annotation(annotation)
            self.variables.initialize_feature_tracking(annotation.uid)

            # render it in the collection panel
            self.collection_panel.viewer.rerender_annotation(annotation.uid, set_focus=False)
            # make it current
            self.set_current_feature_id(annotation.uid)
            self.set_current_geometry_id(None, check_popup=False)
            self.image_panel.current_tool = 'VIEW'
        self.callback_popup_annotation()

    def callback_new_point(self):
        self.image_panel.canvas.set_current_tool_to_draw_point()
        self._set_focus_on_main()

    def callback_new_line(self):
        self.image_panel.canvas.set_current_tool_to_draw_line()
        self._set_focus_on_main()

    def callback_new_rect(self):
        self.image_panel.canvas.set_current_tool_to_draw_rect()
        self._set_focus_on_main()

    def callback_new_ellipse(self):
        self.image_panel.canvas.set_current_tool_to_draw_ellipse()
        self._set_focus_on_main()

    def callback_new_polygon(self):
        self.image_panel.canvas.set_current_tool_to_draw_polygon()
        self._set_focus_on_main()

    def callback_popup_annotation(self):
        self.annotate_popup.deiconify()
        self._set_focus_on_annotation_popup()

    def callback_popup_apply(self):
        self.annotate.save()
        self._check_current_shape_color()
        self.collection_panel.update_annotation()

    def callback_popup_cancel(self):
        self.annotate.cancel()

    # event listeners
    # noinspection PyUnusedLocal
    def handle_image_index_prechange(self, event):
        """
        Handle that the image index is about to change.

        Parameters
        ----------
        event
        """

        # dump all the shapes prior to index change
        self._empty_all_shapes()

    # noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self._initialize_annotation_file(
            self.variables.annotation_file_name, self.variables.file_annotation_collection)
        self.my_populate_metaicon()
        self.show_valid_data()

    def shape_create_on_canvas(self, event):
        """
        Handles the event that a shape has been created on the canvas.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        if self._modifying_shapes_on_canvas:
            return  # nothing required, and avoid recursive loop

        if self.variables.current_feature_id is None:
            raise ValueError('No current feature')

        self.image_panel.canvas.current_shape_id = event.x
        self._add_shape_to_feature(
            self.variables.current_feature_id, event.x, set_focus=True, set_current=True)

    def shape_finalized_on_canvas(self, event):
        """
        Handles the event that a shapes coordinates have been (possibly temporarily)
        finalized (i.e. certainly not dragged).

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # extract the appropriate feature, and sync changes to the list
        feature_id = self.variables.get_feature_for_canvas(event.x)
        self._update_feature_geometry(feature_id)
        geometry_id = self.variables.get_geometry_for_canvas(event.x)
        self.set_current_geometry_id(geometry_id)

    def shape_delete_on_canvas(self, event):
        """
        Handles the event that a shape has been deleted from the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        if self.variables.current_canvas_id == event.x:
            self.set_current_geometry_id(None)

        if self._modifying_shapes_on_canvas:
            return

        # NB: any feature association must have already been handled, or we will
        # get a fatal error here

        # remove this shape from tracking completely
        self.variables.delete_shape_from_tracking(event.x)

    def shape_selected_on_canvas(self, event):
        """
        Handles the event that a shape has been selected on the panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        if self.variables.current_canvas_id == event.x:
            return  # nothing needs to be done
        geometry_id = self.variables.get_geometry_for_canvas(event.x)
        self.set_current_geometry_id(geometry_id, check_popup=True)

    # noinspection PyUnusedLocal
    def feature_selected_on_viewer(self, event):
        """
        Triggered by a selection or selection change on the collection panel viewer

        Parameters
        ----------
        event
            The event.
        """

        feature_id = self.collection_panel.viewer.focus()
        if feature_id == '':
            return

        old_feature_id = self.variables.current_feature_id
        if feature_id == old_feature_id:
            return  # nothing needs to be done

        self.set_current_feature_id(feature_id)

    # noinspection PyUnusedLocal
    def geometry_selected_on_viewer(self, event):
        """
        Triggered by a selection or selection change of the annotation popup geometry viewer

        Parameters
        ----------
        event
        """

        current_geometry_id = self.variables.current_geometry_id
        self.set_current_geometry_id(current_geometry_id, check_popup=False)


def main(reader=None, annotation=None):
    """
    Main method for initializing the annotation_tool

    Parameters
    ----------
    reader : None|str|BaseReader|GeneralCanvasImageReader
    annotation : None|str|FileAnnotationCollection
    """

    root = tkinter.Tk()
    root.geometry("1000x800")

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = AnnotationTool(root, reader=reader, annotation_collection=annotation)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the annotation tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None, nargs='?',
        help='The path to the optional image file for opening.')
    parser.add_argument(
        '-a', '--annotation', metavar='annotation', default=None,
        help='The path to the optional annotation file. '
             'If the image input is not specified, then this has no effect. '
             'If both are specified, then a check will be performed that the '
             'annotation actually applies to the provided image.')
    this_args = parser.parse_args()

    main(reader=this_args.input, annotation=this_args.annotation)
