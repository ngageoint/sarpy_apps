from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ButtonPanel(WidgetPanel):
    _widget_list = ("line_draw", "point_draw")
    line_draw = widget_descriptors.ButtonDescriptor("line_draw", default_text="line")  # type: basic_widgets.Button
    point_draw = widget_descriptors.ButtonDescriptor("point_draw", default_text="point")  # type:  basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(2, column_widths=8, row_heights=2)
