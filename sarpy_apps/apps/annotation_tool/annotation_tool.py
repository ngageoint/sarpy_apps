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
from tkinter.messagebox import showinfo, askyesnocancel, askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename

import numpy

from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes import file_filters
from sarpy_apps.apps.annotation_tool.schema_editor import select_schema_entry

from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.image_canvas import ToolConstants
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor
from tk_builder.widgets.axes_image_canvas import AxesImageCanvas
from tk_builder.panels.image_panel import ImagePanel

from sarpy.compliance import string_types
from sarpy.annotation.schema_processing import LabelSchema
from sarpy.annotation.annotate import FileAnnotationCollection, Annotation, AnnotationMetadata
from sarpy.geometry.geometry_elements import Polygon


##############
# Context Panel Definition

class DashboardButtonPanel(WidgetPanel):
    """
    Button panle for context dashboard
    """

    _widget_list = ("pan", "select", "move_rect")

    pan = widget_descriptors.ButtonDescriptor("pan")  # type: basic_widgets.Button
    select = widget_descriptors.ButtonDescriptor("select")  # type: basic_widgets.Button
    move_rect = widget_descriptors.ButtonDescriptor("move_rect")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ContextMasterDash(WidgetPanel):
    """
    Context dashboard
    """
    _widget_list = ("buttons",)
    buttons = widget_descriptors.PanelDescriptor("buttons", DashboardButtonPanel)  # type: DashboardButtonPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_basic_widget_list(3, [1, 1, 2])


class ContextButtons(WidgetPanel):
    """
    Button panel for context panel.
    """

    _widget_list = ("select_area", "edit_selection")
    select_area = widget_descriptors.ButtonDescriptor("select_area")  # type: basic_widgets.Button
    edit_selection = widget_descriptors.ButtonDescriptor("edit_selection")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ContextImagePanel(WidgetPanel):
    """
    Context panel.
    """
    _widget_list = ("buttons", "image_panel")
    buttons = widget_descriptors.PanelDescriptor("buttons", ContextButtons)  # type: ContextButtons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
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

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class AnnotateImagePanel(WidgetPanel):
    _widget_list = ("buttons", "image_panel")
    buttons = widget_descriptors.PanelDescriptor("buttons", AnnotationButtons)   # type: AnnotationButtons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, parent):
        # set the master frame
        WidgetPanel.__init__(self, parent)
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

    def __init__(self, parent, main_app_variables):
        """

        Parameters
        ----------
        parent
            The app parent.
        main_app_variables : AppVariables
        """

        self.label_schema = main_app_variables.label_schema
        self.main_app_variables = main_app_variables

        self.parent = parent
        self.primary_frame = tkinter.Frame(parent)
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
        self.parent.destroy()

    def setup_confidence_selections(self):
        self.confidence.update_combobox_values(self.main_app_variables.label_schema.confidence_values)


#########
# Main Annotation Tool

class AppVariables(object):
    """
    The main application variables for the annotation panel.
    """
    label_schema = TypedDescriptor(
        'label_schema', LabelSchema,
        docstring='The label schema object.')  # type: LabelSchema
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileAnnotationCollection,
        docstring='The file annotation collection.')  # type: FileAnnotationCollection
    annotation_file_name = StringDescriptor(
        'annotation_file_name',
        docstring='The path for the annotation results file.')  # type: str
    annotate_canvas = TypedDescriptor(
        'annotate_canvas', AxesImageCanvas,
        docstring='The image canvas panel for the annotation.')  # type: AxesImageCanvas
    context_canvas = TypedDescriptor(
        'context_canvas', AxesImageCanvas,
        docstring='The image canvas panel for the context.')  # type: AxesImageCanvas
    new_annotation = BooleanDescriptor(
        'new_annotation', default_value=False,
        docstring='The state variable for whether a new annotation has been '
                  'created.')  # type: bool

    def __init__(self):
        self._feature_id_dict = OrderedDict()
        self._annotate_id_dict = OrderedDict()
        self._context_id_dict = OrderedDict()
        self._current_annotate_canvas_id = ''
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
        str: The current annotation feature id.
        """

        return self._current_annotate_canvas_id

    @current_annotate_canvas_id.setter
    def current_annotate_canvas_id(self, value):
        if value is None or value.strip() == '':
            self._current_annotate_canvas_id = ''
            self._current_feature_id = ''
        else:
            self._current_annotate_canvas_id = value
            self._current_feature_id = self._annotate_id_dict.get(value, '')

    @property
    def current_feature_id(self):
        """
        str: The current feature id.
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
        self._current_annotate_canvas_id = ''


class AnnotationTool(WidgetPanel):
    _widget_list = ("context_panel", "annotate_panel")
    context_panel = widget_descriptors.PanelDescriptor("context_panel", ContextImagePanel)  # type: ContextImagePanel
    annotate_panel = widget_descriptors.PanelDescriptor("annotate_panel", AnnotateImagePanel)  # type: AnnotateImagePanel

    def __init__(self, primary):
        self._schema_browse_directory = os.path.expanduser('~')
        self._image_browse_directory = os.path.expanduser('~')
        self.primary = tkinter.Frame(primary)

        WidgetPanel.__init__(self, self.primary)  # TODO: primary or self.primary?

        self.init_w_horizontal_layout()
        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.variables = AppVariables()

        self.context_panel.buttons.select_area.config(command=self.callback_context_set_to_select)
        self.context_panel.buttons.edit_selection.config(command=self.callback_context_set_to_edit_selection)

        self.context_panel.image_panel.canvas.on_left_mouse_release(self.callback_context_handle_left_mouse_release)

        # set up annotate panel event listeners
        self.annotate_panel.image_panel.canvas.on_mouse_wheel(self.callback_handle_annotate_mouse_wheel)
        self.annotate_panel.image_panel.canvas.on_left_mouse_click(self.callback_annotate_handle_canvas_left_mouse_click)
        self.annotate_panel.image_panel.canvas.on_left_mouse_release(self.callback_annotate_handle_left_mouse_release)
        self.annotate_panel.image_panel.canvas.on_right_mouse_click(self.callback_annotate_handle_right_mouse_click)

        self.annotate_panel.buttons.draw_polygon.config(command=self.callback_set_to_draw_polygon)
        self.annotate_panel.buttons.annotate.config(command=self.callback_annotation_popup)
        self.annotate_panel.buttons.select_closest.config(command=self.callback_set_to_select_closest_shape)
        self.annotate_panel.buttons.edit_polygon.config(command=self.callback_set_to_edit_shape)
        self.annotate_panel.buttons.delete.config(command=self.callback_delete_shape)

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
        filemenu.add_command(label="Exit", command=self.exit)

        # create more pulldown menus
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Popups", menu=popups_menu)

        self.context_panel.buttons.fill_y(False)
        self.context_panel.buttons.do_not_expand()
        self.context_panel.buttons.pack(side="bottom")
        self.annotate_panel.buttons.fill_y(False)
        self.annotate_panel.buttons.do_not_expand()
        self.annotate_panel.buttons.pack(side="bottom")

        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.context_panel.image_panel.resizeable = True
        self.annotate_panel.image_panel.resizeable = True
        # self.context_panel.pack(expand=True, fill=tkinter.BOTH)
        # self.annotate_panel.pack(expand=True, fill=tkinter.BOTH)

        primary.config(menu=menubar)

    def exit(self):
        self.quit()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.deiconify()

    def metaicon_popup(self):
        self.metaicon_popup_panel.deiconify()

    @property
    def image_file_name(self):
        """
        None|str: The image file name.
        """

        return self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader.file_name

    # context callbacks
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
            filetypes=file_filters.nitf_preferred_filter)

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

    def create_new_annotation_file(self):
        if self.image_file_name is None:
            showinfo('No Image Selected', message='First select an image file for annotation.')
            return

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
        self.initialize_geometry(annotation_fname, annotation_collection)

    def select_annotation_file(self):
        if self.image_file_name is None:
            showinfo('No Image Selected', message='First select an image file for annotation.')
            return

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
        # initialize the geometry
        self.initialize_geometry(annotation_fname, annotation_collection)

    def callback_context_set_to_select(self):
        self.context_panel.image_panel.canvas.set_current_tool_to_selection_tool()

    def callback_context_set_to_edit_selection(self):
        self.context_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_context_handle_left_mouse_release(self, event):
        self.context_panel.image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.context_panel.image_panel.canvas.variables.current_tool == ToolConstants.SELECT_TOOL or \
           self.context_panel.image_panel.canvas.variables.current_tool == ToolConstants.TRANSLATE_SHAPE_TOOL:
            rect_id = self.context_panel.image_panel.canvas.variables.select_rect.uid
            image_rect = self.context_panel.image_panel.canvas.get_shape_image_coords(rect_id)
            annotate_zoom_rect = self.annotate_panel.image_panel.canvas.variables.canvas_image_object.full_image_yx_to_canvas_coords(
                image_rect)
            self.annotate_panel.image_panel.canvas.zoom_to_canvas_selection(annotate_zoom_rect, animate=True)

    # annotate callbacks
    def callback_set_to_select_closest_shape(self):
        self.annotate_panel.image_panel.canvas.set_current_tool_to_select_closest_shape()

    def callback_annotate_handle_left_mouse_release(self, event):
        self.annotate_panel.image_panel.canvas.callback_handle_left_mouse_release(event)

    def callback_annotate_handle_canvas_left_mouse_click(self, event):
        self.annotate_panel.image_panel.canvas.callback_handle_left_mouse_click(event)
        # current_shape = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        # self.annotate_panel.image_panel.canvas.variables.current_shape_id = current_shape
        # self.annotate_panel.image_panel.canvas.callback_handle_left_mouse_click(event)

    def callback_annotate_handle_right_mouse_click(self, event):
        self.annotate_panel.image_panel.canvas.callback_handle_right_mouse_click(event)
        # TODO: should this be happening by overriding the canvas methods?
        if self.annotate_panel.image_panel.canvas.variables.current_tool == ToolConstants.DRAW_POLYGON_BY_CLICKING:
            # craft the polygon
            current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
            image_coords = self.annotate_panel.image_panel.canvas.get_shape_image_coords(current_canvas_shape_id)
            geometry_coords = numpy.asarray([x for x in zip(image_coords[0::2], image_coords[1::2])])
            polygon = Polygon(coordinates=[geometry_coords, ])
            # create the annotation and add to the list
            annotation = Annotation(geometry=polygon)
            self.variables.file_annotation_collection.add_annotation(annotation)
            # handle the feature tracking
            self.insert_feature(annotation, annotate_canvas_id=current_canvas_shape_id)

    def callback_set_to_draw_polygon(self):
        self.annotate_panel.image_panel.canvas.variables.current_shape_id = None
        self.annotate_panel.image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()

    def callback_set_to_edit_shape(self):
        self.annotate_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_handle_annotate_mouse_wheel(self, event):
        self.annotate_panel.image_panel.canvas.callback_mouse_zoom(event)

    def callback_delete_shape(self):
        current_geom_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_geom_id == '' or current_geom_id in self.annotate_panel.image_panel.canvas.get_tool_shape_ids():
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
        current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_canvas_shape_id:
            popup = tkinter.Toplevel(self.parent)
            self.variables.current_annotate_canvas_id = current_canvas_shape_id
            AnnotationPopup(popup, self.variables)
        else:
            print("Please select a geometry first.")

    # utility functions
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
                annotate_id = self.annotate_panel.image_panel.canvas.create_new_polygon((0, 0, 1, 1))
                self.annotate_panel.image_panel.canvas.set_shape_pixel_coords(annotate_canvas_id, image_coords)
                # TODO: shapes on the context_panel too?
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
        # TODO: redraw all shapes on the context_panel?

        # enable appropriate GUI elements
        self.context_panel.buttons.enable_all_buttons()


def main():
    root = tkinter.Tk()
    # noinspection PyUnusedLocal
    app = AnnotationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
