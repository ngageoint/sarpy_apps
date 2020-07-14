from tk_builder.panel_builder.widget_panel import WidgetPanel
from sarpy_apps.apps.wake_tool.panels.button_panel import ButtonPanel
from sarpy_apps.apps.wake_tool.panels.info_panel import InfoPanel
from tk_builder.panels.file_selector.file_selector import FileSelector


class SidePanel(WidgetPanel):
    buttons = ButtonPanel
    file_selector = FileSelector
    info_panel = InfoPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        widget_list = ["file_selector", "buttons", "info_panel"]
        self.init_w_basic_widget_list(widget_list, 2, [1, 2])
        self.set_label_text("wake tool controls")
