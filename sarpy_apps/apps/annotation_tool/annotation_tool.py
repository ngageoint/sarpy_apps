import os
from shutil import copyfile
import time
from collections import OrderedDict

import tkinter
from tkinter.messagebox import showinfo, askyesnocancel, askyesno
from tkinter.filedialog import askopenfilename, asksaveasfilename

import numpy

from sarpy_apps.apps.annotation_tool.panels.context_image_panel.context_image_panel import ContextImagePanel
from sarpy_apps.apps.annotation_tool.panels.annotate_image_panel import AnnotateImagePanel
from sarpy_apps.apps.annotation_tool.panels.annotation_popup import AnnotationPopup
from sarpy_apps.apps.annotation_tool.main_app_variables import AppVariables
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes import file_filters

from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.image_canvas import ToolConstants
from tk_builder.widgets import widget_descriptors

from sarpy.annotation.schema_processing import LabelSchema
from sarpy.annotation.annotate import FileAnnotationCollection, Annotation
from sarpy.geometry.geometry_elements import Polygon


__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class AnnotationTool(WidgetPanel):
    _widget_list = ("context_panel", "annotate_panel")
    context_panel = widget_descriptors.PanelDescriptor("context_panel", ContextImagePanel)  # type: ContextImagePanel
    annotate_panel = widget_descriptors.PanelDescriptor("annotate_panel", AnnotateImagePanel)  # type: AnnotateImagePanel

    def __init__(self, primary):
        self._schema_browse_directory = os.path.expanduser('~')
        self._image_brose_directory = os.path.expanduser('~')
        self.primary = tkinter.Frame(primary)

        WidgetPanel.__init__(self, primary)

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

    @property
    def image_file_selected(self):
        """
        bool: Has the image file been selected?
        """

        return self.image_file_name is not None

    # context callbacks
    def select_image_file(self):
        """
        Select the image callback.

        Returns
        -------
        None
        """

        fname = askopenfilename(title='Select image file',
                                initialdir=self._image_brose_directory,
                                filetypes=file_filters.nitf_preferred_filter)
        if fname == '' or fname == ():
            return

        self._image_brose_directory = os.path.split(fname)[0]
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
        if not self.image_file_selected:
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

        annotation_fname = None
        while annotation_fname is None:
            annotation_fname = asksaveasfilename(
                title='Select annotation file',
                initialdir=self._image_brose_directory,
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

        image_fname = os.path.basename(self.image_file_name)
        annotation_collection = FileAnnotationCollection(
            label_schema=label_schema, image_file_name=image_fname)
        self.initialize_geometry(annotation_fname, annotation_collection)

    def select_annotation_file(self):
        if not self.image_file_selected:
            showinfo('No Image Selected', message='First select an image file for annotation.')
            return

        annotation_fname = askopenfilename(
            initialdir=self._image_brose_directory,
            filetypes=[file_filters.json_files, file_filters.all_files])
        if annotation_fname in ['', ()]:
            return

        try:
            annotation_collection = FileAnnotationCollection.from_file(annotation_fname)
        except Exception as e:
            showinfo('File Annotation Error',
                     message='Opening annotation file {} failed with error {}. Aborting.'.format(annotation_fname, e))
            return

        # validate the the image selected matches the annottaion image name
        image_fname = os.path.basename(self.image_file_name)
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
            rect_id = self.context_panel.image_panel.canvas.variables.select_rect_id
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
        if self.annotate_panel.image_panel.canvas.variables.current_tool == ToolConstants.DRAW_POLYGON_BY_CLICKING:
            current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
            image_coords = self.annotate_panel.image_panel.canvas.get_shape_image_coords(current_canvas_shape_id)
            geometry_coords = numpy.asarray([x for x in zip(image_coords[0::2], image_coords[1::2])])
            polygon = Polygon(coordinates=[geometry_coords])

            # TODO: change this to create a new annotation from a feature, then update the features when the user
            # TODO: populuates the feature properties.
            annotation = Annotation()
            annotation.geometry = polygon

            self.variables.canvas_geom_ids_to_annotations_id_dict[str(current_canvas_shape_id)] = annotation

    def callback_set_to_draw_polygon(self):
        self.annotate_panel.image_panel.canvas.variables.current_shape_id = None
        self.annotate_panel.image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()

    def callback_set_to_edit_shape(self):
        self.annotate_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_handle_annotate_mouse_wheel(self, event):
        self.annotate_panel.image_panel.canvas.callback_mouse_zoom(event)

    def callback_delete_shape(self):
        tool_shape_ids = self.annotate_panel.image_panel.canvas.get_tool_shape_ids()
        current_geom_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_geom_id:
            if current_geom_id in tool_shape_ids:
                print("a tool is currently selected.  First select a shape.")
                pass
            else:
                self.annotate_panel.image_panel.canvas.delete_shape(current_geom_id)
                del self.variables.canvas_geom_ids_to_annotations_id_dict[str(current_geom_id)]
        else:
            print("no shape selected")

    def callback_annotation_popup(self):
        current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_canvas_shape_id:
            popup = tkinter.Toplevel(self.parent)
            self.variables.current_canvas_geom_id = current_canvas_shape_id
            AnnotationPopup(popup, self.variables)
        else:
            print("Please select a geometry first.")

    # utility functions
    def insert_feature(self, feature):
        """
        Insert a new feature. It is assumes it is already rendered, or will be
        rendered outside of this effort.

        Parameters
        ----------
        feature : Annotation

        Returns
        -------
        None
        """

        def insert_polygon(the_feature, the_geometry):
            # type: (Annotation, Polygon) -> None

            # this will only render an outer ring
            image_coords = the_geometry._outer_ring.coordinates.flatten()
            tmp_shape_id = self.annotate_panel.image_panel.canvas.create_new_polygon((0, 0, 1, 1))
            self.annotate_panel.image_panel.canvas.set_shape_pixel_coords(tmp_shape_id, image_coords)
            self.variables.canvas_geom_ids_to_annotations_id_dict[str(tmp_shape_id)] = the_feature

        geometry = feature.geometry
        if isinstance(geometry, Polygon):
            insert_polygon(feature, geometry)
        else:
            showinfo(
                'Unhandled Geometry',
                message='Annotation id {} has unsupported feature type {} which '
                        'will be omitted from display. Any save of the annotation '
                        'will not contain this feature.'.format(feature.uid, type(geometry)))

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
        self.variables.canvas_geom_ids_to_annotations_id_dict = OrderedDict()

        # populate all the shapes
        for feature in self.variables.file_annotation_collection.annotations.features:
            self.insert_feature(feature)
        # draw all the shapes on the annotation panel
        self.annotate_panel.image_panel.canvas.redraw_all_shapes()
        # TODO: draw all shapes on the context_panel

        # enable appropriate GUI elements
        self.context_panel.buttons.enable_all_buttons()


def main():
    root = tkinter.Tk()
    # noinspection PyUnusedLocal
    app = AnnotationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
