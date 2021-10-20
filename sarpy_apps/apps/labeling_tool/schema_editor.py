# -*- coding: utf-8 -*-
"""
This module provides a tool for creating labeled annotations for a SAR image.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import os
from typing import Union

import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesno, askyesnocancel
from tkinter.filedialog import askopenfilename, asksaveasfilename

from sarpy.compliance import string_types
from sarpy.annotation.label import LabelSchema

from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor

from tk_builder.widgets.basic_widgets import Frame, Label, Entry, Button
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling

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
# Treeview for a label schema, and associated selection widget

class SchemaViewer(Frame):
    """
    For the purpose of viewing the schema definition.
    """

    def __init__(self, parent, label_schema=None, geometry_size=None, **kwargs):
        """

        Parameters
        ----------
        parent
            The GUI element which is the parent of this node.
        label_schema : None|LabelSchema
            The label schema.
        geometry_size : None|str
            The optional geometry size for the parent.
        kwargs
            The keyword argument collection
        """

        self._label_schema = None
        self.root = parent
        super(SchemaViewer, self).__init__(parent, **kwargs)
        if geometry_size is not None:
            self.root.geometry(geometry_size)
        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        except AttributeError:
            pass

        # instantiate the treeview
        self.treeview = TreeviewWithScrolling(self, columns=('Name', ))  # type: TreeviewWithScrolling
        self.treeview.frame.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        # define the column headings
        self.treeview.heading('#0', text='Name')
        self.treeview.heading('#1', text='ID')
        self.fill_from_label_schema(label_schema)

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.

        Returns
        -------
        None
        """

        self.treeview.delete(*self.treeview.get_children())

    def close_window(self):
        self.root.withdraw()

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

        if the_id in self._label_schema.labels:
            self._label_schema.delete_entry(the_id, recursive=True)

    def rerender_entry(self, the_id):
        """
        Re(create) the entry for the given id.

        Parameters
        ----------
        the_id : str
        """

        if self._label_schema is None:
            self._empty_entries()
            return

        if the_id is None or the_id == '':
            self.fill_from_label_schema(self._label_schema)
        else:

            # noinspection PyBroadException
            try:
                self.treeview.delete(the_id)
            except Exception:
                pass

            if the_id not in self._label_schema.labels:
                return
            parent_id = self._label_schema.get_parent(the_id)
            the_index = self._label_schema.subtypes[parent_id].index(the_id)
            the_label = self._label_schema.labels[the_id]
            self.treeview.insert(parent_id, the_index, the_id, text=the_label, values=(the_id,))
            children = self._label_schema.subtypes.get(the_id, None)
            if children is not None:
                for child_id in children:
                    self.rerender_entry(child_id)

    def fill_from_label_schema(self, schema):
        """
        Fill contents from a label schema.

        Parameters
        ----------
        schema : None|LabelSchema
        """

        self._empty_entries()
        self._label_schema = schema
        if self._label_schema is None:
            return
        for element_id in self._label_schema.subtypes['']:
            self.rerender_entry(element_id)


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
        self.viewer = SchemaViewer(self.root, label_schema=label_schema, geometry_size='250x400')
        self.submit_button = Button(self.root, text='Submit', command=self.set_value)
        self.submit_button.pack()
        self.root.mainloop()

    def set_value(self):
        self._selected_value = self.viewer.treeview.focus()
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
            self.viewer.treeview.selection_set(selected_value)
        except Exception:
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
        except Exception:
            pass


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


#########
# the overall schema editor

class AppVariables(object):
    current_id = StringDescriptor('current_id', default_value=None)  # type: Union[None, str]
    unsaved_edits = BooleanDescriptor('unsaved_edits', default_value=False)  # type: bool
    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    label_file_name = StringDescriptor('label_file_name', default_value=None)  # type: Union[None, str]
    label_schema = TypedDescriptor('label_schema', LabelSchema)  # type: LabelSchema


class LabelEntryPanel(Frame):
    """
    Panel for viewing and editing the details of a given label schema entry.
    """

    def __init__(self, parent, app_variables, **kwargs):
        """

        Parameters
        ----------
        parent : tkinter.Tk|tkinter.ToplLevel
        app_variables : AppVariables
        kwargs
            keyword arguments passed through for frame
        """

        self._app_variables = app_variables
        self._current_id = None
        self._parent_id = None
        self._new_entry = False
        self.id_changed = None

        self.parent = parent
        Frame.__init__(self, parent, **kwargs)
        self.header_message = Label(self, text='', padding=5)
        self.header_message.grid(row=0, column=0, sticky='NSEW', padx=3, pady=3)

        self.frame2 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)
        self.id_label = Label(self.frame2, text='ID:', borderwidth=1, relief=tkinter.RIDGE, padding=5, width=10)
        self.id_label.grid(row=0, column=0, sticky='NW', padx=3, pady=3)
        self.id_entry = Entry(self.frame2, text='')
        self.id_entry.grid(row=0, column=1, sticky='NEW', padx=3, pady=3)

        self.name_label = Label(self.frame2, text='Name:', borderwidth=1, relief=tkinter.RIDGE, padding=5, width=10)
        self.name_label.grid(row=1, column=0, sticky='NW', padx=3, pady=3)
        self.name_entry = Entry(self.frame2, text='')
        self.name_entry.grid(row=1, column=1, sticky='NEW', padx=3, pady=3)

        self.parent_label = Label(self.frame2, text='Parent:', borderwidth=1, relief=tkinter.RIDGE, padding=5, width=10)
        self.parent_label.grid(row=2, column=0, sticky='NW', padx=3, pady=3)
        self.parent_button = Button(self.frame2, text='<Choose>')
        self.parent_button.grid(row=2, column=1, sticky='NEW', padx=3, pady=3)

        self.frame2.grid_columnconfigure(1, weight=1)
        self.frame2.grid(row=1, column=0, sticky='NSEW', padx=3, pady=3)

        self.frame3 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)
        self.cancel_button = Button(self.frame3, text='Cancel')
        self.cancel_button.pack(side=tkinter.RIGHT)
        self.save_button = Button(self.frame3, text='Save')
        self.save_button.pack(side=tkinter.RIGHT)
        self.frame3.grid(row=2, column=0, sticky='NSEW', padx=3, pady=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

        # callbacks
        self.parent_button.config(command=self.parent_callback)
        self.cancel_button.config(command=self.cancel_callback)
        # save_button bound by controlling parent

        self.update_label_schema()

    @property
    def label_schema(self):
        """
        None|LabelSchema : The label schema.
        """

        return self._app_variables.label_schema

    def update_label_schema(self):
        self.update_current_id()

    @property
    def current_id(self):
        """
        None|str: The current id.
        """

        return self._current_id

    def _set_parent_text(self):
        if self._parent_id is None or self._parent_id == '':
            self.parent_button.set_text('<Top Level>')
        else:
            self.parent_button.set_text(self.label_schema.labels[self._parent_id])

    def update_current_id(self):
        self._current_id = self._app_variables.current_id
        if self.label_schema is None:
            self._new_entry = False
            self._parent_id = None
            self.header_message.set_text('No label schema defined.')
            self.id_entry.set_text('')
            self.id_entry.config(state='disabled')
            self.name_entry.set_text('')
            self.name_entry.config(state='disabled')
            self.parent_button.set_text('')
            self.parent_button.config(state='disabled')
        elif self._current_id is None:
            self._parent_id = None
            self._new_entry = True

            self.header_message.set_text(
                'New entry - <ID> is immutable once initialized and <Name> is for simple interpretation.')

            id_suggestion = self.label_schema.suggested_next_id
            str_id_suggestion = '<ID>' if id_suggestion is None else str(id_suggestion)

            self.id_entry.set_text(str_id_suggestion)
            self.id_entry.config(state='normal')
            self.name_entry.set_text('<Name>')
            self.name_entry.config(state='normal')
            self._set_parent_text()
            self.parent_button.config(state='normal')
        else:
            self._new_entry = False
            self._parent_id = self.label_schema.get_parent(self._current_id)

            self.header_message.set_text(
                '<ID> is immutable, <Name> for simple interpretation.')
            self.id_entry.set_text(self._current_id)
            self.id_entry.config(state='disabled')
            self.name_entry.set_text(self.label_schema.labels[self._current_id])
            self.name_entry.config(state='normal')
            self._set_parent_text()
            self.parent_button.config(state='normal')

    def parent_callback(self):
        """
        Edit or populate the parent id.
        """

        if self.label_schema is None:
            return

        self._parent_id = select_schema_entry(self.label_schema, start_id=self._parent_id)
        self._set_parent_text()

    def cancel_callback(self):
        if self.label_schema is None:
            return

        self.update_current_id()
        self.close_window()
        self.parent.grab_release()

    def save_function(self):
        self.id_changed = None
        if self.label_schema is None:
            return True

        the_id = self.id_entry.get()
        the_name = self.name_entry.get()
        the_parent = '' if self._parent_id is None else self._parent_id

        if self._new_entry:
            # if this is a new entry, then verify that both id and name are set
            if the_id == '<ID>' or the_name == '<Name>':
                showinfo('Entries Not Initialized', message='Both `ID` and `Name` must be set.')
                return False

            try:
                self.label_schema.add_entry(the_id, the_name, the_parent=the_parent)
                self.id_changed = the_id
            except Exception as e:
                showinfo("Creation Error", message="Creation error - {}".format(e))
                return False

            self._new_entry = False
            self.update_current_id()
        else:

            try:
                result = self.label_schema.change_entry(the_id, the_name, the_parent)
                self.id_changed = the_id
            except Exception as e:
                showinfo("Edit Error", message="Editing error - {}".format(e))
                return False

        return True

    def hide_on_close(self):
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()


class SchemaEditor(Frame):
    """
    An editor for a label schema
    """

    def __init__(self, parent, label_schema=None, **kwargs):
        """

        Parameters
        ----------
        parent : tkinter.Tk|tkinter.TopLevel
        label_schema : None|str|LabelSchema
        kwargs
            keyword arguments for Frame
        """

        self.variables = AppVariables()
        self.parent = parent
        Frame.__init__(self, parent, **kwargs)

        self.frame1 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)

        self.version_label = Label(
            self.frame1, text='Version Number:', relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5, width=18)
        self.version_label.grid(row=0, column=0, sticky='NEW')
        self.version_entry = Entry(self.frame1, text='')
        self.version_entry.grid(row=0, column=1, sticky='NEW')

        self.version_date_label = Label(
            self.frame1, text='Version Date:', relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5, width=18)
        self.version_date_label.grid(row=1, column=0, sticky='NEW')
        self.version_date_entry = Entry(self.frame1, text='')
        self.version_date_entry.grid(row=1, column=1, sticky='NEW')

        self.classification_label = Label(
            self.frame1, text='Classification:', relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5, width=18)
        self.classification_label.grid(row=2, column=0, sticky='NEW')
        self.classification_entry = Entry(self.frame1, text='')
        self.classification_entry.grid(row=2, column=1, sticky='NEW')

        self.confidence_label = Label(
            self.frame1, text='Confidence Values:', relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5, width=18)
        self.confidence_label.grid(row=3, column=0, sticky='NEW')
        self.confidence_entry = Entry(self.frame1, text='')
        self.confidence_entry.grid(row=3, column=1, sticky='NEW')

        self.geometries_label = Label(
            self.frame1, text='Geometries:', relief=tkinter.RIDGE, justify=tkinter.LEFT, padding=5, width=18)
        self.geometries_label.grid(row=4, column=0, sticky='NEW')
        self.geometries_entry = Entry(self.frame1, text='')
        self.geometries_entry.grid(row=4, column=1, sticky='NEW')

        self.frame1.grid_columnconfigure(1, weight=1)
        self.frame1.pack(side=tkinter.TOP, fill=tkinter.X)

        self.frame2 = Frame(self, borderwidth=1, relief=tkinter.RIDGE)
        self.new_button = Button(self.frame2, text='New Entry')
        self.new_button.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.edit_button = Button(self.frame2, text='Edit Entry')
        self.edit_button.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.delete_button = Button(self.frame2, text='Delete Entry')
        self.delete_button.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.move_up_button = Button(self.frame2, text='Move Entry Up')
        self.move_up_button.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.move_down_button = Button(self.frame2, text='Move Entry Down')
        self.move_down_button.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.frame2.pack(side=tkinter.TOP, fill=tkinter.X)

        self.schema_viewer = SchemaViewer(self)
        self.schema_viewer.pack(side=tkinter.BOTTOM, expand=tkinter.TRUE, fill=tkinter.BOTH)

        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)

        # set up the menu bar
        menu = tkinter.Menu()
        filemenu = tkinter.Menu(menu, tearoff=0)
        filemenu.add_command(label="Open Schema", command=self.callback_open)
        filemenu.add_command(label="New Schema", command=self.callback_new_schema)
        filemenu.add_separator()
        filemenu.add_command(label="Save", command=self.save)
        filemenu.add_command(label="Save As", command=self.callback_save_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)
        menu.add_cascade(label="File", menu=filemenu)
        self.parent.config(menu=menu)

        # setup entry configs and some validation callbacks
        self.schema_viewer.treeview.bind('<<TreeviewSelect>>', self.item_selected_on_viewer)

        self.version_entry.config(validate='focusout', validatecommand=self._version_entry_validate)
        self.version_date_entry.config(state='disabled')
        self.classification_entry.config(validate='focusout', validatecommand=self._classification_validate)
        self.confidence_entry.config(validate='focusout', validatecommand=self._confidence_validate)
        self.geometries_entry.config(state='disabled')
        self.edit_button.config(command=self.callback_edit_entry)
        self.new_button.config(command=self.callback_new_entry)
        self.delete_button.config(command=self.callback_delete_entry)
        self.move_up_button.config(command=self.callback_move_up)
        self.move_down_button.config(command=self.callback_move_down)

        # setup the entry panel
        self.entry_popup = tkinter.Toplevel(self.parent)
        self.entry = LabelEntryPanel(self.entry_popup, self.variables)
        self.entry.hide_on_close()
        self.entry_popup.withdraw()

        self.entry.save_button.config(command=self.callback_save_entry)

        self.set_label_schema(label_schema)

    @property
    def label_schema(self):
        """
        None|LabelSchema: The label schema
        """

        return self.variables.label_schema

    # some entry validation methods
    def _version_entry_validate(self):
        the_value = self.version_entry.get().strip()
        if the_value != '' and self.label_schema.version != the_value:
            self.variables.unsaved_edits = True
            self.label_schema._version = the_value
            self.label_schema.update_version_date(value=None)
            self.version_date_entry.set_text(self.label_schema.version_date)
        return True

    def _classification_validate(self):
        the_value = self.classification_entry.get().strip()
        if self.label_schema.classification != the_value:
            self.variables.unsaved_edits = True
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
            except Exception:
                the_values = temp_values

        if self.label_schema.confidence_values != the_values:
            self.variables.unsaved_edits = True
            self.label_schema.confidence_values = the_values
        return True

    # some helper methods
    def _set_focus_on_entry_popup(self):
        self.entry_popup.deiconify()
        self.entry_popup.focus_set()
        self.entry_popup.lift()
        self.entry_popup.grab_set()

    def _verify_selected(self):
        if self.variables.current_id is None:
            showinfo('No Element Selected', message='Choose element from Viewer')
            return False
        return True

    def _check_save_state(self):
        """
        Checks the save state.

        Returns
        -------
        bool
            Continue (True) or abort (False)
        """

        if not self.variables.unsaved_edits:
            return True

        result = askyesnocancel(
            title="Unsaved Edits",
            message="There are unsaved edits. Save before opening a new file?")
        if result is None:
            return False

        if result is True:
            self.save()
        return True

    def _update_schema_display(self):
        if self.variables.label_schema is None:
            self.version_entry.config(state='disabled', text='')
            self.version_date_entry.set_text('')
            self.classification_entry.config(state='disabled', text='')
            self.confidence_entry.config(state='disabled', text='')
            self.geometries_entry.config(state='disabled', text='')
        else:
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

        self.schema_viewer.fill_from_label_schema(self.variables.label_schema)
        self.entry.update_label_schema()

    def prompt_for_filename(self):
        schema_file = asksaveasfilename(
            initialdir=self.variables.browse_directory,
            filetypes=[file_filters.json_files, file_filters.all_files])

        if schema_file == '' or schema_file == ():
            # closed or cancelled
            return False

        self.variables.browse_directory = os.path.split(schema_file)[0]
        self.variables.label_file_name = schema_file
        # todo: what if this file name exists? It should prompt already?
        return True

    def set_label_schema(self, label_schema):
        """
        Sets the label schema value.

        Parameters
        ----------
        label_schema : None|str|LabelSchema
        """

        if label_schema is None:
            self.variables.label_file_name = None
            self.variables.label_schema = LabelSchema()
        elif isinstance(label_schema, str):
            the_file = label_schema
            label_schema = LabelSchema.from_file(the_file)
            self.variables.label_file_name = the_file
            self.variables.label_schema = label_schema
            browse_dir = os.path.split(os.path.abspath(the_file))[0]
            self.variables.browse_directory = browse_dir
        elif isinstance(label_schema, LabelSchema):
            self.variables.label_file_name = None
            self.variables.label_schema = label_schema
        else:
            raise TypeError(
                'input must be the path for a label schema file or a LabelSchema instance')

        self.variables.unsaved_edits = True
        self.variables.current_id = None
        self._update_schema_display()

    def set_current_id(self, value):
        if value == '':
            value = None
        if (value is None and self.variables.current_id is None) or \
                (value == self.variables.current_id):
            return

        self.variables.current_id = value
        self.entry.update_current_id()
        if value is not None:
            self.schema_viewer.treeview.focus(value)
            self.schema_viewer.treeview.selection_set(value)

    # callbacks and bound methods
    def save(self):
        """
        Save any current progress.
        """

        if self.variables.label_file_name is None:
            if not self.prompt_for_filename():
                return  # they opted to not pick a file

        self.label_schema.to_file(self.variables.label_file_name)
        self.variables.unsaved_edits = False

    def exit(self):
        """
        Exit the application.

        Returns
        -------
        None
        """

        if self.variables.unsaved_edits:
            save_state = askyesno('Save Progress', message='There are unsaved edits. Save?')
            if save_state is True:
                self.save()
        self.parent.destroy()

    def callback_open(self):
        if not self._check_save_state():
            return

        schema_file = askopenfilename(
            initialdir=self.variables.browse_directory,
            filetypes=[file_filters.json_files, file_filters.all_files])
        if schema_file == '' or schema_file == ():
            # closed or cancelled
            return

        self.set_label_schema(schema_file)

    def callback_new_schema(self):
        if not self._check_save_state():
            return

        self.set_label_schema(LabelSchema())

    def callback_save_as(self):
        if self.prompt_for_filename():
            # they chose the new filename
            self.save()

    def callback_edit_entry(self):
        if not self._verify_selected():
            return
        self._set_focus_on_entry_popup()

    def callback_new_entry(self):
        self.variables.current_id = None
        self.entry.update_current_id()
        self._set_focus_on_entry_popup()

    def callback_delete_entry(self):
        if not self._verify_selected():
            return

        selected = self.variables.current_id
        # does the selected entry have any children?
        children = self.label_schema.subtypes.get(selected, None)
        if children is not None and len(children) > 0:
            response = askyesnocancel('Delete Children?', message='Selected entry has children. Delete all children?')
            if response is not True:
                return
        self.schema_viewer.delete_entry(selected)
        self.variables.unsaved_edits = True
        self.set_current_id(None)

    def callback_move_up(self):
        if not self._verify_selected():
            return
        selected = self.variables.current_id

        result = self.label_schema.reorder_child_element(selected, spaces=-1)
        if result:
            self.schema_viewer.rerender_entry(selected)
            self.variables.unsaved_edits = True

    def callback_move_down(self):
        if not self._verify_selected():
            return
        selected = self.variables.current_id

        result = self.label_schema.reorder_child_element(selected, spaces=1)
        if result:
            self.schema_viewer.rerender_entry(selected)
            self.variables.unsaved_edits = True

    def callback_save_entry(self):
        if self.entry.save_function():
            self.schema_viewer.rerender_entry(self.entry.id_changed)
            self.set_current_id(self.entry.id_changed)
            self.entry.close_window()
            self.entry_popup.grab_release()

    # noinspection PyUnusedLocal
    def item_selected_on_viewer(self, event):
        item_id = self.schema_viewer.treeview.focus()
        if item_id == '':
            return
        self.set_current_id(item_id)


def main(label_schema=None):
    """
    Main method for initializing the tool

    Parameters
    ----------
    label_schema : None|str|LabelSchema
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = SchemaEditor(root, label_schema=label_schema)

    root.mainloop()


if __name__ == '__main__':
    if __name__ == '__main__':
        import argparse

        parser = argparse.ArgumentParser(
            description="Open the labeling schema editing tool with optional input file.",
            formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument(
            '-i', '--input', metavar='input', default=None,
            help='The path to the existing schema file for opening.')
        args = parser.parse_args()

        main(label_schema=args.input)
