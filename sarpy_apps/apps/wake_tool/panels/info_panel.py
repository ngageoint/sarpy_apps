from tk_builder.panels.widget_panel.widget_panel import AbstractWidgetPanel
from tk_builder.widgets import basic_widgets


class InfoPanel(AbstractWidgetPanel):
    def __init__(self, parent):
        AbstractWidgetPanel.__init__(self, parent)
        self.canvas_distance_val = basic_widgets.Entry
        self.pixel_distance_val = basic_widgets.Entry
        self.geo_distance_val = basic_widgets.Entry

        widget_list = ["canvas_distance", "canvas_distance_val",
                       "pixel_distance", "pixel_distance_val",
                       "geo_distance", "geo_distance_val"]
        self.init_w_box_layout(widget_list, n_columns=2, column_widths=[20, 10])
        self.set_label_text("info panel")

        self.canvas_distance_val.config(state='disabled')
        self.pixel_distance_val.config(state='disabled')
        self.geo_distance_val.config(state='disabled')
