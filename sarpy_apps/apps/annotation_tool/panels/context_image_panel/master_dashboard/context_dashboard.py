from tk_builder.panel_builder import WidgetPanel
from tk_builder.panels.file_selector import FileSelector
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


class ContextInfoPanel(WidgetPanel):
    _widget_list = ("decimation_label", "decimation_val")
    decimation_label = widget_descriptors.LabelDescriptor("decimation_label")  # type: basic_widgets.Label
    decimation_val = widget_descriptors.EntryDescriptor("decimation_val")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class ContextMasterDash(WidgetPanel):
    _widget_list = ("buttons", "file_selector", "annotation_selector", "info_panel")
    buttons = widget_descriptors.PanelDescriptor("buttons", ButtonPanel)                   # type: ButtonPanel
    file_selector = widget_descriptors.FileSelectorDescriptor("file_selector")           # type: FileSelector
    annotation_selector = widget_descriptors.FileSelectorDescriptor("annotation_selector")  # type: FileSelector
    info_panel = widget_descriptors.PanelDescriptor("info_panel", ContextInfoPanel)           # type: ContextInfoPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_basic_widget_list(3, [1, 1, 2])

