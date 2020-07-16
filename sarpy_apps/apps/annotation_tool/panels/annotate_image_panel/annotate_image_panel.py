from sarpy_apps.apps.annotation_tool.panels.annotate_image_panel.annotate_dashboard.annotate_dashboard import AnnotateDash
from tk_builder.panels.image_canvas_panel import ImageCanvasPanel
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors


class AppVariables:
    def __init__(self):
        self.image_fname = "None"       # type: str
        self.sicd_metadata = None


class AnnotateImagePanel(WidgetPanel):
    _widget_list = ("annotate_dashboard", "image_canvas_panel")
    annotate_dashboard = widget_descriptors.PanelDescriptor("annotate_dashboard", AnnotateDash)   # type: AnnotateDash
    image_canvas_panel = widget_descriptors.ImageCanvasPanelDescriptor("image_canvas_panel")   # type: ImageCanvasPanel

    def __init__(self, parent):
        # set the master frame
        WidgetPanel.__init__(self, parent)
        self.app_variables = AppVariables()
        self.init_w_vertical_layout()

        self.annotate_dashboard.set_spacing_between_buttons(0)
        self.image_canvas_panel.set_canvas_size(600, 400)
