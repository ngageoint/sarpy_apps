from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors


class Toolbar(WidgetPanel):
    _widget_list = ("zoom_in", "zoom_out", "pan", "select_aoi", "submit_aoi")
    zoom_in = widget_descriptors.ButtonDescriptor("zoom_in")
    zoom_out = widget_descriptors.ButtonDescriptor("zoom_out")
    pan = widget_descriptors.ButtonDescriptor("pan")
    select_aoi = widget_descriptors.ButtonDescriptor("select_aoi")
    submit_aoi = widget_descriptors.ButtonDescriptor("submit_aoi")

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()
