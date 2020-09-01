from tk_builder.panel_builder import WidgetPanel

from tk_builder.widgets import widget_descriptors

from tk_builder.panels.pyplot_panel import PyplotPanel


class RcsPlot(WidgetPanel):
    _widget_list = ("azimuth_plot", "range_plot")
    azimuth_plot = widget_descriptors.PyplotPanelDescriptor("azimuth_plot")  # type: PyplotPanel
    range_plot = widget_descriptors.PyplotPanelDescriptor("range_plot")  # type: PyplotPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()