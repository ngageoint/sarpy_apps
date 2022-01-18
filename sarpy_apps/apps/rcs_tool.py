"""
This is a tool for inspection of the Radar Cross Section (RCS) and Radiometric calibration
"""

__classification__ = 'UNCLASSIFIED'
__author__ = 'Thomas McCullough'

import os
from typing import Union

import numpy

import tkinter
from tkinter import ttk, PanedWindow

from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename, asksaveasfilename

from tk_builder.base_elements import TypedDescriptor, StringDescriptor
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.widgets.basic_widgets import Frame, Button, Label, Combobox
from tk_builder.widgets.derived_widgets import TreeviewWithScrolling

from sarpy_apps.apps.annotation_tool import AppVariables as AppVariables_Annotate, \
    NamePanel, AnnotateButtons, AnnotateTabControl, AnnotationPanel, \
    AnnotationCollectionViewer, AnnotationCollectionPanel, AnnotationTool
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.file_filters import all_files, json_files
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.annotation.rcs import FileRCSCollection, RCSFeature, RCSValueCollection
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.complex.converter import open_complex


class AppVariables(AppVariables_Annotate):
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileRCSCollection,
        docstring='The file annotation collection.')  # type: FileRCSCollection
    image_reader = TypedDescriptor(
        'image_reader', SICDTypeCanvasImageReader, docstring='')  # type: SICDTypeCanvasImageReader
    rcs_viewer_units = StringDescriptor(
        'rcs_viewer_units', default_value='')  # type: str

    def get_current_annotation_object(self):
        """
        Gets the current annotation object

        Returns
        -------
        None|RCSFeature
        """

        if self._current_feature_id is None:
            return None
        return self.file_annotation_collection.annotations[self._current_feature_id]

    def get_rcs_units(self):
        if self.image_reader is None:
            return []

        sicd = self.image_reader.get_sicd()
        if sicd.Radiometric is None:
            return ['TotalPixelPower', 'PixelPower']
        else:
            return ['TotalRCS', 'PixelPower', 'RCS', 'BetaZero', 'GammaZero', 'SigmaZero']


class RCSSpecificsPanel(TreeviewWithScrolling):
    def __init__(self, master, app_variables, **kwargs):
        """

        Parameters
        ----------
        master
        app_variables : AppVariables
        kwargs
        """

        self.app_variables = app_variables
        self.current_rcs_values = None  # type: Union[None, RCSValueCollection]
        # NB: "units" is really first...
        kwargs['columns'] = ('mean_db', 'mean', 'std', 'max', 'min')

        TreeviewWithScrolling.__init__(self, master, **kwargs)
        self.heading('#0', text='Name')
        self.column('#0', width=10)
        self.heading('#1', text='Mean[dB]')
        self.column('#1', width=10)
        self.heading('#2', text='Mean[power]')
        self.column('#2', width=10)
        self.heading('#3', text='Std[power]')
        self.column('#3', width=10)
        self.heading('#4', text='Min[power]')
        self.column('#4', width=10)
        self.heading('#5', text='Max[power]')
        self.column('#5', width=10)

    def _empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.
        """

        self.delete(*self.get_children())

    def _fill(self):
        """
        Fill based on the current annotation.
        """

        self._empty_entries()
        if self.current_rcs_values is None:
            return

        for entry in self.app_variables.get_rcs_units():
            self.insert('', 'end', iid=entry, text=entry, values=('', '', '', '', ''))

        for entry in self.current_rcs_values:
            iid = '{}-{}'.format(entry.units, entry.index)
            self.insert(
                entry.units, 'end', iid=iid+'-value', text='{}-{}'.format(entry.polarization, entry.index),
                values=('', '', '', '', '') if entry.value is None else entry.value.get_field_list())
            self.insert(
                iid+'-value', 'end', iid=iid+'-noise', text='Noise',
                values=('', '', '', '', '') if entry.noise is None else entry.noise.get_field_list())

    def set_annotation_feature(self, annotation_feature):
        self.current_rcs_values = None if annotation_feature is None else annotation_feature.properties.parameters
        self._fill()

    def update_annotation(self):
        annotation_feature = self.app_variables.get_current_annotation_object()
        self.set_annotation_feature(annotation_feature)

    def cancel(self):
        self._fill()  # probably unnecessary

    def save(self):
        self._fill()  # probably unnecessary


#############
# refactoring from annotation to accommodate minor differences in the basic elements

class RCSTabControl(AnnotateTabControl):
    def __init__(self, master, app_variables, **kwargs):
        AnnotateTabControl.__init__(self, master, app_variables, **kwargs)
        self.rcs_tab = RCSSpecificsPanel(self, app_variables)
        self.tab_control.add(self.rcs_tab.frame, text='RCS')
        # NB: pack the frame, since the treeview is already packed into a frame

        self.geometry_tab.geometry_buttons.set_active_shapes(['rectangle', 'ellipse', 'polygon'])

    def update_annotation(self):
        self.details_tab.update_annotation()
        self.geometry_tab.update_annotation()
        self.rcs_tab.update_annotation()

    def update_annotation_collection(self):
        self.details_tab.update_annotation_collection()
        self.geometry_tab.update_annotation()
        self.rcs_tab.update_annotation()

    def cancel(self):
        self.details_tab.cancel()
        self.geometry_tab.cancel()
        self.rcs_tab.cancel()

    def save(self):
        self.details_tab.save()
        self.geometry_tab.save()
        self.rcs_tab.save()


class RCSPanel(AnnotationPanel):
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

        self.tab_panel = RCSTabControl(self, app_variables)  # type: RCSTabControl
        self.tab_panel.grid(row=1, column=0, sticky='NSEW')

        self.button_panel = AnnotateButtons(self)  # type: AnnotateButtons
        self.button_panel.grid(row=2, column=0, sticky='NSEW')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)


class RCSCollectionViewer(AnnotationCollectionViewer):

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
        self.heading('#1', text='Value [dB]')
        self.update_annotation_collection()

    @property
    def annotation_collection(self):
        """
        FileRCSCollection : The file annotation collection
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
        if annotation.properties.parameters is None:
            value = ''
        else:
            value = 'NaN'
            the_index = self._app_variables.image_reader.index
            the_units = self._app_variables.rcs_viewer_units
            for entry in annotation.properties.parameters:
                if entry.units == the_units and entry.index == the_index:
                    if entry.value is not None and entry.value.mean is not None and entry.value.mean > 0:
                        value = '{0:0.5G}'.format(10*numpy.log10(entry.value.mean))
                    break
        name = annotation.get_name()
        self.insert(parent, at_index, the_id, text=name, values=(value, ))


class RCSCollectionPanel(AnnotationCollectionPanel):
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

        self.app_variables = app_variables
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
        self.frame1 = Frame(self.button_panel)
        self.units_label = Label(self.frame1, text='Units:', relief=tkinter.RIDGE)
        self.units_label.pack(side=tkinter.LEFT)
        self.units_value = Combobox(self.frame1, text='')
        self.units_value.pack(side=tkinter.LEFT)
        self.frame1.grid(row=4, column=0, sticky='NW')
        self.button_panel.grid(row=0, column=0, sticky='NSEW')

        self.viewer = RCSCollectionViewer(self, app_variables)
        self.viewer.frame.grid(row=1, column=0, sticky='NSEW')
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.units_value.on_selection(self.callback_units_select)

    # noinspection PyUnusedLocal
    def callback_units_select(self, event):
        self.app_variables.rcs_viewer_units = self.units_value.get()
        self.update_annotation_collection()

    def update_annotation_collection(self):
        """
        Should be called on an update of the annotation collection
        """

        current_units = self.units_value.get()
        values = self.app_variables.get_rcs_units()
        self.units_value.update_combobox_values(values)
        if len(values) == 0:
            self.units_value.set_text('')
            self.app_variables.rcs_viewer_units = ''
        elif current_units in values:
            self.units_value.set_text(current_units)
            self.app_variables.rcs_viewer_units = current_units
        elif self.app_variables.rcs_viewer_units in values:
            self.units_value.set_text(self.app_variables.rcs_viewer_units)
        else:
            self.units_value.set(values[0])
            self.app_variables.rcs_viewer_units = values[0]

        self.viewer.update_annotation_collection()


class RCSTool(AnnotationTool):
    _NEW_ANNOTATION_TYPE = RCSFeature
    _NEW_FILE_ANNOTATION_TYPE = FileRCSCollection

    def __init__(self, master, reader=None, annotation_collection=None, **kwargs):
        """

        Parameters
        ----------
        master
            tkinter.Tk|tkinter.TopLevel
        reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
        annotation_collection : None|str|FileRCSCollection
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

        self.collection_panel = RCSCollectionPanel(self, self.variables)  # type: RCSCollectionPanel

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
        self.image_panel.canvas.bind('<<ShapeCoordsEdit>>', self.shape_finalized_on_canvas)  # is this too much?
        self.image_panel.canvas.bind('<<ShapeCoordsFinalized>>', self.shape_finalized_on_canvas)
        self.image_panel.canvas.bind('<<ShapeDelete>>', self.shape_delete_on_canvas)
        self.image_panel.canvas.bind('<<ShapeSelect>>', self.shape_selected_on_canvas)

        # set up the label_panel viewer event listeners
        self.collection_panel.viewer.bind('<<TreeviewSelect>>', self.feature_selected_on_viewer)

        self.annotate_popup = tkinter.Toplevel(master)
        self.annotate_popup.geometry('600x400')
        self.annotate = RCSPanel(self.annotate_popup, self.variables)  # type: RCSPanel
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

        self.set_reader(reader)
        self.set_annotations(annotation_collection)
        self.annotate.update_annotation_collection()

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "RCS Tool"
        else:
            the_title = "RCS Tool for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def set_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
            the_reader = open_complex(the_reader)

        if isinstance(the_reader, SICDTypeReader):
            the_reader = SICDTypeCanvasImageReader(the_reader)

        if not isinstance(the_reader, SICDTypeCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        data_sizes = the_reader.base_reader.get_data_size_as_tuple()

        if len(data_sizes) > 1:
            rep_size = data_sizes[0]
            for entry in data_sizes:
                if rep_size != entry:
                    showinfo(
                        'Differing image sizes',
                        message='Annotation requires that all images in the reader have the same size. Aborting.')
                    return

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_title()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()

        self.set_annotations(None)
        self.show_valid_data()

    def select_annotation_file(self):
        if not self._verify_image_selected():
            return

        # prompt for any unsaved changes
        response = self._prompt_unsaved()
        if not response:
            return

        browse_dir, image_fname = os.path.split(self.image_file_name)
        # guess at a sensible initial file name
        init_file = '{}.rcs.json'.format(image_fname)
        if not os.path.exists(os.path.join(browse_dir, init_file)):
            init_file = ''

        annotation_fname = askopenfilename(
            title='Select RCS annotation file for image file {}'.format(image_fname),
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

        self.set_annotations(None)

    def _prompt_annotation_file_name(self):
        if self.image_file_name is not None:
            browse_dir, image_fname = os.path.split(self.image_file_name)
        else:
            browse_dir = self.variables.browse_directory
            image_fname = 'Unknown_Image'

        annotation_fname = asksaveasfilename(
            title='Select output annotation file name for image file {}'.format(image_fname),
            initialdir=browse_dir,
            initialfile='{}.rcs.json'.format(image_fname),
            filetypes=[json_files, all_files])

        if annotation_fname in ['', ()]:
            annotation_fname = None
        return annotation_fname

    def _delete_geometry(self, geometry_id):
        """
        Removes the given geometry.

        Parameters
        ----------
        geometry_id : str
        """

        if self.variables.current_geometry_id == geometry_id:
            self.set_current_geometry_id(None)

        canvas_id = self.variables.get_canvas_for_geometry(geometry_id)
        if canvas_id is not None:
            # get the feature and get rid of the geometry
            feature_id = self.variables.get_feature_for_canvas(canvas_id)
            feature = self.variables.file_annotation_collection.annotations[feature_id]
            feature.remove_geometry_element(geometry_id)
            feature.set_rcs_parameters_from_reader(self.variables.image_reader.base_reader)

        # remove geometry from tracking
        canvas_id = self.variables.delete_geometry_from_tracking(geometry_id)
        # remove canvas id from tracking, and delete the shape
        if canvas_id is not None:
            self.variables.delete_shape_from_tracking(canvas_id)
            self.image_panel.canvas.delete_shape(canvas_id)

        self.collection_panel.update_annotation()
        self.annotate.update_annotation()

    def _update_feature_geometry(self, feature_id, set_focus=False):
        """
        Updates the entry in the file annotation list, because the geometry has
        somehow changed.

        Parameters
        ----------
        feature_id : str
        """

        geometry = self._get_geometry_for_feature(feature_id)

        if feature_id is not None:
            annotation = self.variables.file_annotation_collection.annotations[feature_id]
            annotation.set_rcs_parameters_from_reader(self.variables.image_reader.base_reader)
            self.variables.file_annotation_collection.annotations[feature_id].geometry = geometry
            self.collection_panel.viewer.rerender_annotation(annotation.uid, set_focus=set_focus)
        self.annotate.update_annotation()
        self.variables.unsaved_changes = True

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

        if self.variables.current_feature_id is None:
            raise ValueError('No current feature')

        self.image_panel.canvas.current_shape_id = event.x
        self._add_shape_to_feature(
            self.variables.current_feature_id, event.x, set_focus=True, set_current=True)


def main(reader=None, annotation=None):
    """
    Main method for initializing the annotation_tool

    Parameters
    ----------
    reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
    annotation : None|str|FileRCSCollection
    """

    root = tkinter.Tk()
    root.geometry("1200x800")

    the_style = ttk.Style()
    the_style.theme_use('classic')

    # noinspection PyUnusedLocal
    app = RCSTool(root, reader=reader, annotation_collection=annotation)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the rcs tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None, nargs='?',
        help='The path to the optional image file for opening.')
    parser.add_argument(
        '-a', '--annotation', metavar='annotation', default=None,
        help='The path to the optional rcs annotation file. '
             'If the image input is not specified, then this has no effect. '
             'If both are specified, then a check will be performed that the '
             'annotation actually applies to the provided image.')
    this_args = parser.parse_args()

    main(reader=this_args.input, annotation=this_args.annotation)
