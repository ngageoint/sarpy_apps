"""
A tool for creating basic annotations on an image
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from typing import Union, List

import tkinter
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesno, askyesnocancel

from tk_builder.widgets import basic_widgets, widget_descriptors
from tk_builder.panel_builder import WidgetPanelNoLabel
from tk_builder.panels.image_panel import ImagePanel

from sarpy.annotation.base import AnnotationCollection, AnnotationFeature, GeometryProperties


class NamePanel(WidgetPanelNoLabel):
    """
    A simple panel for name display
    """

    _widget_list = ('name_label', 'name_value')
    name_label = widget_descriptors.LabelDescriptor(
        'name_label', default_text='Name:')  # type: basic_widgets.Label
    name_value = widget_descriptors.EntryDescriptor(
        'name_value', default_text='<no name>')  # type: basic_widgets.Entry

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
        WidgetPanelNoLabel.__init__(self, master)
        self.init_w_horizontal_layout()
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


class AnnotateDetailsPanel(WidgetPanelNoLabel):
    """
    A panel for displaying the basic details of the annotation
    """

    _widget_list = (
        ('directory_label', 'directory_value'),
        ('applicable_label', 'applicable_value'),
        ('description_label', 'description_value'))
    directory_label = widget_descriptors.LabelDescriptor(
        'directory_label', default_text='Directory:')  # type: basic_widgets.Label
    directory_value = widget_descriptors.ComboboxDescriptor(
        'directory_value', default_text='')  # type: basic_widgets.Combobox

    applicable_label = widget_descriptors.LabelDescriptor(
        'applicable_label', default_text='Applicable\nIndices:')  # type: basic_widgets.Label
    applicable_value = widget_descriptors.EntryDescriptor(
        'applicable_value', default_text='')  # type: basic_widgets.Entry

    description_label = widget_descriptors.LabelDescriptor(
        'description_label', default_text='Description:')  # type: basic_widgets.Label
    description_value = widget_descriptors.TextDescriptor(
        'description_value')  # type: basic_widgets.Text

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
        WidgetPanelNoLabel.__init__(self, master)
        self.init_w_rows()
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
            self.description_value.delete('1.0', 'end')
        else:
            self.description_value.delete('1.0', 'end')
            self.description_value.insert(tkinter.END, value)

    def _get_description(self):
        # type: () -> Union[None, str]
        value = self.description_value.get("1.0", 'end').strip()
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

class GeometryButtons(WidgetPanelNoLabel):
    _widget_list = ('label', 'point', 'line', 'rectangle', 'ellipse', 'polygon')
    label = widget_descriptors.LabelDescriptor(
        'label', default_text='Add Geometry:')  # type: basic_widgets.Label
    point = widget_descriptors.ButtonDescriptor(
        'point', default_text='Point')  # type: basic_widgets.Button
    line = widget_descriptors.ButtonDescriptor(
        'line', default_text='Line')  # type: basic_widgets.Button
    rectangle = widget_descriptors.ButtonDescriptor(
        'rectangle', default_text='Rectangle')  # type: basic_widgets.Button
    ellipse = widget_descriptors.ButtonDescriptor(
        'ellipse', default_text='Ellipse')  # type: basic_widgets.Button
    polygon = widget_descriptors.ButtonDescriptor(
        'polygon', default_text='Polygon')  # type: basic_widgets.Button

    def __init__(self, master):
        """

        Parameters
        ----------
        master
            The parent widget
        """

        WidgetPanelNoLabel.__init__(self, master)
        self.init_w_horizontal_layout()


class GeometryPropertiesPanel(WidgetPanelNoLabel):
    """
    A panel for displaying the basic geometry properties
    """
    _widget_list = (
        ('uid_label', 'uid_value'),
        ('name_label', 'name_value'),
        ('color_label', 'color_button'))
    uid_label = widget_descriptors.LabelDescriptor(
        'uid_label', default_text='UID:')  # type: basic_widgets.Label
    uid_value = widget_descriptors.LabelDescriptor(
        'uid_value', default_text='')  # type: basic_widgets.Label

    name_label = widget_descriptors.LabelDescriptor(
        'name_label', default_text='Name:')  # type: basic_widgets.Label
    name_value = widget_descriptors.EntryDescriptor(
        'name_value', default_text='<no name>')  # type: basic_widgets.Entry

    color_label = widget_descriptors.LabelDescriptor(
        'color_label', default_text='Color:')  # type: basic_widgets.Label
    color_button = widget_descriptors.ButtonDescriptor(
        'color_button', default_text='')  # type: basic_widgets.Button

    def __init__(self, master, geometry_properties=None):
        """

        Parameters
        ----------
        master
            The parent widget
        geometry_properties : None|GeometryProperties
        """

        self.default_color = '#dd0088'
        self.default_name = '<no name>'
        self.geometry_properties = None  # type: Union[None, GeometryProperties]
        self.color = None  # type: Union[None, str]
        WidgetPanelNoLabel.__init__(self, master)
        self.init_w_rows()
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


class GeometryDetailsPanel(WidgetPanelNoLabel):
    """
    A panel for displaying the basic geometry details
    """

    _widget_list = (
        ('geometry_buttons', ),
        ('geometry_view', 'geometry_properties'))
    geometry_buttons = widget_descriptors.TypedDescriptor(
        'geometry_buttons', GeometryButtons, docstring='the button panel')  # type: GeometryButtons
    geometry_view = widget_descriptors.TreeviewDescriptor(
        'geometry_view', docstring='the geometry viewer')  # type: basic_widgets.Treeview
    geometry_properties = widget_descriptors.TypedDescriptor(
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
        WidgetPanelNoLabel.__init__(self, master)
        self.init_w_rows()
        self.geometry_view.heading('#0', text='Name')
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


class AnnotateTabControl(WidgetPanelNoLabel):
    # todo: assemble the AnnotateDetailsPanel and GeometryDetailsPanels
    #  and set up callbacks
    #   what else am I missing???
    pass


class AnnotationPanel(WidgetPanelNoLabel):
    _widget_list = (
        ('name panel', ),
        ('tab_control', ),
        ('cancel_button', 'apply_button'))

    cancel_button = widget_descriptors.ButtonDescriptor(
        'cancel_button', default_text='Cancel', docstring='')  # type: basic_widgets.Button
    apply_button = widget_descriptors.ButtonDescriptor(
        'apply_button', default_text='Apply', docstring='')  # type: basic_widgets.Button




