"""
A structured labeling tool
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import os
from typing import Union
from datetime import datetime

import tkinter
from tkinter import ttk, PanedWindow

from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename, asksaveasfilename

from tk_builder.base_elements import TypedDescriptor
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets.basic_widgets import Frame, Button, Label, Combobox, Entry
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling, TextWithScrolling

from sarpy_apps.apps.annotation_tool import AppVariables as AppVariables_Annotate, \
    NamePanel, AnnotateButtons, AnnotateTabControl, AnnotationPanel, \
    AnnotationCollectionViewer, AnnotationCollectionPanel, AnnotationTool
from sarpy_apps.apps.labeling_tool.schema_editor import SchemaEditor, select_schema_entry
from sarpy_apps.supporting_classes.file_filters import all_files, json_files
from sarpy_apps.supporting_classes.image_reader import GeneralCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.annotation.label import FileLabelCollection, LabelFeature, \
    LabelMetadataList, LabelMetadata, LabelSchema
from sarpy.io.general.base import BaseReader


def get_default_schema():
    return LabelSchema(labels={'0': 'unknown'})


class AppVariables(AppVariables_Annotate):
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileLabelCollection,
        docstring='The file annotation collection.')  # type: FileLabelCollection

    @property
    def label_schema(self):
        """
        None|LabelSchema: The label schema.
        """

        return None if self.file_annotation_collection is None else \
            self.file_annotation_collection.label_schema

    def get_label(self, label_id):
        if self.file_annotation_collection is None or label_id is None:
            return None
        return self.file_annotation_collection.label_schema.labels[label_id]

    def get_current_annotation_object(self):
        """
        Gets the current annotation object

        Returns
        -------
        None|LabelFeature
        """

        if self._current_feature_id is None:
            return None
        return self.file_annotation_collection.annotations[self._current_feature_id]


###########
# elements for editing the label details

class LabelSpecificsPanel(Frame):
    """
    Edit/Display widget for LabelMetadata object
    """

    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
        app_variables : AppVariables
        kwargs
        """

        self.app_variables = app_variables
        self.current_metadata_list = None  # type: Union[None, LabelMetadataList]
        self.in_progess_metadata = None  # type: Union[None, LabelMetadata]
        self.has_confidence = False
        Frame.__init__(self, master, **kwargs)

        self.object_type_label = Label(self, text='Type:', relief=tkinter.RIDGE, width=15, padding=3)
        self.object_type_label.grid(row=0, column=0, sticky='NEW', padx=3, pady=3)
        self.object_type_button = Button(self, text='<Choose>')
        self.object_type_button.grid(row=0, column=1, sticky='NEW', padx=3, pady=3)

        self.comment_label = Label(self, text='Comment:', relief=tkinter.RIDGE, width=15, padding=3)
        self.comment_label.grid(row=1, column=0, sticky='NEW', padx=3, pady=3)
        self.comment_text = TextWithScrolling(self, height=5)
        self.comment_text.frame.grid(row=1, column=1, sticky='NSEW', padx=3, pady=3)

        self.confidence_label = Label(self, text='Confidence:', relief=tkinter.RIDGE, width=15, padding=3)
        self.confidence_label.grid(row=2, column=0, sticky='NEW', padx=3, pady=3)
        self.confidence_combo = Combobox(self)
        self.confidence_combo.grid(row=2, column=1, sticky='NEW', padx=3, pady=3)

        self.user_id_label = Label(self, text='User ID:', relief=tkinter.RIDGE, width=15, padding=3)
        self.user_id_label.grid(row=3, column=0, sticky='NEW', padx=3, pady=3)
        self.user_id_value = Entry(self, text='', relief=tkinter.RIDGE, width=15, state='disabled')
        self.user_id_value.grid(row=3, column=1, sticky='NEW', padx=3, pady=3)

        self.timestamp_label = Label(self, text='Timestamp:', relief=tkinter.RIDGE, width=15, padding=3)
        self.timestamp_label.grid(row=4, column=0, sticky='NEW', padx=3, pady=3)
        self.timestamp_value = Entry(self, text='', relief=tkinter.RIDGE, width=15, state='disabled')
        self.timestamp_value.grid(row=4, column=1, sticky='NEW', padx=3, pady=3)

        self.frame1 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)
        self.cancel_button = Button(self.frame1, text='Cancel')
        self.cancel_button.pack(side=tkinter.RIGHT)
        self.submit_button = Button(self.frame1, text='Submit')
        self.submit_button.pack(side=tkinter.RIGHT)
        self.frame1.grid(row=5, column=0, columnspan=2, sticky='NSEW')
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.object_type_button.config(command=self.callback_select_object_type)
        self.cancel_button.config(command=self.callback_cancel)

    def _populate_values_into_inprogress(self):
        msg = ''
        status = True
        if self.in_progess_metadata.label_id is None:
            msg += 'The label ID must be set\n'
            status = False
        comment = self.comment_text.get_value()
        self.in_progess_metadata.comment = None if comment == '' else comment

        if self.has_confidence:
            confidence = self.confidence_combo.get()
            self.in_progess_metadata.confidence = None if confidence == '' else confidence
        return status, msg

    def _fill_metadata(self, entry):
        """
        Populates the values from entry.

        Parameters
        ----------
        entry : None|LabelMetadata
        """

        if entry is None:
            self.object_type_button.set_text('')
            self.comment_text.set_value('')
            self.confidence_combo.set_text('')
            self.user_id_value.set_text('')
            self.timestamp_value.set_text('')
        else:
            self.object_type_button.set_text(
                '<Choose>' if entry.label_id is None else self.app_variables.get_label(entry.label_id))
            self.comment_text.set_value('' if entry.comment is None else entry.comment)
            self.confidence_combo.set_text('' if entry.confidence is None else str(entry.confidence))
            self.user_id_value.set_text(entry.user_id)
            self.timestamp_value.set_text(datetime.utcfromtimestamp(entry.timestamp).isoformat('T'))

    def set_entry(self, index):
        """
        Sets the entry to display

        Parameters
        ----------
        index : None|int
        """

        def disable():
            self.object_type_button.config(state='disabled')
            self.comment_text.config(state='disabled')
            self.confidence_combo.config(state='disabled')
            self.cancel_button.config(state='disabled')
            self.submit_button.config(state='disabled')

        def enable():
            self.object_type_button.config(state='normal')
            self.comment_text.config(state='normal')
            if self.has_confidence:
                self.confidence_combo.config(state='normal')
            self.cancel_button.config(state='normal')
            self.submit_button.config(state='normal')

        if index is not None:
            entry = self.current_metadata_list[index]
            self._fill_metadata(entry)
            disable()
            return

        if self.current_metadata_list is None:
            # nothing to be done
            self._fill_metadata(None)
            disable()
            return

        if len(self.current_metadata_list) == 0:
            self.in_progess_metadata = LabelMetadata()
        else:
            self.in_progess_metadata = self.current_metadata_list[0].replicate()
            self.in_progess_metadata.comment = None
        self._fill_metadata(self.in_progess_metadata)
        enable()

    def update_annotation(self):
        feature = self.app_variables.get_current_annotation_object()
        if feature is None:
            self.current_metadata_list = None
            self.set_entry(None)
        else:
            self.current_metadata_list = feature.properties.parameters
            if len(self.current_metadata_list) > 0:
                self.set_entry(0)
            else:
                self.set_entry(None)

    def update_annotation_collection(self):
        if self.app_variables.file_annotation_collection is not None:
            confidence_values = self.app_variables.file_annotation_collection.label_schema.confidence_values
            if confidence_values is None:
                self.has_confidence = False
                self.confidence_combo.update_combobox_values([])
            else:
                self.has_confidence = True
                self.confidence_combo.update_combobox_values(['{}'.format(entry) for entry in confidence_values])
        self.update_annotation()

    def callback_select_object_type(self):
        if self.app_variables is None or \
                self.app_variables.file_annotation_collection is None or \
                self.in_progess_metadata is None:
            return  # this would be broken state, and should not happen

        current_value = self.in_progess_metadata.label_id
        value = select_schema_entry(self.app_variables.label_schema, start_id=current_value)
        if value is None:
            return

        self.in_progess_metadata.label_id = value
        self.object_type_button.set_text(self.app_variables.get_label(value))

    def callback_cancel(self):
        self.in_progess_metadata = None
        self.update_annotation()

    def callback_submit(self):
        # NB: this should be called by the controlling parent for holistic state change everywhere
        status, msg = self._populate_values_into_inprogress()
        if not status:
            showinfo('Incomplete data population', message=msg)
            return status

        self.current_metadata_list.insert_new_element(self.in_progess_metadata)
        self.in_progess_metadata = None
        return status


class LabelDetailsPanel(Frame):
    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
        app_variables : AppVariables
        kwargs
        """

        self.app_variables = app_variables
        self.current_annotation = None  # type: Union[None, LabelFeature]
        Frame.__init__(self, master, **kwargs)

        self.update_label_button = Button(
            self, text='Update Label', command=self.callback_update_label)  # type: Button
        self.update_label_button.grid(row=0, column=0, columnspan=2, sticky='NE', padx=3, pady=3)

        self.viewer = TreeviewWithScrolling(
            self, columns=('confidence', ), selectmode=tkinter.BROWSE)  # type: TreeviewWithScrolling
        self.viewer.heading('#0', text='Label')
        self.viewer.heading('#1', text='Confidence')
        self.viewer.frame.grid(row=1, column=0, sticky='NSEW', padx=3, pady=3)
        # NB: reference the frame for packing, since it's already packed into a frame

        self.label_specifics = LabelSpecificsPanel(self, app_variables, border=1, relief=tkinter.RIDGE)
        self.label_specifics.grid(row=1, column=1, sticky='NSEW', padx=3, pady=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.update_annotation()

        self.viewer.bind('<<TreeviewSelect>>', self.callback_label_selected_on_viewer)

    def _set_focus(self, uid):
        self.viewer.set_selection_with_expansion(uid)

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.
        """

        self.viewer.delete(*self.viewer.get_children())

    def _fill_treeview(self):
        """
        Fills the treeview based on the current annotation.
        """

        if self.current_annotation is None or \
                self.current_annotation.properties.parameters is None or \
                len(self.current_annotation.properties.parameters) == 0:
            self._empty_entries()
            self.label_specifics.update_annotation()
            self.label_specifics.set_entry(None)
            return

        self._empty_entries()
        label_list = self.current_annotation.properties.parameters
        for i, entry in enumerate(label_list):
            label = self.app_variables.get_label(entry.label_id)
            conf = '' if entry.confidence is None else entry.confidence
            self.viewer.insert('', 'end', iid=str(i), text=label, values=(conf, ))
        if len(label_list) > 0:
            self._set_focus('0')

    # noinspection PyUnusedLocal
    def callback_label_selected_on_viewer(self, event):
        label_index = self.viewer.focus()
        if label_index == '':
            return
        self.label_specifics.set_entry(int(label_index))

    def callback_update_label(self):
        self.label_specifics.set_entry(None)

    def set_annotation_feature(self, annotation_feature):
        self.current_annotation = annotation_feature
        self._fill_treeview()
        self.label_specifics.update_annotation()

    def update_annotation(self):
        annotation_feature = self.app_variables.get_current_annotation_object()
        self.set_annotation_feature(annotation_feature)

    def cancel(self):
        self._fill_treeview()  # probably unnecessary

    def save(self):
        self._fill_treeview()  # probably unnecessary


#############
# refactoring from annotation to accommodate minor differences in the basic elements

class LabelTabControl(AnnotateTabControl):
    def __init__(self, master, app_variables, **kwargs):
        AnnotateTabControl.__init__(self, master, app_variables, **kwargs)
        self.label_tab = LabelDetailsPanel(self, app_variables)
        self.tab_control.add(self.label_tab, text='Label')

    def update_annotation(self):
        self.details_tab.update_annotation()
        self.geometry_tab.update_annotation()
        self.label_tab.update_annotation()

    def _set_active_shapes(self):
        label_schema = self.app_variables.label_schema  # type: LabelSchema
        if label_schema is None or \
                label_schema.permitted_geometries is None or \
                len(label_schema.permitted_geometries) == 0:
            shapes = None
        else:
            shapes = []
            if 'point' in label_schema.permitted_geometries:
                shapes.append('point')
            if 'line' in label_schema.permitted_geometries:
                shapes.append('line')
            if 'polygon' in label_schema.permitted_geometries:
                shapes.extend(['rectangle', 'ellipse', 'polygon'])
        self.geometry_tab.geometry_buttons.set_active_shapes(shapes)

    def update_annotation_collection(self):
        self.details_tab.update_annotation_collection()
        self.geometry_tab.update_annotation()
        self.label_tab.update_annotation()
        self._set_active_shapes()

    def cancel(self):
        self.details_tab.cancel()
        self.geometry_tab.cancel()
        self.label_tab.cancel()

    def save(self):
        self.details_tab.save()
        self.geometry_tab.save()
        self.label_tab.save()


class LabelPanel(AnnotationPanel):
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

        self.tab_panel = LabelTabControl(self, app_variables)  # type: LabelTabControl
        self.tab_panel.grid(row=1, column=0, sticky='NSEW')

        self.button_panel = AnnotateButtons(self)  # type: AnnotateButtons
        self.button_panel.grid(row=2, column=0, sticky='NSEW')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)


class LabelCollectionViewer(AnnotationCollectionViewer):

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
        kwargs['columns'] = ('label', )
        TreeviewWithScrolling.__init__(self, master, **kwargs)
        self.heading('#0', text='Name')
        self.heading('#1', text='Label')
        self.update_annotation_collection()

    @property
    def annotation_collection(self):
        """
        FileLabelCollection : The file annotation collection
        """

        return self._app_variables.file_annotation_collection

    def _render_directory(self, directory, at_index='end'):
        if directory != '' and not self.exists(directory):
            stem, leaf = os.path.split(directory)
            self.insert(stem, at_index, directory, text=leaf, values=('', ))
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
        label_id = annotation.get_label_id()
        label = self._app_variables.get_label(label_id)
        if label is None:
            label = ''
        if name == annotation.uid and label_id != '':
            name = label
        self.insert(parent, at_index, the_id, text=name, values=(label, ))


class LabelCollectionPanel(AnnotationCollectionPanel):
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

        self.viewer = LabelCollectionViewer(self, app_variables)
        self.viewer.frame.grid(row=1, column=0, sticky='NSEW')
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)


#########################
# the main tool

class LabelingTool(AnnotationTool):
    _NEW_ANNOTATION_TYPE = LabelFeature
    _NEW_FILE_ANNOTATION_TYPE = FileLabelCollection

    def __init__(self, master, reader=None, annotation_collection=None, **kwargs):
        """

        Parameters
        ----------
        master
            tkinter.Tk|tkinter.TopLevel
        reader : None|str|BaseReader|GeneralCanvasImageReader
        annotation_collection : None|str|FileLabelCollection
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

        self.collection_panel = LabelCollectionPanel(self, self.variables)  # type: LabelCollectionPanel

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
        self.edit_menu.add_command(label='Edit Label Schema', command=self.callback_edit_schema)
        self.edit_menu.add_separator()
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
        self.image_panel.hide_select_index()
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
        self.annotate_popup.geometry('700x500')
        self.annotate = LabelPanel(self.annotate_popup, self.variables)  # type: LabelPanel
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

        # bind the label specifics submit button specifically
        self.annotate.tab_panel.label_tab.label_specifics.submit_button.config(command=self.callback_submit_label)

        self.set_reader(reader)
        self.set_annotations(annotation_collection)
        self.annotate.update_annotation_collection()

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Labeling Tool"
        else:
            the_title = "Labeling Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

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

        self.set_annotations(annotation_fname)

    def create_new_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        label_schema_file = self._prompt_for_label_schema()
        if label_schema_file is None:
            label_schema = get_default_schema()
        else:
            label_schema = LabelSchema.from_file(label_schema_file)

        annotations = self._NEW_FILE_ANNOTATION_TYPE(label_schema)
        self.set_annotations(annotations)

    def _prompt_annotation_file_name(self):
        if self.image_file_name is not None:
            browse_dir, image_fname = os.path.split(self.image_file_name)
        else:
            browse_dir = self.variables.browse_directory
            image_fname = 'Unknown_Image'

        annotation_fname = asksaveasfilename(
            title='Select output annotation file name for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile='{}.labels.json'.format(image_fname),
            filetypes=[json_files, all_files])

        if annotation_fname in ['', ()]:
            annotation_fname = None
        return annotation_fname

    def _get_default_collection(self):
        return self._NEW_FILE_ANNOTATION_TYPE(label_schema=get_default_schema(), image_file_name=self.image_file_name)

    def _prompt_for_label_schema(self):
        browse_dir = self.variables.browse_directory
        label_schema_file = askopenfilename(
            title='Select Label Schema',
            initialdir=browse_dir,
            filetypes=[json_files, all_files])

        if label_schema_file in ['', ()]:
            label_schema_file = None
        return label_schema_file

    def callback_edit_schema(self):
        if self.variables.file_annotation_collection is None:
            return

        if self.variables.file_annotation_collection.annotations is not None and \
                len(self.variables.file_annotation_collection.annotations) > 0:
            showinfo(
                'label schema editing',
                message='You are opting to edit the label schema with existing labeled features.\n'
                        'Deleting any labels which are currently applied somewhere will result\n'
                        'in a non-viable label collection, and no error checking will be performed here.\n'
                        '\nDo not delete any labels from the schema unless you are sure.')

        root = tkinter.Toplevel(self.master)  # create a new toplevel with its own mainloop, so it's blocking
        # noinspection PyUnusedLocal
        tool = SchemaEditor(root, label_schema=self.variables.file_annotation_collection.label_schema)
        root.grab_set()
        root.wait_window()
        # update for any important state changes
        self.set_annotations(self.variables.file_annotation_collection)

    def callback_submit_label(self):
        """
        Submit the new label for the selected feature
        """

        if self.annotate.tab_panel.label_tab.label_specifics.callback_submit():
            self.annotate.update_annotation()
            self.collection_panel.update_annotation()


def main(reader=None, annotation=None):
    """
    Main method for initializing the labeling tool

    Parameters
    ----------
    reader : None|str|BaseReader|GeneralCanvasImageReader
    annotation : None|str|FileLabelCollection
    """

    root = tkinter.Tk()
    root.geometry("1000x800")

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = LabelingTool(root, reader=reader, annotation_collection=annotation)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the labeling tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None,  nargs='?',
        help='The path to the optional image file for opening.')
    parser.add_argument(
        '-a', '--annotation', metavar='annotation', default=None,
        help='The path to the optional annotation file. '
             'If the image input is not specified, then this has no effect. '
             'If both are specified, then a check will be performed that the '
             'annotation actually applies to the provided image.')
    this_args = parser.parse_args()

    main(reader=this_args.input, annotation=this_args.annotation)
