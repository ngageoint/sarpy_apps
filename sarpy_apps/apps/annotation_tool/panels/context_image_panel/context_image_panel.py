from sarpy_apps.apps.annotation_tool.panels.context_image_panel.master_dashboard.context_dashboard import ContextMasterDash
from tk_builder.widgets.axes_image_canvas import AxesImageCanvas
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors


class AppVariables:
    def __init__(self):
        self.image_fname = "None"       # type: str
        self.sicd_metadata = None


class ContextImagePanel(WidgetPanel):
    _widget_list = ("context_dashboard", "image_canvas_panel")
    context_dashboard = widget_descriptors.PanelDescriptor("context_dashboard", ContextMasterDash)   # type: ContextMasterDash
    image_canvas_panel = widget_descriptors.AxesImageCanvasDescriptor("image_canvas_panel")   # type: AxesImageCanvas

    def __init__(self, parent):
        # set the master frame
        WidgetPanel.__init__(self, parent)
        self.app_variables = AppVariables()

        self.init_w_vertical_layout()

        self.context_dashboard.set_spacing_between_buttons(0)
        self.image_canvas_panel.set_canvas_size(600, 400)

        self.context_dashboard.file_selector.set_fname_filters(["*.NITF", ".nitf"])
