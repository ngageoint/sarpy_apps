from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets, widget_descriptors


class PhaseHistoryPanel(WidgetPanel):
    _widget_list = ["r1c1", "cross_range_label", "r1c3", "range_label", "r1c5",
                    "start_percent_label", "start_percent_cross", "r2c3", "start_percent_range", "r2c5",
                    "stop_percent_label", "stop_percent_cross", "r3c3", "stop_percent_range", "r3c5",
                    "fraction_label", "fraction_cross", "r4c3", "fraction_range", "r4c5",
                    "resolution_label", "resolution_cross", "resolution_cross_units", "resolution_range", "resolution_range_units",
                    "sample_spacing_label", "sample_spacing_cross", "sample_spacing_cross_units", "sample_spacing_range", "sample_spacing_range_units",
                    "ground_resolution_label", "ground_resolution_cross", "ground_resolution_cross_units", "ground_resolution_range", "ground_resolution_range_units",
                    "full_aperture_button", "english_units_checkbox"]

    r1c1 = widget_descriptors.LabelDescriptor("r1c1", default_text="")
    r1c3 = widget_descriptors.LabelDescriptor("r1c3", default_text="")
    r1c5 = widget_descriptors.LabelDescriptor("r1c5", default_text="")

    r2c3 = widget_descriptors.LabelDescriptor("r2c3", default_text="")
    r2c5 = widget_descriptors.LabelDescriptor("r2c5", default_text="")

    r3c3 = widget_descriptors.LabelDescriptor("r3c3", default_text="")
    r3c5 = widget_descriptors.LabelDescriptor("r3c5", default_text="")

    r4c3 = widget_descriptors.LabelDescriptor("r4c3", default_text="")
    r4c5 = widget_descriptors.LabelDescriptor("r4c5", default_text="")

    cross_range_label = widget_descriptors.LabelDescriptor("cross_range_label", default_text="Cross-Range")
    range_label = widget_descriptors.LabelDescriptor("range_label", default_text="Range")

    start_percent_label = widget_descriptors.LabelDescriptor("start_percent_label", default_text="Start %")
    stop_percent_label = widget_descriptors.LabelDescriptor("stop_percent_label", default_text="Stop %")
    fraction_label = widget_descriptors.LabelDescriptor("fraction_label", default_text="Fraction")
    resolution_label = widget_descriptors.LabelDescriptor("resolution_label", default_text="Resolution")
    sample_spacing_label = widget_descriptors.LabelDescriptor("sample_spacing_label", default_text="Sample Spacing")
    ground_resolution_label = widget_descriptors.LabelDescriptor("ground_resolution_label", default_text="Ground Resolution")

    start_percent_cross = widget_descriptors.EntryDescriptor("start_percent_cross")  # type: basic_widgets.Entry
    stop_percent_cross = widget_descriptors.EntryDescriptor("stop_percent_cross")  # type: basic_widgets.Entry
    fraction_cross = widget_descriptors.EntryDescriptor("fraction_cross")  # type: basic_widgets.Entry
    resolution_cross = widget_descriptors.EntryDescriptor("resolution_cross")  # type: basic_widgets.Entry
    sample_spacing_cross = widget_descriptors.EntryDescriptor("sample_spacing_cross")  # type: basic_widgets.Entry
    ground_resolution_cross = widget_descriptors.EntryDescriptor("ground_resolution_cross")  # type: basic_widgets.Entry

    start_percent_range = widget_descriptors.EntryDescriptor("start_percent_range")  # type: basic_widgets.Entry
    stop_percent_range = widget_descriptors.EntryDescriptor("stop_percent_range")  # type: basic_widgets.Entry
    fraction_range = widget_descriptors.EntryDescriptor("fraction_range")  # type: basic_widgets.Entry
    resolution_range = widget_descriptors.EntryDescriptor("resolution_range")  # type: basic_widgets.Entry
    sample_spacing_range = widget_descriptors.EntryDescriptor("sample_spacing_range")  # type: basic_widgets.Entry
    ground_resolution_range = widget_descriptors.EntryDescriptor("ground_resolution_range")  # type: basic_widgets.Entry

    resolution_cross_units = widget_descriptors.LabelDescriptor("resolution_cross_units")  # type: basic_widgets.Label
    sample_spacing_cross_units = widget_descriptors.LabelDescriptor("sample_spacing_cross_units")  # type: basic_widgets.Label
    ground_resolution_cross_units = widget_descriptors.LabelDescriptor("ground_resolution_cross_units")  # type: basic_widgets.Label

    resolution_range_units = widget_descriptors.LabelDescriptor("resolution_range_units")  # type: basic_widgets.Label
    sample_spacing_range_units = widget_descriptors.LabelDescriptor("sample_spacing_range_units")  # type: basic_widgets.Label
    ground_resolution_range_units = widget_descriptors.LabelDescriptor("ground_resolution_range_units")  # type: basic_widgets.Label

    full_aperture_button = widget_descriptors.ButtonDescriptor("full_aperture_button")  # type: basic_widgets.Button
    english_units_checkbox = widget_descriptors.CheckButtonDescriptor("english_units_checkbox")  # type: basic_widgets.CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent
        self.config(borderwidth=2)

        self.init_w_box_layout(5, column_widths=20)

        self.resolution_cross_units.set_text("Units")
        self.sample_spacing_cross_units.set_text("Units")
        self.ground_resolution_cross_units.set_text("Units")

        self.resolution_range_units.set_text("Units")
        self.sample_spacing_range_units.set_text("Units")
        self.ground_resolution_range_units.set_text("Units")

        self.full_aperture_button.set_text("Full Aperture")
        self.english_units_checkbox.set_text("English Units")

        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()
