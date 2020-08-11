from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors
from tk_builder.widgets import basic_widgets


class Buttons(WidgetPanel):
    _widget_list = ("draw_polygon", "edit_polygon", "select_closest", "delete", "annotate")
    draw_polygon = widget_descriptors.ButtonDescriptor("draw_polygon")  # type: basic_widgets.Button
    edit_polygon = widget_descriptors.ButtonDescriptor("edit_polygon")  # type: basic_widgets.Button
    select_closest = widget_descriptors.ButtonDescriptor("select_closest")  # type: basic_widgets.Button
    delete = widget_descriptors.ButtonDescriptor("delete")  # type: basic_widgets.Button
    annotate = widget_descriptors.ButtonDescriptor("annotate")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class AnnotateImagePanel(WidgetPanel):
    _widget_list = ("image_panel", "buttons")
    buttons = widget_descriptors.PanelDescriptor("buttons", Buttons)   # type: Buttons
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")   # type: ImagePanel

    def __init__(self, parent):
        # set the master frame
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()
