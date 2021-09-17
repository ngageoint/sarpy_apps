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
from typing import Union, Dict, List, Tuple, Any
from datetime import datetime, timezone

import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesnocancel, askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename

from sarpy_apps.apps.labeling_tool.schema_editor import select_schema_entry

from sarpy_apps.supporting_classes.file_filters import all_files, json_files, \
    nitf_preferred_collection
from sarpy_apps.supporting_classes.image_reader import ComplexCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.panel_builder import WidgetPanel, WidgetPanelNoLabel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor
from tk_builder.panels.image_panel import ImagePanel

from sarpy.compliance import string_types, integer_types
from sarpy.annotation.label import FileLabelCollection, LabelFeature, \
    LabelMetadata, LabelMetadataList, LabelSchema
from sarpy.geometry.geometry_elements import Geometry, GeometryCollection, \
    Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, LinearRing
from sarpy.io.general.base import BaseReader


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
        self.object_type_label = basic_widgets.Label(
            master, text='Type:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.choose_type = basic_widgets.Button(
            master, text='Choose')
        self.comment_label = basic_widgets.Label(
            master, text='Comment:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.comment = tkinter.Text(master)
        self.confidence_label = basic_widgets.Label(
            master, text='Confidence:', anchor=tkinter.CENTER, relief=tkinter.RIDGE)
        self.confidence = basic_widgets.Combobox(master, text='')
        self.cancel = basic_widgets.Button(
            master, text='Cancel')
        self.submit = basic_widgets.Button(
            master, text='Submit')
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
                isinstance(annotation_metadata_list, LabelMetadataList))
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
        annotation_metadata = LabelMetadata(
            comment=the_comment,
            label_id=self._object_type_id,
            confidence=self.widget.confidence.get())
        self.annotation.add_annotation_metadata(annotation_metadata)
        self.main_app_variables.unsaved_changes = True
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
        # noinspection PyBroadException
        try:
            self.root.destroy()
        except Exception:
            pass


##############
# Annotation List Viewer and panel

class LabelCollectionViewer(basic_widgets.Frame):
    """
    Widget for visualizing an annotation list.
    """

    def __init__(self, master, annotation_list=None, geometry_size=None, **kwargs):
        """

        Parameters
        ----------
        master
            The tkinter element master.
        annotation_list : None|FileLabelCollection
        geometry_size : None|str
        kwargs
            The optional keywords for the Frame initialization.
        """

        self._annotation_list = None  # type: Union[None, FileLabelCollection]
        super(LabelCollectionViewer, self).__init__(master, **kwargs)
        self.parent = master
        if geometry_size is not None:
            self.parent.geometry(geometry_size)
        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        try:
            self.parent.protocol("WM_DELETE_WINDOW", self.close_window)
        except AttributeError:
            pass

        self.treeview = basic_widgets.Treeview(self, columns=('Date', 'Geometry', 'ID'))
        # define the column headings
        self.treeview.heading('#0', text='Label')
        self.treeview.heading('#1', text='Date')
        self.treeview.heading('#2', text='Geometry')
        self.treeview.heading('#3', text='ID')
        # instantiate the scroll bar and bind commands
        self.vert_scroll_bar = basic_widgets.Scrollbar(
            self.treeview.master, orient=tkinter.VERTICAL, command=self.treeview.yview)
        self.treeview.configure(xscrollcommand=self.vert_scroll_bar.set)
        self.horz_scroll_bar = basic_widgets.Scrollbar(
            self.treeview.master, orient=tkinter.HORIZONTAL, command=self.treeview.xview)
        self.treeview.configure(yscrollcommand=self.vert_scroll_bar.set)
        # pack these components into the frame
        self.vert_scroll_bar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        self.horz_scroll_bar.pack(side=tkinter.BOTTOM, fill=tkinter.X)
        self.treeview.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        self.fill_from_annotation_list(annotation_list)

    def _render_entry(self, annotation):
        """
        Render the given annotation.

        Parameters
        ----------
        annotation : LabelFeature
        """

        def get_annotation_string():
            # type: () -> (str, str)
            # fetch the properties
            properties = annotation.properties
            if properties is None or len(properties) == 0:
                return '<None>', ''
            else:
                entry = properties[0]
                return self._annotation_list.label_schema.labels[entry.label_id], \
                    datetime.fromtimestamp(entry.timestamp, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        def get_geometry_string():
            # type: () -> str
            if annotation.geometry is None:
                return '<None>'
            else:
                return annotation.geometry.__class__.__name__

        the_label, the_date_str = get_annotation_string()
        geometry_string = get_geometry_string()
        the_index = self._annotation_list.annotations.get_integer_index(annotation.uid)
        self.treeview.insert(
            '', the_index, annotation.uid, text=the_label,
            values=(the_date_str, geometry_string, annotation.uid))

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.

        Returns
        -------
        None
        """

        self.treeview.delete(*self.treeview.get_children())

    def delete_entry(self, the_id):
        """
        Delete the given entry.

        Parameters
        ----------
        the_id : str
        """

        # noinspection PyBroadException
        try:
            self.treeview.delete(the_id)  # try to delete, and just skip if it fails
        except Exception:
            pass

        if the_id in self._annotation_list.annotations:
            self._annotation_list.delete_annotation(the_id)

    def rerender_entry(self, the_id):
        """
        Rerender the given entry.

        Parameters
        ----------
        the_id : str
        """

        if self._annotation_list is None:
            self._empty_entries()
            return

        if the_id is None or the_id == '':
            self.fill_from_annotation_list(self._annotation_list)
        else:
            # noinspection PyBroadException
            try:
                self.treeview.delete(the_id)
            except Exception:
                pass

            self._render_entry(self._annotation_list.annotations[the_id])

    def fill_from_annotation_list(self, annotation_list):
        """
        Fill the treeview from the given annotation list.

        Parameters
        ----------
        annotation_list : None|FileLabelCollection
        """

        self._empty_entries()
        self._annotation_list = annotation_list
        if self._annotation_list is None or self._annotation_list.annotations is None:
            return
        for annotation in self._annotation_list.annotations:
            self._render_entry(annotation)

    def close_window(self):
        self.parent.withdraw()


class LabelPanelButtons(WidgetPanelNoLabel):
    _widget_list = ("annotate_button", "zoom_button")
    annotate_button = widget_descriptors.ButtonDescriptor(
        "annotate_button", default_text="Set Label")  # type: basic_widgets.Button
    zoom_button = widget_descriptors.ButtonDescriptor(
        "zoom_button", default_text="Zoom to Feature")  # type: basic_widgets.Button

    def __init__(self, master):
        super(LabelPanelButtons, self).__init__(master)
        self.init_w_horizontal_layout()


class LabelCollectionPanel(WidgetPanelNoLabel):
    """
    The panel for the annotation list.
    """

    _widget_list = ("buttons", "viewer")
    buttons = widget_descriptors.TypedDescriptor(
        "buttons", LabelPanelButtons)  # type: LabelPanelButtons
    viewer = widget_descriptors.TypedDescriptor(
        "viewer", LabelCollectionViewer)  # type: LabelCollectionViewer

    def __init__(self, master):
        super(LabelCollectionPanel, self).__init__(master)
        self.init_w_vertical_layout()
        self.buttons.config(relief=tkinter.RIDGE)
        self.buttons.master.pack(expand=tkinter.FALSE, fill=tkinter.X)
        self.viewer.master.pack(expand=tkinter.TRUE, side=tkinter.BOTTOM)


#########
# Main Annotation Window elements

class AppVariables(object):
    """
    The main application variables for the annotation panel.
    """

    unsaved_changes = BooleanDescriptor(
        'unsaved_changes', default_value=False,
        docstring='Are there unsaved annotation changes to be saved?')  # type: bool
    image_reader = TypedDescriptor(
        'image_reader', ComplexCanvasImageReader,
        docstring='The complex type image reader object.')  # type: ComplexCanvasImageReader
    label_schema = TypedDescriptor(
        'label_schema', LabelSchema,
        docstring='The label schema object.')  # type: LabelSchema
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileLabelCollection,
        docstring='The file annotation collection.')  # type: FileLabelCollection
    annotation_file_name = StringDescriptor(
        'annotation_file_name',
        docstring='The path for the annotation results file.')  # type: str
    add_shape_to_current_annotation = BooleanDescriptor(
        'add_shape_to_current_annotation', default_value=False,
        docstring='We a new shape is created, do we add it to the current annotation, '
                  'or create a new annotation?')  # type: bool

    def __init__(self):
        self._feature_dict = OrderedDict()
        self._canvas_to_feature = OrderedDict()
        self._current_canvas_id = None
        self._current_feature_id = None

    # do these variables need to be unveiled?
    @property
    def feature_dict(self):
        # type: () -> Dict[str, Dict]
        """
        dict: The dictionary of feature_id to corresponding items on annotate canvas.
        """

        return self._feature_dict

    @property
    def canvas_to_feature(self):
        # type: () -> Dict[int, str]
        """
        dict: The dictionary of annotate canvas id to feature_id.
        """

        return self._canvas_to_feature

    # good properties
    @property
    def current_canvas_id(self):
        """
        None|int: The current annotation feature id.
        """

        return self._current_canvas_id

    @property
    def current_feature_id(self):
        """
        None|str: The current feature id.
        """

        return self._current_feature_id

    # fetch tracking information
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

        out = self._feature_dict.get(feature_id, {'canvas_id': None})
        return out['canvas_id']

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

    def get_feature_for_annotate(self, canvas_id):
        """
        Gets the feature id associated with the given annotate id.

        Parameters
        ----------
        canvas_id : int

        Returns
        -------
        None|str
        """

        return self._canvas_to_feature.get(canvas_id, None)

    def reinitialize_features(self):
        """
        Reinitialize the feature tracking dictionaries. NOte that this assumes that
        the context and annotate canvases have been reinitialized elsewhere.

        Returns
        -------
        None
        """

        self._feature_dict = OrderedDict()
        self._canvas_to_feature = OrderedDict()
        self._current_canvas_id = None
        self._current_feature_id = None

    def set_feature_tracking(self, feature_id, canvas_id, color):
        """
        Initialize feature tracking between the given feature id, the given annotate
        ids, and store the given color.

        Parameters
        ----------
        feature_id : str
        canvas_id : int|List[int]
        color : None|str
        """

        self._initialize_feature_tracking(feature_id, color)
        self.append_shape_to_feature_tracking(feature_id, canvas_id)

    def append_shape_to_feature_tracking(self, feature_id, canvas_id, the_color=None):
        """
        Add a new shape or shapes to the given feature.

        Parameters
        ----------
        feature_id : str
        canvas_id : int|List[int]
        the_color : None|str
        """

        if feature_id not in self._feature_dict:
            raise KeyError('We are not tracking feature id {}'.format(feature_id))

        the_dict = self._feature_dict[feature_id]
        the_canvas_ids = the_dict['canvas_id']
        if the_color is not None:
            the_dict['color'] = the_color

        if isinstance(canvas_id, integer_types):
            self._initialize_annotate_feature_tracking(canvas_id, feature_id)
            the_canvas_ids.append(canvas_id)
        elif isinstance(canvas_id, (list, tuple)):
            for entry in canvas_id:
                self._initialize_annotate_feature_tracking(entry, feature_id)
                the_canvas_ids.append(entry)
        else:
            raise TypeError('Got unhandled canvas_id type {}'.format(type(canvas_id)))

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
        primary_annotate_list = primary_dict['canvas_id']
        for feat_id in args[1:]:
            the_dict = self._feature_dict[feat_id]
            for canvas_id in the_dict['canvas_id']:
                # re-associate the annotate shape with the new feature
                self._canvas_to_feature[canvas_id] = primary_id
                primary_annotate_list.append(canvas_id)
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

        feature_id = self._canvas_to_feature.get(annotation_id, None)
        if feature_id is None:
            return None

        the_list = self._feature_dict[feature_id]['canvas_id']
        if annotation_id in the_list:
            the_list.remove(annotation_id)
        self._canvas_to_feature[annotation_id] = None
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
        the_canvas_ids = the_dict['canvas_id']

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
                delete_shapes.append(entry)
        # remove the feature from tracking
        del self._feature_dict[feature_id]
        return delete_shapes

    def delete_shape_from_tracking(self, annotation_id):
        """
        Remove the annotation id from tracking. This requires that the shape has
        been removed from any associated feature.

        Parameters
        ----------
        annotation_id : int
        """

        if annotation_id not in self._canvas_to_feature:
            return

        # verify that association with None as feature.
        feat_id = self._canvas_to_feature[annotation_id]
        if feat_id is not None:
            raise ValueError(
                "We can't delete annotation id {}, because it is still associated "
                "with feature {}".format(annotation_id, feat_id))

        # actually remove the tracking entries
        del self._canvas_to_feature[annotation_id]

    # helper methods
    def _initialize_annotate_feature_tracking(self, canvas_id, feature_id):
        """
        Helper function for associating tracking of the feature id for the given
        annotate id.

        Parameters
        ----------
        canvas_id : int
        feature_id : str
        """

        if not (isinstance(canvas_id, integer_types) and isinstance(feature_id, string_types)):
            raise TypeError('canvas_id must be of integer type, and feature_id must be of string type.')

        current_feature_partner = self._canvas_to_feature.get(canvas_id, None)
        if current_feature_partner is None:
            # new tracking
            self._canvas_to_feature[canvas_id] = feature_id
            return
        if current_feature_partner == feature_id:
            # already the current tracking
            return
        # otherwise, we are in a bad state
        raise ValueError(
            'annotate id {} is currently associated with feature id {}, '
            'not feature id {}'.format(canvas_id, current_feature_partner, feature_id))

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

        self._feature_dict[feature_id] = {'canvas_id': [], 'color': color}


class LabelingTool(basic_widgets.Frame, WidgetWithMetadata):
    def __init__(self, primary):
        """

        Parameters
        ----------
        primary : tkinter.Tk|tkinter.Toplevel
        """

        self.root = primary
        self._schema_browse_directory = os.path.expanduser('~')
        self._image_browse_directory = os.path.expanduser('~')
        self.primary = tkinter.PanedWindow(primary, sashrelief=tkinter.RIDGE, orient=tkinter.HORIZONTAL)
        # temporary state variables
        self._modifying_shapes_on_canvas = False

        basic_widgets.Frame.__init__(self, primary)
        WidgetWithMetadata.__init__(self, primary)

        self.label_panel = LabelCollectionPanel(self.primary)  # type: LabelCollectionPanel
        self.label_panel.config(borderwidth=0)
        self.primary.add(self.label_panel, width=400, height=700, padx=5, pady=5, sticky=tkinter.NSEW)

        self.context_panel = ImagePanel(self.primary)  # type: ImagePanel
        self.context_panel.canvas.set_canvas_size(200, 500)
        self.context_panel.config(borderwidth=0)
        self.primary.add(self.context_panel, width=200, height=700, padx=5, pady=5, sticky=tkinter.NSEW)

        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.variables = AppVariables()

        # menu_bar items
        menu_bar = tkinter.Menu()
        file_menu = tkinter.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Image", command=self.select_image_file)
        file_menu.add_command(label="Open Existing Annotation File", command=self.select_annotation_file)
        file_menu.add_command(label="Create New Annotation File", command=self.create_new_annotation_file)
        file_menu.add_separator()
        file_menu.add_command(label="Save Annotation File", command=self.save_annotation_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit)

        # edit menu
        edit_menu = tkinter.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Delete Shape", command=self.callback_delete_shape)
        edit_menu.add_command(label="Delete Feature/Annotation", command=self.callback_delete_feature)

        # metadata popup menu
        metadata_menu = tkinter.Menu(menu_bar, tearoff=0)
        metadata_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        metadata_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # TODO: make a feature merge tool?

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        menu_bar.add_cascade(label="Metadata", menu=metadata_menu)

        primary.config(menu=menu_bar)

        # hide unwanted elements on the panel toolbars
        self.context_panel.hide_tools('select')
        self.context_panel.hide_shapes(['arrow', 'text'])
        self.context_panel.hide_select_index()
        # disable tools until an image is selected
        self.context_panel.disable_tools()
        self.context_panel.disable_shapes()

        # set button callbacks
        self.label_panel.buttons.annotate_button.config(command=self.callback_annotation_popup)
        self.label_panel.buttons.zoom_button.config(command=self.callback_zoom_to_feature)

        # set up context panel canvas event listeners
        self.context_panel.canvas.bind('<<ImageIndexChanged>>', self.sync_image_index_changed)
        self.context_panel.canvas.bind('<<ShapeCreate>>', self.shape_create_on_canvas)
        self.context_panel.canvas.bind('<<ShapeCoordsFinalized>>', self.shape_finalized_on_canvas)
        self.context_panel.canvas.bind('<<ShapeDelete>>', self.shape_delete_on_canvas)
        self.context_panel.canvas.bind('<<ShapeSelect>>', self.shape_selected_on_canvas)

        # set up the label_panel viewer event listeners
        self.label_panel.viewer.treeview.bind('<<TreeviewSelect>>', self.feature_selected_on_viewer)

    def set_current_canvas_id(self, value, check_feature=True):
        if value is None:
            self.variables._current_canvas_id = None
            self.context_panel.canvas.current_shape_id = None
        else:
            self.variables._current_canvas_id = value
            self.context_panel.canvas.current_shape_id = value
            if check_feature:
                self.set_current_feature_id(self.variables.canvas_to_feature.get(value, None))

    def set_current_feature_id(self, feature_id):
        """
        Sets the current feature id.
        """

        if (feature_id is None) or (feature_id not in self.variables.feature_dict):
            self.variables._current_feature_id = None
            self.set_current_canvas_id(None, check_feature=False)
            return

        self.variables._current_feature_id = feature_id
        self.label_panel.viewer.treeview.focus(feature_id)
        self.label_panel.viewer.treeview.selection_set(feature_id)
        canvas_shapes = self.variables.get_canvas_shapes_for_feature(feature_id)
        if canvas_shapes is None:
            self.set_current_canvas_id(None, check_feature=False)
        elif len(canvas_shapes) == 1:
            self.set_current_canvas_id(canvas_shapes[0], check_feature=False)
        elif self.variables.current_canvas_id not in canvas_shapes:
            self.set_current_canvas_id(None, check_feature=False)

    @property
    def image_file_name(self):
        """
        None|str: The image file name.
        """

        if self.variables.image_reader is None:
            return None
        return self.variables.image_reader.file_name

    # utility functions
    ####
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
        for canvas_id in self.variables.get_canvas_shapes_for_feature(feature_id):
            self.context_panel.canvas.change_shape_color(canvas_id, the_color)

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

        geometry_object = self.context_panel.canvas.get_geometry_for_shape(shape_id, coordinate_type='image')
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
            return GeometryCollection(geometries=[self._get_geometry_from_shape(entry) for entry in canvas_ids])

    def _create_shape_from_geometry(self, feature, the_geometry, the_color=None):
        """
        Helper function for creating shapes on the annotation and context canvases
        from the given feature element.

        Parameters
        ----------
        feature : LabelFeature
            The feature, only used here for logging a failure.
        the_geometry : Point|LineString|Polygon
        the_color : None|str

        Returns
        -------
        canvas_id : int
            The id of the element on the annotation canvas
        the_color : str
            The color of the shape.
        """

        def insert_point():
            # type: () -> Tuple[int, str]
            image_coords = the_geometry.coordinates[:2].tolist()
            # create the shape on the annotate panel
            canvas_id = self.context_panel.canvas.create_new_point((0, 0), **kwargs)
            self.context_panel.canvas.modify_existing_shape_using_image_coords(
                canvas_id, image_coords)
            the_annotate_vector = self.context_panel.canvas.get_vector_object(canvas_id)
            kwargs['color'] = the_annotate_vector.color
            return canvas_id, kwargs['color']

        def insert_line():
            # type: () -> Tuple[int, str]
            image_coords = the_geometry.coordinates[:, :2].flatten().tolist()
            # create the shape on the annotate panel
            canvas_id = self.context_panel.canvas.create_new_line((0, 0, 0, 0), **kwargs)
            self.context_panel.canvas.modify_existing_shape_using_image_coords(
                canvas_id, image_coords)
            the_annotate_vector = self.context_panel.canvas.get_vector_object(canvas_id)
            kwargs['color'] = the_annotate_vector.color
            return canvas_id, kwargs['color']

        def insert_polygon():
            # type: () -> Tuple[int, str]

            # this will only render an outer ring
            image_coords = the_geometry.outer_ring.coordinates[:, :2].flatten().tolist()
            # create the shape on the annotate panel
            canvas_id = self.context_panel.canvas.create_new_polygon((0, 0, 0, 0), **kwargs)
            self.context_panel.canvas.modify_existing_shape_using_image_coords(canvas_id, image_coords)
            the_annotate_vector = self.context_panel.canvas.get_vector_object(canvas_id)
            kwargs['color'] = the_annotate_vector.color
            return canvas_id, kwargs['color']

        kwargs = {'make_current': False}  # type: Dict[str, Any]
        if the_color is not None:
            kwargs = {'color': the_color}

        self._modifying_shapes_on_canvas = True
        if isinstance(the_geometry, Point):
            annotate_shape_id, shape_color = insert_point()
        elif isinstance(the_geometry, LineString):
            annotate_shape_id, shape_color = insert_line()
        elif isinstance(the_geometry, Polygon):
            annotate_shape_id, shape_color = insert_polygon()
        else:
            showinfo(
                'Unhandled Geometry',
                message='LabelFeature id {} has unsupported feature component of type {} which '
                        'will be omitted from display. Any save of the annotation '
                        'will not contain this feature.'.format(feature.uid, type(the_geometry)))
            self._modifying_shapes_on_canvas = False
            return None, None

        self._modifying_shapes_on_canvas = False
        # set up the tracking for the new shapes
        self.variables.append_shape_to_feature_tracking(feature.uid, annotate_shape_id, the_color=shape_color)
        return annotate_shape_id, shape_color

    def _insert_feature_from_file(self, feature):
        """
        This is creating all shapes from the given geometry. This short-circuits
        the event listeners, so must handle all tracking updates itself.

        Parameters
        ----------
        feature : LabelFeature
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
            canvas_id, the_color = self._create_shape_from_geometry(
                feature, geometry, the_color=the_color)
        self._ensure_color_for_shapes(feature.uid)

    def _create_feature_from_shape(self, canvas_id, make_current=True):
        """
        Create a blank annotation from an annotation shape.

        Parameters
        ----------
        canvas_id : int
        make_current : bool

        Returns
        -------
        str
            The id of the newly created annotation feature object.
        """

        # NB: this assumes that the context shape has already been synced from
        # the event listener method

        geometry_object = self._get_geometry_from_shape(canvas_id)
        annotation = LabelFeature(geometry=geometry_object)
        self.variables.file_annotation_collection.add_annotation(annotation)
        self.variables.unsaved_changes = True

        vector_object = self.context_panel.canvas.get_vector_object(canvas_id)
        self.variables.set_feature_tracking(annotation.uid, canvas_id, color=vector_object.color)
        self.label_panel.viewer.rerender_entry(annotation.uid)
        if make_current:
            self.set_current_canvas_id(canvas_id, check_feature=True)
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
        self.label_panel.viewer.rerender_entry(annotation.uid)
        self.variables.unsaved_changes = True

    def _add_shape_to_feature(self, feature_id, canvas_id):
        """
        Add the annotation shape to the given feature. This assumes it's not
        otherwise being tracked as part of another feature.

        Parameters
        ----------
        feature_id : str
        canvas_id : int
        """

        # NB: this assumes that the context shape has already been synced from
        # the event listener method

        # verify feature color is set
        the_color = self.variables.get_color_for_feature(feature_id)
        if the_color is None:
            vector_object = self.context_panel.canvas.get_vector_object(canvas_id)
            the_color = vector_object.color
        # update feature tracking
        self.variables.append_shape_to_feature_tracking(feature_id, canvas_id, the_color=the_color)
        # ensure all shapes for this feature are colored correctly
        self._ensure_color_for_shapes(feature_id)
        # update the entry of our annotation object
        self._update_feature_geometry(feature_id)
        self.variables.unsaved_changes = True
        self.label_panel.viewer.rerender_entry(feature_id)

    def _initialize_geometry(self, annotation_file_name, annotation_collection):
        """
        Initialize the geometry elements from the annotation.

        Parameters
        ----------
        annotation_file_name : str
        annotation_collection : FileLabelCollection

        Returns
        -------
        None
        """

        # set our appropriate variables
        self.variables.annotation_file_name = annotation_file_name
        self.variables.label_schema = annotation_collection.label_schema
        self.variables.file_annotation_collection = annotation_collection
        self.set_current_feature_id(None)

        # dump all the old shapes
        self._modifying_shapes_on_canvas = True
        self.context_panel.canvas.reinitialize_shapes()
        self._modifying_shapes_on_canvas = False

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
        annotation_collection : FileLabelCollection
        """

        self.label_panel.viewer.fill_from_annotation_list(annotation_collection)
        self._initialize_geometry(annotation_fname, annotation_collection)
        self.context_panel.enable_tools()
        self.context_panel.enable_shapes()
        self.variables.unsaved_changes = False

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
        canvas_ids = self.variables.delete_feature_from_tracking(feature_id)
        # delete the shapes - this will also remove from tracking
        for entry in canvas_ids:
            self.context_panel.canvas.delete_shape(entry)
        # delete from the treeview
        self.label_panel.viewer.delete_entry(feature_id)
        self.variables.unsaved_changes = True

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
        self.context_panel.canvas.zoom_to_full_image_selection(zoom_box)

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
    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Labeling Tool"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Labeling Tool, Multiple Files"
        else:
            the_title = "Labeling Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        """
        The tool exit function
        """

        response = self._prompt_unsaved()
        if response:
            self.root.destroy()

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : str|BaseReader|CanvasImageReader
        update_browse : None|str
        """

        if update_browse is not None:
            self._image_browse_directory = update_browse
        elif isinstance(the_reader, string_types):
            self._image_browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, string_types):
            the_reader = ComplexCanvasImageReader(the_reader)

        if isinstance(the_reader, BaseReader):
            if the_reader.reader_type != 'SICD':
                raise ValueError('reader for the aperture tool is expected to be complex')
            the_reader = ComplexCanvasImageReader(the_reader)

        if not isinstance(the_reader, ComplexCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        self.variables.image_reader = the_reader
        self.context_panel.set_image_reader(the_reader)

        self.set_title()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.context_panel.enable_tools()

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
            initialdir=self._image_browse_directory,
            filetypes=nitf_preferred_collection)

        if fname in ['', ()]:
            return

        image_reader = ComplexCanvasImageReader(fname)
        if image_reader.image_count != 1:
            showinfo('Single Image Required',
                     message='The given image reader for file {} has {} distinct images. '
                             'Annotation is only permitted for single image readers. '
                             'Aborting'.format(image_reader.file_name, image_reader.image_count))
            return

        self.update_reader(image_reader, update_browse=os.path.split(fname)[0])

    def create_new_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

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
                initialfile='{}.labels.json'.format(image_fname),
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

        annotation_collection = FileLabelCollection(
            label_schema=label_schema, image_file_name=image_fname)

        self._initialize_annotation_file(annotation_fname, annotation_collection)
        self.variables.file_annotation_collection.to_file(self.variables.annotation_file_name)

    def select_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        browse_dir, image_fname = os.path.split(self.image_file_name)
        # guess at a sensible initial file name
        init_file = '{}.labels.json'.format(image_fname)
        if not os.path.exists(os.path.join(browse_dir, init_file)):
            init_file = ''

        annotation_fname = askopenfilename(
            title='Select annotation file for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile=init_file,
            filetypes=[json_files, all_files])
        if annotation_fname in ['', ()]:
            return

        self.set_existing_annotation_file(annotation_fname)

    def set_existing_annotation_file(self, annotation_fname):
        """
        Try to set the annotation file as an existing file.

        Parameters
        ----------
        annotation_fname : str
            The path to the annotation file.
        """

        _, image_fname = os.path.split(self.image_file_name)
        if not os.path.exists(annotation_fname):
            showinfo('File does not exist', message='Annotation file {} does not exist'.format(annotation_fname))
            return

        try:
            annotation_collection = FileLabelCollection.from_file(annotation_fname)
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
            self.variables.unsaved_changes = False
            return

        self.variables.file_annotation_collection.to_file(self.variables.annotation_file_name)
        self.variables.unsaved_changes = False

    def callback_delete_shape(self):
        """
        Remove the given shape from the current annotation.
        """

        if not self._verify_file_annotation_selected(popup=True):
            return  # nothing to be done

        shape_id = self.variables.current_canvas_id
        feature_id = self.variables.current_feature_id
        if shape_id is None:
            showinfo('No shape is selected', message="No shape is selected.")
            return

        response = askyesnocancel('Confirm deletion?', message='Confirm shape deletion.')
        if response is None or response is False:
            return

        # remove the shape from the given feature tracking
        remaining_shapes = self.variables.remove_annotation_from_feature(shape_id)
        # delete the shape
        self.context_panel.canvas.delete_shape(shape_id)
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
                self.set_current_feature_id(feature_id)

    def callback_delete_feature(self):
        """
        Deletes the currently selected feature.
        """

        if not self._verify_file_annotation_selected(popup=True):
            return  # nothing to be done

        feature_id = self.variables.current_feature_id
        if feature_id is None:
            showinfo('No feature is selected', message="No feature is selected to delete.")
            return

        response = askyesnocancel('Confirm deletion?', message='Confirm shape deletion.')
        if response is None or response is False:
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
        self.label_panel.viewer.rerender_entry(self.variables.current_feature_id)
        popup.destroy()

    def callback_zoom_to_feature(self):
        """
        Handles pressing the zoom to feature button.
        """
        self._verify_file_annotation_selected()

        if self.variables.current_feature_id is None:
            showinfo('No feature is selected', message="Please select the feature to view.")
            return

        self.zoom_to_feature(self.variables.current_feature_id)

    # event listeners
    # noinspection PyUnusedLocal
    def sync_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.my_populate_metaicon()
        # What else should conceptually happen? This is not possible unless
        #  we permit an image with more than a single index.

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

        # if the current_feature is set, ask whether to add, or create new?
        if self.variables.current_feature_id is not None:
            response = askyesno('Add shape to current annotation?',
                                message='Should we add this newly created shape to the '
                                        'current annotation (Yes), or create a new annotation (No)?')
            if response is True:
                self._add_shape_to_feature(self.variables.current_feature_id, event.x)
                return

        _ = self._create_feature_from_shape(event.x)
        self.set_current_canvas_id(event.x, check_feature=True)

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
        feature_id = self.variables.get_feature_for_annotate(event.x)
        self._update_feature_geometry(feature_id)
        self.set_current_canvas_id(event.x, check_feature=True)

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
            self.set_current_canvas_id(None, check_feature=False)

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
        self.set_current_canvas_id(event.x, check_feature=True)
        if self.variables.current_feature_id is not None:
            self.label_panel.viewer.treeview.focus(self.variables.current_feature_id)

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.context_panel.canvas.variables.canvas_image_object is None or \
                self.context_panel.canvas.variables.canvas_image_object.image_reader is None:
            image_reader = None
            the_index = 0
        else:
            image_reader = self.context_panel.canvas.variables.canvas_image_object.image_reader
            the_index = self.context_panel.canvas.get_image_index()
        self.populate_metaicon(image_reader, the_index)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.context_panel.canvas.variables.canvas_image_object is None:
            image_reader = None
        else:
            image_reader = self.context_panel.canvas.variables.canvas_image_object.image_reader
        self.populate_metaviewer(image_reader)

    # noinspection PyUnusedLocal
    def feature_selected_on_viewer(self, event):
        """
        Triggered by a selection or selection change on the

        Parameters
        ----------
        event
            The event.
        """

        old_feature_id = self.variables.current_feature_id

        feature_id = self.label_panel.viewer.treeview.focus()
        if feature_id == old_feature_id:
            return  # nothing needs to be done

        self.set_current_feature_id(feature_id)


def main(reader=None, annotation=None):
    """
    Main method for initializing the tool

    Parameters
    ----------
    reader : None|str|BaseReader|ComplexCanvasImageReader
    annotation : None|str
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = LabelingTool(root)
    if reader is not None:
        app.update_reader(reader)
        if annotation is not None:
            app.set_existing_annotation_file(annotation)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the labeling tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None,
        help='The path to the optional image file for opening.')
    parser.add_argument(
        '-a', '--annotation', metavar='annotation', default=None,
        help='The path to the optional annotation file. '
             'If the image input is not specified, then this has no effect. '
             'If both are specified, then a check will be performed that the '
             'annotation actually applies to the provided image.')
    this_args = parser.parse_args()

    main(reader=this_args.input, annotation=this_args.annotation)
