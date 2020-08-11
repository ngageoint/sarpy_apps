from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ButtonPanel(WidgetPanel):
    _widget_list = ("pan", "select", "move_rect")

    pan = widget_descriptors.ButtonDescriptor("pan")  # type: basic_widgets.Button
    select = widget_descriptors.ButtonDescriptor("select")  # type: basic_widgets.Button
    move_rect = widget_descriptors.ButtonDescriptor("move_rect")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ContextMasterDash(WidgetPanel):
    _widget_list = ("buttons",)
    buttons = widget_descriptors.PanelDescriptor("buttons", ButtonPanel)                   # type: ButtonPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_basic_widget_list(3, [1, 1, 2])

