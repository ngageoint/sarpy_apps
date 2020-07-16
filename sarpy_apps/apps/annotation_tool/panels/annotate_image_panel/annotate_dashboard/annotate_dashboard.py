from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ButtonPanel(WidgetPanel):
    _widget_list = ("pan", "draw_polygon", "select_closest_shape", "delete_shape", "popup")
    pan = widget_descriptors.ButtonDescriptor("pan")  # type: basic_widgets.Button
    draw_polygon = widget_descriptors.ButtonDescriptor("draw_polygon")  # type: basic_widgets.Button
    select_closest_shape = widget_descriptors.ButtonDescriptor("select_closest_shape")  # type: basic_widgets.Button
    delete_shape = widget_descriptors.ButtonDescriptor("delete_shape")  # type: basic_widgets.Button
    popup = widget_descriptors.ButtonDescriptor("popup")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class AnnotateInfoPanel(WidgetPanel):
    _widget_list = ("decimation_label", "annotate_decimation_val")
    decimation_label = widget_descriptors.LabelDescriptor("decimation_label")  # type: basic_widgets.Label
    annotate_decimation_val = widget_descriptors.EntryDescriptor("annotate_decimation_val")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])

        self.decimation_label.config(text="decimation")
        self.annotate_decimation_val.config(state='disabled')


class AnnotateDash(WidgetPanel):
    _widget_list = ("controls", "info_panel")
    controls = widget_descriptors.PanelDescriptor("controls", ButtonPanel)  # type: ButtonPanel
    info_panel = widget_descriptors.PanelDescriptor("info_panel", AnnotateInfoPanel)  # type: AnnotateInfoPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_basic_widget_list(2, [1, 2])
