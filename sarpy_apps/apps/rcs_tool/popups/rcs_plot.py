from tk_builder.panel_builder import WidgetPanel

from tk_builder.widgets import widget_descriptors

from tk_builder.widgets.pyplot_canvas import PyplotCanvas


class RcsPlot(WidgetPanel):
    _widget_list = ("azimuth_plot", "range_plot")
    azimuth_plot = widget_descriptors.PyplotPanelDescriptor("azimuth_plot")  # type: PyplotCanvas
    range_plot = widget_descriptors.PyplotPanelDescriptor("range_plot")  # type: PyplotCanvas

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()