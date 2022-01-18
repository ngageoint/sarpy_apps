# -*- coding: utf-8 -*-
"""
This module provides a version of the aperture tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import os
import time
import numpy
from typing import Union, Tuple

from scipy.constants import foot, inch

import tkinter
from tkinter import ttk

from tkinter.filedialog import asksaveasfilename, askopenfilenames, askdirectory
from tkinter.messagebox import showinfo

from tk_builder.base_elements import TypedDescriptor, IntegerDescriptor, \
    BooleanDescriptor, FloatDescriptor, StringDescriptor
from tk_builder.image_reader import NumpyCanvasImageReader
from tk_builder.panel_builder import WidgetPanel, RadioButtonPanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.utils.frame_sequence_utils import save_numpy_frame_sequence_to_animated_gif

from tk_builder.widgets.widget_descriptors import RadioButtonDescriptor, \
    PanelDescriptor, ImagePanelDescriptor, CheckButtonDescriptor, LabelDescriptor, \
    EntryDescriptor, ButtonDescriptor
from tk_builder.widgets.basic_widgets import Frame, RadioButton, CheckButton, \
    Label, Entry, Button

from sarpy.visualization.remap import NRL
from sarpy.processing.subaperture import ApertureFilter
from sarpy.io.complex.base import SICDTypeReader

from sarpy_apps.supporting_classes.file_filters import common_use_collection
from sarpy_apps.supporting_classes.image_reader import SICDTypeCanvasImageReader
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata


##################
# Animation panel

class ModeSelections(RadioButtonPanel):
    _widget_list = (
        "slow_time", "fast_time", "aperture_percent", "full_range_bandwidth", "full_az_bandwidth")
    slow_time = RadioButtonDescriptor("slow_time")  # type: RadioButton
    fast_time = RadioButtonDescriptor("fast_time")  # type: RadioButton
    aperture_percent = RadioButtonDescriptor("aperture_percent")   # type: RadioButton
    full_range_bandwidth = RadioButtonDescriptor("full_range_bandwidth")  # type: RadioButton
    full_az_bandwidth = RadioButtonDescriptor("full_az_bandwidth")  # type: RadioButton

    def __init__(self, parent):
        RadioButtonPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_horizontal_layout()


class ModePanel(WidgetPanel):
    _widget_list = ("mode_selections", "reverse")
    mode_selections = PanelDescriptor("mode_selections", ModeSelections)  # type: ModeSelections
    reverse = CheckButtonDescriptor("reverse")  # type: CheckButton

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class FastSlowSettingsPanel(WidgetPanel):
    _widget_list = ("label", "aperture_fraction")
    label = LabelDescriptor("label", default_text="Aperture Fraction:")  # type: Label
    aperture_fraction = EntryDescriptor("aperture_fraction", default_text="0.25")  # type: Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class ResolutionSettingsPanel(WidgetPanel):
    _widget_list = ("min_res_label", "min_res", "max_res_label", "max_res")
    min_res_label = LabelDescriptor("min_res_label", default_text="Min Res")  # type: Label
    max_res_label = LabelDescriptor("max_res_label", default_text="Max Res")  # type: Label
    min_res = EntryDescriptor("min_res", default_text="10")  # type: Entry
    max_res = EntryDescriptor("max_res", default_text="100")  # type: Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class AnimationSettingsPanel(WidgetPanel):
    _widget_list = (
        "number_of_frames_label", "number_of_frames", "r1c3", "r1c4",
        "frame_rate_label", "frame_rate", "fps_label", "r2c4",
        "step_back", "step_forward", "play", "stop",
        "cycle_continuously")

    number_of_frames_label = LabelDescriptor(
        "number_of_frames_label", default_text="Number of Frames:")  # type: Label
    frame_rate_label = LabelDescriptor(
        "frame_rate_label", default_text="Frame Rate:")  # type: Label
    fps_label = LabelDescriptor("fps_label", default_text="fps")  # type: Label

    r1c3 = LabelDescriptor("r1c3", default_text="")  # type: Label
    r1c4 = LabelDescriptor("r1c4", default_text="")  # type: Label
    r2c4 = LabelDescriptor("r2c4", default_text="")  # type: Label

    number_of_frames = EntryDescriptor("number_of_frames")  # type: Entry
    aperture_fraction = EntryDescriptor("aperture_fraction")  # type: Entry
    frame_rate = EntryDescriptor("frame_rate")  # type: Entry
    cycle_continuously = CheckButtonDescriptor("cycle_continuously")  # type: CheckButton
    step_forward = ButtonDescriptor("step_forward")  # type: Button
    step_back = ButtonDescriptor("step_back")  # type: Button
    play = ButtonDescriptor("play")  # type: Button
    stop = ButtonDescriptor("stop")  # type: Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=4, column_widths=[20, 10, 3, 3])
        self.number_of_frames.set_text("7")
        self.frame_rate.set_text("5")


class AnimationPanel(WidgetPanel):
    _widget_list = (
        "mode_panel", "animation_settings", "fast_slow_settings", "resolution_settings", "save")

    mode_panel = TypedDescriptor("mode_panel", ModePanel)  # type: ModePanel
    animation_settings = TypedDescriptor(
        "animation_settings", AnimationSettingsPanel)  # type: AnimationSettingsPanel
    fast_slow_settings = TypedDescriptor(
        "fast_slow_settings", FastSlowSettingsPanel)  # type: FastSlowSettingsPanel
    resolution_settings = TypedDescriptor(
        "resolution_settings", ResolutionSettingsPanel)  # type: ResolutionSettingsPanel
    save = ButtonDescriptor("save")  # type: Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_vertical_layout()
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)


###########
# Image info panel

class DeskewFastSlow(RadioButtonPanel):
    _widget_list = ("fast", "slow",)
    fast = RadioButtonDescriptor("fast")  # type: RadioButton
    slow = RadioButtonDescriptor("slow")  # type: RadioButton

    def __init__(self, primary):
        self.primary = primary
        RadioButtonPanel.__init__(self, primary)
        self.init_w_vertical_layout()


class PhdOptionsPanel(WidgetPanel):
    _widget_list = ("apply_deskew", "uniform_weighting", "deskew_fast_slow")
    apply_deskew = CheckButtonDescriptor(
        "apply_deskew", default_text="apply deskew")  # type: CheckButton
    uniform_weighting = CheckButtonDescriptor(
        "uniform_weighting", default_text="apply uniform weighting")  # type: CheckButton
    deskew_fast_slow = PanelDescriptor(
        "deskew_fast_slow", DeskewFastSlow, default_text="direction")  # type: DeskewFastSlow

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ChipSizePanel(WidgetPanel):
    _widget_list = ("nx_label", "nx", "ny_label", "ny")
    nx_label = LabelDescriptor("nx_label")  # type: Label
    nx = EntryDescriptor("nx")  # type: Entry
    ny_label = LabelDescriptor("ny_label")  # type: Label
    ny = EntryDescriptor("ny")  # type: Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2)
        self.nx.config(state="disabled")
        self.ny.config(state="disabled")
        self.nx_label.set_text("nx: ")
        self.ny_label.set_text("ny: ")


class ImageInfoPanel(WidgetPanel):
    _widget_list = ("file_label", "chip_size_panel", "phd_options")
    file_label = LabelDescriptor(
        "file_label", default_text='', docstring='The file name label.')  # type: Label
    chip_size_panel = PanelDescriptor("chip_size_panel", ChipSizePanel)  # type: ChipSizePanel
    phd_options = PanelDescriptor("phd_options", PhdOptionsPanel)  # type: PhdOptionsPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)


##########
# Phase history panel

class PhaseHistoryPanel(WidgetPanel):
    _widget_list = (
        "r1c1", "cross_range_label", "r1c3", "range_label", "r1c5",
        "start_percent_label", "start_percent_cross", "r2c3", "start_percent_range", "r2c5",
        "stop_percent_label", "stop_percent_cross", "r3c3", "stop_percent_range", "r3c5",
        "fraction_label", "fraction_cross", "r4c3", "fraction_range", "r4c5",
        "resolution_label", "resolution_cross", "resolution_cross_units", "resolution_range",
        "resolution_range_units", "sample_spacing_label", "sample_spacing_cross", "sample_spacing_cross_units",
        "sample_spacing_range", "sample_spacing_range_units", "ground_resolution_label", "ground_resolution_cross",
        "ground_resolution_cross_units", "ground_resolution_range", "ground_resolution_range_units",
        "full_aperture_button", "english_units_checkbox")

    r1c1 = LabelDescriptor("r1c1", default_text="")  # type: Label
    r1c3 = LabelDescriptor("r1c3", default_text="")  # type: Label
    r1c5 = LabelDescriptor("r1c5", default_text="")  # type: Label

    r2c3 = LabelDescriptor("r2c3", default_text="")  # type: Label
    r2c5 = LabelDescriptor("r2c5", default_text="")  # type: Label

    r3c3 = LabelDescriptor("r3c3", default_text="")  # type: Label
    r3c5 = LabelDescriptor("r3c5", default_text="")  # type: Label

    r4c3 = LabelDescriptor("r4c3", default_text="")  # type: Label
    r4c5 = LabelDescriptor("r4c5", default_text="")  # type: Label

    cross_range_label = LabelDescriptor("cross_range_label", default_text="Cross-Range")  # type: Label
    range_label = LabelDescriptor("range_label", default_text="Range")  # type: Label

    start_percent_label = LabelDescriptor("start_percent_label", default_text="Start %")  # type: Label
    stop_percent_label = LabelDescriptor("stop_percent_label", default_text="Stop %")  # type: Label
    fraction_label = LabelDescriptor("fraction_label", default_text="Fraction")  # type: Label
    resolution_label = LabelDescriptor("resolution_label", default_text="Resolution")  # type: Label
    sample_spacing_label = LabelDescriptor("sample_spacing_label", default_text="Sample Spacing")  # type: Label
    ground_resolution_label = LabelDescriptor(
        "ground_resolution_label", default_text="Ground Resolution")  # type: Label

    start_percent_cross = EntryDescriptor("start_percent_cross")  # type: Entry
    stop_percent_cross = EntryDescriptor("stop_percent_cross")  # type: Entry
    fraction_cross = EntryDescriptor("fraction_cross")  # type: Entry
    resolution_cross = EntryDescriptor("resolution_cross")  # type: Entry
    sample_spacing_cross = EntryDescriptor("sample_spacing_cross")  # type: Entry
    ground_resolution_cross = EntryDescriptor("ground_resolution_cross")  # type: Entry

    start_percent_range = EntryDescriptor("start_percent_range")  # type: Entry
    stop_percent_range = EntryDescriptor("stop_percent_range")  # type: Entry
    fraction_range = EntryDescriptor("fraction_range")  # type: Entry
    resolution_range = EntryDescriptor("resolution_range")  # type: Entry
    sample_spacing_range = EntryDescriptor("sample_spacing_range")  # type: Entry
    ground_resolution_range = EntryDescriptor("ground_resolution_range")  # type: Entry

    resolution_cross_units = LabelDescriptor("resolution_cross_units")  # type: Label
    sample_spacing_cross_units = LabelDescriptor("sample_spacing_cross_units")  # type: Label
    ground_resolution_cross_units = LabelDescriptor("ground_resolution_cross_units")  # type: Label

    resolution_range_units = LabelDescriptor("resolution_range_units")  # type: Label
    sample_spacing_range_units = LabelDescriptor("sample_spacing_range_units")  # type: Label
    ground_resolution_range_units = LabelDescriptor("ground_resolution_range_units")  # type: Label

    full_aperture_button = ButtonDescriptor("full_aperture_button")  # type: Button
    english_units_checkbox = CheckButtonDescriptor("english_units_checkbox")  # type: CheckButton

    def __init__(self, parent):
        self.parent = parent
        WidgetPanel.__init__(self, parent)
        self.config(borderwidth=2)

        self.init_w_box_layout(5, column_widths=20)

        self.resolution_cross_units.set_text("Units")
        self.sample_spacing_cross_units.set_text("Units")
        self.ground_resolution_cross_units.set_text("Units")

        self.resolution_range_units.set_text("Units")
        self.sample_spacing_range_units.set_text("Units")
        self.ground_resolution_range_units.set_text("Units")

        self.full_aperture_button.set_text("Full Aperture")
        self.english_units_checkbox.set_text("English Units")

        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()


###########
# The aperture tool

class AnimationProperties(object):
    """
    Properties for animation.
    """

    n_frames = IntegerDescriptor(
        'n_frames',
        docstring='')  # type: int
    aperture_faction = FloatDescriptor(
        'aperture_faction',
        docstring='')  # type: float
    cycle_continuously = BooleanDescriptor(
        'cycle_continuously', default_value=False,
        docstring='')  # type: bool
    current_position = IntegerDescriptor(
        'current_position', default_value=0,
        docstring='')  # type: int
    stop_pressed = BooleanDescriptor(
        'stop_pressed', default_value=False,
        docstring='')  # type: bool
    min_aperture_percent = FloatDescriptor(
        'min_aperture_percent',
        docstring='')  # type: float
    max_aperture_percent = FloatDescriptor(
        'max_aperture_percent',
        docstring='')  # type: float


class ApertureTool(WidgetPanel):
    """
    The widget for understanding the relationship between the phase data and the
    reconstructed complex image.
    """

    _widget_list = ("phase_history_panel", "filtered_panel")

    phase_history_panel = ImagePanelDescriptor(
        "phase_history_panel")  # type: ImagePanel
    filtered_panel = ImagePanelDescriptor(
        "filtered_panel")  # type: ImagePanel

    image_info_panel = PanelDescriptor("image_info_panel", ImageInfoPanel)  # type: ImageInfoPanel
    phase_history = PanelDescriptor("phase_history", PhaseHistoryPanel)  # type: PhaseHistoryPanel
    animation_panel = PanelDescriptor("animation_panel", AnimationPanel)   # type: AnimationPanel

    def __init__(self, primary, app_variables, **kwargs):
        """

        Parameters
        ----------
        primary : tkinter.Tk|tkinter.Toplevel
        app_variables : AppVariables
        kwargs
        """

        self.app_variables = app_variables
        self.primary = primary
        self._can_use_tool = True
        self._update_on_changed = True
        self._skip_update = False

        WidgetPanel.__init__(self, primary, **kwargs)
        self.init_w_horizontal_layout()

        # define some informational popups
        self.image_info_popup_panel = tkinter.Toplevel(self.primary)
        self.image_info_panel = ImageInfoPanel(self.image_info_popup_panel)
        self.image_info_popup_panel.withdraw()

        self.ph_popup_panel = tkinter.Toplevel(self.primary)
        self.phase_history = PhaseHistoryPanel(self.ph_popup_panel)
        self.ph_popup_panel.withdraw()

        self.animation_popup_panel = tkinter.Toplevel(self.primary)
        self.animation_panel = AnimationPanel(self.animation_popup_panel)
        self.animation_popup_panel.withdraw()

        self.menu_bar = tkinter.Menu()
        self.controls_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.controls_menu.add_command(label="Main Controls", command=self.main_controls_popup)
        self.controls_menu.add_command(label="Phase History", command=self.ph_popup)
        self.controls_menu.add_command(label="Animation", command=self.animation_fast_slow_popup)
        self.menu_bar.add_cascade(label="Details", menu=self.controls_menu)

        primary.config(menu=self.menu_bar)
        self.phase_history_panel.master.pack(side='left', fill=tkinter.BOTH, expand=tkinter.YES)
        self.filtered_panel.master.pack(side='right', fill=tkinter.BOTH, expand=tkinter.YES)
        self.filtered_panel.canvas.set_canvas_size(300, 400)
        self.phase_history_panel.canvas.set_canvas_size(300, 400)

        # callbacks for animation
        self.animation_panel.animation_settings.play.config(command=self.callback_play_animation)
        self.animation_panel.animation_settings.step_forward.config(command=self.callback_step_forward)
        self.animation_panel.animation_settings.step_back.config(command=self.callback_step_back)
        self.animation_panel.animation_settings.stop.config(command=self.callback_stop_animation)
        self.animation_panel.save.config(command=self.callback_save_animation)

        # configure our panels
        self.phase_history_panel.hide_tools()
        self.phase_history_panel.hide_shapes()
        self.phase_history_panel.hide_select_index()
        self.phase_history_panel.hide_remap_combo()

        self.phase_history_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_finalized)
        self.phase_history_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)

        self.filtered_panel.hide_tools()
        self.filtered_panel.hide_shapes()
        self.filtered_panel.hide_select_index()
        self.filtered_panel.hide_remap_combo()

        self.image_info_panel.phd_options.uniform_weighting.config(command=self.callback_update_weighting)
        self.image_info_panel.phd_options.apply_deskew.config(command=self.callback_update_apply_deskew)
        self.image_info_panel.phd_options.deskew_fast_slow.slow.config(command=self.callback_update_deskew_direction)
        self.image_info_panel.phd_options.deskew_fast_slow.fast.config(command=self.callback_update_deskew_direction)
        self.primary.protocol("WM_DELETE_WINDOW", self.close_window)
        self.pack(fill=tkinter.BOTH, expand=tkinter.YES)

    def close_window(self):
        self.primary.withdraw()

    def callback_update_deskew_direction(self):
        if self.image_info_panel.phd_options.deskew_fast_slow.selection() == \
                self.image_info_panel.phd_options.deskew_fast_slow.slow:
            self.app_variables.aperture_filter.dimension = 1
        else:
            self.app_variables.aperture_filter.dimension = 0
        self.update_fft_image()
        self.update_filtered_image()

    def callback_update_weighting(self):
        if self.image_info_panel.phd_options.uniform_weighting.is_selected():
            self.app_variables.aperture_filter.apply_deweighting = True
        else:
            self.app_variables.aperture_filter.apply_deweighting = False
        self.update_fft_image()
        self.update_filtered_image()

    def callback_update_apply_deskew(self):
        if self.image_info_panel.phd_options.apply_deskew.is_selected():
            self.app_variables.aperture_filter.apply_deskew = True
            self.image_info_panel.phd_options.deskew_fast_slow.fast.configure(state="normal")
            self.image_info_panel.phd_options.deskew_fast_slow.slow.configure(state="normal")
        else:
            self.app_variables.aperture_filter.apply_deskew = False
            self.image_info_panel.phd_options.deskew_fast_slow.fast.configure(state="disabled")
            self.image_info_panel.phd_options.deskew_fast_slow.slow.configure(state="disabled")

        self.update_fft_image()
        self.update_filtered_image()

    # TODO: update variables, some don't exist in the current form.
    def callback_save_animation(self):
        self.update_animation_params()
        filename = asksaveasfilename(
            initialdir=os.path.expanduser("~"), title="Select file",
            filetypes=(("animated gif", "*.gif"), ("all files", "*.*")))

        extension = filename[-4:]
        if extension.lower() != ".gif":
            filename = filename + ".gif"
        frame_sequence = []
        direction_forward_or_back = "forward"
        if self.animation_panel.mode_panel.reverse.is_selected():
            direction_forward_or_back = "back"
        self.animation_panel.animation_settings.stop.config(state="normal")

        self.animation_panel.animation_settings.disable_all_widgets()
        self.animation_panel.animation_settings.stop.config(state="normal")
        if direction_forward_or_back == "forward":
            self.app_variables.animation.current_position = -1
        else:
            self.app_variables.animation.current_position = self.app_variables.animation.n_frames
        for i in range(self.app_variables.animation.n_frames):
            filtered_image = self.get_filtered_image()
            frame_sequence.append(filtered_image)
            self.update_animation_params()
            self.step_animation(direction_forward_or_back)
            self.phase_history_panel.update()
        fps = float(self.animation_panel.animation_settings.frame_rate.get())
        save_numpy_frame_sequence_to_animated_gif(frame_sequence, filename, fps)
        self.animation_panel.animation_settings.enable_all_widgets()

    def callback_step_forward(self):
        self.step_animation("forward")

    def callback_step_back(self):
        self.step_animation("back")

    def callback_stop_animation(self):
        self.app_variables.animation.stop_pressed = True

    def callback_play_animation(self):
        self.update_animation_params()

        direction_forward_or_back = "forward"
        if self.animation_panel.mode_panel.reverse.is_selected():
            direction_forward_or_back = "back"
        time_between_frames = 1 / float(self.animation_panel.animation_settings.frame_rate.get())
        self.animation_panel.animation_settings.stop.config(state="normal")

        def play_animation():
            self.animation_panel.animation_settings.disable_all_widgets()
            self.animation_panel.animation_settings.stop.config(state="normal")
            if direction_forward_or_back == "forward":
                self.app_variables.animation.current_position = -1
            else:
                self.app_variables.animation.current_position = self.app_variables.animation.n_frames
            for i in range(self.app_variables.animation.n_frames):
                self.update_animation_params()
                if self.app_variables.animation.stop_pressed:
                    self.animation_panel.animation_settings.enable_all_widgets()
                    break
                tic = time.time()
                self.step_animation(direction_forward_or_back)
                self.phase_history_panel.update()
                toc = time.time()
                if (toc - tic) < time_between_frames:
                    time.sleep(time_between_frames - (toc - tic))

        self.app_variables.animation.stop_pressed = False
        if self.animation_panel.animation_settings.cycle_continuously.is_selected():
            while not self.app_variables.animation.stop_pressed:
                play_animation()
        else:
            play_animation()
        self.app_variables.animation.stop_pressed = False
        self.animation_panel.animation_settings.enable_all_widgets()

    # noinspection PyUnusedLocal
    def handle_selection_finalized(self, event):
        """
        This handles the change in selection in the phase history panel.

        Parameters
        ----------
        event
        """

        self.update_phase_history_selection()
        self.update_filtered_image()

    # noinspection PyUnusedLocal
    def handle_selection_change(self, event):
        """
        This handles the change in selection in the phase history panel.

        Parameters
        ----------
        event
        """

        if self._skip_update:
            return

        if self._update_on_changed:
            self.update_phase_history_selection()
            self.update_filtered_image()

    def exit(self):
        self.primary.destroy()

    # various methods used in the callbacks
    def make_blank(self):
        junk_data = numpy.zeros((100, 100), dtype='uint8')
        self.phase_history_panel.set_image_reader(NumpyCanvasImageReader(junk_data))
        self.filtered_panel.set_image_reader(NumpyCanvasImageReader(junk_data))

    def handle_main_selection_update(self):
        """
        Handle that the selected region has changed. This is expected to be called
        by the RegionSelector.
        """

        if self._can_use_tool:
            self.update_fft_image()

    def handle_reader_update(self):
        """
        Handle that the reader and/or index has been updated. This is expected to
        be called by the region selector.
        """
        self._can_use_tool = True
        if self.app_variables.image_reader is None:
            self._can_use_tool = False
            self.image_info_panel.file_label.set_text('')
            self.app_variables.aperture_filter = None
            self.make_blank()
            return  # nothing to be done

        file_name = self.app_variables.image_reader.file_name
        if file_name is None:
            file_name = ''
        self.image_info_panel.file_label.set_text(file_name)

        the_sicd = self.app_variables.image_reader.get_sicd()

        # handle the case of no deskew:
        if the_sicd.Grid.Row.DeltaKCOAPoly is None or the_sicd.Grid.Col.DeltaKCOAPoly is None:
            self._can_use_tool = False
            showinfo(
                'DeltaKCOAPolys not populated',
                message='At least one of the DeltaKCOAPolys is unpopulated. There is nothing to do.')
            self.app_variables.aperture_filter = None
            self.image_info_panel.phd_options.deskew_fast_slow.fast.configure(state="disabled")
            self.image_info_panel.phd_options.deskew_fast_slow.slow.configure(state="disabled")
            self.image_info_panel.phd_options.apply_deskew.config(state="disabled")
            self.image_info_panel.phd_options.uniform_weighting.config(state="disabled")
            return

        self.image_info_panel.phd_options.deskew_fast_slow.fast.configure(state="normal")
        self.image_info_panel.phd_options.deskew_fast_slow.slow.configure(state="normal")
        self.image_info_panel.phd_options.apply_deskew.config(state="normal")
        self.image_info_panel.phd_options.apply_deskew.value.set(True)

        row_delta_kcoa = the_sicd.Grid.Row.DeltaKCOAPoly.get_array()
        if row_delta_kcoa.size == 1 and row_delta_kcoa[0, 0] == 0:
            the_dimension = 1
            self.image_info_panel.phd_options.deskew_fast_slow.set_selection(1)
        else:
            the_dimension = 0
            self.image_info_panel.phd_options.deskew_fast_slow.set_selection(0)

        if the_sicd.Grid.Row.WgtFunct is None or the_sicd.Grid.Col.WgtFunct is None:
            deweighting = False
            self.image_info_panel.phd_options.uniform_weighting.config(state="disabled")
            self.image_info_panel.phd_options.uniform_weighting.value.set(False)
        else:
            deweighting = True
            self.image_info_panel.phd_options.uniform_weighting.config(state="normal")
            self.image_info_panel.phd_options.uniform_weighting.value.set(True)

        self.app_variables.aperture_filter = ApertureFilter(
            self.app_variables.image_reader.base_reader,
            dimension=the_dimension,
            apply_deskew=True,
            apply_deweighting=deweighting)

        self.update_fft_image()

    def update_animation_params(self):
        self.app_variables.animation.n_frames = int(self.animation_panel.animation_settings.number_of_frames.get())
        self.app_variables.animation.aperture_faction = \
            float(self.animation_panel.fast_slow_settings.aperture_fraction.get())
        self.app_variables.animation.cycle_continuously = \
            self.animation_panel.animation_settings.cycle_continuously.is_selected()
        self.app_variables.animation.min_aperture_percent = \
            float(self.animation_panel.resolution_settings.min_res.get()) * 0.01
        self.app_variables.animation.max_aperture_percent = \
            float(self.animation_panel.resolution_settings.max_res.get()) * 0.01

    def step_animation(self, direction_forward_or_back):
        """
        Steps the animation.

        Parameters
        ----------
        direction_forward_or_back : str

        Returns
        -------
        None
        """

        self.update_animation_params()
        fft_canvas_bounds = self.phase_history_panel.canvas.image_coords_to_canvas_coords(
            self.get_fft_image_bounds())
        full_canvas_x_aperture = fft_canvas_bounds[2] - fft_canvas_bounds[0]
        full_canvas_y_aperture = fft_canvas_bounds[3] - fft_canvas_bounds[1]

        mode = self.animation_panel.mode_panel.mode_selections.selection()

        if direction_forward_or_back == "forward":
            if self.app_variables.animation.current_position < self.app_variables.animation.n_frames - 1:
                self.app_variables.animation.current_position += 1
        elif direction_forward_or_back == "back":
            if self.app_variables.animation.current_position > 0:
                self.app_variables.animation.current_position -= 1

        if mode == self.animation_panel.mode_panel.mode_selections.slow_time:
            aperture_distance = full_canvas_x_aperture * self.app_variables.animation.aperture_faction

            start_locs = numpy.linspace(
                fft_canvas_bounds[0], fft_canvas_bounds[2] - aperture_distance, self.app_variables.animation.n_frames)

            x_start = start_locs[self.app_variables.animation.current_position]
            new_rect = (x_start, fft_canvas_bounds[1], x_start + aperture_distance, fft_canvas_bounds[3])
        elif mode == self.animation_panel.mode_panel.mode_selections.fast_time:
            aperture_distance = full_canvas_y_aperture * self.app_variables.animation.aperture_faction

            start_locs = numpy.linspace(
                fft_canvas_bounds[1], fft_canvas_bounds[3] - aperture_distance, self.app_variables.animation.n_frames)
            start_locs = numpy.flip(start_locs)
            y_start = start_locs[self.app_variables.animation.current_position]
            new_rect = (
                fft_canvas_bounds[0], y_start, fft_canvas_bounds[2], y_start + aperture_distance)
        else:
            xul, yul, xlr, ylr = fft_canvas_bounds
            mid_x = 0.5*(xul+xlr)
            mid_y = 0.5*(yul+ylr)
            max_x_width = 0.5*full_canvas_x_aperture*self.app_variables.animation.max_aperture_percent
            max_y_width = 0.5*full_canvas_y_aperture*self.app_variables.animation.max_aperture_percent
            min_x_width = 0.5*full_canvas_x_aperture*self.app_variables.animation.min_aperture_percent
            min_y_width = 0.5*full_canvas_y_aperture*self.app_variables.animation.min_aperture_percent

            if mode == self.animation_panel.mode_panel.mode_selections.full_az_bandwidth:
                canvas_xul_start, canvas_xlr_start = xul, xlr
                canvas_xul_stop, canvas_xlr_stop = xul, xlr
            else:
                canvas_xul_start, canvas_xlr_start = mid_x - max_x_width, mid_x + max_x_width
                canvas_xul_stop, canvas_xlr_stop = mid_x - min_x_width, mid_x + min_x_width

            if mode == self.animation_panel.mode_panel.mode_selections.full_range_bandwidth:
                canvas_yul_start, canvas_ylr_start = yul, ylr
                canvas_yul_stop, canvas_ylr_stop = yul, ylr
            else:
                canvas_yul_start, canvas_ylr_start = mid_y - max_y_width, mid_y + max_y_width
                canvas_yul_stop, canvas_ylr_stop = mid_y - min_y_width, mid_y + min_y_width

            x_uls = numpy.linspace(canvas_xul_start, canvas_xul_stop, self.app_variables.animation.n_frames)
            x_lrs = numpy.linspace(canvas_xlr_start, canvas_xlr_stop, self.app_variables.animation.n_frames)
            y_uls = numpy.linspace(canvas_yul_start, canvas_yul_stop, self.app_variables.animation.n_frames)
            y_lrs = numpy.linspace(canvas_ylr_start, canvas_ylr_stop, self.app_variables.animation.n_frames)

            frame_num = self.app_variables.animation.current_position
            new_rect = (x_uls[frame_num], y_uls[frame_num], x_lrs[frame_num], y_lrs[frame_num])

        select_uid = self.phase_history_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
        self.phase_history_panel.canvas.modify_existing_shape_using_canvas_coords(select_uid, new_rect)
        self.update_filtered_image()
        self.update_phase_history_selection()

    def animation_fast_slow_popup(self):
        self.animation_popup_panel.deiconify()

    def main_controls_popup(self):
        self.image_info_popup_panel.deiconify()

    def ph_popup(self):
        self.ph_popup_panel.deiconify()

    # updating the various image data
    def update_fft_image(self):
        """
        This changes the underlying phase history data from the new aperture_filter object.
        """

        if self.app_variables.aperture_filter is None or \
                self.app_variables.aperture_filter.normalized_phase_history is None:
            self.make_blank()
            return

        # set the phase history image data
        temp_phase_history = numpy.abs(self.app_variables.aperture_filter.normalized_phase_history)
        min_phase_history = numpy.min(temp_phase_history)
        max_phase_history = numpy.max(temp_phase_history)
        display_phase_history = numpy.empty(temp_phase_history.shape, dtype='uint8')
        display_phase_history[:] = 255*(temp_phase_history - min_phase_history)/(max_phase_history - min_phase_history)

        if not self.app_variables.aperture_filter.flip_x_axis:
            display_phase_history = numpy.fliplr(display_phase_history)
        fft_reader = NumpyCanvasImageReader(display_phase_history)

        self._skip_update = True  # begin short circuiting a stupid canvas update
        self.phase_history_panel.set_image_reader(fft_reader)

        # set up the selection rectangle properties
        self.phase_history_panel.canvas.current_tool = "SELECT"
        vector_object = self.phase_history_panel.canvas.variables.get_tool_shape_by_name('SELECT')
        rect_bounds = self.get_fft_image_bounds()
        vector_object.image_drag_limits = rect_bounds
        self.phase_history_panel.canvas.modify_existing_shape_using_image_coords(vector_object.uid, rect_bounds)
        self._skip_update = False  # short circuiting a stupid canvas update

        # update the information about the phase history area selection
        the_shape = self.app_variables.aperture_filter.normalized_phase_history.shape
        self.image_info_panel.chip_size_panel.nx.set_text(the_shape[1])
        self.image_info_panel.chip_size_panel.ny.set_text(the_shape[0])

        # update the filtered images and other phase history information
        self.update_filtered_image()
        self.update_phase_history_selection()

    def get_fft_image_bounds(self):
        # type: () -> (int, int, int, int)
        """
        Fetch the bounds for the real phase data from the phase history image.
        This is based on the SICD.Grid ImpRespBW and SS parameters.

        Returns
        -------
        Tuple
        """

        meta = self.app_variables.image_reader.get_sicd()

        row_ratio = meta.Grid.Row.ImpRespBW*meta.Grid.Row.SS
        col_ratio = meta.Grid.Col.ImpRespBW*meta.Grid.Col.SS

        full_n_rows = self.phase_history_panel.canvas.variables.canvas_image_object.image_reader.full_image_ny
        full_n_cols = self.phase_history_panel.canvas.variables.canvas_image_object.image_reader.full_image_nx

        full_im_y_start = int(full_n_rows * (1 - row_ratio) / 2)
        full_im_y_end = full_n_rows - full_im_y_start

        full_im_x_start = int(full_n_cols * (1 - col_ratio) / 2)
        full_im_x_end = full_n_cols - full_im_x_start

        return full_im_y_start, full_im_x_start, full_im_y_end, full_im_x_end

    def update_filtered_image(self):
        """
        This updates the reconstructed image, from the selected filtered image area.
        """

        filter_image = self.get_filtered_image()
        if self.phase_history_panel.canvas.variables.canvas_image_object is None:
            return
        if filter_image is None:
            full_n_rows = self.phase_history_panel.canvas.variables.canvas_image_object.image_reader.full_image_ny
            full_n_cols = self.phase_history_panel.canvas.variables.canvas_image_object.image_reader.full_image_nx
            filter_image = numpy.zeros((full_n_rows, full_n_cols), dtype='uint8')
        self.filtered_panel.set_image_reader(NumpyCanvasImageReader(filter_image))

    def get_filtered_image(self):
        """
        Fetches the actual underlying reconstructed image
        Returns
        -------

        """
        if self.app_variables.aperture_filter is None:
            return None

        # fetch the remap function
        remap_function = self.app_variables.image_reader.remap_function
        if remap_function is None:
            remap_function = NRL()

        # fetch the data
        select_uid = self.phase_history_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
        full_image_rect = self.phase_history_panel.canvas.get_shape_image_coords(select_uid)
        if full_image_rect is None:
            return None

        y_min = int(min(full_image_rect[0::2]))
        y_max = int(max(full_image_rect[0::2]))
        x_min = int(min(full_image_rect[1::2]))
        x_max = int(max(full_image_rect[1::2]))
        if y_min == y_max or x_min == x_max:
            return None
        return remap_function(self.app_variables.aperture_filter[y_min:y_max, x_min:x_max])

    def update_phase_history_selection(self):
        """
        This updates the information in the various popups from the selected phase
        history information.
        """

        if self.app_variables.image_reader is None or \
                self.app_variables.image_reader.base_reader is None:
            return

        the_sicd = self.app_variables.image_reader.get_sicd()

        image_bounds = self.get_fft_image_bounds()
        select_uid = self.phase_history_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
        current_bounds = self.phase_history_panel.canvas.shape_image_coords_to_canvas_coords(select_uid)
        x_min = min(current_bounds[1::2])
        x_max = max(current_bounds[1::2])
        y_min = min(current_bounds[0::2])
        y_max = max(current_bounds[0::2])

        x_full_image_range = image_bounds[3] - image_bounds[1]
        y_full_image_range = image_bounds[2] - image_bounds[0]

        start_cross = 100*(x_min - image_bounds[1])/float(x_full_image_range)
        stop_cross = 100*(x_max - image_bounds[1])/float(x_full_image_range)
        fraction_cross = 100*(x_max - x_min)/float(x_full_image_range)

        start_range = 100*(y_min - image_bounds[0])/float(y_full_image_range)
        stop_range = 100*(y_max - image_bounds[0])/float(y_full_image_range)
        fraction_range = 100*(y_max - y_min)/float(y_full_image_range)

        self.phase_history.start_percent_cross.set_text("{:0.4f}".format(start_cross))
        self.phase_history.stop_percent_cross.set_text("{:0.4f}".format(stop_cross))
        self.phase_history.fraction_cross.set_text("{:0.4f}".format(fraction_cross))
        self.phase_history.start_percent_range.set_text("{:0.4f}".format(start_range))
        self.phase_history.stop_percent_range.set_text("{:0.4f}".format(stop_range))
        self.phase_history.fraction_range.set_text("{:0.4f}".format(fraction_range))

        # handle units
        self.phase_history.resolution_range_units.set_text("meters")
        self.phase_history.resolution_cross_units.set_text("meters")
        range_resolution = the_sicd.Grid.Row.ImpRespWid/(0.01*fraction_range)
        cross_resolution = the_sicd.Grid.Col.ImpRespWid/(0.01*fraction_cross)

        tmp_range_resolution = range_resolution
        tmp_cross_resolution = cross_resolution

        if self.phase_history.english_units_checkbox.is_selected():
            tmp_range_resolution = range_resolution/foot
            tmp_cross_resolution = cross_resolution/foot
            if tmp_range_resolution < 1:
                tmp_range_resolution = range_resolution/inch
                self.phase_history.resolution_range_units.set_text("inches")
            else:
                self.phase_history.resolution_range_units.set_text("feet")
            if tmp_cross_resolution < 1:
                tmp_cross_resolution = cross_resolution/inch
                self.phase_history.resolution_cross_units.set_text("inches")
            else:
                self.phase_history.resolution_cross_units.set_text("feet")
        else:
            if range_resolution < 1:
                tmp_range_resolution = range_resolution*100
                self.phase_history.resolution_range_units.set_text("cm")
            if cross_resolution < 1:
                tmp_cross_resolution = cross_resolution*100
                self.phase_history.resolution_cross_units.set_text("cm")

        self.phase_history.resolution_range.set_text("{:0.2f}".format(tmp_range_resolution))
        self.phase_history.resolution_cross.set_text("{:0.2f}".format(tmp_cross_resolution))

        cross_sample_spacing = the_sicd.Grid.Col.SS
        range_sample_spacing = the_sicd.Grid.Row.SS

        tmp_cross_ss = cross_sample_spacing
        tmp_range_ss = range_sample_spacing

        if self.phase_history.english_units_checkbox.is_selected():
            tmp_cross_ss = cross_sample_spacing / foot
            tmp_range_ss = range_sample_spacing / foot
            if tmp_cross_ss < 1:
                tmp_cross_ss = cross_sample_spacing / inch
                self.phase_history.sample_spacing_cross_units.set_text("inches")
            else:
                self.phase_history.sample_spacing_cross_units.set_text("feet")
            if tmp_range_ss < 1:
                tmp_range_ss = range_sample_spacing / inch
                self.phase_history.sample_spacing_range_units.set_text("inches")
            else:
                self.phase_history.sample_spacing_range_units.set_text("feet")
        else:
            if cross_sample_spacing < 1:
                tmp_cross_ss = cross_sample_spacing * 100
                self.phase_history.sample_spacing_cross_units.set_text("cm")
            if range_sample_spacing < 1:
                tmp_range_ss = range_sample_spacing * 100
                self.phase_history.sample_spacing_range_units.set_text("cm")

        self.phase_history.sample_spacing_cross.set_text("{:0.2f}".format(tmp_cross_ss))
        self.phase_history.sample_spacing_range.set_text("{:0.2f}".format(tmp_range_ss))

        # only update if we have twist angle and graze angles
        if the_sicd.SCPCOA.TwistAng and the_sicd.SCPCOA.GrazeAng:
            cross_ground_resolution = cross_resolution/numpy.cos(numpy.deg2rad(the_sicd.SCPCOA.TwistAng))
            range_ground_resolution = range_resolution/numpy.cos(numpy.deg2rad(the_sicd.SCPCOA.GrazeAng))

            tmp_cross_ground_res = cross_ground_resolution
            tmp_range_ground_res = range_ground_resolution

            if self.phase_history.english_units_checkbox.is_selected():
                tmp_cross_ground_res = cross_ground_resolution/foot
                tmp_range_ground_res = range_ground_resolution/foot
                if tmp_cross_ground_res < 1:
                    tmp_cross_ground_res = cross_ground_resolution/inch
                    self.phase_history.ground_resolution_cross_units.set_text("inches")
                else:
                    self.phase_history.ground_resolution_cross_units.set_text("feet")
                if tmp_range_ground_res < 1:
                    tmp_range_ground_res = range_ground_resolution / inch
                    self.phase_history.ground_resolution_range_units.set_text("inches")
                else:
                    self.phase_history.ground_resolution_range_units.set_text("feet")
            else:
                if cross_ground_resolution < 1:
                    tmp_cross_ground_res = cross_ground_resolution*100
                    self.phase_history.ground_resolution_cross_units.set_text("cm")
                if range_ground_resolution < 1:
                    tmp_range_ground_res = range_ground_resolution*100
                    self.phase_history.ground_resolution_range_units.set_text("cm")

            self.phase_history.ground_resolution_cross.set_text("{:0.2f}".format(tmp_cross_ground_res))
            self.phase_history.ground_resolution_range.set_text("{:0.2f}".format(tmp_range_ground_res))


###########
# The main app

class AppVariables(object):
    """
    App variables for the aperture tool.
    """

    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', SICDTypeCanvasImageReader,
        docstring='The complex type image reader object.')  # type: SICDTypeCanvasImageReader
    aperture_filter = TypedDescriptor(
        'aperture_filter', ApertureFilter,
        docstring='The aperture filter calculator.')  # type: ApertureFilter
    animation = TypedDescriptor(
        'animation', AnimationProperties,
        docstring='The animation configuration.')  # type: AnimationProperties
    minimum_selection_size = IntegerDescriptor(
        'minimum_selection_size', default_value=50,
        docstring='The minimum size to activate the aperture tool.')  # type: int
    maximum_selection_size = IntegerDescriptor(
        'maximum_selection_size', default_value=2500,
        docstring='The maximum size to activate the aperture tool.')  # type: int

    def __init__(self):
        self.selected_region = None     # type: Union[None, Tuple]
        self.animation = AnimationProperties()


class RegionSelection(Frame, WidgetWithMetadata):
    """
    The widget for selecting the Area of Interest for the aperture tool.
    """

    _widget_list = ("instructions", "image_panel")
    instructions = LabelDescriptor(
        "instructions",
        default_text='First, open a complex type image file using the File Menu.\n'
                     'Then, selecting a region, using the select tool, which '
                     'will open the aperture tool for that region.',
        docstring='The basic instructions.')   # type: Label
    image_panel = ImagePanelDescriptor("image_panel", docstring='The image panel.')  # type: ImagePanel

    def __init__(self, parent, reader=None, **kwargs):
        """

        Parameters
        ----------
        parent : tkinter.Tk|tkinter.Toplevel
        reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
        kwargs
        """

        # set the parent frame
        self.root = parent
        Frame.__init__(self, parent, **kwargs)
        WidgetWithMetadata.__init__(self, parent)

        self.variables = AppVariables()

        self.set_title()
        self.instructions = Label(
            self, text='First, open a complex type image file using the File Menu.\n'
                       'Then, selecting a region, using the select tool, which '
                       'will open the aperture tool for that region.')  # type: Label
        self.instructions.pack(side=tkinter.TOP, expand=tkinter.NO, fill=tkinter.X)

        self.image_panel = ImagePanel(self)  # type: ImagePanel
        self.image_panel.pack(side=tkinter.BOTTOM, expand=tkinter.TRUE, fill=tkinter.BOTH)
        self.pack(expand=tkinter.TRUE, fill=tkinter.BOTH)

        # jazz up the instruction a little
        self.instructions.config(
            font=('Arial', '12'), anchor=tkinter.CENTER, relief=tkinter.RIDGE,
            justify=tkinter.CENTER, padding=5)
        # hide some extraneous image panel elements
        self.image_panel.hide_tools('shape_drawing')
        self.image_panel.hide_shapes()

        # setup the aperture tool
        self.aperture_popup_panel = tkinter.Toplevel(parent)
        self.aperture_tool = ApertureTool(self.aperture_popup_panel, self.variables)
        self.aperture_popup_panel.withdraw()

        # define menus
        self.menu_bar = tkinter.Menu()
        # file menu
        self.file_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open Image", command=self.callback_select_files)
        self.file_menu.add_command(label="Open Directory", command=self.callback_select_directory)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        self.metadata_menu = tkinter.Menu(self.menu_bar, tearoff=0)
        self.metadata_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        self.metadata_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        self._valid_data_shown = tkinter.IntVar(self, value=0)
        self.metadata_menu.add_checkbutton(
            label='ValidData', variable=self._valid_data_shown, command=self.show_valid_data)
        # ensure menus cascade
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Metadata", menu=self.metadata_menu)

        # handle packing
        self.root.config(menu=self.menu_bar)
        self.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        # define the callbacks
        self.image_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        self.image_panel.canvas.bind('<<RemapChanged>>', self.handle_remap_change)
        self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)

        self.update_reader(reader)

    # callbacks
    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Aperture Tool"
        elif isinstance(file_name, (list, tuple)):
            the_title = "Aperture Tool, Multiple Files"
        else:
            the_title = "Aperture for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self.root.destroy()

    def show_valid_data(self):
        if self.variables.image_reader is None:
            return

        the_value = self._valid_data_shown.get()
        if the_value == 1:
            # we just checked on
            sicd = self.variables.image_reader.get_sicd()
            if sicd.ImageData.ValidData is not None:
                self.image_panel.canvas.show_valid_data(sicd.ImageData.ValidData.get_array(dtype='float64'))
        else:
            # we checked it off
            try:
                valid_data_id = self.image_panel.canvas.variables.get_tool_shape_id_by_name('VALID_DATA')
                self.image_panel.canvas.hide_shape(valid_data_id)
            except KeyError:
                pass

    def aperture_tool_popup(self):
        """
        Show the aperture tool
        """

        self.aperture_popup_panel.deiconify()

    # noinspection PyUnusedLocal
    def handle_selection_change(self, event):
        """
        Handle a change in the selection area.

        Parameters
        ----------
        event
        """

        if self.variables.image_reader is None:
            # this shouldn't ever happen?
            return

        self.aperture_tool_popup()
        # update the aperture filter
        select_uid = self.image_panel.canvas.variables.get_tool_shape_id_by_name('SELECT')
        selection_image_coords = self.image_panel.canvas.get_shape_image_coords(select_uid)

        if selection_image_coords is None:
            self.variables.aperture_filter.set_sub_image_bounds(None, None)
            self.aperture_tool.handle_main_selection_update()
            return

        min_size = min(self.variables.minimum_selection_size,
                       self.variables.image_reader.full_image_ny,
                       self.variables.image_reader.full_image_nx)
        max_size = self.variables.maximum_selection_size

        y1 = int(min(selection_image_coords[0], selection_image_coords[2]))
        x1 = int(min(selection_image_coords[1], selection_image_coords[3]))
        y2 = int(max(selection_image_coords[0], selection_image_coords[2]))
        x2 = int(max(selection_image_coords[1], selection_image_coords[3]))
        if x2-x1 < min_size or y2-y1 < min_size:
            showinfo('Minimum size selection not met.',
                     message='The selection is not as large as the specified minimum '
                             '({} pixels on an edge).'.format(min_size))
            return
        elif x2-x1 > max_size or y2-y1 > max_size:
            showinfo('Maximum size selection not met.',
                     message='The selection is not as large as the specified maximum '
                             '({} pixels on an edge).'.format(max_size))
            return

        if self.variables.aperture_filter is not None:
            self.variables.aperture_filter.set_sub_image_bounds((y1, y2), (x1, x2))
            self.aperture_tool.handle_main_selection_update()

    # noinspection PyUnusedLocal
    def handle_remap_change(self, event):
        """
        Handle that the remap for the image canvas has changed.

        Parameters
        ----------
        event
        """

        if self.variables.image_reader is not None:
            self.aperture_tool.update_filtered_image()

    # noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.my_populate_metaicon()
        self.aperture_tool.handle_reader_update()
        self.show_valid_data()

    def callback_select_files(self):
        fnames = askopenfilenames(initialdir=self.variables.browse_directory, filetypes=common_use_collection)
        if fnames is None or fnames in ['', ()]:
            return

        if len(fnames) == 1:
            the_reader = SICDTypeCanvasImageReader(fnames[0])
        else:
            the_reader = SICDTypeCanvasImageReader(fnames)
        self.update_reader(the_reader, update_browse=os.path.split(fnames[0])[0])

    def callback_select_directory(self):
        dirname = askdirectory(initialdir=self.variables.browse_directory, mustexist=True)
        if dirname is None or dirname in [(), '']:
            return
        self.update_reader(dirname, update_browse=os.path.split(dirname)[0])

    # methods used in callbacks
    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
            the_reader = SICDTypeCanvasImageReader(the_reader)

        if isinstance(the_reader, SICDTypeReader):
            the_reader = SICDTypeCanvasImageReader(the_reader)

        if not isinstance(the_reader, SICDTypeCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_title()
        # refresh appropriate GUI elements
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.aperture_tool.handle_reader_update()
        self.show_valid_data()

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon(self.variables.image_reader)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer(self.variables.image_reader)


def main(reader=None):
    """
    Main method for initializing the aperture tool

    Parameters
    ----------
    reader : None|str|SICDTypeReader|SICDTypeCanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = RegionSelection(root, reader=reader)
    root.geometry("1000x800")
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the aperture tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'input', metavar='input', default=None,  nargs='?',
        help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
