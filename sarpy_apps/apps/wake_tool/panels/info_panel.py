from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class InfoPanel(WidgetPanel):
    _widget_list = ("canvas_distance_label", "canvas_distance_val",
                    "pixel_distance_label", "pixel_distance_val",
                    "geo_distance_label", "geo_distance_val")

    canvas_distance_label = widget_descriptors.LabelDescriptor(
        "canvas_distance_label", default_text="canvas distance")  # type: basic_widgets.Label
    pixel_distance_label = widget_descriptors.LabelDescriptor(
        "pixel_distance_label", default_text="pixel distance")  # type: basic_widgets.Label
    geo_distance_label = widget_descriptors.LabelDescriptor(
        "geo_distance_label", default_text="geo distance")  # type: basic_widgets.Label

    canvas_distance_val = widget_descriptors.EntryDescriptor(
        "canvas_distance_val", default_text="")  # type: basic_widgets.Entry
    pixel_distance_val = widget_descriptors.EntryDescriptor(
        "pixel_distance_val", default_text="")  # type: basic_widgets.Entry
    geo_distance_val = widget_descriptors.EntryDescriptor(
        "geo_distance_val", default_text="")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])

        self.canvas_distance_val.config(state='disabled')
        self.pixel_distance_val.config(state='disabled')
        self.geo_distance_val.config(state='disabled')
