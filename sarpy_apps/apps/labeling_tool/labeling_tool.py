"""
A structured labeling tool
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import os
from typing import Union
from datetime import datetime

import tkinter
from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename, asksaveasfilename

from tk_builder.base_elements import TypedDescriptor
from tk_builder.widgets.basic_widgets import Frame, Button, Label, Combobox, Entry
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling, TextWithScrolling

from sarpy_apps.apps.annotation_tool import AppVariables as AppVariables_Annotate, \
    NamePanel, AnnotateButtons, AnnotateTabControl, AnnotationPanel, \
    AnnotationCollectionViewer, AnnotationCollectionPanel, AnnotationTool
from sarpy_apps.apps.labeling_tool.schema_editor import SchemaEditor, select_schema_entry

from sarpy.annotation.label import FileLabelCollection, LabelCollection, \
    LabelFeature, LabelProperties, LabelMetadataList, LabelMetadata, LabelSchema
from sarpy_apps.supporting_classes.file_filters import all_files, json_files


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
        if self.file_annotation_collection is None:
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
        self.comment_text = TextWithScrolling(self)
        self.comment_text.frame.grid(row=1, column=1, sticky='NSEW', padx=3, pady=3)

        self.confidence_label = Label(self, text='Confidence:', relief=tkinter.RIDGE, width=15, padding=3)
        self.confidence_label.grid(row=2, column=0, sticky='NEW', padx=3, pady=3)
        self.confidence_combo = Combobox(self)
        self.confidence_combo.grid(row=2, column=1, sticky='NEW', padx=3, pady=3)

        self.user_id_label = Label(self, text='User ID:', relief=tkinter.RIDGE, width=15, padding=3)
        self.user_id_label.grid(row=3, column=0, sticky='NEW', padx=3, pady=3)
        self.user_id_value = Entry(self, text='', relief=tkinter.RIDGE, width=15, padding=3, state='disabled')
        self.user_id_value.grid(row=3, column=1, sticky='NEW', padx=3, pady=3)

        self.timestamp_label = Label(self, text='Timestamp:', relief=tkinter.RIDGE, width=15, padding=3)
        self.timestamp_label.grid(row=4, column=0, sticky='NEW', padx=3, pady=3)
        self.timestamp_value = Entry(self, text='', relief=tkinter.RIDGE, width=15, padding=3, state='disabled')
        self.timestamp_value.grid(row=4, column=1, sticky='NEW', padx=3, pady=3)

        self.frame1 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)
        self.cancel_button = Button(self.frame1, text='Cancel')
        self.cancel_button.pack(side=tkinter.RIGHT)
        self.submit_button = Button(self.frame1, text='Submit')
        self.submit_button.pack(side=tkinter.RIGHT)
        self.frame1.grid(row=5, column=0, columspan=2, sticky='NSEW')
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
            self.object_type_button.set_text('<Choose>' if entry.label_id is None else self.app_variables.get_label(entry.label_id))
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
        # NB: this should be called by the controlling parent for holistic state change elsewhere
        status, msg = self._populate_values_into_inprogress()
        if not status:
            showinfo('Incomplete data population', message=msg)
            return

        self.current_metadata_list.insert_new_element(self.in_progess_metadata)
        self.in_progess_metadata = None
        self.update_annotation()


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
        Frame.__init__(self, master, **kwargs)
        # todo: what are the right pieces?
        #   - sort of like geometry panel
        #   - a button for new or add or something
        #   - a simpler viewer (label & timestamp?)
        #   - LabelSpecificsPanel (change name - LabelEditPanel?)

        pass

    def update_annotation(self):
        # todo:
        pass

    def update_annotation_collection(self):
        # todo:
        pass

    def cancel(self):
        # todo: nothing necessary here?
        pass

    def save(self):
        # todo: nothing necessary here?
        pass


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

    def update_annotation_collection(self):
        self.details_tab.update_annotation_collection()
        self.geometry_tab.update_annotation()
        self.label_tab.update_annotation()

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
        AnnotationTool.__init__(master, reader=reader, annotation_collection=annotation_collection, **kwargs)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label='Edit Label Schema', command=self.callback_edit_schema)

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
            title='Select output label schema',
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
                        'Deleting any labels which are currently applied with result in a non-viable label collection.\n'
                        'Do not delete any labels from the schema unless you are sure.')

        root = tkinter.Toplevel(self.master)  # create a new toplevel with its own mainloop, so it's blocking
        tool = SchemaEditor(root, label_schema=self.variables.file_annotation_collection.label_schema)
        root.grab_set()
        root.wait_window()
        # update for any important state changes
        self.set_annotations(self.variables.file_annotation_collection)
