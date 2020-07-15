from tk_builder.panel_builder.widget_panel import WidgetPanel
from tk_builder.widgets import basic_widgets


class OrthoButtonPanel(WidgetPanel):
    fname_select = basic_widgets.Button
    pan = basic_widgets.Button
    display_ortho = basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_vertical_layout(["fname_select",
                                     "pan",
                                     "display_ortho"])

        self.set_label_text("ortho buttons")
