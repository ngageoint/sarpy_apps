# -*- coding: utf-8 -*-
"""
This module provides a tool for creating a general annotation for a SAR image.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import os
from shutil import copyfile
import time
from collections import OrderedDict
from typing import Dict, List, Tuple, Any

import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesnocancel, askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename

from sarpy_apps.apps.annotation_tool.schema_editor import select_schema_entry

from sarpy_apps.supporting_classes.file_filters import all_files, json_files, \
    nitf_preferred_collection
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.wiget_with_metadata import WidgetWithMetadata
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon

from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.image_canvas import ToolConstants, ShapeTypeConstants
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor
from tk_builder.panels.image_panel import ImagePanel

from sarpy.compliance import string_types, integer_types
from sarpy.annotation.schema_processing import LabelSchema
from sarpy.annotation.annotate import FileAnnotationCollection, Annotation, \
    AnnotationMetadata, AnnotationMetadataList
from sarpy.geometry.geometry_elements import Geometry, GeometryCollection, \
    Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, LinearRing


##############
# Labeling Panel and Popup Widget

class LabelingPanel(WidgetPanel):
    _widget_list = (
        ("object_type_label", "choose_type"),
        ("comment_label", "comment"),
        ("confidence_label", "confidence"),
        ("cancel", "submit"))
    object_type_label = widget_descriptors.LabelDescriptor(
        "object_type_label", default_text='Type:')  # type: basic_widgets.Label
    choose_type = widget_descriptors.ButtonDescriptor(
        "choose_type", default_text='Choose')  # type: basic_widgets.Button

    comment_label = widget_descriptors.LabelDescriptor(
        "comment_label", default_text='Comment:')  # type: basic_widgets.Label
    comment = widget_descriptors.TypedDescriptor(
        "comment", tkinter.Text)  # type: tkinter.Text

    confidence_label = widget_descriptors.LabelDescriptor(
        "confidence_label", default_text='Confidence:')  # type: basic_widgets.Label
    confidence = widget_descriptors.ComboboxDescriptor(
        "confidence", default_text='')  # type: basic_widgets.Combobox

    cancel = widget_descriptors.ButtonDescriptor(
        "cancel", default_text='Cancel')  # type: basic_widgets.Button
    submit = widget_descriptors.ButtonDescriptor(
        "submit", default_text='Submit')  # type: basic_widgets.Button

    def __init__(self, master):
        """

        Parameters
        ----------
        master : tkinter.Toplevel
            The app master.
        """

        WidgetPanel.__init__(self, master)
        # manually instantiate the elements
        self.object_type_label = basic_widgets.Label(master, text='Type:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.choose_type = basic_widgets.Button(master, text='Choose')
        self.comment_label = basic_widgets.Label(master, text='Comment:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.comment = tkinter.Text(master)
        self.confidence_label = basic_widgets.Label(master, text='Confidence:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.confidence = basic_widgets.Combobox(master, text='')
        self.cancel = basic_widgets.Button(master, text='Cancel')
        self.submit = basic_widgets.Button(master, text='Submit')
        # manually set the positioning
        self.object_type_label.grid(row=0, column=0, sticky='NESW')
        self.choose_type.grid(row=0, column=1, sticky='NESW')
        self.comment_label.grid(row=1, column=0, sticky='NESW')
        self.comment.grid(row=1, column=1, rowspan=3, sticky='NESW')
        self.confidence_label.grid(row=4, column=0, sticky='NESW')
        self.confidence.grid(row=4, column=1, sticky='NESW')
        self.cancel.grid(row=5, column=0, sticky='NESW')
        self.submit.grid(row=5, column=1, sticky='NESW')


class LabelingPopup(object):
    """
    This is a widget for performing the labeling portion of the annotation.

    This starts it's own tkinter.Toplevel, which maintains it's own mainloop.
    This allows it to freeze execution of the calling application.
    """

    def __init__(self, main_app_variables):
        """

        Parameters
        ----------
        main_app_variables : AppVariables
        """

        self._object_type_id = None
        self.main_app_variables = main_app_variables
        self.label_schema = main_app_variables.label_schema

        self.root = tkinter.Toplevel()
        self.widget = LabelingPanel(self.root)

        self.widget.set_text("Annotate")

        # set up base types for initial dropdown menu
        self.setup_confidence_selections()

        # get the current annotation
        current_id = self.main_app_variables.current_feature_id
        self.annotation = self.main_app_variables.file_annotation_collection.annotations[current_id]

        # populate existing fields if editing an existing geometry
        annotation_metadata_list = self.annotation.properties
        # verify that we can operate on this thing
        assert (annotation_metadata_list is None or
                isinstance(annotation_metadata_list, AnnotationMetadataList))
        if annotation_metadata_list is not None and len(annotation_metadata_list) > 0:
            annotate_metadata = annotation_metadata_list[0]
            self._object_type_id = annotate_metadata.label_id
            self.widget.choose_type.set_text(self.label_schema.labels[self._object_type_id])
            self.widget.comment.insert(tkinter.INSERT, annotate_metadata.comment)
            self.widget.confidence.set(annotate_metadata.confidence)
        else:
            self._object_type_id = None
            self.widget.choose_type.set_text("****")
            self.widget.comment.insert(tkinter.INSERT, "")
            self.widget.confidence.set("")

        # label appearance
        self.widget.object_type_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.widget.comment_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.widget.confidence_label.config(anchor=tkinter.CENTER, relief=tkinter.RIDGE)

        # set up callbacks
        self.widget.choose_type.config(command=self.select_object_type)
        self.widget.cancel.config(command=self.callback_cancel)
        self.widget.submit.config(command=self.callback_submit)
        self.root.mainloop()

    def select_object_type(self):
        current_value = self._object_type_id
        value = select_schema_entry(self.label_schema, start_id=current_value)
        self._object_type_id = value
        self.widget.choose_type.set_text(self.label_schema.labels[value])

    def callback_cancel(self):
        self.root.quit()

    def callback_submit(self):
        if self._object_type_id is None:
            showinfo("Select Object Type", message="Select the object type")
            return

        the_comment = self.widget.comment.get('1.0', 'end-1c')
        annotation_metadata = AnnotationMetadata(
            comment=the_comment,
            label_id=self._object_type_id,
            confidence=self.widget.confidence.get())
        self.annotation.add_annotation_metadata(annotation_metadata)
        self.main_app_variables.unsaved_changed = True
        self.root.quit()

    def setup_confidence_selections(self):
        confidence_values = self.label_schema.confidence_values
        if confidence_values is None or len(confidence_values) < 1:
            self.widget.confidence.set('')
            self.widget.confidence.config(state='disabled')
        else:
            self.widget.confidence.update_combobox_values(confidence_values)
            self.widget.confidence.config(state='readonly')

    def destroy(self):
        try:
            self.root.destroy()
        except:
            pass

    def __del__(self):
        self.destroy()


#########
# Main Annotation Window elements

class ContextImagePanel(WidgetPanel):
    """
    Context panel.
    """
    _widget_list = ("context_label", "image_panel")
    context_label = widget_descriptors.LabelDescriptor(
        "context_label",
        default_text='Some useful text describing things...',
        docstring='Useful instruction area for context panel.')  # type: basic_widgets.Label
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_vertical_layout()


class AnnotationButtons(WidgetPanel):
    _widget_list = ("delete_shape", "delete_annotation", "annotate")
    delete_shape = widget_descriptors.ButtonDescriptor(
        "delete_shape", default_text='delete shape')  # type: basic_widgets.Button
    delete_annotation = widget_descriptors.ButtonDescriptor(
        "delete_annotation", default_text='delete annotation')  # type: basic_widgets.Button
    annotate = widget_descriptors.ButtonDescriptor(
        "annotate", default_text="annotation")  # type: basic_widgets.Button

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_horizontal_layout()


class AnnotateImagePanel(WidgetPanel):
    _widget_list = ("buttons", "image_panel")
    buttons = widget_descriptors.PanelDescriptor("buttons", AnnotationButtons)   # type: AnnotationButtons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, master):
        # set the master frame
        WidgetPanel.__init__(self, master)
        self.init_w_vertical_layout()


class AppVariables(object):
    """
    The main application variables for the annotation panel.
    """
    unsaved_changed = BooleanDescriptor(
        'unsaved_changes', default_value=False,
        docstring='Are there unsaved annotation changes to be saved?')  # type: bool
    label_schema = TypedDescriptor(
        'label_schema', LabelSchema,
        docstring='The label schema object.')  # type: LabelSchema
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileAnnotationCollection,
        docstring='The file annotation collection.')  # type: FileAnnotationCollection
    annotation_file_name = StringDescriptor(
        'annotation_file_name',
        docstring='The path for the annotation results file.')  # type: str
    add_shape_to_current_annotation = BooleanDescriptor(
        'add_shape_to_current_annotation', default_value=False,
        docstring='We a new shape is created, do we add it to the current annotation, '
                  'or create a new annotation?')  # type: bool

    def __init__(self):
        self._feature_dict = OrderedDict()
        self._annotate_to_feature = OrderedDict()
        self._annotate_to_context = OrderedDict()
        self._context_to_annotate = OrderedDict()
        self._current_annotate_canvas_id = None
        self._current_feature_id = ''

    # do these variables need to be unveiled?
    @property
    def feature_dict(self):
        # type: () -> Dict[str, Dict]
        """
        dict: The dictionary of feature_id to corresponding items on annotate canvas.
        """

        return self._feature_dict

    @property
    def annotate_to_feature(self):
        # type: () -> Dict[int, str]
        """
        dict: The dictionary of annotate canvas id to feature_id.
        """

        return self._annotate_to_feature

    @property
    def annotate_to_context(self):
        # type: () -> Dict[int, int]
        """
        dict: The dictionary of annotate canvas id to context canvas id.
        """

        return self._annotate_to_context

    @property
    def context_to_annotate(self):
        # type: () -> Dict[int, int]
        """
        dict: The dictionary of context canvas id to annotate feature id.
        """

        return self._context_to_annotate

    # good properties
    @property
    def current_annotate_canvas_id(self):
        """
        None|int: The current annotation feature id.
        """

        return self._current_annotate_canvas_id

    @current_annotate_canvas_id.setter
    def current_annotate_canvas_id(self, value):
        if value is None:
            self._current_annotate_canvas_id = None
            self._current_feature_id = None
        else:
            self._current_annotate_canvas_id = value
            self._current_feature_id = self._annotate_to_feature.get(value, None)

    @property
    def current_feature_id(self):
        """
        None|str: The current feature id.
        """

        return self._current_feature_id

    def set_current_feature_id(self, feature_id):
        """
        Sets the current feature id.
        """

        if (feature_id is None) or (feature_id not in self._feature_dict):
            self._current_feature_id = None
            self._current_annotate_canvas_id = None
            return

        self._current_feature_id = feature_id
        if self._current_annotate_canvas_id is None:
            return
        if self._current_annotate_canvas_id not in self.get_annotate_shapes_for_feature(feature_id):
            self._current_annotate_canvas_id = None

    # fetch tracking information
    def get_annotate_shapes_for_feature(self, feature_id):
        """
        Gets the annotation shape ids associated with the given feature id.

        Parameters
        ----------
        feature_id : str

        Returns
        -------
        None|List[int]
        """

        if feature_id not in self._feature_dict:
            return None
        return self._feature_dict[feature_id]['annotate_id']

    def get_color_for_feature(self, feature_id):
        """
        Gets the color associated with the given feature id.

        Parameters
        ----------
        feature_id : str

        Returns
        -------
        None|str
        """

        if feature_id not in self._feature_dict:
            return None
        return self._feature_dict[feature_id]['color']

    def get_context_for_annotate(self, annotate_id):
        """
        Gets the context shape id associated with the given annotate_id.

        Parameters
        ----------
        annotate_id : int

        Returns
        -------
        None|int
        """

        return self._annotate_to_context.get(annotate_id, None)

    def get_feature_for_annotate(self, annotate_id):
        """
        Gets the feature id associated with the given annotate id.

        Parameters
        ----------
        annotate_id : int

        Returns
        -------
        None|str
        """

        return self._annotate_to_feature.get(annotate_id, None)

    def reinitialize_features(self):
        """
        Reinitialize the feature tracking dictionaries. NOte that this assumes that
        the context and annotate canvases have been reinitialized elsewhere.

        Returns
        -------
        None
        """

        self._feature_dict = OrderedDict()
        self._annotate_to_feature = OrderedDict()
        self._annotate_to_context = OrderedDict()
        self._context_to_annotate = OrderedDict()
        self._current_annotate_canvas_id = None
        self._current_feature_id = None

    def set_annotate_context_tracking(self, annotate_id, context_id):
        """
        Associate tracking between the annotate canvas shape and context canvas
        shape given by the respective ids.

        Parameters
        ----------
        annotate_id : int
        context_id : int
        """

        if not (isinstance(annotate_id, integer_types) and isinstance(context_id, integer_types)):
            raise TypeError('Both annotate_id and context_id must be of integer type.')

        current_context_partner = self._annotate_to_context.get(annotate_id, None)
        current_annotate_partner = self._context_to_annotate.get(context_id, None)

        if current_annotate_partner is None and current_context_partner is None:
            # this is new tracking
            self._annotate_to_context[annotate_id] = context_id
            self._context_to_annotate[context_id] = annotate_id
            return
        if current_annotate_partner == annotate_id and current_context_partner == context_id:
            # this is already the tracking
            return

        # otherwise, we're in some kind of bad state.
        raise ValueError(
            'annotate id {} is currently associated with context id {}, and '
            'context id {} is currently associated with annotate id {}'.format(
                annotate_id, current_context_partner, context_id, current_annotate_partner))

    def set_feature_tracking(self, feature_id, annotate_id, color):
        """
        Initialize feature tracking between the given feature id, the given annotate
        ids, and store the given color.

        Parameters
        ----------
        feature_id : str
        annotate_id : int|List[int]
        color : None|str
        """

        self._initialize_feature_tracking(feature_id, color)
        self.append_shape_to_feature_tracking(feature_id, annotate_id)

    def append_shape_to_feature_tracking(self, feature_id, annotate_id, the_color=None):
        """
        Add a new shape or shapes to the given feature.

        Parameters
        ----------
        feature_id : str
        annotate_id : int|List[int]
        the_color : None|str
        """

        if feature_id not in self._feature_dict:
            raise KeyError('We are not tracking feature id {}'.format(feature_id))

        the_dict = self._feature_dict[feature_id]
        the_annotate_ids = the_dict['annotate_id']
        if the_color is not None:
            the_dict['color'] = the_color

        if isinstance(annotate_id, integer_types):
            self._initialize_annotate_feature_tracking(annotate_id, feature_id)
            the_annotate_ids.append(annotate_id)
        elif isinstance(annotate_id, (list, tuple)):
            for entry in annotate_id:
                self._initialize_annotate_feature_tracking(entry, feature_id)
                the_annotate_ids.append(entry)
        else:
            raise TypeError('Got unhandled annotate_id type {}'.format(type(annotate_id)))

    def merge_features(self, *args):
        """
        Merge the collection of features into the initial feature. The color and
        annotation from the initial feature will be maintained.

        Note that this does not actually change the colors of the rendered shapes,
        nor modify the actual annotation list.

        Parameters
        ----------
        args
            A collection of feature ids. The color of the first will be used. Note
            that this does not actually change any of the colors of the shapes on
            the canvases.
        """

        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = args[0]
        if len(args) <= 1:
            raise ValueError('More than one feature id must be supplied for merging.')
        for entry in args:
            if entry not in self._feature_dict:
                raise KeyError('Got untracked feature id {}'.format(entry))

        primary_id = args[0]
        primary_dict = self.feature_dict[primary_id]
        primary_annotate_list = primary_dict['annotate_id']
        for feat_id in args[1:]:
            the_dict = self._feature_dict[feat_id]
            for annotate_id in the_dict['annotate_id']:
                # re-associate the annotate shape with the new feature
                self._annotate_to_feature[annotate_id] = primary_id
                primary_annotate_list.append(annotate_id)
            # delete feat_id from tracking
            del self._feature_dict[feat_id]

    def remove_annotation_from_feature(self, annotation_id):
        """
        Remove the association of this shape with any feature.

        Parameters
        ----------
        annotation_id : int

        Returns
        -------
        None|int
            The number of remaining shapes associated with the feature. This is
            None if the shape is not associated with any feature.
        """

        feature_id = self._annotate_to_feature.get(annotation_id, None)
        if feature_id is None:
            return None

        the_list = self._feature_dict[feature_id]['annotate_id']
        if annotation_id in the_list:
            the_list.remove(annotation_id)
        self._annotate_to_feature[annotation_id] = None
        return len(the_list)

    def delete_feature_from_tracking(self, feature_id):
        """
        Remove the given feature from tracking. The associated annotate shape
        elements which should be deleted will be returned.

        Parameters
        ----------
        feature_id : str

        Returns
        -------
        List[int]
            The list of annotate shape ids for deletion.
        """

        if feature_id not in self._feature_dict:
            return  # nothing to be done

        the_dict = self._feature_dict[feature_id]
        the_annotate_ids = the_dict['annotate_id']

        delete_shapes = []

        # for any shape not reassigned, set assignment to None
        for entry in the_annotate_ids:
            if entry not in self._annotate_to_feature:
                continue  # we've already actually deleted the shape
            associated_feat = self._annotate_to_feature[entry]
            if associated_feat is None:
                # this is marked for deletion, but deletion didn't happen
                delete_shapes.append(entry)
            elif associated_feat != feature_id:
                # reassigned to a different feature, do nothing
                continue
            else:
                # assign this tracking to None, to mark for deletion
                self._annotate_to_feature[entry] = None
                delete_shapes.append(entry)
        # remove the feature from tracking
        del self._feature_dict[feature_id]
        return delete_shapes

    def mark_context_for_deletion(self, context_id):
        """
        Indicate that the given context shape has been deleted from the canvas.

        Parameters
        ----------
        context_id : int
        """

        if context_id not in self._context_to_annotate:
            return  # it wasn't being tracked

        self._context_to_annotate[context_id] = None

    def delete_annotation_from_tracking(self, annotation_id):
        """
        Remove the annotation id from tracking. This requires that the shape has
        been removed from any associated feature, and the associated context shape
        has been marked for deletion.

        Parameters
        ----------
        annotation_id : int
        """

        if annotation_id not in self._annotate_to_feature:
            return

        # verify that association with None as feature.
        feat_id = self._annotate_to_feature[annotation_id]
        if feat_id is not None:
            raise ValueError(
                "We can't delete annotation id {}, because it is still associated "
                "with feature {}".format(annotation_id, feat_id))

        if annotation_id in self._annotate_to_context:
            # verify that the context shape associated is already deleted.
            cont_id = self._annotate_to_context[annotation_id]
            if cont_id in self._context_to_annotate:
                if self._context_to_annotate[cont_id] is not None:
                    raise ValueError(
                        "We can't delete annotation id {}, because it is still associated "
                        "with context id {}".format(annotation_id, cont_id))
            del self._context_to_annotate[cont_id]
        # actually remove the tracking entries
        del self._annotate_to_context[annotation_id]
        del self._annotate_to_feature[annotation_id]

    # helper methods
    def _initialize_annotate_feature_tracking(self, annotate_id, feature_id):
        """
        Helper function for associating tracking of the feature id for the given
        annotate id.

        Parameters
        ----------
        annotate_id : int
        feature_id : str
        """

        if not (isinstance(annotate_id, integer_types) and isinstance(feature_id, string_types)):
            raise TypeError('annotate_id must be of integer type, and feature_id must be of string type.')

        current_feature_partner = self._annotate_to_feature.get(annotate_id, None)
        if current_feature_partner is None:
            # new tracking
            self._annotate_to_feature[annotate_id] = feature_id
            return
        if current_feature_partner == feature_id:
            # already the current tracking
            return
        # otherwise, we are in a bad state
        raise ValueError(
            'annotate id {} is currently associated with feature id {}, '
            'not feature id {}'.format(annotate_id, current_feature_partner, feature_id))

    def _initialize_feature_tracking(self, feature_id, color):
        """
        Helper function to initialize feature tracking.

        Parameters
        ----------
        feature_id : str
        color : None|str
        """

        if feature_id in self._feature_dict:
            raise KeyError('We are already tracking feature id {}'.format(feature_id))

        self._feature_dict[feature_id] = {'annotate_id': [], 'color': color}


class AnnotationTool(WidgetPanel, WidgetWithMetadata):
    _widget_list = ("context_panel", "annotate_panel")
    context_panel = widget_descriptors.PanelDescriptor(
        "context_panel", ContextImagePanel,
        docstring='The overall image panel.')  # type: ContextImagePanel
    annotate_panel = widget_descriptors.PanelDescriptor(
        "annotate_panel", AnnotateImagePanel,
        docstring='The detail panel for crafting annotations.')  # type: AnnotateImagePanel

    def __init__(self, primary):
        """

        Parameters
        ----------
        primary : tkinter.Tk|tkinter.Toplevel
        """

        self._schema_browse_directory = os.path.expanduser('~')
        self._image_browse_directory = os.path.expanduser('~')
        self.primary = basic_widgets.Frame(primary)
        # temporary state variables
        self._modifying_shapes_on_annotate = False
        self._modifying_context_selection = False
        self._modifying_annotate_tool = False

        WidgetPanel.__init__(self, self.primary)
        WidgetWithMetadata.__init__(self, primary)

        self.init_w_horizontal_layout()
        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.variables = AppVariables()

        menubar = tkinter.Menu()

        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.select_image_file)
        filemenu.add_command(label="Open Existing Annotation", command=self.select_annotation_file)
        filemenu.add_command(label="Create New Annotation", command=self.create_new_annotation_file)
        filemenu.add_separator()
        filemenu.add_command(label="Save Annotation File", command=self.save_annotation_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        # create more pulldown menus
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Popups", menu=popups_menu)

        self.context_panel.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        self.context_panel.context_label.master.pack(side='top', expand=tkinter.NO)
        self.context_panel.master.pack(side='bottom', fill=tkinter.BOTH, expand=tkinter.YES)
        self.context_panel.image_panel.canvas.set_canvas_size(400, 300)

        self.annotate_panel.buttons.fill_y(False)
        self.annotate_panel.buttons.do_not_expand()
        # self.annotate_panel.buttons.pack(side="bottom")
        self.annotate_panel.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        self.annotate_panel.image_panel.canvas.set_canvas_size(400, 300)

        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        primary.config(menu=menubar)

        # hide unwanted elements on the panel toolbars
        self.context_panel.set_text('')
        self.context_panel.context_label.set_text('Select an image file using the File menu.')
        self.context_panel.image_panel.set_text('The contextual area.')
        self.context_panel.image_panel.hide_tools('shape_drawing')
        self.context_panel.image_panel.hide_shapes()
        self.context_panel.image_panel.hide_select_index()
        # disable tools until an image is selected
        self.context_panel.image_panel.disable_tools()

        self.annotate_panel.set_text('')
        self.annotate_panel.image_panel.set_text('The annotation area.')
        self.annotate_panel.image_panel.hide_tools('select')
        self.annotate_panel.image_panel.hide_shapes(['arrow', 'text'])
        self.annotate_panel.image_panel.hide_remap_combo()
        self.annotate_panel.image_panel.hide_select_index()
        # disable tools and shapes until a file annotation is selected
        self.annotate_panel.image_panel.disable_tools()
        self.annotate_panel.image_panel.disable_shapes()

        # set button callbacks
        self.annotate_panel.buttons.delete_shape.config(command=self.callback_delete_shape)
        self.annotate_panel.buttons.delete_annotation.config(command=self.callback_delete_feature)
        self.annotate_panel.buttons.annotate.config(command=self.callback_annotation_popup)

        # set up context panel event listeners
        self.context_panel.image_panel.canvas.bind('<<SelectionFinalized>>', self.sync_context_selection_to_annotate_zoom)
        self.context_panel.image_panel.canvas.bind('<<RemapChanged>>', self.sync_remap_change)
        self.context_panel.image_panel.canvas.bind('<<ImageIndexChanged>>', self.sync_image_index_changed)

        # set up annotate panel listeners
        self.annotate_panel.image_panel.canvas.bind('<<CurrentToolChanged>>', self.verify_setting_annotate_tool)
        self.annotate_panel.image_panel.canvas.bind('<<ImageExtentChanged>>', self.sync_annotate_zoom_to_context_selection)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeCreate>>', self.shape_create_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeCoordsFinalized>>', self.shape_finalized_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeDelete>>', self.shape_delete_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeSelect>>', self.shape_selected_on_annotate)

    @property
    def image_file_name(self):
        """
        None|str: The image file name.
        """

        return self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader.file_name

    # utility functions
    ####
    def _create_context_shape_from_annotate_shape(self, annotate_id):
        """
        Create a context shape from an annotate shape, and initiate the tracking.

        Parameters
        ----------
        annotate_id : int
        """

         # get the vector
        vector_object = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
        if vector_object is None:
            raise ValueError('No vector associate with shape id {}'.format(annotate_id))

        if vector_object.type == ShapeTypeConstants.POINT:
            context_id = self.context_panel.image_panel.canvas.create_new_point(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        elif vector_object.type == ShapeTypeConstants.LINE:
            context_id = self.context_panel.image_panel.canvas.create_new_line(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        elif vector_object.type == ShapeTypeConstants.RECT:
            context_id = self.context_panel.image_panel.canvas.create_new_rect(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        elif vector_object.type == ShapeTypeConstants.ELLIPSE:
            context_id = self.context_panel.image_panel.canvas.create_new_ellipse(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        elif vector_object.type == ShapeTypeConstants.POLYGON:
            context_id = self.context_panel.image_panel.canvas.create_new_polygon(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        elif vector_object.type == ShapeTypeConstants.ARROW:
            context_id = self.context_panel.image_panel.canvas.create_new_arrow(
                vector_object.image_coords, make_current=False, increment_color=False, color=vector_object.color)
        else:
            raise ValueError('Unsupported vector object type for copying {}'.format(ShapeTypeConstants.get_name(vector_object.type)))
        # set up the association between the two shapes
        self.variables.set_annotate_context_tracking(annotate_id, context_id)

    def _sync_annotate_shape_to_context_shape(self, annotate_id):
        """
        Synchronize the annotate shape to the context shape. This assumes that
        tracking is in place.

        Parameters
        ----------
        annotate_id : int
        """

        # get the vector
        vector_object = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
        if vector_object is None:
            raise ValueError('No vector associate with shape id {}'.format(annotate_id))

        # get the context shape id
        cont_id = self.variables.get_context_for_annotate(annotate_id)
        if cont_id is None:
            raise ValueError('No context shape associate with annotate shape id {}'.format(annotate_id))

        # update the context shape coordinates
        self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(cont_id, vector_object.image_coords)

    def _ensure_color_for_shapes(self, feature_id):
        """
        Ensure that all shapes associated with the given feature_id are rendered
        with the correct color.

        Parameters
        ----------
        feature_id : str
        """

        # get the correct color
        the_color = self.variables.get_color_for_feature(feature_id)
        if the_color is None:
            return
        for annotate_id in self.variables.get_annotate_shapes_for_feature(feature_id):
            context_id = self.variables.get_context_for_annotate(annotate_id)
            self.annotate_panel.image_panel.canvas.change_shape_color(annotate_id, the_color)
            self.context_panel.image_panel.canvas.change_shape_color(context_id, the_color)

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

        geometry_object = self.annotate_panel.image_panel.canvas.get_geometry_for_shape(shape_id, coordinate_type='image')
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

        annotate_ids = self.variables.get_annotate_shapes_for_feature(feature_id)
        if annotate_ids is None:
            return None
        elif len(annotate_ids) == 1:
            return self._get_geometry_from_shape(annotate_ids[0])
        else:
            return GeometryCollection(geometries=[self._get_geometry_from_shape(entry) for entry in annotate_ids])

    def _create_shape_from_geometry(self, feature, the_geometry, the_color=None):
        """
        Helper function for creating shapes on the annotation and context canvases
        from the given feature element.

        Parameters
        ----------
        feature : Annotation
            The feature, only used here for logging a failure.
        the_geometry : Point|LineString|Polygon
        the_color : None|str

        Returns
        -------
        annotate_id : int
            The id of the element on the annotation canvas
        the_color : str
            The color of the shape.
        """

        def insert_point():
            # type: () -> Tuple[int, int, str]
            image_coords = the_geometry.coordinates[:2].tolist()
            # create the shape on the annotate panel
            annotate_id = self.annotate_panel.image_panel.canvas.create_new_point((0, 0), **kwargs)
            self.annotate_panel.image_panel.canvas.modify_existing_shape_using_image_coords(
                annotate_id, image_coords)
            # create the identical shape on the context panel
            the_annotate_vector = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
            kwargs['color'] = the_annotate_vector.color

            context_canvas_id = self.context_panel.image_panel.canvas.create_new_point((0, 0), **kwargs)
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(
                context_canvas_id, image_coords)
            return annotate_id, context_canvas_id, kwargs['color']

        def insert_line():
            # type: () -> Tuple[int, int, str]
            image_coords = the_geometry.coordinates[:, 2].tolist()
            # create the shape on the annotate panel
            annotate_id = self.annotate_panel.image_panel.canvas.create_new_line((0, 0, 0, 0), **kwargs)
            self.annotate_panel.image_panel.canvas.modify_existing_shape_using_image_coords(
                annotate_id, image_coords)
            # create the identical shape on the context panel
            the_annotate_vector = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
            kwargs['color'] = the_annotate_vector.color

            context_canvas_id = self.context_panel.image_panel.canvas.create_new_line((0, 0), **kwargs)
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(
                context_canvas_id, image_coords)
            return annotate_id, context_canvas_id, kwargs['color']

        def insert_polygon():
            # type: () -> Tuple[int, int, str]

            # this will only render an outer ring
            image_coords = the_geometry.outer_ring.coordinates[:, :2].flatten().tolist()
            # create the shape on the annotate panel
            annotate_id = self.annotate_panel.image_panel.canvas.create_new_polygon((0, 0, 0, 0), **kwargs)
            self.annotate_panel.image_panel.canvas.modify_existing_shape_using_image_coords(annotate_id, image_coords)
            # create the identical shape on the context panel
            the_annotate_vector = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
            kwargs['color'] = the_annotate_vector.color

            context_canvas_id = self.context_panel.image_panel.canvas.create_new_polygon((0, 0, 0, 0), **kwargs)
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(context_canvas_id, image_coords)
            return annotate_id, context_canvas_id, kwargs['color']

        kwargs = {'make_current': False}  # type: Dict[str, Any]
        if the_color is not None:
            kwargs = {'color': the_color}

        self._modifying_shapes_on_annotate = True
        if isinstance(the_geometry, Point):
            annotate_shape_id, context_shape_id, shape_color = insert_point()
        elif isinstance(the_geometry, LineString):
            annotate_shape_id, context_shape_id, shape_color = insert_line()
        elif isinstance(the_geometry, Polygon):
            annotate_shape_id, context_shape_id, shape_color = insert_polygon()
        else:
            showinfo(
                'Unhandled Geometry',
                message='Annotation id {} has unsupported feature component of type {} which '
                        'will be omitted from display. Any save of the annotation '
                        'will not contain this feature.'.format(feature.uid, type(the_geometry)))
            self._modifying_shapes_on_annotate = False
            return None, None

        self._modifying_shapes_on_annotate = False
        # set up the tracking for the new shapes
        self.variables.set_annotate_context_tracking(annotate_shape_id, context_shape_id)
        self.variables.append_shape_to_feature_tracking(feature.uid, annotate_shape_id, the_color=shape_color)
        return annotate_shape_id, shape_color

    def _insert_feature_from_file(self, feature):
        """
        This is creating all shapes from the given geometry. This short-circuits
        the event listeners, so must handle all tracking updates itself.

        Parameters
        ----------
        feature : Annotation
        """

        def extract_base_geometry(the_element, base_collection):
            # type: (Geometry, List) -> None
            if the_element is None:
                return
            elif isinstance(the_element, GeometryCollection):
                if the_element.geometries is None:
                    return
                for sub_element in the_element.geometries:
                    extract_base_geometry(sub_element, base_collection)
            elif isinstance(the_element, MultiPoint):
                if the_element.points is None:
                    return
                base_collection.extend(the_element.points)
            elif isinstance(the_element, MultiLineString):
                if the_element.lines is None:
                    return
                base_collection.extend(the_element.lines)
            elif isinstance(the_element, MultiPolygon):
                if the_element.polygons is None:
                    return
                base_collection.extend(the_element.polygons)
            else:
                base_collection.append(the_element)

        the_color = None
        # initialize the feature tracking
        self.variables.set_feature_tracking(feature.uid, [], None)
        # extract a list of base geometry elements
        base_geometries = []
        extract_base_geometry(feature.geometry, base_geometries)
        # create shapes for all the geometries
        for geometry in base_geometries:
            annotate_id, the_color = self._create_shape_from_geometry(
                feature, geometry, the_color=the_color)

    def _create_feature_from_shape(self, annotate_id):
        """
        Create a blank annotation from an annotation shape.

        Parameters
        ----------
        annotate_id : int

        Returns
        -------
        str
            The id of the newly created annotation feature object.
        """

        # NB: this assumes that the context shape has already been synced from
        # the event listener method

        geometry_object = self._get_geometry_from_shape(annotate_id)
        annotation = Annotation(geometry=geometry_object)
        self.variables.file_annotation_collection.add_annotation(annotation)
        self.variables.unsaved_changed = True

        vector_object = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
        self.variables.set_feature_tracking(annotation.uid, annotate_id, color=vector_object.color)
        # TODO: update the treeview?
        return annotation.uid

    def _update_feature_geometry(self, feature_id):
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
        # TODO: update the treeview?
        self.variables.unsaved_changed = True

    def _add_shape_to_feature(self, feature_id, annotate_id):
        """
        Add the annotation shape to the given feature. This assumes it's not
        otherwise being tracked as part of another feature.

        Parameters
        ----------
        feature_id : str
        annotate_id : int
        """

        # NB: this assumes that the context shape has already been synced from
        # the event listener method

        # verify feature color is set
        the_color = self.variables.get_color_for_feature(feature_id)
        if the_color is None:
            vector_object = self.annotate_panel.image_panel.canvas.get_vector_object(annotate_id)
            the_color = vector_object.color
        # update feature tracking
        self.variables.append_shape_to_feature_tracking(feature_id, annotate_id, the_color=the_color)
        # ensure all shapes for this feature are colored correctly
        self._ensure_color_for_shapes(feature_id)
        # update the entry of our annotation object
        self._update_feature_geometry(feature_id)
        self.variables.unsaved_changed = True

    def _initialize_geometry(self, annotation_file_name, annotation_collection):
        """
        Initialize the geometry elements from the annotation.

        Parameters
        ----------
        annotation_file_name : str
        annotation_collection : FileAnnotationCollection

        Returns
        -------
        None
        """

        # set our appropriate variables
        self.variables.annotation_file_name = annotation_file_name
        self.variables.label_schema = annotation_collection.label_schema
        self.variables.file_annotation_collection = annotation_collection
        self.variables.current_annotate_canvas_id = None # TODO: any other state variables to update?

        # dump all the old shapes
        self._modifying_shapes_on_annotate = True
        self.annotate_panel.image_panel.canvas.reinitialize_shapes()
        self.context_panel.image_panel.canvas.reinitialize_shapes()
        self._modifying_shapes_on_annotate = False

        # reinitialize dictionary relating canvas shapes and annotation shapes
        self.variables.reinitialize_features()

        # populate all the shapes
        if annotation_collection.annotations is not None:
            for feature in annotation_collection.annotations.features:
                self._insert_feature_from_file(feature)

    def _initialize_annotation_file(self, annotation_fname, annotation_collection):
        """
        The final initialization steps for the annotation file.

        Parameters
        ----------
        annotation_fname : str
        annotation_collection : FileAnnotationCollection
        """

        self._initialize_geometry(annotation_fname, annotation_collection)
        self.annotate_panel.image_panel.enable_tools()
        self.annotate_panel.image_panel.enable_shapes()
        self.variables.unsaved_changed = False
        self.context_panel.context_label.set_text('Create annotations on the annotation panel.')

    def _delete_feature(self, feature_id):
        """
        Removes the given feature.

        Parameters
        ----------
        feature_id : str
        """

        if self.variables.current_feature_id == feature_id:
            self.variables.set_current_feature_id(None)

        # remove feature from tracking, and get list of shapes to delete
        annotate_ids = self.variables.delete_feature_from_tracking(feature_id)
        # delete the shapes - this will also deleting the corresponding context
        # shapes and remove from tracking
        for entry in annotate_ids:
            self.annotate_panel.image_panel.canvas.delete_shape(entry)
        # TODO: update treeview!

    # helper functions for callbacks
    #####
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

    def _verify_file_annotation_selected(self, popup=True):
        """
        Verify that a file annotation has been selected. Deploy helpful popup if not.

        Parameters
        ----------
        popup : bool
            Should we deploy the popup?

        Returns
        -------
        bool
        """

        if not self._verify_image_selected(popup=popup):
            return False

        if self.variables.file_annotation_collection is None:
            if popup:
                showinfo('No Annotation file set up.', message='Please define an Annotation file, using the file menu.')
            return False
        return True

    @staticmethod
    def _get_side_lengths(coords):
        """
        Get the side lengths from a rectangle coordinate list/tuple.

        Parameters
        ----------
        coords : Tuple|List

        Returns
        -------
        (float, float)
        """

        y_min = min(coords[0::2])
        y_max = max(coords[0::2])
        x_min = min(coords[1::2])
        x_max = max(coords[1::2])
        return y_max-y_min, x_max-x_min

    # main callback functions
    #####
    def exit(self):
        """
        The tool exit function
        """

        self.quit()

    def select_image_file(self):
        """
        Select the image callback.

        Returns
        -------
        None
        """

        fname = askopenfilename(
            title='Select image file',
            initialdir=self._image_browse_directory,
            filetypes=nitf_preferred_collection)

        if fname in ['', ()]:
            return

        self._image_browse_directory = os.path.split(fname)[0]
        image_reader = ComplexImageReader(fname)
        if image_reader.image_count != 1:
            showinfo('Single Image Required',
                     message='The given image reader for file {} has {} distinct images. '
                             'Annotation is only permitted for single image readers. '
                             'Aborting'.format(image_reader.file_name, image_reader.image_count))
            return

        self.context_panel.context_label.set_text('Create or select an annotation file using the File menu.')
        self.context_panel.image_panel.set_image_reader(image_reader)
        self.annotate_panel.image_panel.set_image_reader(image_reader)
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.context_panel.image_panel.enable_tools()

    def create_new_annotation_file(self):
        if not self._verify_image_selected():
            return

        # TODO: prompt for any unsaved changes

        schema_fname = askopenfilename(
            title='Select label schema',
            initialdir=self._schema_browse_directory,
            filetypes=[json_files, all_files])
        if schema_fname in ['', ()]:
            return

        self._schema_browse_directory = os.path.split(schema_fname)[0]
        try:
            label_schema = LabelSchema.from_file(schema_fname)
        except Exception as e:
            showinfo(
                'Failed Opening Schema',
                message='Failed opening schema {} with exception {}. '
                        'Aborting new annotation creation.'.format(schema_fname, e))
            return

        browse_dir, image_fname = os.path.split(self.image_file_name)

        annotation_fname = None
        while annotation_fname is None:
            annotation_fname = asksaveasfilename(
                title='Select annotation file for image file {}'.format(image_fname),
                initialdir=browse_dir,
                initialfile='{}.annotation.json'.format(image_fname),
                filetypes=[json_files, all_files])
            if annotation_fname in ['', ()]:
                annotation_fname = None

                response = askyesnocancel(
                    'No annotation selected?',
                    message='No annotation was selected, and the creation of new annotation file is incomplete. '
                            'Should the effort be continued?')
                if response is not True:
                    # we've cancelled the effort
                    break
                # all other cases, annotation_fname is defined appropriately

        if annotation_fname is None:
            return

        annotation_collection = FileAnnotationCollection(
            label_schema=label_schema, image_file_name=image_fname)
        self._initialize_annotation_file(annotation_fname, annotation_collection)

    def select_annotation_file(self):
        if not self._verify_image_selected():
            return

        # TODO: prompt for any unsaved changes

        # TODO: verify functionality
        browse_dir, image_fname = os.path.split(self.image_file_name)
        # guess at a sensible initial file name
        init_file = '{}.annotation.json'.format(image_fname)
        if not os.path.exists(os.path.join(browse_dir, init_file)):
            init_file = ''

        annotation_fname = askopenfilename(
            title='Select annotation file for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile=init_file,
            filetypes=[json_files, all_files])
        if annotation_fname in ['', ()]:
            return
        if not os.path.exists(annotation_fname):
            showinfo('File does not exist', message='Annotation file {} does not exist'.format(annotation_fname))
            return

        try:
            annotation_collection = FileAnnotationCollection.from_file(annotation_fname)
        except Exception as e:
            showinfo('File Annotation Error',
                     message='Opening annotation file {} failed with error {}. Aborting.'.format(annotation_fname, e))
            return

        # validate the the image selected matches the annotation image name
        if annotation_collection.image_file_name != image_fname:
            showinfo('Image File Mismatch',
                     message='The annotation selected applies to image file {}, '
                             'while the selected image file is {}. '
                             'Aborting.'.format(annotation_collection.image_file_name, image_fname))
            return

        response = askyesno('Create annotation backup?', message='Should a backup of the annotation file be created?')
        if response is True:
            backup_fname = annotation_fname + '.{0:0.0f}.bak'.format(time.time())
            copyfile(annotation_fname, backup_fname)
        # finish initialization
        self._initialize_annotation_file(annotation_fname, annotation_collection)

    def save_annotation_file(self):
        """
        Save the annotation file.
        """

        if not self._verify_file_annotation_selected(popup=True):
            self.variables.unsaved_changed = False
            return

        self.variables.file_annotation_collection.to_file(self.variables.annotation_file_name)
        self.variables.unsaved_changed = False

    def callback_delete_shape(self):
        """
        Remove the given shape from the current annotation.
        """

        if not self._verify_file_annotation_selected(popup=True):
            return # nothing to be done

        shape_id = self.variables.current_annotate_canvas_id
        feature_id = self.variables.current_feature_id
        if shape_id is None:
            showinfo('No shape is selected', message="No shape is selected.")
            return

        # remove the shape from the given feature tracking
        remaining_shapes = self.variables.remove_annotation_from_feature(shape_id)
        # delete the shape -
        #   this will also deleting the corresponding context and reset the current id
        self.annotate_panel.image_panel.canvas.delete_shape(shape_id)
        if remaining_shapes is None or remaining_shapes > 0:
            return  # nothing more to be done
        else:
            # we may not want an orphaned feature
            response = askyesno('Annotation with empty geometry',
                                message='The shape just deleted is the only geometry '
                                        'associated feature {}. Delete the feature?'.format(feature_id))
            if response is True:
                self._delete_feature(feature_id)
            else:
                self.variables.set_current_feature_id(feature_id)

    def callback_delete_feature(self):
        """
        Deletes the currently selected feature.
        """

        if not self._verify_file_annotation_selected(popup=True):
            return # nothing to be done

        feature_id = self.variables.current_feature_id
        if feature_id is None:
            showinfo('No feature is selected', message="No feature is selected to delete.")
            return
        self._delete_feature(feature_id)

    def callback_annotation_popup(self):
        """
        Open an annotation popup window.
        """

        self._verify_file_annotation_selected()

        if self.variables.current_feature_id is None:
            showinfo('No feature is selected', message="Please select the feature to view.")
            return

        popup = LabelingPopup(self.variables)
        popup.destroy()

    # event listeners
    #####
    # noinspection PyUnusedLocal
    def sync_remap_change(self, event):
        """
        Sync changing the remap value from the context panel to the
        annotate panel.

        Parameters
        ----------
        event
        """

        self.annotate_panel.image_panel.canvas.update_current_image()

    #noinspection PyUnusedLocal
    def sync_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.my_populate_metaicon()
        # TODO: what else should conceptually happen? This is not possible unless
        #  we permit an image with more than a single index.

    # noinspection PyUnusedLocal
    def verify_setting_annotate_tool(self, event):
        """
        Verify annotate_panel tool setting is sensible.

        Parameters
        ----------
        event
        """

        if self._modifying_annotate_tool:
            # don't get caught in a recursive loop
            return

        should_be_enabled = self._verify_file_annotation_selected(popup=False)
        if not should_be_enabled:
            self.annotate_panel.image_panel.disable_tools()
            self.annotate_panel.image_panel.disable_shapes()

        new_tool = self.annotate_panel.image_panel.canvas.current_tool
        if new_tool == ToolConstants.VIEW:
            return  # this is always fine
        elif not should_be_enabled:
            self._modifying_annotate_tool = True
            # NB: this temporary state variable is required to prevent recursive calls
            self.annotate_panel.image_panel.canvas.set_tool(ToolConstants.VIEW)
            self._modifying_annotate_tool = False
            return

    # noinspection PyUnusedLocal
    def sync_context_selection_to_annotate_zoom(self, event):
        """
        Sync the selection on the context panel to the annotate panel.

        Parameters
        ----------
        event
        """

        if self._modifying_context_selection:
            return  # avoid a infinite recursion

        self._modifying_context_selection = True  # temporary state to avoid infinite recursion
        # extract the zoom rectangle coordinates
        rect_id = self.context_panel.image_panel.canvas.variables.select_rect.uid
        self.context_panel.image_panel.canvas.show_shape(rect_id)  # just in case we got caught in a bad state

        # get the image coordinates for the context panel's selection rectangle
        image_rect = self.context_panel.image_panel.canvas.get_shape_image_coords(rect_id)

        annotate_zoom_rect = self.annotate_panel.image_panel.canvas.variables.\
            canvas_image_object.full_image_yx_to_canvas_coords(image_rect)
        # verify that the image_rect is big enough...or simply reset to what it should
        # be based on the annotate panel
        y_side, x_side = self._get_side_lengths(annotate_zoom_rect)
        size_threshold = self.context_panel.image_panel.canvas.variables.config.select_size_threshold
        if y_side <= 1 or x_side <=1:
            pass  # do nothing on tool reset/initialization
        elif y_side < size_threshold or x_side < size_threshold:
            # this is too small, reset back to here
            self.sync_annotate_zoom_to_context_selection(None)
        else:
            self.annotate_panel.image_panel.canvas.zoom_to_full_image_selection(image_rect)
            # NB: this triggers a call to the sync_annotate_zoom_to_context_selection()
            # This in turns will adjust the context selection box to account for differences
            # in aspect ratio of the selection rectangle and annotate canvas.
            #
            # That adjust will lead to this function being called again. We avoid
            # an infinite recursive loop, by stopping it here. The return call here
            # must do nothing.
        self._modifying_context_selection = False

    # noinspection PyUnusedLocal
    def sync_annotate_zoom_to_context_selection(self, event):
        """
        Sync the zoom on the annotation panel to the selection on the context panel.

        Parameters
        ----------
        event
        """

        # get the image extent for our current display
        image_rectangle, decimation = self.annotate_panel.image_panel.canvas.get_image_extent()
        y_side, x_side = self._get_side_lengths(image_rectangle)
        # get the full image size
        full_y = self.annotate_panel.image_panel.canvas.variables.canvas_image_object.image_reader.full_image_ny
        full_x = self.annotate_panel.image_panel.canvas.variables.canvas_image_object.image_reader.full_image_nx
        # if we are sufficiently close to the full rectangle, then reinitialize
        # the selection rectangle
        rect_id = self.context_panel.image_panel.canvas.variables.select_rect.uid


        if y_side >= 0.9*full_y and x_side >= 0.9*full_x:
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(rect_id, (0, 0, 0, 0))
        else:
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(rect_id, image_rectangle)
            self.context_panel.image_panel.canvas.show_shape(rect_id)  # just in case we got caught in a bad state

    def shape_create_on_annotate(self, event):
        """
        Handles the event that a shape has been created on the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        if self._modifying_shapes_on_annotate:
            return  # nothing required, and avoid recursive loop

        # sync over to the context panel
        self._create_context_shape_from_annotate_shape(event.x)

        # if the current_feature is set, ask whether to add, or create new?
        if self.variables.current_feature_id is not None:
            response = askyesno('Add shape to current annotation?',
                                message='Should we add this newly created shape to the '
                                        'current annotation (Yes), or create a new annotation (No)?')
            if response is True:
                self._add_shape_to_feature(self.variables.current_feature_id, event.x)
                return

        the_id = self._create_feature_from_shape(event.x)
        self.variables.current_annotate_canvas_id = event.x
        # TODO: update the treeview? Maybe set the selection?

    def shape_finalized_on_annotate(self, event):
        """
        Handles the event that a shapes coordinates have been (possibly temporarily)
        finalized (i.e. certainly not dragged).

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # TODO: this should not need to be short-circuited?

        # sync the given shape over to the context panel
        self._sync_annotate_shape_to_context_shape(event.x)
        # extract the appropriate feature, and sync changes to the list
        feature_id = self.variables.get_feature_for_annotate(event.x)
        self._update_feature_geometry(feature_id)

    def shape_delete_on_annotate(self, event):
        """
        Handles the event that a shape has been deleted from the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        if self.variables.current_annotate_canvas_id == event.x:
            self.variables.current_annotate_canvas_id = None

        if self._modifying_shapes_on_annotate:
            return

        # NB: any feature association must have already been handled, or we will
        # get a fatal error here

        # handle any context association
        context_id = self.variables.get_context_for_annotate(event.x)
        if context_id is not None:
            self.context_panel.image_panel.canvas.delete_shape(context_id)
            self.variables.mark_context_for_deletion(context_id)
        # remove this shape from tracking completely
        self.variables.delete_annotation_from_tracking(event.x)

    def shape_selected_on_annotate(self, event):
        """
        Handles the event that a shape has been selected on the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        self.variables.current_annotate_canvas_id = event.x
        # TODO: update the treeview!

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.context_panel.image_panel.canvas.variables.canvas_image_object is None or \
                self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader is None:
            image_reader = None
            the_index = 0
        else:
            image_reader = self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader
            the_index = self.context_panel.image_panel.canvas.get_image_index()
        self.populate_metaicon(image_reader, the_index)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.context_panel.image_panel.canvas.variables.canvas_image_object is None:
            image_reader = None
        else:
            image_reader = self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader
        self.populate_metaviewer(image_reader)


def main():
    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = AnnotationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
