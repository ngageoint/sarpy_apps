from tk_builder.panels.widget_panel.widget_panel_2 import AbstractWidgetPanel
from tk_builder.widgets.widget_elements import widget_descriptors
from tk_builder.widgets import basic_widgets

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

resolution_cross_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")   # type: basic_widgets.Label
sample_spacing_cross_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")    # type: basic_widgets.Label
ground_resolution_cross_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")  # type: basic_widgets.Label

resolution_range_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")       # type: basic_widgets.Label
sample_spacing_range_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")   # type: basic_widgets.Label
ground_resolution_range_units = widget_descriptors.LabelDesctriptor("resolution_cross_units")   # type: basic_widgets.Label

full_aperture_button = widget_descriptors.ButtonDescriptor("full_aperture_button")   # type: basic_widgets.Button
english_units_checkbox = widget_descriptors.CheckButtonDescriptor("english_units_checkbox")   # type: basic_widgets.CheckButton


class PhaseHistoryPanel(AbstractWidgetPanel):

    def __init__(self, parent):
        AbstractWidgetPanel.__init__(self, parent)
        self.parent = parent
        self.config(borderwidth=2)

        widget_list = ["", "Cross-Range", "", "Range", "",
                       "Start %", start_percent_cross, "", start_percent_range, "",
                       "Stop %", stop_percent_cross, "", stop_percent_range, "",
                       "Fraction", fraction_cross, "", fraction_range, "",
                       "Resolution", resolution_cross, resolution_cross_units, resolution_range, resolution_range_units,
                       "Sample Spacing", sample_spacing_cross, sample_spacing_cross_units, sample_spacing_range, sample_spacing_range_units,
                       "Ground Resolution", ground_resolution_cross, ground_resolution_cross_units, ground_resolution_range, ground_resolution_range_units,
                       full_aperture_button, english_units_checkbox]
        self.init_w_box_layout(widget_list, 5, column_widths=20)

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
