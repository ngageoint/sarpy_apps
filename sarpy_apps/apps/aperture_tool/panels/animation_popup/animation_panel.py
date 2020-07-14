import tkinter
from tk_builder.panel_builder.widget_panel import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors


class ModePanel(WidgetPanel):
    slow_time = basic_widgets.RadioButton          # type: basic_widgets.RadioButton
    fast_time = basic_widgets.RadioButton          # type: basic_widgets.RadioButton
    aperture_percent = basic_widgets.RadioButton     # type: basic_widgets.RadioButton
    full_range_bandwidth = basic_widgets.RadioButton    # type: basic_widgets.RadioButton
    full_az_bandwidth = basic_widgets.RadioButton       # type: basic_widgets.RadioButton
    reverse = basic_widgets.CheckButton             # type: basic_widgets.CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout(["slow_time", "fast_time", "aperture_percent", "full_range_bandwidth", "full_az_bandwidth", "reverse"])
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
    min_res = basic_widgets.Entry
    max_res = basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(["Min Res", "min_res",
                                "Max Res", "max_res"],
                               n_columns=2, column_widths=[20, 10])

        self.min_res.set_text("10")
        self.max_res.set_text("100")


class AnimationSettingsPanel(WidgetPanel):

    number_of_frames = basic_widgets.Entry
    aperture_fraction = basic_widgets.Entry
    frame_rate = basic_widgets.Entry
    cycle_continuously = basic_widgets.CheckButton
    step_forward = basic_widgets.Button
    step_back = basic_widgets.Button
    play = basic_widgets.Button
    stop = basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(["Number of Frames:", "number_of_frames", "", "",
                                "Frame Rate:", "frame_rate", "fps", "",
                                "step_back", "step_forward", "play", "stop",
                                "cycle_continuously",], n_columns=4, column_widths=[20, 10, 3, 3])

        self.number_of_frames.set_text("7")
        self.frame_rate.set_text("5")


class AnimationPanel(WidgetPanel):
    mode_panel = ModePanel         # type: ModePanel
    animation_settings = AnimationSettingsPanel     # type: AnimationSettingsPanel
    fast_slow_settings = FastSlowSettingsPanel      # type: FastSlowSettingsPanel
    resolution_settings = ResolutionSettingsPanel       # type: ResolutionSettingsPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent
        widgets_list = ["mode_panel", "animation_settings", "fast_slow_settings", "resolution_settings"]

        self.init_w_vertical_layout(widgets_list)
        self.pack()
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)
