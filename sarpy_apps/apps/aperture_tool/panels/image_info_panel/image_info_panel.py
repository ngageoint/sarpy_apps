from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.panels.file_selector import FileSelector
from tk_builder.widgets import widget_descriptors


class PhdOptionsPanel(WidgetPanel):
    _widget_list = ("deskew_slow", "deskew_fast", "uniform_weighting")
    deskew_slow = widget_descriptors.CheckButtonDescriptor(
        "deskew_slow", default_text="Deskew Slow Time")  # type: basic_widgets.CheckButton
    deskew_fast = widget_descriptors.CheckButtonDescriptor(
        "deskew_fast", default_text="Deskew Fast Time")  # type: basic_widgets.CheckButton
    uniform_weighting = widget_descriptors.CheckButtonDescriptor(
        "uniform_weighting", default_text="Apply Uniform Weighting")  # type: basic_widgets.CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()


class ChipSizePanel(WidgetPanel):
    _widget_list = ("nx_label", "nx", "ny_label", "ny")
    nx_label = widget_descriptors.LabelDescriptor("nx_label")          # type: basic_widgets.Label
    nx = widget_descriptors.EntryDescriptor("nx")                # type: basic_widgets.Entry
    ny_label = widget_descriptors.LabelDescriptor("ny_label")          # type: basic_widgets.Label
    ny = widget_descriptors.EntryDescriptor("ny")                # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2)
        self.nx.config(state="disabled")
        self.ny.config(state="disabled")

        self.nx_label.set_text("nx: ")
        self.ny_label.set_text("ny: ")


class ImageInfoPanel(WidgetPanel):
    _widget_list = ("file_selector", "chip_size_panel", "phd_options")
    file_selector = widget_descriptors.PanelDescriptor("file_selector", FileSelector)          # type: FileSelector
    chip_size_panel = widget_descriptors.PanelDescriptor("chip_size_panel", ChipSizePanel)     # type: ChipSizePanel
    phd_options = widget_descriptors.PanelDescriptor("phd_options", PhdOptionsPanel)  # type: PhdOptionsPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        # self.init_w_basic_widget_list(n_rows=2, n_widgets_per_row_list=[1, 2])
        self.init_w_vertical_layout()

        self.file_selector.set_fname_filters([("NITF files", ".nitf .NITF .ntf .NTF")])
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

