import tkinter
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from sarpy_apps.apps.aperture_tool.app_variables import AppVariables
from tk_builder.widgets import widget_descriptors
from tk_builder.widgets import basic_widgets


class Toolbar(WidgetPanel):
    _widget_list = ("select_aoi", "submit_aoi")
    select_aoi = widget_descriptors.ButtonDescriptor("select_aoi")  # type: basic_widgets.Button
    submit_aoi = widget_descriptors.ButtonDescriptor("submit_aoi")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class SelectedRegionPanel(WidgetPanel):
    _widget_list = ("toolbar", "image_panel")
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")  # type: ImagePanel
    toolbar = widget_descriptors.PanelDescriptor("toolbar", Toolbar)   # type: Toolbar

    def __init__(self,
                 parent,
                 app_variables,         # type: AppVariables
                 ):
        # set the parent frame
        WidgetPanel.__init__(self, parent)

        self.parent = parent
        self.app_variables = app_variables

        self.init_w_vertical_layout()
        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        self.toolbar.pack(expand=tkinter.YES, fill=tkinter.X)
        self.image_panel.resizeable = True

        sicd_reader = ComplexImageReader(app_variables.sicd_reader_object.base_reader.file_name)
        self.image_panel.set_image_reader(sicd_reader)

        self.toolbar.select_aoi.on_left_mouse_click(self.set_current_tool_to_selection_tool)
        self.toolbar.submit_aoi.on_left_mouse_click(self.submit_aoi)

    # noinspection PyUnusedLocal
    def set_current_tool_to_selection_tool(self, event):
        self.image_panel.canvas.set_current_tool_to_selection_tool()

    # noinspection PyUnusedLocal
    def submit_aoi(self, event):
        selection_image_coords = self.image_panel.canvas.get_shape_image_coords(self.image_panel.canvas.variables.select_rect_id)
        if selection_image_coords:
            self.app_variables.selected_region = selection_image_coords
            y1 = int(min(selection_image_coords[0], selection_image_coords[2]))
            x1 = int(min(selection_image_coords[1], selection_image_coords[3]))
            y2 = int(max(selection_image_coords[0], selection_image_coords[2]))
            x2 = int(max(selection_image_coords[1], selection_image_coords[3]))
            complex_data = self.app_variables.sicd_reader_object.base_reader[y1:y2, x1:x2]
            self.app_variables.aperture_filter.set_sub_image_bounds((y1, y2), (x1, x2))
            self.app_variables.selected_region_complex_data = complex_data
            self.parent.destroy()
        else:
            # TODO: where would this go? Should be a popup or something?
            print("need to select region first")
