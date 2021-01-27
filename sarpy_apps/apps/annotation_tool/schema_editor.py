# -*- coding: utf-8 -*-
"""
This module provides a tool for creating annotation for a SAR image.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import os
import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesno, askyesnocancel
from tkinter.filedialog import askopenfilename, asksaveasfilename

from sarpy.compliance import string_types
from sarpy.annotation.schema_processing import LabelSchema

from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.widget_descriptors import ButtonDescriptor, LabelDescriptor, \
    EntryDescriptor, TypedDescriptor
from tk_builder.widgets import basic_widgets

from sarpy_apps.supporting_classes import file_filters


####
# Utility functions

def _validate_schema(schema):
    """
    Utility function for verifying that an input argument is or points to a LabelSchema.

    Parameters
    ----------
    schema : str|LabelSchema

    Returns
    -------
    LabelSchema
    """

    if isinstance(schema, string_types):
        schema = LabelSchema.from_file(schema)
    if not isinstance(schema, LabelSchema):
        raise TypeError(
            'label_schema must be either a path to am appropriate .json file or a '
            'LabelSchema object. Got type {}'.format(type(schema)))
    return schema


###########
# Treeview for a label schema, and associated widget

class SchemaViewer(basic_widgets.Treeview):
    """
    For the purpose of viewing the schema definition.
    """

    def __init__(self, master, geometry_size=None):
        """

        Parameters
        ----------
        master : tk.Tk|tk.TopLevel
            The GUI element which is the parent or master of this node.
        geometry_size : None|str
            The optional geometry size for the parent.
        """

        super(SchemaViewer, self).__init__(master, columns=('Name', ))
        self.parent = master
        if geometry_size is not None:
            self.parent.geometry(geometry_size)
        self.pack(expand=True, fill='both')
        try:
            self.parent.protocol("WM_DELETE_WINDOW", self.close_window)
        except AttributeError:
            pass
        # define the column headings
        self.heading('#0', text='Name')
        self.heading('#1', text='ID')

    def empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.

        Returns
        -------
        None
        """

        self.delete(*self.get_children())

    def close_window(self):
        self.parent.withdraw()

    def fill_from_label_schema(self, schema):
        """
        Fill contents from a label schema.

        Parameters
        ----------
        schema : str|LabelSchema

        Returns
        -------
        None
        """

        def iterate(the_id, parent_id):
            self.insert(parent_id, 'end', the_id, text=schema.labels[the_id], values=(the_id, ))
            for child_id in schema.subtypes.get(the_id, []):
                iterate(child_id, the_id)

        # validate the label schema input
        schema = _validate_schema(schema)
        # empty any present entries
        self.empty_entries()

        for element_id in schema.subtypes['']:
            iterate(element_id, '')


class _SchemaSelectionWidget(object):
    """
    Class for interactive label schema selection widget.
    """

    def __init__(self, label_schema):
        """

        Parameters
        ----------
        label_schema : str|LabelSchema
        """

        # validate label schema input
        label_schema = _validate_schema(label_schema)
        # initialize the selected value option
        self._selected_value = ''

        self.root = tkinter.Toplevel()
        self.root.wm_title('Select Label Schema Entry')
        self.viewer = SchemaViewer(self.root, geometry_size='250x400')
        self.viewer.fill_from_label_schema(label_schema)
        self.submit_button = basic_widgets.Button(self.root, text='Submit', command=self.set_value)
        self.submit_button.pack()
        self.root.mainloop()

    def set_value(self):
        self._selected_value = self.viewer.focus()
        self.root.quit()

    @property
    def selected_value(self):
        """
        str: The id of the selected element.
        """

        return self._selected_value

    def set_selected_value(self, selected_value):
        """
        Set the treeview selection to the provided id.

        Parameters
        ----------
        selected_value : str

        Returns
        -------
        None
        """

        if selected_value is None or selected_value == '':
            return

        # noinspection PyBroadException
        try:
            self.viewer.selection_set(selected_value)
        except:
            pass

    def destroy(self):
        """
        Destroy the widget elements.

        Returns
        -------
        None
        """

        # noinspection PyBroadException
        try:
            self.root.destroy()
        except:
            pass

    def __del__(self):
        self.destroy()


def select_schema_entry(label_schema, start_id=None):
    """
    Get user selected label schema entry from treeview widget.

    Parameters
    ----------
    label_schema : str|LabelSchema
        The path to a LabelSchema json file, or a LabelSchema object.
    start_id : None|str
        The starting point for the selection.

    Returns
    -------
    str
    """

    selection_widget = _SchemaSelectionWidget(label_schema)
    selection_widget.set_selected_value(start_id)
    value = selection_widget.selected_value
    selection_widget.destroy()
    return value


########
# Widget for creating/editing a label schema, and associated elements

class _LabelEntryPanel(WidgetPanel):
    _widget_list = (
        ('header_message', ),
        ('id_label', 'id_entry', 'name_label', 'name_entry', 'parent_label', 'parent_entry'),
        ('cancel_button', 'okay_button'))
    header_message = LabelDescriptor(
        'header_message', default_text='', docstring='The header message.')# type: basic_widgets.Label
    id_label = LabelDescriptor(
        'id_label', default_text='ID:', docstring='The id label')  # type: basic_widgets.Label
    id_entry = EntryDescriptor(
        'id_entry', default_text='', docstring='The id value')  # type: basic_widgets.Entry

    name_label = LabelDescriptor(
        'name_label', default_text='Name:', docstring='The name label')  # type: basic_widgets.Label
    name_entry = EntryDescriptor(
        'name_entry', default_text='', docstring='The name value')  # type: basic_widgets.Entry

    parent_label = LabelDescriptor(
        'parent_label', default_text='Parent ID:', docstring='The parent label')  # type: basic_widgets.Label
    parent_entry = EntryDescriptor(
        'parent_entry', default_text='', docstring='The parent value')  # type: basic_widgets.Entry

    cancel_button = ButtonDescriptor(
        'cancel_button', default_text='Cancel', docstring='The cancel button')  # type: basic_widgets.Button
    okay_button = ButtonDescriptor(
        'okay_button', default_text='Okay', docstring='The okay button')  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_rows()


class _LabelEntryWidget(object):
    """
    The widget element that actually performs the label schema entry edit. This
    edits the provided label schema in place.

    This object creates a pop-up. So it creates a tkinter.TopLevel which maintains
    it's own mainloop(), and the TopLevel gets destroyed by this object.
    """

    def __init__(self, label_schema, edit_id=None):
        """

        Parameters
        ----------
        label_schema : LabelSchema
            The label schema, to be edited in place.
        edit_id : None|str
            The entry to edit. A new entry will be created, if `None`.
        """

        if not isinstance(label_schema, LabelSchema):
            raise TypeError('label_schema must be a label_schema type.')
        self.label_schema = label_schema
        if edit_id is not None and edit_id not in label_schema.labels:
            raise KeyError('edit_id is not a label label id.')

        self.edit_id = edit_id

        self.root = tkinter.Toplevel()
        self.entry_widget = _LabelEntryPanel(self.root)
        self.entry_widget.parent_entry.config(validate='focusin', validatecommand=self.parent_callback)
        if self.edit_id is not None:
            self.entry_widget.header_message.set_text(
                'The <ID> is immutable, and <Name> is for simple interpretation.')
            the_name = self.label_schema.labels[edit_id]
            parent_id = self.label_schema.get_parent(edit_id)
            self.entry_widget.id_entry.config(state='disabled')
            self.entry_widget.id_entry.set_text(self.edit_id)
            self.entry_widget.name_entry.set_text(the_name)
            self.entry_widget.parent_entry.set_text(parent_id)
        else:
            id_suggestion = self.label_schema.suggested_next_id
            str_id_suggestion = '<SET>' if id_suggestion is None else str(id_suggestion)
            self.entry_widget.header_message.set_text(
                '<ID> is immutable once finalized, and <Name> is for simple interpretation.')
            self.entry_widget.id_entry.set_text(str_id_suggestion)
            self.entry_widget.name_entry.set_text('<SET>')
            self.entry_widget.parent_entry.set_text('')
        self.entry_widget.cancel_button.config(command=self.cancel_callback)
        self.entry_widget.okay_button.config(command=self.okay_callback)
        self.root.mainloop()

    def parent_callback(self):
        current_value = self.entry_widget.parent_entry.get()
        value = select_schema_entry(self.label_schema, start_id=current_value)
        self.entry_widget.parent_entry.set_text(value)

    def cancel_callback(self):
        self.root.quit()

    def okay_callback(self):
        the_id = self.entry_widget.id_entry.get()
        the_name = self.entry_widget.name_entry.get()
        the_parent = self.entry_widget.parent_entry.get()

        if self.edit_id is None:
            # if this is a new entry, then verify that both id and name are set
            if the_id == '<SET>' or the_name == '<SET>':
                showinfo('Entries Not Initialized', message='Both `ID` and `Name` must be set.')
                return

            try:
                self.label_schema.add_entry(the_id, the_name, the_parent=the_parent)
            except Exception as e:
                showinfo("Creation Error", message="Got Error: {}".format(e))
                return
        else:
            try:
                self.label_schema.change_entry(the_id, the_name, the_parent)
            except Exception as e:
                showinfo("Edit Error", message="Got Error: {}".format(e))
                return
        self.root.quit()

    def destroy(self):
        """
        Destroys the widget elements.

        Returns
        -------
        None
        """

        # noinspection PyBroadException
        try:
            self.root.destroy()
        except:
            pass

    def __del__(self):
        self.destroy()


class SchemaEditor(WidgetPanel):
    _widget_list = (
        ('version_label', 'version_entry'),
        ('version_date_label', 'version_date_entry'),
        ('classification_label', 'classification_entry'),
        ('confidence_label', 'confidence_entry'),
        ('geometries_label', 'geometries_entry'),
        ('edit_button', 'new_button'),
        ('treeview', ))

    version_label = LabelDescriptor(
        'version_label', default_text='Version:', docstring='The version label')  # type: basic_widgets.Label
    version_entry = EntryDescriptor(
        'version_entry', default_text='', docstring='The version value')  # type: basic_widgets.Entry

    version_date_label = LabelDescriptor(
        'version_date_label', default_text='Version:', docstring='The version_date label')  # type: basic_widgets.Label
    version_date_entry = EntryDescriptor(
        'version_date_entry', default_text='', docstring='The version_date value')  # type: basic_widgets.Entry

    classification_label = LabelDescriptor(
        'classification_label', default_text='Classification:', docstring='The classification label')  # type: basic_widgets.Label
    classification_entry = EntryDescriptor(
        'classification_entry', default_text='', docstring='The classification value')  # type: basic_widgets.Entry

    confidence_label = LabelDescriptor(
        'confidence_label', default_text='Confidence Values:', docstring='The confidence label')  # type: basic_widgets.Label
    confidence_entry = EntryDescriptor(
        'confidence_entry', default_text='', docstring='The confidence value')  # type: basic_widgets.Entry

    geometries_label = LabelDescriptor(
        'geometries_label', default_text='Geometries:', docstring='The geometries label')  # type: basic_widgets.Label
    geometries_entry = EntryDescriptor(
        'geometries_entry', default_text='', docstring='The geometries value')  # type: basic_widgets.Entry

    edit_button = ButtonDescriptor(
        'edit_button', default_text='Edit Selected',
        docstring='The edit button')  # type: basic_widgets.Button
    new_button = ButtonDescriptor(
        'new_button', default_text='New Entry',
        docstring='The new entry button')  # type: basic_widgets.Button
    treeview = TypedDescriptor(
        'treeview', SchemaViewer,
        docstring='The treeview of the label schema')  # type: SchemaViewer

    def __init__(self, root):
        self.browse_directory = os.path.expanduser('~')
        self._file_name = None
        self.label_schema = LabelSchema()  # type: LabelSchema
        self._new_file = None
        self._unsaved_edits = None

        self.primary = basic_widgets.Frame(root)
        WidgetPanel.__init__(self, self.primary)
        self.init_w_rows()

        # setup the appearance of labels
        self.version_label.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5)
        self.version_date_label.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5)
        self.classification_label.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5)
        self.confidence_label.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5)
        self.geometries_label.config(relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5)

        # setup the GUI callbacks and appearance of labels
        self.version_entry.config(state='disabled', validate='focusout', validatecommand=self._version_entry_validate)
        self.version_date_entry.config(state='disabled')
        self.classification_entry.config(state='disabled', validate='focusout', validatecommand=self._classification_validate)
        self.confidence_entry.config(state='disabled', validate='focusout', validatecommand=self._confidence_validate)
        self.geometries_entry.config(state='disabled')
        self.edit_button.config(command=self.edit_entry)
        self.new_button.config(command=self.new_entry)

        # set up the menu bar
        menu = tkinter.Menu()
        filemenu = tkinter.Menu(menu, tearoff=0)
        filemenu.add_command(label="New Schema", command=self.new_schema)
        filemenu.add_command(label="Open Schema", command=self.open_schema)
        filemenu.add_command(label="Save", command=self.save)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)
        menu.add_cascade(label="File", menu=filemenu)
        self.primary.pack(fill=tkinter.BOTH)  #, expand=tkinter.YES)
        root.config(menu=menu)

    def set_file_name(self, file_name):
        self._file_name = file_name
        if os.path.exists(file_name):
            self.label_schema = LabelSchema.from_file(file_name)
        else:
            self.label_schema = LabelSchema()

        # TODO: set our entries as appropriate
        if self._new_file:
            pass
        else:
            pass

    # main schema element edit callbacks - piggyback on validation methods
    def _version_entry_validate(self):
        the_value = self.version_entry.get().strip()
        if the_value != '' and self.label_schema.version != the_value:
            self._unsaved_edits = True
            self.label_schema._version = the_value
            self.label_schema.update_version_date(value=None)
            self.version_date_entry.set_text(self.label_schema.version_date)
        return True

    def _classification_validate(self):
        the_value = self.classification_entry.get().strip()
        if self.label_schema.classification != the_value:
            self._unsaved_edits = True
            self.label_schema._classification = the_value
        return True

    def _confidence_validate(self):
        the_value = self.confidence_entry.get().strip()
        if the_value == '':
            the_values = None
        else:
            temp_values = the_value.split()

            # noinspection PyBroadException
            try:
                the_values = [int(entry) for entry in temp_values]
            except:
                the_values = temp_values

        if self.label_schema.confidence_values != the_values:
            self._unsaved_edits = True
            self.label_schema.confidence_values = the_values
        return True

    def _populate_all(self):
        self._populate_fields_schema()
        self._populate_treeview_schema()

    def _populate_fields_schema(self):
        """
        Populate the GUI values from the schema.

        Returns
        -------
        None
        """

        self.version_entry.config(state='normal')
        self.version_entry.set_text(self.label_schema.version)

        self.version_date_entry.set_text(self.label_schema.version_date)

        self.classification_entry.config(state='normal')
        self.classification_entry.set_text(self.label_schema.classification)

        self.confidence_entry.config(state='normal')
        if self.label_schema.confidence_values is None:
            self.confidence_entry.set_text('')
        else:
            self.confidence_entry.set_text(
                ' '.join('{}'.format(entry) for entry in self.label_schema.confidence_values))

        self.confidence_entry.config(state='normal')
        if self.label_schema.permitted_geometries is None:
            self.geometries_entry.set_text('')
        else:
            self.geometries_entry.set_text(
                ' '.join(self.label_schema.permitted_geometries))

    def _populate_treeview_schema(self):
        self.treeview.fill_from_label_schema(self.label_schema)

    def edit_entry(self):
        """
        Edit the selected element.

        Returns
        -------
        None
        """

        if self._file_name is None:
            showinfo('No Schema Selected', message='Choose schema location from File menu')
            return

        selected = self.treeview.focus()
        if selected == '':
            showinfo('No Element Selected', message='Choose element from treeview')
            return
        else:
            self._unsaved_edits = True
            popup = _LabelEntryWidget(self.label_schema, edit_id=selected)
            self._populate_treeview_schema()
            popup.destroy()

    def new_entry(self):
        """
        Create a new label schema entry.

        Returns
        -------
        None
        """

        if self._file_name is None:
            showinfo('No Schema Selected', message='Choose schema location from File menu')
            return

        self._unsaved_edits = True
        popup = _LabelEntryWidget(self.label_schema, edit_id=None)
        self._populate_treeview_schema()
        popup.destroy()

    def new_schema(self):
        """
        Create a new schema.

        Returns
        -------
        None
        """

        schema_file = asksaveasfilename(
            initialdir=self.browse_directory,
            filetypes=[file_filters.json_files, file_filters.all_files])

        if schema_file == '' or schema_file == ():
            # closed or cancelled
            return

        self.browse_directory = os.path.split(schema_file)[0]
        self._file_name = schema_file
        self._new_file = True
        self._unsaved_edits = True
        self.label_schema = LabelSchema()
        self._populate_all()

    def open_schema(self):
        """
        Open and edit a schema file.

        Returns
        -------
        None
        """

        if self._file_name is not None and self._unsaved_edits:
            result = askyesnocancel(
                title="Unsaved Edits",
                message="There are unsaved edits. Save before opening a new file?")
            if result is True:
                self.save()
            elif result is None:
                return

        schema_file = askopenfilename(initialdir=self.browse_directory, filetypes=[file_filters.json_files, file_filters.all_files])
        if schema_file == '' or schema_file == ():
            # closed or cancelled
            return

        self.browse_directory = os.path.split(schema_file)[0]
        self._file_name = schema_file

        self._new_file = False
        self._unsaved_edits = False
        self.label_schema = LabelSchema.from_file(schema_file)
        self._populate_all()

    def save(self):
        """
        Save any current progress.

        Returns
        -------
        None
        """

        if self._file_name is None:
            showinfo('No Schema Selected', message='Choose schema location from File menu')
            return

        if self._unsaved_edits:
            self.label_schema.to_file(self._file_name)
            self._unsaved_edits = False

    def exit(self):
        """
        Exit the application.

        Returns
        -------
        None
        """

        if self._file_name is not None and self._unsaved_edits:
            save_state = askyesno('Save Progress', message='There are unsaved edits. Save?')
            if save_state is True:
                self.save()
        self.quit()


def main():
    """
    Creates a Tk() and runs the SchemaEditor tool.

    Returns
    -------
    None
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = SchemaEditor(root)
    root.mainloop()


if __name__ == '__main__':
    main()
