from tk_builder.panel_builder.widget_panel import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class TaserButtonPanel(WidgetPanel):
    _widget_list = ("single_channel_fname_select",
                    "quad_pole_fname_select",
                    "zoom_in",
                    "zoom_out",
                    "rect_select",
                    "pan",
                    "remap_dropdown")
    single_channel_fname_select = widget_descriptors.ButtonDescriptor("single_channel_fname_select")
    quad_pole_fname_select = widget_descriptors.ButtonDescriptor("quad_pole_fname_select")
    zoom_in = widget_descriptors.ButtonDescriptor("zoom_in")
    zoom_out = widget_descriptors.ButtonDescriptor("zoom_out")
    rect_select = widget_descriptors.ButtonDescriptor("rect_select")
    pan = widget_descriptors.ButtonDescriptor("pan")
    remap_dropdown = widget_descriptors.ComboboxDescriptor("remap_dropdown")         # type: basic_widgets.Combobox

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_vertical_layout()

        self.remap_dropdown.update_combobox_values(["density",
                                                    "brighter",
                                                    "darker",
                                                    "high contrast",
                                                    "linear",
                                                    "log",
                                                    "pedf",
                                                    "nrl"])
