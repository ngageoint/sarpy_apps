from tk_builder.panel_builder import WidgetPanel
from sarpy_apps.apps.wake_tool.panels.button_panel import ButtonPanel
from sarpy_apps.apps.wake_tool.panels.info_panel import InfoPanel
from tk_builder.panels.file_selector import FileSelector
from tk_builder.widgets import widget_descriptors


class SidePanel(WidgetPanel):
    _widget_list = ("file_selector", "buttons", "info_panel")
    buttons = widget_descriptors.PanelDescriptor(
        "buttons", ButtonPanel, default_text="wake tool buttons")    # type: ButtonPanel
    file_selector = widget_descriptors.FileSelectorDescriptor(
        "file_selector")  # type: FileSelector
    info_panel = widget_descriptors.PanelDescriptor(
        "info_panel", InfoPanel, default_text="info panel")  # type: InfoPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_basic_widget_list(2, [1, 2])
