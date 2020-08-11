from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors
from tk_builder.widgets import basic_widgets


class Buttons(WidgetPanel):
    _widget_list = ("select_area", "edit_selection")
    select_area = widget_descriptors.ButtonDescriptor("select_area")  # type: basic_widgets.Button
    edit_selection = widget_descriptors.ButtonDescriptor("edit_selection")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ContextImagePanel(WidgetPanel):
    _widget_list = ("image_panel", "buttons")
    buttons = widget_descriptors.PanelDescriptor("buttons", Buttons)  # type: Buttons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()
