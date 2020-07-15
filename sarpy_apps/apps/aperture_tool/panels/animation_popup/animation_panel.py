import tkinter
from tk_builder.panel_builder.widget_panel import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ModePanel(WidgetPanel):
    _widget_list = ("slow_time",
                    "fast_time",
                    "aperture_percent",
                    "full_range_bandwidth",
                    "full_az_bandwidth",
                    "reverse")
    slow_time = widget_descriptors.RadioButtonDescriptor("slow_time")          # type: basic_widgets.RadioButton
    fast_time = widget_descriptors.RadioButtonDescriptor("fast_time")          # type: basic_widgets.RadioButton
    aperture_percent = widget_descriptors.RadioButtonDescriptor("aperture_percent")      # type: basic_widgets.RadioButton
    full_range_bandwidth = widget_descriptors.RadioButtonDescriptor("full_range_bandwidth")     # type: basic_widgets.RadioButton
    full_az_bandwidth = widget_descriptors.RadioButtonDescriptor("full_az_bandwidth")       # type: basic_widgets.RadioButton
    reverse = widget_descriptors.CheckButtonDescriptor("reverse")              # type: basic_widgets.CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()
        self.selected_value = tkinter.IntVar()
        self.selected_value.set(1)

        self.slow_time.config(variable=self.selected_value, value=1)
        self.fast_time.config(variable=self.selected_value, value=2)
        self.aperture_percent.config(variable=self.selected_value, value=3)
        self.full_range_bandwidth.config(variable=self.selected_value, value=4)
        self.full_az_bandwidth.config(variable=self.selected_value, value=5)
        self.pack()

    class Modes:
        fast = "fast"
        slow = "slow"
        aperture_percent = "aperture_percent"
        full_range_badwidth = "full range bandwidth"
        full_azimuth_bandwidth = "full azimuth bandwidth"

    def get_mode(self):
        if self.selected_value.get() == 1:
            return self.Modes.slow
        if self.selected_value.get() == 2:
            return self.Modes.fast
        if self.selected_value.get() == 3:
            return self.Modes.aperture_percent
        if self.selected_value.get() == 4:
            return self.Modes.full_range_badwidth
        if self.selected_value.get() == 5:
            return self.Modes.full_azimuth_bandwidth


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

    number_of_frames_label = widget_descriptors.LabelDescriptor("number_of_frames_label", default_text="Number of Frames:")
    frame_rate_label = widget_descriptors.LabelDescriptor("frame_rate_label", default_text="Frame Rate:")
    fps_label = widget_descriptors.LabelDescriptor("fps_label", default_text="fps")

    r1c3 = widget_descriptors.LabelDescriptor("r1c3", default_text="")
    r1c4 = widget_descriptors.LabelDescriptor("r1c4", default_text="")
    r2c4 = widget_descriptors.LabelDescriptor("r2c4", default_text="")

    number_of_frames = widget_descriptors.EntryDescriptor("number_of_frames")
    aperture_fraction = widget_descriptors.EntryDescriptor("aperture_fraction")
    frame_rate = widget_descriptors.EntryDescriptor("frame_rate")
    cycle_continuously = widget_descriptors.CheckButtonDescriptor("cycle_continuously")
    step_forward = widget_descriptors.ButtonDescriptor("step_forward")
    step_back = widget_descriptors.ButtonDescriptor("step_back")
    play = widget_descriptors.ButtonDescriptor("play")
    stop = widget_descriptors.ButtonDescriptor("stop")

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=4, column_widths=[20, 10, 3, 3])

        self.number_of_frames.set_text("7")
        self.frame_rate.set_text("5")


class AnimationPanel(WidgetPanel):
    _widget_list = ("mode_panel", "animation_settings", "fast_slow_settings", "resolution_settings")

    mode_panel = widget_descriptors.PanelDescriptor("mode_panel", ModePanel)         # type: ModePanel
    animation_settings = widget_descriptors.PanelDescriptor("animation_settings", AnimationSettingsPanel)  # type: AnimationSettingsPanel
    fast_slow_settings = widget_descriptors.PanelDescriptor("fast_slow_settings", FastSlowSettingsPanel)       # type: FastSlowSettingsPanel
    resolution_settings = widget_descriptors.PanelDescriptor("resolution_settings", ResolutionSettingsPanel)        # type: ResolutionSettingsPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent

        self.init_w_vertical_layout()
        self.pack()
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)
