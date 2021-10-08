"""
A tool for creating basic annotations on an image
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

import logging
from typing import Union, List, Sequence

import tkinter
from tkinter import ttk, Button as tk_button
from tkinter.messagebox import showinfo, askyesno, askyesnocancel

from tk_builder.widgets.basic_widgets import Frame, Label, Entry, Button, \
    Combobox, Notebook
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling, TextWithScrolling
from tkinter.scrolledtext import ScrolledText
from tk_builder.widgets.widget_descriptors import LabelDescriptor, ButtonDescriptor, \
    EntryDescriptor, ComboboxDescriptor, TypedDescriptor
from tk_builder.panels.image_panel import ImagePanel

from sarpy.annotation.base import AnnotationCollection, AnnotationFeature, \
    GeometryProperties


logger = logging.getLogger(__name__)


class NamePanel(Frame):
    """
    A simple panel for name display
    """

    name_label = LabelDescriptor(
        'name_label', default_text='Name:')  # type: Label
    name_value = EntryDescriptor(
        'name_value', default_text='<no name>')  # type: Entry

    def __init__(self, master, annotation_feature=None):
        """

        Parameters
        ----------
        master
            The parent widget
        annotation_feature : None|AnnotationFeature
        """

        self.default_name = '<no name>'
        self.annotation_feature = None  # type: Union[None, AnnotationFeature]
        Frame.__init__(self, master)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.name_label = Label(self, text='Name:', width=12)
        self.name_label.grid(row=0, column=0, sticky='NW')

        self.name_value = Entry(self, text=self.default_name, width=12)
        self.name_value.grid(row=0, column=1, sticky='NEW')

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.set_annotation_feature(annotation_feature)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        if annotation_feature is None or annotation_feature.properties is None:
            self._set_name_value(None)
            return
        self._set_name_value(annotation_feature.properties.name)

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
        self.annotation_feature.properties.name = self._get_name_value()


class AnnotateDetailsPanel(Frame):
    """
    A panel for displaying the basic details of the annotation
    """

    directory_label = LabelDescriptor(
        'directory_label', default_text='Directory:')  # type: Label
    directory_value = ComboboxDescriptor(
        'directory_value', default_text='')  # type: Combobox

    applicable_label = LabelDescriptor(
        'applicable_label', default_text='Applicable\nIndices:')  # type: Label
    applicable_value = EntryDescriptor(
        'applicable_value', default_text='')  # type: Entry

    description_label = LabelDescriptor(
        'description_label', default_text='Description:')  # type: Label
    description_value = TypedDescriptor(
        'description_value', TextWithScrolling)  # type: TextWithScrolling

    def __init__(self, master, annotation_feature=None, annotation_collection=None):
        """

        Parameters
        ----------
        master
            The parent widget
        annotation_feature : None|AnnotationFeature
        annotation_collection : None|AnnotationCollection
        """

        self.annotation_feature = None  # type: Union[None, AnnotationFeature]
        self.annotation_collection = None  # type: Union[None, AnnotationCollection]
        self.directory_values = set()
        Frame.__init__(self, master)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.directory_label = Label(self, text='Directory:', width=12)
        self.directory_label.grid(row=0, column=0, sticky='NW', padx=5, pady=5)
        self.directory_value = Combobox(self, text='')
        self.directory_value.grid(row=0, column=1, sticky='NEW', padx=5, pady=5)

        self.applicable_label = Label(self, text='Applicable\nIndices:', width=12)
        self.applicable_label.grid(row=1, column=0, sticky='NW', padx=5, pady=5)
        self.applicable_value = Entry(self, text='')
        self.applicable_value.grid(row=1, column=1, sticky='NEW', padx=5, pady=5)

        self.description_label = Label(self, text='Description:', width=12)
        self.description_label.grid(row=2, column=0, sticky='NW', padx=5, pady=5)
        self.description_value = TextWithScrolling(self)
        self.description_value.frame.grid(row=2, column=1, sticky='NSEW', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.set_annotation_collection(annotation_feature, annotation_collection)

    def _set_directory(self, value):
        # type: (Union[None, str]) -> None
        self.directory_value.set_text('' if value is None else value)

    def _get_directory(self):
        # type: () -> str
        value = self.directory_value.get().strip()
        return None if value == '' else value

    def _set_applicable_value(self, value):
        # type: (Union[None, List[int]]) -> None
        if value is None:
            self.applicable_value.set_text('')
        else:
            self.applicable_value.set_text(
                ' '.join('{0:d}'.format(entry) for entry in value))

    def _get_applicable_value(self):
        # type: () -> Union[None, List[int]]

        value = self.directory_value.get().strip()
        if value == '':
            return None

        parts = value.split()
        # noinspection PyBroadException
        try:
            parts = sorted([int(entry) for entry in parts])
            return parts
        except Exception:
            showinfo(
                'applicable indices un-parseable',
                message='The applicable indices value must be a space delimited\n\t'
                        'list of integers. The current value was un-parseable, '
                        'and not saved.')
            return []

    def _set_description(self, value):
        # type: (Union[None, str]) -> None
        if value is None:
            value = ''
        self.description_value.set_value(value)

    def _get_description(self):
        # type: () -> Union[None, str]
        value = self.description_value.get_value().strip()
        return None if value == '' else value

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        if annotation_feature is None or annotation_feature.properties is None:
            self._set_directory(None)
            self._set_applicable_value(None)
            self._set_description(None)
            return

        properties = annotation_feature.properties
        self._set_directory(properties.directory)
        self._set_applicable_value(properties.applicable_indices)
        self._set_description(properties.description)

    def set_annotation_collection(self, annotation_feature, annotation_collection):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        annotation_collection : None|AnnotationCollection
        """

        self.annotation_collection = annotation_collection
        self.directory_values = set()
        if annotation_collection is not None:
            for entry in annotation_collection.features:
                dir_value = entry.properties.directory
                dir_parts = dir_value.split('/')
                for i in range(1, len(dir_parts)):
                    intermediate = '/'.join(dir_parts[:i])
                    self.directory_values.add(intermediate)
        self.directory_value.update_combobox_values(sorted(list(self.directory_values)))
        # populate the combobox values here?
        self.set_annotation_feature(annotation_feature)

    def cancel(self):
        self.set_annotation_feature(self.annotation_feature)

    def save(self):
        if self.annotation_feature is None or self.annotation_feature.properties is None:
            return

        self.annotation_feature.properties.directory = self._get_directory()
        app_inds = self._get_applicable_value()
        if app_inds is not None and app_inds != []:
            # handling the unparseable case - don't populate then
            self.annotation_feature.properties.applicable_indices = app_inds
        self.annotation_feature.properties.description = self._get_description()


###########
# Geometry details parts

class GeometryButtons(Frame):
    _shapes = ('point', 'line', 'rectangle', 'ellipse', 'polygon')
    label = LabelDescriptor(
        'label', default_text='Add Geometry:')  # type: Label
    point = ButtonDescriptor(
        'point', default_text='Point')  # type: Button
    line = ButtonDescriptor(
        'line', default_text='Line')  # type: Button
    rectangle = ButtonDescriptor(
        'rectangle', default_text='Rectangle')  # type: Button
    ellipse = ButtonDescriptor(
        'ellipse', default_text='Ellipse')  # type: Button
    polygon = ButtonDescriptor(
        'polygon', default_text='Polygon')  # type: Button

    def __init__(self, master, active_shapes=None):
        """

        Parameters
        ----------
        master
            The parent widget
        active_shapes : None|Sequence[str]
            The active shapes.
        """

        self.active_shapes = None
        Frame.__init__(self, master)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.label = Label(self, text='Add Geometry:')
        self.label.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.point = Button(self, text='Point')
        self.point.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.line = Button(self, text='Line')
        self.line.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.rectangle = Button(self, text='Rectangle')
        self.rectangle.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.ellipse = Button(self, text='Ellipse')
        self.ellipse.pack(side=tkinter.LEFT, padx=5, pady=5)
        self.polygon = Button(self, text='Polygon')
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
    _widget_list = (
        ('uid_label', 'uid_value'),
        ('name_label', 'name_value'),
        ('color_label', 'color_button'))
    uid_label = LabelDescriptor(
        'uid_label', default_text='UID:')  # type: Label
    uid_value = LabelDescriptor(
        'uid_value', default_text='')  # type: Label

    name_label = LabelDescriptor(
        'name_label', default_text='Name:')  # type: Label
    name_value = EntryDescriptor(
        'name_value', default_text='<no name>')  # type: Entry

    color_label = LabelDescriptor(
        'color_label', default_text='Color:')  # type: Label
    color_button = TypedDescriptor(
        'color_button', tk_button)  # type: tk_button

    def __init__(self, master, geometry_properties=None):
        """

        Parameters
        ----------
        master
            The parent widget
        geometry_properties : None|GeometryProperties
        """

        self.default_color = '#ff0066'
        self.default_name = '<no name>'
        self.geometry_properties = None  # type: Union[None, GeometryProperties]
        self.color = None  # type: Union[None, str]
        Frame.__init__(self, master)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.uid_label = Label(self, text='UID:')
        self.uid_label.grid(row=0, column=0, padx=3, pady=3, sticky='NW')
        self.uid_value = Label(self, text='', width=25)
        self.uid_value.grid(row=0, column=1, padx=3, pady=3, sticky='NEW')

        self.name_label = Label(self, text='Name:')
        self.name_label.grid(row=1, column=0, padx=3, pady=3, sticky='NW')
        self.name_value = Entry(self, text=self.default_name, width=25)
        self.name_value.grid(row=1, column=1, padx=3, pady=3, sticky='NEW')

        self.color_label = Label(self, text='Color:')
        self.color_label.grid(row=2, column=0, padx=3, pady=3, sticky='NW')
        self.color_button = tk_button(self, bg=self.default_color, text='')
        self.color_button.grid(row=2, column=1, padx=3, pady=3, sticky='NEW')

        self.set_geometry_properties(geometry_properties)

    def _set_uid_value(self, value):
        if value is None:
            value = ''
        self.uid_value.set_text(value)

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

    def set_geometry_properties(self, geometry_properties):
        """

        Parameters
        ----------
        geometry_properties : None|GeometryProperties
        """

        self.geometry_properties = geometry_properties
        if geometry_properties is None:
            self._set_uid_value(None)
            self._set_name_value(None)
            self._set_color(None)
        else:
            self._set_uid_value(geometry_properties.uid)
            self._set_name_value(geometry_properties.name)
            self._set_color(geometry_properties.color)

    def cancel(self):
        self.set_geometry_properties(self.geometry_properties)

    def save(self):
        self.geometry_properties.name = self._get_name_value()
        self.geometry_properties.color = self._get_color()


class GeometryDetailsPanel(Frame):
    """
    A panel for displaying the basic geometry details
    """

    geometry_buttons = TypedDescriptor(
        'geometry_buttons', GeometryButtons, docstring='the button panel')  # type: GeometryButtons
    geometry_view = TypedDescriptor(
        'geometry_view', TreeviewWithScrolling, docstring='the geometry viewer')  # type: TreeviewWithScrolling
    geometry_properties = TypedDescriptor(
        'geometry_properties', GeometryPropertiesPanel,
        docstring='the geometry properties')  # type: GeometryPropertiesPanel

    def __init__(self, master, annotation_feature=None):
        """

        Parameters
        ----------
        master
            The parent widget
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = None  # type: Union[None, AnnotationFeature]
        self.selected_geometry_uid = None
        Frame.__init__(self, master)
        self.geometry_buttons = GeometryButtons(self, active_shapes=None)
        self.geometry_buttons.grid(row=0, column=0, columnspan=2, sticky='NEW', padx=3, pady=3)

        self.geometry_view = TreeviewWithScrolling(self)
        self.geometry_view.heading('#0', text='Name')
        self.geometry_view.frame.grid(row=1, column=0, sticky='NSEW', padx=3, pady=3)  # NB: reference the frame for packing

        self.geometry_properties = GeometryPropertiesPanel(self)
        self.geometry_properties.grid(row=1, column=1, sticky='NSEW', padx=3, pady=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.set_annotation_feature(annotation_feature)

        # configure the callback for treeview element selection
        self.geometry_view.bind('<<TreeviewSelect>>', self.geometry_selected_on_viewer)

    def _set_focus(self, index):
        self.geometry_view.selection_set(index)

    def _set_geometry_index(self, index):
        geometry_property = self.annotation_feature.properties.geometry_properties[index]
        self.selected_geometry_uid = geometry_property.uid
        self.geometry_properties.set_geometry_properties(geometry_property)

    def _render_entry(self, index):
        name = self.annotation_feature.properties.geometry_properties[index].name
        if name is None:
            name = '<no name>'
        self.geometry_view.item(index, text=name)

    def geometry_selected_on_viewer(self):
        geometry_index = self.geometry_view.focus()
        self._set_geometry_index(geometry_index)

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.

        Returns
        -------
        None
        """

        self.geometry_view.delete(*self.geometry_view.get_children())

    def _fill_treeview(self):
        if self.annotation_feature is None or self.annotation_feature.geometry_count == 0:
            self._empty_entries()
            self.geometry_properties.set_geometry_properties(None)
            return
        if self.annotation_feature.properties.geometry_properties is None:
            self.geometry_properties.set_geometry_properties(None)
            self._empty_entries()
            showinfo(
                'No geometry properties defined',
                message='Feature id `{}` has no geometry properties,\n\t'
                        'but some geometry. '
                        'You cannot edit any details here.'.format(self.annotation_feature.uid))
            return

        if self.annotation_feature.geometry_count != len(self.annotation_feature.properties.geometry_properties):
            self.geometry_properties.set_geometry_properties(None)
            self._empty_entries()
            showinfo(
                'geometry properties does not match geometry elements',
                message='Feature id `{}` has a mismatch between the geometry elements\n\t'
                        'and the defined geometry properties. '
                        'You cannot edit any details here.'.format(self.annotation_feature.uid))
            return
        for i, properties in enumerate(self.annotation_feature.properties.geometry_properties):
            name = properties.name
            if name is None:
                name = '<no name>'
            self.geometry_view.insert('', 'end', iid=i, text=name)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.annotation_feature = annotation_feature
        self._fill_treeview()

    def cancel(self):
        self.geometry_properties.cancel()
        self._fill_treeview()

    def save(self):
        self.geometry_properties.save()
        self._fill_treeview()


class AnnotateTabControl(Frame):
    """
    A tab control panel which holds the feature details panels
    """

    tab_control = TypedDescriptor(
        'tab_control', Notebook)  # type: Notebook

    def __init__(self, master, annotation_feature=None, annotation_collection=None):
        Frame.__init__(self, master)

        self.tab_control = Notebook(self)
        self.details_tab = AnnotateDetailsPanel(
            self.tab_control,
            annotation_feature=annotation_feature,
            annotation_collection=annotation_collection)
        self.geometry_tab = GeometryDetailsPanel(
            self.tab_control,
            annotation_feature=annotation_feature)

        self.tab_control.add(self.details_tab, text='Overall')
        self.tab_control.add(self.geometry_tab, text='Geometry')
        self.tab_control.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """

        self.details_tab.set_annotation_feature(annotation_feature)
        self.geometry_tab.set_annotation_feature(annotation_feature)

    def set_annotation_collection(self, annotation_feature, annotation_collection):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        annotation_collection : None|AnnotationCollection
        """

        self.details_tab.set_annotation_collection(annotation_feature, annotation_collection)
        self.geometry_tab.set_annotation_feature(annotation_feature)

    def cancel(self):
        self.details_tab.cancel()
        self.geometry_tab.cancel()

    def save(self):
        self.details_tab.save()
        self.geometry_tab.save()


class AnnotateButtons(Frame):
    _widget_list = ('cancel_button', 'apply_button')
    cancel_button = ButtonDescriptor(
        'cancel_button', default_text='Cancel', docstring='')  # type: Button
    save_button = ButtonDescriptor(
        'save_button', default_text='Save', docstring='')  # type: Button

    def __init__(self, master):
        Frame.__init__(self, master)
        self.config(borderwidth=2, relief=tkinter.RIDGE)

        self.cancel_button = Button(self, text='Cancel')
        self.cancel_button.pack(side=tkinter.RIGHT, padx=3, pady=3)
        self.save_button = Button(self, text='Save')
        self.save_button.pack(side=tkinter.RIGHT, padx=3, pady=3)


class AnnotationPanel(Frame):
    name_panel = TypedDescriptor('name_panel', NamePanel)  # type: NamePanel
    tab_panel = TypedDescriptor('tab_panel', AnnotateTabControl)  # type: AnnotateTabControl
    button_panel = TypedDescriptor('button_panel', AnnotateButtons)  # type: AnnotateButtons

    def __init__(self, master, annotation_feature=None, annotation_collection=None):
        Frame.__init__(self, master)

        self.name_panel = NamePanel(self, annotation_feature=annotation_feature)
        self.name_panel.grid(row=0, column=0, sticky='NSEW')

        self.tab_panel = AnnotateTabControl(self, annotation_feature=annotation_feature, annotation_collection=annotation_collection)
        self.tab_panel.grid(row=1, column=0, sticky='NSEW')

        self.button_panel = AnnotateButtons(self)
        self.button_panel.grid(row=2, column=0, sticky='NSEW')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # todo: more buttons/bind button commands?
        self.button_panel.cancel_button.config(command=self.cancel)
        self.button_panel.save_button.config(command=self.save)

    def set_annotation_feature(self, annotation_feature):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        """
        self.name_panel.set_annotation_feature(annotation_feature)
        self.tab_panel.set_annotation_feature(annotation_feature)

    def set_annotation_collection(self, annotation_feature, annotation_collection):
        """

        Parameters
        ----------
        annotation_feature : None|AnnotationFeature
        annotation_collection : None|AnnotationCollection
        """
        self.name_panel.set_annotation_feature(annotation_feature)
        self.tab_panel.set_annotation_collection(annotation_feature, annotation_collection)

    def cancel(self):
        self.name_panel.cancel()
        self.tab_panel.cancel()

    def save(self):
        self.name_panel.save()
        self.tab_panel.save()


def main(reader=None):
    """
    Main method for initializing the annotation_tool

    Parameters
    ----------
    reader : None|str|BaseReader|CanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # todo: what is the app?
    # app = RegionSelection(root)
    # root.geometry("1000x800")
    # if reader is not None:
    #     app.update_reader(reader)
    #
    # root.mainloop()


if __name__ == '__main__':
    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = AnnotationPanel(root)
    app.pack(expand=tkinter.TRUE, fill=tkinter.BOTH)
    root.geometry("600x600")
    root.mainloop()