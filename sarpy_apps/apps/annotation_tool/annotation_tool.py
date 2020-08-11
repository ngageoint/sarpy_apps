import os
import json

import tkinter
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from tkinter import Menu

import numpy as np
from shutil import copyfile

from sarpy_apps.apps.annotation_tool.panels.context_image_panel.context_image_panel import ContextImagePanel
from sarpy_apps.apps.annotation_tool.panels.annotate_image_panel.annotate_image_panel import AnnotateImagePanel
from sarpy_apps.apps.annotation_tool.panels.annotation_popup.annotation_popup import AnnotationPopup
from sarpy_apps.apps.annotation_tool.main_app_variables import AppVariables

from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets.image_canvas import ToolConstants
from tk_builder.widgets import widget_descriptors
from sarpy.geometry.geometry_elements import Polygon
from sarpy.annotation.annotate import FileAnnotationCollection
from sarpy.annotation.annotate import Annotation
from sarpy.annotation.annotate import LabelSchema

from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon

from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader


class AnnotationTool(WidgetPanel):
    _widget_list = ("context_panel", "annotate_panel")
    context_panel = widget_descriptors.PanelDescriptor("context_panel", ContextImagePanel)  # type: ContextImagePanel
    annotate_panel = widget_descriptors.PanelDescriptor("annotate_panel", AnnotateImagePanel)  # type: AnnotateImagePanel

    def __init__(self, primary):
        self.primary = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary)

        self.init_w_horizontal_layout()
        self.primary.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.context_panel.image_panel.resizeable = True
        self.annotate_panel.image_panel.resizeable = True

        self.variables = AppVariables()

        self.context_panel.buttons.select_area.on_left_mouse_click(self.callback_context_set_to_select)
        self.context_panel.buttons.edit_selection.on_left_mouse_click(self.callback_context_set_to_edit_selection)

        self.context_panel.image_panel.canvas.on_left_mouse_release(self.callback_context_handle_left_mouse_release)

        # set up annotate panel event listeners
        self.annotate_panel.image_panel.canvas.on_mouse_wheel(self.callback_handle_annotate_mouse_wheel)
        self.annotate_panel.image_panel.canvas.on_left_mouse_click(self.callback_annotate_handle_canvas_left_mouse_click)
        self.annotate_panel.image_panel.canvas.on_left_mouse_release(self.callback_annotate_handle_left_mouse_release)
        self.annotate_panel.image_panel.canvas.on_right_mouse_click(self.callback_annotate_handle_right_mouse_click)

        self.annotate_panel.buttons.draw_polygon.on_left_mouse_click(self.callback_set_to_draw_polygon)
        self.annotate_panel.buttons.annotate.on_left_mouse_click(self.callback_annotation_popup)
        self.annotate_panel.buttons.select_closest.on_left_mouse_click(self.callback_set_to_select_closest_shape)
        self.annotate_panel.buttons.edit_polygon.on_left_mouse_click(self.callback_set_to_edit_shape)
        self.annotate_panel.buttons.delete.on_left_mouse_click(self.callback_delete_shape)

        self.metaicon_popup_panel = tkinter.Toplevel(self.primary)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)
        self.metaicon_popup_panel.withdraw()

        self.metaviewer_popup_panel = tkinter.Toplevel(self.primary)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)
        self.metaviewer_popup_panel.withdraw()
        menubar = Menu()

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open SICD", command=self.select_sicd_file)
        filemenu.add_command(label="Open annotation", command=self.select_annotation_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        # create more pulldown menus
        popups_menu = Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Popups", menu=popups_menu)

        primary.config(menu=menubar)

    def exit(self):
        self.quit()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.deiconify()

    def metaicon_popup(self):
        self.metaicon_popup_panel.deiconify()

    # context callbacks
    def select_sicd_file(self):
        fname = askopenfilename(filetypes=[("nitf", ".nitf .NITF"), ("all files", "*")])
        if fname:
            image_reader = ComplexImageReader(fname)
            self.context_panel.image_panel.set_image_reader(image_reader)
            self.annotate_panel.image_panel.set_image_reader(image_reader)
            self.metaicon.create_from_reader(image_reader.base_reader, index=0)
            self.metaviewer.create_w_sicd(image_reader.base_reader.sicd_meta)

    def select_annotation_file(self):
        json_fname = askopenfilename(filetypes=[('json files', '*.json'), ("all files", "*")])
        image_fname = os.path.basename(
            self.context_panel.image_panel.canvas.variables.canvas_image_object.image_reader.base_reader.file_name)
        with open(json_fname, 'r') as fi:
            json_dict = json.load(fi)
        # If version is in the dictionary the user has selected a schema and will be working on a new annotation
        if "version" in json_dict:
            self.variables.label_schema = LabelSchema.from_file(json_fname)
            file_annotation_fname = asksaveasfilename(filetypes=[('json files', '*.json'), ("all files", "*")])
            if file_annotation_fname != '':
                self.variables.file_annotation_fname = file_annotation_fname
                self.variables.file_annotation_collection = FileAnnotationCollection(label_schema=self.variables.label_schema,
                                                                                     image_file_name=image_fname)
            else:
                print("select a valid label schema file.")
        elif "label_schema" in json_dict:
            # save a backup
            backup_file_fname = os.path.join(os.path.dirname(json_fname), os.path.basename(json_fname) + '.bak' )
            copyfile(json_fname, backup_file_fname)
            self.variables.file_annotation_fname = json_fname
            self.variables.file_annotation_collection = FileAnnotationCollection.from_dict(json_dict)
            self.variables.label_schema = self.variables.file_annotation_collection.label_schema
            if self.variables.file_annotation_collection.image_file_name == image_fname:
                self.context_panel.buttons.enable_all_buttons()
                # create canvas shapes from existing annotations and create dictionary to keep track of canvas geometries
                # that are mapped to the annotations
                for feature in self.variables.file_annotation_collection.annotations.features:
                    geometry = feature.geometry
                    if isinstance(geometry, Polygon):
                        image_coords = geometry.get_coordinate_list()[0]  # the "outer" ring is always first
                    else:
                        raise TypeError('Unhandled geometry type {}'.format(type(geometry)))
                    image_coords_1d = list(np.reshape(image_coords, np.asarray(image_coords).size))
                    tmp_shape_id = self.annotate_panel.image_panel.canvas.create_new_polygon((0, 0, 1, 1))
                    self.annotate_panel.image_panel.canvas.set_shape_pixel_coords(tmp_shape_id, image_coords_1d)
                    self.variables.canvas_geom_ids_to_annotations_id_dict[str(tmp_shape_id)] = feature
                self.annotate_panel.image_panel.canvas.redraw_all_shapes()
            else:
                print("the image filename and the filename of the annotation do not match.  Select an annotation")
                print("that matches the input filename.")
        else:
            print("select a valid schema file or existing annotation file..")

    # noinspection PyUnusedLocal
    def callback_context_set_to_select(self, event):
        self.context_panel.image_panel.canvas.set_current_tool_to_selection_tool()

    # noinspection PyUnusedLocal
    def callback_context_set_to_edit_selection(self, event):
        self.context_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_context_handle_left_mouse_release(self, event):
        self.context_panel.image_panel.canvas.callback_handle_left_mouse_release(event)
        if self.context_panel.image_panel.canvas.variables.current_tool == ToolConstants.SELECT_TOOL or \
           self.context_panel.image_panel.canvas.variables.current_tool == ToolConstants.TRANSLATE_SHAPE_TOOL:
            rect_id = self.context_panel.image_panel.canvas.variables.select_rect_id
            image_rect = self.context_panel.image_panel.canvas.get_shape_image_coords(rect_id)
            annotate_zoom_rect = self.annotate_panel.image_panel.canvas.variables.canvas_image_object.full_image_yx_to_canvas_coords(
                image_rect)
            self.annotate_panel.image_panel.canvas.zoom_to_selection(annotate_zoom_rect, animate=True)

    # annotate callbacks
    # noinspection PyUnusedLocal
    def callback_set_to_select_closest_shape(self, event):
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
            geometry_coords = np.asarray([x for x in zip(image_coords[0::2], image_coords[1::2])])
            polygon = Polygon(coordinates=[geometry_coords])

            annotation = Annotation()
            annotation.geometry = polygon

            self.variables.canvas_geom_ids_to_annotations_id_dict[str(current_canvas_shape_id)] = annotation

    def callback_set_to_draw_polygon(self, event):
        self.annotate_panel.image_panel.canvas.variables.current_shape_id = None
        self.annotate_panel.image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()

    def callback_set_to_edit_shape(self, event):
        self.annotate_panel.image_panel.canvas.set_current_tool_to_edit_shape()

    def callback_handle_annotate_mouse_wheel(self, event):
        self.annotate_panel.image_panel.canvas.callback_mouse_zoom(event)

    # noinspection PyUnusedLocal
    def callback_delete_shape(self, event):
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

    # noinspection PyUnusedLocal
    def callback_annotation_popup(self, event):
        current_canvas_shape_id = self.annotate_panel.image_panel.canvas.variables.current_shape_id
        if current_canvas_shape_id:
            popup = tkinter.Toplevel(self.parent)
            self.variables.current_canvas_geom_id = current_canvas_shape_id
            AnnotationPopup(popup, self.variables)
        else:
            print("Please select a geometry first.")


def main():
    root = tkinter.Tk()
    # noinspection PyUnusedLocal
    app = AnnotationTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
