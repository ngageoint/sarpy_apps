from tk_builder.panel_templates.widget_panel.widget_panel import AbstractWidgetPanel
from tk_builder.widgets import basic_widgets


class TaserButtonPanel(AbstractWidgetPanel):
    single_channel_fname_select = basic_widgets.Button
    quad_pole_fname_select = basic_widgets.Button
    zoom_in = basic_widgets.Button
    zoom_out = basic_widgets.Button
    rect_select = basic_widgets.Button
    pan = basic_widgets.Button
    remap_dropdown = basic_widgets.Combobox         # type: basic_widgets.Combobox

    def __init__(self, parent):
        AbstractWidgetPanel.__init__(self, parent)

        self.init_w_vertical_layout(["single_channel_fname_select",
                                     "quad_pole_fname_select",
                                     "zoom_in",
                                     "zoom_out",
                                     "pan",
                                     "rect_select",
                                     "remap_dropdown"])

        self.remap_dropdown.update_combobox_values(["density",
                                                    "brighter",
                                                    "darker",
                                                    "high contrast",
                                                    "linear",
                                                    "log",
                                                    "pedf",
                                                    "nrl"])
        self.set_label_text("taser buttons")
