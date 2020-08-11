from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class CanvasDemoButtonPanel(WidgetPanel):
    _widget_list = ("fname_select",
                    "zoom_in",
                    "zoom_out",
                    "rect_select",
                    "update_rect_image",
                    "pan",
                    "draw_line_w_drag",
                    "draw_line_w_click",
                    "draw_arrow_w_drag",
                    "draw_arrow_w_click",
                    "draw_rect_w_drag",
                    "draw_rect_w_click",
                    "draw_polygon_w_click",
                    "draw_point_w_click",
                    "modify_existing_shape_coords",
                    "edit_existing_shape",
                    "color_selector",
                    "save_kml",
                    "select_existing_shape",
                    "remap_dropdown",
                    )
    fname_select = widget_descriptors.ButtonDescriptor("fname_select")
    zoom_in = widget_descriptors.ButtonDescriptor("zoom_in")
    zoom_out = widget_descriptors.ButtonDescriptor("zoom_out")
    rect_select = widget_descriptors.ButtonDescriptor("rect_select")
    update_rect_image = widget_descriptors.ButtonDescriptor("update_rect_image")
    pan = widget_descriptors.ButtonDescriptor("pan")
    draw_line_w_drag = widget_descriptors.ButtonDescriptor("draw_line_w_drag")
    draw_line_w_click = widget_descriptors.ButtonDescriptor("draw_line_w_click")
    draw_arrow_w_drag = widget_descriptors.ButtonDescriptor("draw_arrow_w_drag")
    draw_arrow_w_click = widget_descriptors.ButtonDescriptor("draw_arrow_w_click")
    draw_rect_w_drag = widget_descriptors.ButtonDescriptor("draw_rect_w_drag")
    draw_rect_w_click = widget_descriptors.ButtonDescriptor("draw_rect_w_click")
    draw_polygon_w_click = widget_descriptors.ButtonDescriptor("draw_polygon_w_click")
    draw_point_w_click = widget_descriptors.ButtonDescriptor("draw_point_w_click")
    modify_existing_shape_coords = widget_descriptors.ButtonDescriptor("modify_existing_shape_coords")
    edit_existing_shape = widget_descriptors.ButtonDescriptor("edit_existing_shape")
    color_selector = widget_descriptors.ButtonDescriptor("color_selector")
    save_kml = widget_descriptors.ButtonDescriptor("save_kml")
    select_existing_shape = widget_descriptors.ComboboxDescriptor("select_existing_shape")  # type: basic_widgets.Combobox
    remap_dropdown = widget_descriptors.ComboboxDescriptor("remap_dropdown")         # type: basic_widgets.Combobox

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(4, column_widths=20)

        self.remap_dropdown.update_combobox_values(["density",
                                                    "brighter",
                                                    "darker",
                                                    "high contrast",
                                                    "linear",
                                                    "log",
                                                    "pedf",
                                                    "nrl"])


if __name__ == '__main__':
    print(dir(WidgetPanel))
