from tk_builder.panel_builder import WidgetPanel
from tk_builder.panel_builder import RadioButtonPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ModeSelections(RadioButtonPanel):
    _widget_list = ("slow_time",
                    "fast_time",
                    "aperture_percent",
                    "full_range_bandwidth",
                    "full_az_bandwidth")
    slow_time = widget_descriptors.RadioButtonDescriptor("slow_time")  # type: basic_widgets.RadioButton
    fast_time = widget_descriptors.RadioButtonDescriptor("fast_time")  # type: basic_widgets.RadioButton
    aperture_percent = widget_descriptors.RadioButtonDescriptor("aperture_percent")   # type: basic_widgets.RadioButton
    full_range_bandwidth = \
        widget_descriptors.RadioButtonDescriptor("full_range_bandwidth")  # type: basic_widgets.RadioButton
    full_az_bandwidth = \
        widget_descriptors.RadioButtonDescriptor("full_az_bandwidth")  # type: basic_widgets.RadioButton

    def __init__(self, parent):
        RadioButtonPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_horizontal_layout()


class ModePanel(WidgetPanel):
    _widget_list = ("mode_selections",
                    "reverse")
    mode_selections = widget_descriptors.PanelDescriptor("mode_selections", ModeSelections)  # type: ModeSelections
    reverse = widget_descriptors.CheckButtonDescriptor("reverse")              # type: basic_widgets.CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class FastSlowSettingsPanel(WidgetPanel):
    _widget_list = ("label", "aperture_fraction")
    label = widget_descriptors.LabelDescriptor("label", default_text="Aperture Fraction:")
    aperture_fraction = widget_descriptors.EntryDescriptor("aperture_fraction", default_text="0.25")

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class ResolutionSettingsPanel(WidgetPanel):
    _widget_list = ("min_res_label", "min_res", "max_res_label", "max_res")
    min_res_label = widget_descriptors.LabelDescriptor("min_res_label", default_text="Min Res")
    max_res_label = widget_descriptors.LabelDescriptor("max_res_label", default_text="Max Res")
    min_res = widget_descriptors.EntryDescriptor("min_res", default_text="10")
    max_res = widget_descriptors.EntryDescriptor("max_res", default_text="100")

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class AnimationSettingsPanel(WidgetPanel):

    _widget_list = ("number_of_frames_label", "number_of_frames", "r1c3", "r1c4",
                    "frame_rate_label", "frame_rate", "fps_label", "r2c4",
                    "step_back", "step_forward", "play", "stop",
                    "cycle_continuously")

    number_of_frames_label = \
        widget_descriptors.LabelDescriptor("number_of_frames_label", default_text="Number of Frames:")
    frame_rate_label = widget_descriptors.LabelDescriptor("frame_rate_label", default_text="Frame Rate:")
    fps_label = widget_descriptors.LabelDescriptor("fps_label", default_text="fps")

    r1c3 = widget_descriptors.LabelDescriptor("r1c3", default_text="")
    r1c4 = widget_descriptors.LabelDescriptor("r1c4", default_text="")
    r2c4 = widget_descriptors.LabelDescriptor("r2c4", default_text="")

    number_of_frames = widget_descriptors.EntryDescriptor("number_of_frames")  # type: basic_widgets.Entry
    aperture_fraction = widget_descriptors.EntryDescriptor("aperture_fraction")  # type: basic_widgets.Entry
    frame_rate = widget_descriptors.EntryDescriptor("frame_rate")  # type: basic_widgets.Entry
    cycle_continuously = widget_descriptors.\
        CheckButtonDescriptor("cycle_continuously")  # type: basic_widgets.CheckButton
    step_forward = widget_descriptors.ButtonDescriptor("step_forward")  # type: basic_widgets.Button
    step_back = widget_descriptors.ButtonDescriptor("step_back")  # type: basic_widgets.Button
    play = widget_descriptors.ButtonDescriptor("play")  # type: basic_widgets.Button
    stop = widget_descriptors.ButtonDescriptor("stop")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=4, column_widths=[20, 10, 3, 3])

        self.number_of_frames.set_text("7")
        self.frame_rate.set_text("5")


class AnimationPanel(WidgetPanel):
    _widget_list = ("mode_panel", "animation_settings", "fast_slow_settings", "resolution_settings", "save")

    mode_panel = widget_descriptors.PanelDescriptor("mode_panel", ModePanel)  # type: ModePanel
    animation_settings = widget_descriptors.PanelDescriptor("animation_settings",
                                                            AnimationSettingsPanel)  # type: AnimationSettingsPanel
    fast_slow_settings = widget_descriptors.PanelDescriptor("fast_slow_settings",
                                                            FastSlowSettingsPanel)  # type: FastSlowSettingsPanel
    resolution_settings = widget_descriptors.PanelDescriptor("resolution_settings",
                                                             ResolutionSettingsPanel)  # type: ResolutionSettingsPanel
    save = widget_descriptors.ButtonDescriptor("save")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent

        self.init_w_vertical_layout()
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)
