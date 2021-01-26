# -*- coding: utf-8 -*-
"""
This module provides a tool for creating annotation for a SAR image.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


import logging
import os
from shutil import copyfile
import time
from collections import OrderedDict
from typing import Union, Dict

import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesnocancel, askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename

from sarpy_apps.apps.annotation_tool.schema_editor import select_schema_entry
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes import file_filters

from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.image_canvas import ToolConstants
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor
from tk_builder.panels.image_panel import ImagePanel

from sarpy.compliance import string_types
from sarpy.annotation.schema_processing import LabelSchema
from sarpy.annotation.annotate import FileAnnotationCollection, Annotation, AnnotationMetadata
from sarpy.geometry.geometry_elements import Polygon


##############
# Context Panel Definition

class DashboardButtonPanel(WidgetPanel):
    """
    Button panel for context dashboard
    """

    _widget_list = ("pan", "select", "move_rect")

    pan = widget_descriptors.ButtonDescriptor("pan")  # type: basic_widgets.Button
    select = widget_descriptors.ButtonDescriptor("select")  # type: basic_widgets.Button
    move_rect = widget_descriptors.ButtonDescriptor("move_rect")  # type: basic_widgets.Button

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_horizontal_layout()


class ContextMasterDash(WidgetPanel):
    """
    Context dashboard
    """
    _widget_list = ("buttons",)
    buttons = widget_descriptors.PanelDescriptor("buttons", DashboardButtonPanel)  # type: DashboardButtonPanel

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_basic_widget_list(3, [1, 1, 2])


class ContextButtons(WidgetPanel):
    """
    Button panel for context panel.
    """

    _widget_list = ("select_area", "edit_selection")
    select_area = widget_descriptors.ButtonDescriptor("select_area")  # type: basic_widgets.Button
    edit_selection = widget_descriptors.ButtonDescriptor("edit_selection")  # type: basic_widgets.Button

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_horizontal_layout()


class ContextImagePanel(WidgetPanel):
    """
    Context panel.
    """
    _widget_list = ("buttons", "image_panel")
    buttons = widget_descriptors.PanelDescriptor("buttons", ContextButtons)  # type: ContextButtons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, master):
        WidgetPanel.__init__(self, master)
        self.init_w_vertical_layout()


#############
# Annotation Panel Definition

class AnnotationButtons(WidgetPanel):
    _widget_list = ("draw_polygon", "edit_polygon", "select_closest", "delete", "annotate")
    draw_polygon = widget_descriptors.ButtonDescriptor("draw_polygon")  # type: basic_widgets.Button
    edit_polygon = widget_descriptors.ButtonDescriptor("edit_polygon")  # type: basic_widgets.Button
    select_closest = widget_descriptors.ButtonDescriptor("select_closest")  # type: basic_widgets.Button
    delete = widget_descriptors.ButtonDescriptor("delete")  # type: basic_widgets.Button
    annotate = widget_descriptors.ButtonDescriptor("annotate")  # type: basic_widgets.Button

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


##############
# Annotation Popup

class AnnotationPopup(WidgetPanel):
    _widget_list = (
        ("object_type_label", "object_type"),
        ("comment_label", "comment"),
        ("confidence_label", "confidence"),
        ("reset", "submit"))
    object_type = widget_descriptors.EntryDescriptor(
        "object_type", default_text='')  # type: basic_widgets.Entry
    reset = widget_descriptors.ButtonDescriptor(
        "reset", default_text='Reset')  # type: basic_widgets.Button
    submit = widget_descriptors.ButtonDescriptor(
        "submit", default_text='Submit')  # type: basic_widgets.Button
    comment = widget_descriptors.EntryDescriptor(
        "comment", default_text='')  # type: basic_widgets.Entry
    confidence = widget_descriptors.ComboboxDescriptor(
        "confidence", default_text='')  # type: basic_widgets.Combobox

    object_type_label = widget_descriptors.LabelDescriptor(
        "object_type_label", default_text='Object Type:')  # type: basic_widgets.Label
    comment_label = widget_descriptors.LabelDescriptor(
        "comment_label", default_text='Comment:')  # type: basic_widgets.Label
    confidence_label = widget_descriptors.LabelDescriptor(
        "confidence_label", default_text='Confidence:')  # type: basic_widgets.Label

    def __init__(self, master, main_app_variables):
        """

        Parameters
        ----------
        master
            The app master.
        main_app_variables : AppVariables
        """

        self.label_schema = main_app_variables.label_schema
        self.main_app_variables = main_app_variables

        self.master = master
        self.primary_frame = basic_widgets.Frame(master)
        WidgetPanel.__init__(self, self.primary_frame)

        self.init_w_rows()

        self.set_text("Annotate")

        # set up base types for initial dropdown menu
        self.setup_confidence_selections()

        self.primary_frame.pack()

        # set up callbacks
        self.object_type.config(validate='focusin', validatecommand=self.select_object_type)
        self.reset.config(command=self.callback_reset)
        self.submit.config(command=self.callback_submit)

        # get the current annotation
        current_id = self.main_app_variables.current_feature_id
        self.annotation = self.main_app_variables.file_annotation_collection.annotations[current_id]

        # populate existing fields if editing an existing geometry
        if self.annotation.properties:
            object_type = self.annotation.properties.elements[0].label_id
            comment = self.annotation.properties.elements[0].comment
            confidence = self.annotation.properties.elements[0].confidence

            self.object_type.set_text(object_type)
            self.object_type.configure(state="disabled")
            self.comment.set_text(comment)
            self.confidence.set(confidence)
        else:
            self.object_type.set_text("")
            self.comment.set_text("")
            self.confidence.set("")

    def select_object_type(self):
        current_value = self.object_type.get()
        value = select_schema_entry(self.label_schema, start_id=current_value)
        self.object_type.set_text(value)

    def callback_reset(self):
        self.object_type.configure(state="normal")

    def callback_submit(self):
        # TODO: review this
        if self.object_type.get() == '':
            showinfo("Select Object Type", message="Select the object type")
            return

        if self.confidence.get() not in self.main_app_variables.label_schema.confidence_values:
            result = askyesno("Confidence Selection?", message="The confidence selected in not one of the permitted values. Continue?")
            if not (result is True):
                return

        annotation_metadata = AnnotationMetadata(comment=self.comment.get(),
                                                 label_id=self.object_type.get(),
                                                 confidence=self.confidence.get())
        self.annotation.add_annotation_metadata(annotation_metadata)
        # save the annotation file automatically now?
        self.main_app_variables.file_annotation_collection.to_file(self.main_app_variables.annotation_file_name)
        self.master.destroy()

    def setup_confidence_selections(self):
        self.confidence.update_combobox_values(self.main_app_variables.label_schema.confidence_values)


#########
# Main Annotation Tool

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
    new_annotation = BooleanDescriptor(
        'new_annotation', default_value=False,
        docstring='The state variable for whether a new annotation has been '
                  'created.')  # type: bool

    def __init__(self):
        self._feature_id_dict = OrderedDict()
        self._annotate_id_dict = OrderedDict()
        self._context_id_dict = OrderedDict()
        self._current_annotate_canvas_id = None
        self._current_feature_id = ''

    @property
    def feature_id_dict(self):
        # type: () -> Dict[str, Dict]
        """
        dict: The dictionary of feature_id to corresponding canvas ids.
        """

        return self._feature_id_dict

    @property
    def annotate_id_dict(self):
        # type: () -> Dict[str, str]
        """
        dict: The dictionary of annotate canvas id to feature_id.
        """

        return self._annotate_id_dict

    @property
    def context_id_dict(self):
        # type: () -> Dict[str, str]
        """
        dict: The dictionary of context canvas id to feature_id.
        """

        return self._context_id_dict

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
            self._current_feature_id = self._annotate_id_dict.get(value, None)

    @property
    def current_feature_id(self):
        """
        None|str: The current feature id.
        """

        return self._current_feature_id

    @staticmethod
    def _add_canvas_dict(feature_id, canvas_id, canvas_dict):
        """
        Add the entries to the appropriate canvas id dictionary.

        Parameters
        ----------
        feature_id : str
        canvas_id : None|str|List[str]
        canvas_dict : dict

        Returns
        -------
        None
        """

        # populate annotate_id_dict
        if canvas_id is None:
            pass
        elif isinstance(canvas_id, (tuple, list)):
            for entry in canvas_id:
                canvas_dict[entry] = feature_id
        else:
            if not isinstance(canvas_id, string_types):
                logging.warning(
                    'For feature_id {}, got unexpected canvas id type {}. '
                    'This may results in unexpected errors.'.format(feature_id, type(canvas_id)))
            canvas_dict[canvas_id] = feature_id

    @staticmethod
    def _delete_canvas_dict(canvas_id, canvas_dict):
        """
        Delete the entries from the appropriate canvas id dictionary.

        Parameters
        ----------
        canvas_id : None|str|List[str]
        canvas_dict : dict

        Returns
        -------
        None
        """

        # populate annotate_id_dict
        if canvas_id is None:
            pass
        elif isinstance(canvas_id, (tuple, list)):
            for entry in canvas_id:
                if entry in canvas_dict:
                    del canvas_dict[entry]
        else:
            if canvas_id in canvas_dict:
                del canvas_dict[canvas_id]

    def _update_canvas_dict(self, feature_id, old_canvas_id, new_canvas_id, canvas_dict):
        """
        Update the provided canvas dict.

        Parameters
        ----------
        feature_id : str
        old_canvas_id : None|str|List[str]
        new_canvas_id : None|str|List[str]
        canvas_dict : dict

        Returns
        -------
        None
        """

        self._delete_canvas_dict(old_canvas_id, canvas_dict)
        self._add_canvas_dict(feature_id, new_canvas_id, canvas_dict)

    def add_feature_tracking(self, feature_id, annotate_id, context_id=None):
        """
        Add tracking for new feature.

        Parameters
        ----------
        feature_id : str
        annotate_id : str|List[str]
        context_id : None|str|List[str]

        Returns
        -------
        None
        """

        if feature_id in self._feature_id_dict:
            logging.error('The feature_id {} is already being tracked.'.format(feature_id))
            return

        # populate the feature_id_dict
        self._feature_id_dict[feature_id] = OrderedDict([('annotate_id', annotate_id), ('context_id', context_id)])

        # populate annotate_id_dict
        self._add_canvas_dict(feature_id, annotate_id, self._annotate_id_dict)
        # populate context_id_dict
        self._add_canvas_dict(feature_id, context_id, self._context_id_dict)

    def update_feature_tracking(self, feature_id, annotate_id=None, context_id=None):
        """
        Update the feature tracking.

        Parameters
        ----------
        feature_id : str
        annotate_id : None|str|List[str]
        context_id : None|str|List[str]

        Returns
        -------
        None
        """

        if feature_id not in self._feature_id_dict:
            pass

        the_entry = self._feature_id_dict[feature_id]
        # update the annotate_id tracking
        if annotate_id is not None and annotate_id != the_entry['annotate_id']:
            self._update_canvas_dict(feature_id, the_entry['annotate_id'], annotate_id, self._annotate_id_dict)
        # update the context_id tracking
        if context_id is not None and context_id != the_entry['context_id']:
            self._update_canvas_dict(feature_id, the_entry['context_id'], context_id, self._context_id_dict)

    def reinitialize_features(self):
        """
        Reinitialize the feature tracking dictionaries. NOte that this assumes that
        the context and annotate canvases have been reinitialized elsewhere.

        Returns
        -------
        None
        """

        self._feature_id_dict = OrderedDict()
        self._annotate_id_dict = OrderedDict()
        self._context_id_dict = OrderedDict()
        self._current_annotate_canvas_id = None


class AnnotationTool(WidgetPanel):
    _widget_list = ("context_panel", "annotate_panel")
    context_panel = widget_descriptors.PanelDescriptor(
        "context_panel", ContextImagePanel,
        docstring='The overall image panel.')  # type: ContextImagePanel
    annotate_panel = widget_descriptors.PanelDescriptor(
        "annotate_panel", AnnotateImagePanel,
        docstring='The detail panel for crafting annotations.')  # type: AnnotateImagePanel

    def __init__(self, primary):
        self._schema_browse_directory = os.path.expanduser('~')
        self._image_browse_directory = os.path.expanduser('~')
        self.primary = basic_widgets.Frame(primary)
        # temporary state variables
        self._modifying_context_selection = False
        self._modifying_annotate_tool = False

        WidgetPanel.__init__(self, self.primary)

        self.init_w_horizontal_layout()
        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.variables = AppVariables()

        self.metaicon_popup_panel = tkinter.Toplevel(self.primary)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)
        self.metaicon_popup_panel.withdraw()

        self.metaviewer_popup_panel = tkinter.Toplevel(self.primary)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)
        self.metaviewer_popup_panel.withdraw()

        menubar = tkinter.Menu()

        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.select_image_file)
        filemenu.add_command(label="Create New Annotation", command=self.create_new_annotation_file)
        filemenu.add_command(label="Open Annotation", command=self.select_annotation_file)
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

        self.context_panel.pack(expand=True, fill=tkinter.BOTH)
        self.context_panel.buttons.fill_y(False)
        self.context_panel.buttons.do_not_expand()
        self.context_panel.buttons.pack(side="bottom")
        self.context_panel.image_panel.canvas.set_canvas_size(400, 300)

        self.annotate_panel.buttons.fill_y(False)
        self.annotate_panel.buttons.do_not_expand()
        self.annotate_panel.buttons.pack(side="bottom")
        self.annotate_panel.pack(expand=True, fill=tkinter.BOTH)
        self.annotate_panel.image_panel.canvas.set_canvas_size(400, 300)

        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        primary.config(menu=menubar)

        # hide unwanted elements on the panel toolbars
        self.context_panel.set_text('')
        self.context_panel.image_panel.set_text('The contextual area.')
        self.context_panel.image_panel.hide_tools('shape_drawing')
        self.context_panel.image_panel.hide_shapes()
        self.context_panel.image_panel.hide_select_index()
        # disable tools until an image is selected
        self.context_panel.image_panel.disable_tools()

        self.annotate_panel.set_text('')
        self.annotate_panel.image_panel.set_text('The annotation area.')
        self.annotate_panel.image_panel.hide_tools('select')
        self.annotate_panel.image_panel.hide_shapes(['point', 'line', 'arrow', 'text'])
        self.annotate_panel.image_panel.hide_remap_combo()
        self.annotate_panel.image_panel.hide_select_index()
        # disable tools and shapes until a file annotation is selected
        self.annotate_panel.image_panel.disable_tools()
        self.annotate_panel.image_panel.disable_shapes()

        # TODO: these should all be defunct, and functionality replaced in listeners below
        self.annotate_panel.image_panel.canvas.on_right_mouse_click(self.callback_annotate_handle_right_mouse_click)

        self.annotate_panel.buttons.draw_polygon.config(command=self.callback_set_to_draw_polygon)
        self.annotate_panel.buttons.annotate.config(command=self.callback_annotation_popup)
        self.annotate_panel.buttons.edit_polygon.config(command=self.callback_set_to_edit_shape)
        self.annotate_panel.buttons.delete.config(command=self.callback_delete_shape)
        # END DEFUNCT

        # set up context panel event listeners
        self.context_panel.image_panel.canvas.bind('<<SelectionFinalized>>', self._sync_context_selection_to_annotate_zoom)
        self.context_panel.image_panel.canvas.bind('<<RemapChanged>>', self._sync_remap_change)

        # set up annotate panel listeners
        self.annotate_panel.image_panel.canvas.bind('<<CurrentToolChanged>>', self._verify_setting_annotate_tool)
        self.annotate_panel.image_panel.canvas.bind('<<ImageExtentChanged>>', self._sync_annotate_zoom_to_context_selection)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeCreate>>', self._shape_create_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeCoordsFinalized>>', self._shape_finalized_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeDelete>>', self._shape_delete_on_annotate)
        self.annotate_panel.image_panel.canvas.bind('<<ShapeSelect>>', self._shape_selected_on_annotate)

        # TODO: set up event listeners for the image panels
        #   X - 1.) Change in selection on context should change view in annotate
        #   X - 2.) Change in image extent on annotate should change selection in context
        #       Make sure that 1.) and 2.) don't get stuck in a loop, since one will
        #       trigger the other.
        #   3.) Creation/editing of shape in annotate is synced to context. "<<ShapeCreate>>", "<<ShapeCoordsFinalized>>"
        #   4.) Deletion of shape in annotate performs deletion of corresponding
        #       shape in context and deletes or edits the annotation. "<<ShapeDelete>>"
        #   5.) Selection of shape in annotate selects annotation. "<<ShapeSelect>>"

    @property
    def image_file_name(self):
        """
        None|str: The image file name.
        """

        return self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader.file_name

    # utility functions
    ####
    def insert_feature(self, feature, annotate_canvas_id=None):
        """
        Insert a new feature into the tracking.

        Parameters
        ----------
        feature : Annotation
        annotate_canvas_id : None|str|List[str]
            Rendered on annotate canvas if None.

        Returns
        -------
        None
        """

        def insert_polygon(uid, annotate_id, the_geometry):
            # type: (str, Union[None, str], Polygon) -> None
            if annotate_id is None:
                # create the shape on the annotation panel
                # this will only render an outer ring
                image_coords = the_geometry.outer_ring.coordinates.flatten()
                annotate_id = self.annotate_panel.image_panel.canvas.create_new_polygon((0, 0, 0, 0))
                # TODO: we may have to modify drawing state?
                self.annotate_panel.image_panel.canvas.modify_existing_shape_using_image_coords(annotate_canvas_id, image_coords)

                # TODO: shapes on the context_panel too...
            self.variables.add_feature_tracking(uid, annotate_id, context_id=None)

        geometry = feature.geometry
        if isinstance(geometry, Polygon):
            insert_polygon(feature.uid, annotate_canvas_id, geometry)
        else:
            showinfo(
                'Unhandled Geometry',
                message='Annotation id {} has unsupported feature type {} which '
                        'will be omitted from display. Any save of the annotation '
                        'will not contain this feature.'.format(feature.uid, type(geometry)))
        # TODO: re-render treeview of the features?

    def initialize_geometry(self, annotation_file_name, annotation_collection):
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

        # dump all the old shapes
        self.annotate_panel.image_panel.canvas.reinitialize_shapes()
        self.context_panel.image_panel.canvas.reinitialize_shapes()

        # reinitialize dictionary relating canvas shapes and annotation shapes
        self.variables.reinitialize_features()

        # populate all the shapes
        if annotation_collection.annotations is not None:
            for feature in annotation_collection.annotations.features:
                self.insert_feature(feature)

        # redraw all the shapes on the annotation panel
        self.annotate_panel.image_panel.canvas.redraw_all_shapes()
        # TODO: redraw all shapes on the context_panel

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

    def metaviewer_popup(self):
        """
        Pops up the metadata viewer.
        """

        self.metaviewer_popup_panel.deiconify()

    def metaicon_popup(self):
        """
        Pops up the metaicon viewer.
        """

        self.metaicon_popup_panel.deiconify()

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
            filetypes=file_filters.nitf_preferred_collection)

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

        self.context_panel.image_panel.set_image_reader(image_reader)
        self.annotate_panel.image_panel.set_image_reader(image_reader)
        self.metaicon.create_from_reader(image_reader.base_reader, index=0)
        self.metaviewer.populate_from_reader(image_reader.base_reader)
        self.context_panel.image_panel.enable_tools()

    def _initialize_annotation_file(self, annotation_fname, annotation_collection):
        """
        The final initialization steps for the annotation file.

        Parameters
        ----------
        annotation_fname : str
        annotation_collection : FileAnnotationCollection
        """

        self.initialize_geometry(annotation_fname, annotation_collection)
        self.annotate_panel.image_panel.enable_tools()
        self.annotate_panel.image_panel.enable_shapes()
        self.variables.unsaved_changed = False

    def create_new_annotation_file(self):
        # TODO: verify functionality
        if not self._verify_image_selected():
            return

        # TODO: prompt for any unsaved changes

        schema_fname = askopenfilename(
            title='Select label schema',
            initialdir=self._schema_browse_directory,
            filetypes=[file_filters.json_files, file_filters.all_files])
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
                filetypes=[file_filters.json_files, file_filters.all_files])
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
            filetypes=[file_filters.json_files, file_filters.all_files])
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

        if self.variables.unsaved_changed:
            self.variables.file_annotation_collection.to_file(self.variables.annotation_file_name)
        self.variables.unsaved_changed = False

    # event listeners
    #####
    # noinspection PyUnusedLocal
    def _sync_remap_change(self, event):
        """
        Sync changing the remap value from the context panel to the
        annotate panel.

        Parameters
        ----------
        event
        """

        self.annotate_panel.image_panel.canvas.update_current_image()

    # noinspection PyUnusedLocal
    def _verify_setting_annotate_tool(self, event):
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

        # TODO: what dependencies on annotation state here?

    # noinspection PyUnusedLocal
    def _sync_context_selection_to_annotate_zoom(self, event):
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
            self._sync_annotate_zoom_to_context_selection(None)
        else:
            self.annotate_panel.image_panel.canvas.zoom_to_full_image_selection(image_rect)
            # NB: this triggers a call to the _sync_annotate_zoom_to_context_selection()
            # THis in turns will adjust the context selection box to account for differences
            # in aspect ratio of the selection rectangle and annotate canvas.
            #
            # That adjust will lead to this function being called again. We avoid
            # an infinite recursive loop, by stopping it here. The return call here
            # must do nothing.
        self._modifying_context_selection = False

    # noinspection PyUnusedLocal
    def _sync_annotate_zoom_to_context_selection(self, event):
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

        # print('image_rectangle', image_rectangle, 'decimation', decimation, 'y_side', y_side, 'x_side', x_side)
        # print('anchor', self.context_panel.image_panel.canvas.variables.canvas_image_object.canvas_coords_to_full_image_yx(
        #     self.context_panel.image_panel.canvas.variables.shape_drawing.anchor_point_xy),
        #       'tmp_anchor', self.context_panel.image_panel.canvas.variables.canvas_image_object.canvas_coords_to_full_image_yx(
        #         self.context_panel.image_panel.canvas.variables.shape_drawing.tmp_anchor_point_xy))

        if y_side >= 0.9*full_y and x_side >= 0.9*full_x:
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(rect_id, (0, 0, 0, 0))
        else:
            self.context_panel.image_panel.canvas.modify_existing_shape_using_image_coords(rect_id, image_rectangle)
            self.context_panel.image_panel.canvas.show_shape(rect_id)  # just in case we got caught in a bad state

        # # TODO: we may have to reset drawing state?
        # if self.context_panel.image_panel.canvas.current_tool == ToolConstants.SELECT:
        #     self.context_panel.image_panel.canvas.variables.shape_drawing.set_inactive()

    def _shape_create_on_annotate(self, event):
        """
        Handles the event that a shape has been created on the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # we may need a temporary state variable to avoid unnecessary recursion

        # TODO: what to do here?
        pass

    def _shape_finalized_on_annotate(self, event):
        """
        Handles the event that a shapes coordinates have been (possibly temporarily)
        finalized (i.e. certainly not dragged).

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # we may need a temporary state variable to avoid unnecessary recursion

        # TODO: what to do here?
        pass

    def _shape_delete_on_annotate(self, event):
        """
        Handles the event that a shape has been deleted from the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # we may need a temporary state variable to avoid unnecessary recursion

        # TODO: what to do here?
        pass

    def _shape_selected_on_annotate(self, event):
        """
        Handles the event that a shape has been selected on the annotate panel.

        Parameters
        ----------
        event
            Through abuse of object, event.x is the shape id (int) and event.y is
            the shape type (int) enum value.
        """

        # we may need a temporary state variable to avoid unnecessary recursion

        # TODO: what to do here?
        pass

    # DEFUNCT context callbacks
    def callback_annotate_handle_right_mouse_click(self, event):
        # TODO: this is definitely stupid
        self.annotate_panel.image_panel.canvas.callback_handle_right_mouse_click(event)

        # if self.annotate_panel.image_panel.canvas.current_tool == ToolConstants.EDIT_SHAPE:
        #     # craft the polygon
        #     current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        #     image_coords = self.annotate_panel.image_panel.canvas.get_shape_image_coords(current_canvas_shape_id)
        #     geometry_coords = numpy.asarray([x for x in zip(image_coords[0::2], image_coords[1::2])])
        #     polygon = Polygon(coordinates=[geometry_coords, ])
        #     # create the annotation and add to the list
        #     annotation = Annotation(geometry=polygon)
        #     self.variables.file_annotation_collection.add_annotation(annotation)
        #     # handle the feature tracking
        #     self.insert_feature(annotation, annotate_canvas_id=current_canvas_shape_id)

    def callback_set_to_draw_polygon(self):
        # TODO: this should replaced with a listening function for resetting shape
        self._verify_file_annotation_selected()
        self.annotate_panel.image_panel.canvas.variables.current_shape_id = None
        self.annotate_panel.image_panel.canvas.set_current_tool_to_draw_polygon()

    def callback_set_to_edit_shape(self):
        # TODO: this should replaced with a listening function for resetting shape
        self._verify_file_annotation_selected()
        self.annotate_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_delete_shape(self):
        # TODO: verify this functionality...
        self._verify_file_annotation_selected()
        current_geom_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_geom_id is None or \
                current_geom_id in self.annotate_panel.image_panel.canvas.get_tool_shape_ids():
            showinfo('No Shape Selected', message='No shape is currently selected.')
            return

        # find the associated feature
        feature_id = self.variables.current_feature_id
        if feature_id == '':
            # no associated feature, so just delete from canvas
            self.annotate_panel.image_panel.canvas.delete_shape(current_geom_id)
        else:
            # find all shapes on both canvases and delete
            entries = self.variables.feature_id_dict.get(feature_id, None)
            if entries is None:
                showinfo(
                    'Bad State',
                    message='The selected feature id and feature_id_dict are out of sync. '
                            'This is an unexpected failure.')
                return

            annotate_entry = entries.get('annotate_id', None)
            if annotate_entry is None or annotate_entry == '':
                pass
            elif isinstance(annotate_entry, string_types):
                if annotate_entry != current_geom_id:
                    showinfo(
                        'Shape ID mismatch',
                        message='The selected shape and selected feature id are unexpectedly '
                                'out of sync. Proceeding to the best of our ability.')
                self.annotate_panel.image_panel.canvas.delete_shape(annotate_entry)
            elif isinstance(annotate_entry, (tuple, list)):
                for entry in annotate_entry:
                    self.annotate_panel.image_panel.canvas.delete_shape(entry)
            else:
                raise TypeError('Unhandled type {}'.format(type(annotate_entry)))

            context_entry = entries.get('context_id', None)
            if context_entry is None or context_entry == '':
                pass
            elif isinstance(context_entry, string_types):
                self.context_panel.image_panel.canvas.delete_shape(context_entry)
            elif isinstance(context_entry, (tuple, list)):
                for entry in context_entry:
                    self.context_panel.image_panel.canvas.delete_shape(entry)
            else:
                raise TypeError('Unhandled type {}'.format(type(context_entry)))

            # now, delete the feature
            del self.variables.file_annotation_collection.annotations[feature_id]
            # TODO: sync any display of the feature list?

    def callback_annotation_popup(self):
        # TODO: what is the correct workflow here?
        self._verify_file_annotation_selected()

        current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_canvas_shape_id is None:
            showinfo('No shape selected', message='Please draw/select a shape feature first.')
            return

        popup = tkinter.Toplevel(self.master)
        self.variables.current_annotate_canvas_id = current_canvas_shape_id
        AnnotationPopup(popup, self.variables)


def main():
    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('clam')

    # noinspection PyUnusedLocal
    app = AnnotationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
