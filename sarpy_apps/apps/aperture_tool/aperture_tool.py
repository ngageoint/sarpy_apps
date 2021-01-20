# -*- coding: utf-8 -*-
"""
This module provides a version of the aperture tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import os
import time
import numpy
import scipy.constants.constants as scipy_constants
from typing import Union, Tuple

import tkinter
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showinfo

from tk_builder.base_elements import TypedDescriptor, IntegerDescriptor, BooleanDescriptor, FloatDescriptor
from tk_builder.image_reader import NumpyImageReader
from tk_builder.panel_builder import WidgetPanel, RadioButtonPanel
from tk_builder.panels.file_selector import FileSelector
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.utils.image_utils import frame_sequence_utils
from tk_builder.widgets import widget_descriptors, basic_widgets

import sarpy.visualization.remap as remap
from sarpy.processing.aperture_filter import ApertureFilter

from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes.metaviewer import Metaviewer

# TODO: review the RadioButtonPanel situation?


##################
# Animation panel

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
    label = widget_descriptors.LabelDescriptor(
        "label", default_text="Aperture Fraction:")  # type: basic_widgets.Label
    aperture_fraction = widget_descriptors.EntryDescriptor(
        "aperture_fraction", default_text="0.25")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class ResolutionSettingsPanel(WidgetPanel):
    _widget_list = ("min_res_label", "min_res", "max_res_label", "max_res")
    min_res_label = widget_descriptors.LabelDescriptor(
        "min_res_label", default_text="Min Res")  # type: basic_widgets.Label
    max_res_label = widget_descriptors.LabelDescriptor(
        "max_res_label", default_text="Max Res")  # type: basic_widgets.Label
    min_res = widget_descriptors.EntryDescriptor(
        "min_res", default_text="10")  # type: basic_widgets.Entry
    max_res = widget_descriptors.EntryDescriptor(
        "max_res", default_text="100")  # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2, column_widths=[20, 10])


class AnimationSettingsPanel(WidgetPanel):

    _widget_list = ("number_of_frames_label", "number_of_frames", "r1c3", "r1c4",
                    "frame_rate_label", "frame_rate", "fps_label", "r2c4",
                    "step_back", "step_forward", "play", "stop",
                    "cycle_continuously")

    number_of_frames_label = \
        widget_descriptors.LabelDescriptor(
            "number_of_frames_label", default_text="Number of Frames:")  # type: basic_widgets.Label
    frame_rate_label = widget_descriptors.LabelDescriptor(
        "frame_rate_label", default_text="Frame Rate:")  # type: basic_widgets.Label
    fps_label = widget_descriptors.LabelDescriptor(
        "fps_label", default_text="fps")  # type: basic_widgets.Label

    r1c3 = widget_descriptors.LabelDescriptor(
        "r1c3", default_text="")  # type: basic_widgets.Label
    r1c4 = widget_descriptors.LabelDescriptor(
        "r1c4", default_text="")  # type: basic_widgets.Label
    r2c4 = widget_descriptors.LabelDescriptor(
        "r2c4", default_text="")  # type: basic_widgets.Label

    number_of_frames = widget_descriptors.EntryDescriptor(
        "number_of_frames")  # type: basic_widgets.Entry
    aperture_fraction = widget_descriptors.EntryDescriptor(
        "aperture_fraction")  # type: basic_widgets.Entry
    frame_rate = widget_descriptors.EntryDescriptor(
        "frame_rate")  # type: basic_widgets.Entry
    cycle_continuously = widget_descriptors.CheckButtonDescriptor(
        "cycle_continuously")  # type: basic_widgets.CheckButton
    step_forward = widget_descriptors.ButtonDescriptor(
        "step_forward")  # type: basic_widgets.Button
    step_back = widget_descriptors.ButtonDescriptor(
        "step_back")  # type: basic_widgets.Button
    play = widget_descriptors.ButtonDescriptor(
        "play")  # type: basic_widgets.Button
    stop = widget_descriptors.ButtonDescriptor(
        "stop")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)

        self.init_w_box_layout(n_columns=4, column_widths=[20, 10, 3, 3])

        self.number_of_frames.set_text("7")
        self.frame_rate.set_text("5")


class AnimationPanel(WidgetPanel):
    _widget_list = ("mode_panel", "animation_settings", "fast_slow_settings", "resolution_settings", "save")

    mode_panel = widget_descriptors.TypedDescriptor(
        "mode_panel", ModePanel)  # type: ModePanel
    animation_settings = widget_descriptors.TypedDescriptor(
        "animation_settings", AnimationSettingsPanel)  # type: AnimationSettingsPanel
    fast_slow_settings = widget_descriptors.TypedDescriptor(
        "fast_slow_settings", FastSlowSettingsPanel)  # type: FastSlowSettingsPanel
    resolution_settings = widget_descriptors.TypedDescriptor(
        "resolution_settings", ResolutionSettingsPanel)  # type: ResolutionSettingsPanel
    save = widget_descriptors.ButtonDescriptor("save")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent

        self.init_w_vertical_layout()
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)


###########
# Image info panel

class DeskewFastSlow(RadioButtonPanel):
    _widget_list = ("fast", "slow",)
    fast = widget_descriptors.RadioButtonDescriptor("fast")  # type: basic_widgets.RadioButton
    slow = widget_descriptors.RadioButtonDescriptor("slow")  # type: basic_widgets.RadioButton

    def __init__(self, primary):
        self.primary = primary
        RadioButtonPanel.__init__(self, primary)
        self.init_w_vertical_layout()


class PhdOptionsPanel(WidgetPanel):

    _widget_list = ("apply_deskew", "uniform_weighting", "deskew_fast_slow")
    apply_deskew = widget_descriptors.CheckButtonDescriptor(
        "apply_deskew", default_text="apply deskew")  # type: basic_widgets.CheckButton
    uniform_weighting = widget_descriptors.CheckButtonDescriptor(
        "uniform_weighting", default_text="apply uniform weighting")  # type: basic_widgets.CheckButton
    deskew_fast_slow = widget_descriptors.PanelDescriptor(
        "deskew_fast_slow", DeskewFastSlow, default_text="direction")  # type: DeskewFastSlow

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class ChipSizePanel(WidgetPanel):
    _widget_list = ("nx_label", "nx", "ny_label", "ny")
    nx_label = widget_descriptors.LabelDescriptor("nx_label")          # type: basic_widgets.Label
    nx = widget_descriptors.EntryDescriptor("nx")                # type: basic_widgets.Entry
    ny_label = widget_descriptors.LabelDescriptor("ny_label")          # type: basic_widgets.Label
    ny = widget_descriptors.EntryDescriptor("ny")                # type: basic_widgets.Entry

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_box_layout(n_columns=2)
        self.nx.config(state="disabled")
        self.ny.config(state="disabled")

        self.nx_label.set_text("nx: ")
        self.ny_label.set_text("ny: ")


class ImageInfoPanel(WidgetPanel):
    _widget_list = ("file_selector", "chip_size_panel", "phd_options")
    file_selector = widget_descriptors.PanelDescriptor("file_selector", FileSelector)          # type: FileSelector
    chip_size_panel = widget_descriptors.PanelDescriptor("chip_size_panel", ChipSizePanel)     # type: ChipSizePanel
    phd_options = widget_descriptors.PanelDescriptor("phd_options", PhdOptionsPanel)  # type: PhdOptionsPanel

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        # self.init_w_basic_widget_list(n_rows=2, n_widgets_per_row_list=[1, 2])
        self.init_w_vertical_layout()

        self.file_selector.set_fname_filters([("NITF files", ".nitf .NITF .ntf .NTF")])
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

    r1c1 = widget_descriptors.LabelDescriptor("r1c1", default_text="")
    r1c3 = widget_descriptors.LabelDescriptor("r1c3", default_text="")
    r1c5 = widget_descriptors.LabelDescriptor("r1c5", default_text="")

    r2c3 = widget_descriptors.LabelDescriptor("r2c3", default_text="")
    r2c5 = widget_descriptors.LabelDescriptor("r2c5", default_text="")

    r3c3 = widget_descriptors.LabelDescriptor("r3c3", default_text="")
    r3c5 = widget_descriptors.LabelDescriptor("r3c5", default_text="")

    r4c3 = widget_descriptors.LabelDescriptor("r4c3", default_text="")
    r4c5 = widget_descriptors.LabelDescriptor("r4c5", default_text="")

    cross_range_label = widget_descriptors.LabelDescriptor("cross_range_label", default_text="Cross-Range")
    range_label = widget_descriptors.LabelDescriptor("range_label", default_text="Range")

    start_percent_label = widget_descriptors.LabelDescriptor("start_percent_label", default_text="Start %")
    stop_percent_label = widget_descriptors.LabelDescriptor("stop_percent_label", default_text="Stop %")
    fraction_label = widget_descriptors.LabelDescriptor("fraction_label", default_text="Fraction")
    resolution_label = widget_descriptors.LabelDescriptor("resolution_label", default_text="Resolution")
    sample_spacing_label = widget_descriptors.LabelDescriptor("sample_spacing_label", default_text="Sample Spacing")
    ground_resolution_label = widget_descriptors.LabelDescriptor("ground_resolution_label", default_text="Ground Resolution")

    start_percent_cross = widget_descriptors.EntryDescriptor("start_percent_cross")  # type: basic_widgets.Entry
    stop_percent_cross = widget_descriptors.EntryDescriptor("stop_percent_cross")  # type: basic_widgets.Entry
    fraction_cross = widget_descriptors.EntryDescriptor("fraction_cross")  # type: basic_widgets.Entry
    resolution_cross = widget_descriptors.EntryDescriptor("resolution_cross")  # type: basic_widgets.Entry
    sample_spacing_cross = widget_descriptors.EntryDescriptor("sample_spacing_cross")  # type: basic_widgets.Entry
    ground_resolution_cross = widget_descriptors.EntryDescriptor("ground_resolution_cross")  # type: basic_widgets.Entry

    start_percent_range = widget_descriptors.EntryDescriptor("start_percent_range")  # type: basic_widgets.Entry
    stop_percent_range = widget_descriptors.EntryDescriptor("stop_percent_range")  # type: basic_widgets.Entry
    fraction_range = widget_descriptors.EntryDescriptor("fraction_range")  # type: basic_widgets.Entry
    resolution_range = widget_descriptors.EntryDescriptor("resolution_range")  # type: basic_widgets.Entry
    sample_spacing_range = widget_descriptors.EntryDescriptor("sample_spacing_range")  # type: basic_widgets.Entry
    ground_resolution_range = widget_descriptors.EntryDescriptor("ground_resolution_range")  # type: basic_widgets.Entry

    resolution_cross_units = widget_descriptors.LabelDescriptor("resolution_cross_units")  # type: basic_widgets.Label
    sample_spacing_cross_units = widget_descriptors.LabelDescriptor("sample_spacing_cross_units")  # type: basic_widgets.Label
    ground_resolution_cross_units = widget_descriptors.LabelDescriptor("ground_resolution_cross_units")  # type: basic_widgets.Label

    resolution_range_units = widget_descriptors.LabelDescriptor("resolution_range_units")  # type: basic_widgets.Label
    sample_spacing_range_units = widget_descriptors.LabelDescriptor("sample_spacing_range_units")  # type: basic_widgets.Label
    ground_resolution_range_units = widget_descriptors.LabelDescriptor("ground_resolution_range_units")  # type: basic_widgets.Label

    full_aperture_button = widget_descriptors.ButtonDescriptor("full_aperture_button")  # type: basic_widgets.Button
    english_units_checkbox = widget_descriptors.CheckButtonDescriptor("english_units_checkbox")  # type: basic_widgets.CheckButton

    def __init__(self, parent):
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

        self.master.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.master.withdraw()


###########
# selected region popup

class Toolbar(WidgetPanel):
    _widget_list = ("select_aoi", "submit_aoi")
    select_aoi = widget_descriptors.ButtonDescriptor("select_aoi")  # type: basic_widgets.Button
    submit_aoi = widget_descriptors.ButtonDescriptor("submit_aoi")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class SelectedRegionPanel(WidgetPanel):
    _widget_list = ("toolbar", "image_panel")
    image_panel = widget_descriptors.ImagePanelDescriptor(
        "image_panel")  # type: ImagePanel
    toolbar = widget_descriptors.PanelDescriptor(
        "toolbar", Toolbar)   # type: Toolbar

    def __init__(self, parent, app_variables):
        """

        Parameters
        ----------
        parent : tkinter.Tk|tkinter.TopLevel
        app_variables : AppVariables
        """

        # set the parent frame
        WidgetPanel.__init__(self, parent)

        self.parent = parent
        self.app_variables = app_variables

        self.init_w_vertical_layout()
        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)
        self.toolbar.pack(expand=tkinter.YES, fill=tkinter.X)

        sicd_reader = ComplexImageReader(app_variables.sicd_reader_object.base_reader.file_name)
        self.image_panel.set_image_reader(sicd_reader)

        self.image_panel.hide_controls()

        self.toolbar.select_aoi.config(command=self.set_current_tool_to_select)
        self.toolbar.submit_aoi.config(command=self.submit_aoi)
        self.toolbar.do_not_expand()

    def set_current_tool_to_select(self):
        self.image_panel.canvas.set_current_tool_to_select()

    def submit_aoi(self):
        selection_image_coords = self.image_panel.canvas.get_shape_image_coords(
            self.image_panel.canvas.variables.select_rect.uid)
        if selection_image_coords:
            self.app_variables.selected_region = selection_image_coords
            y1 = int(min(selection_image_coords[0], selection_image_coords[2]))
            x1 = int(min(selection_image_coords[1], selection_image_coords[3]))
            y2 = int(max(selection_image_coords[0], selection_image_coords[2]))
            x2 = int(max(selection_image_coords[1], selection_image_coords[3]))
            complex_data = self.app_variables.sicd_reader_object.base_reader[y1:y2, x1:x2]
            self.app_variables.aperture_filter.set_sub_image_bounds((y1, y2), (x1, x2))
            self.app_variables.selected_region_complex_data = complex_data
            self.parent.destroy()
        else:
            showinfo('No Region Selected', message='Select region for action.')
            return


###########
# The main app

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


class AppVariables(object):
    sicd_reader_object = TypedDescriptor(
        'sicd_reader_object', ComplexImageReader,
        docstring='')  # type: ComplexImageReader
    aperture_filter = TypedDescriptor(
        'aperture_filter', ApertureFilter,
        docstring='')  # type: ApertureFilter
    fft_complex_data = TypedDescriptor(
        'fft_complex_data', numpy.ndarray,
        docstring='')  # type: numpy.ndarray
    selected_region_complex_data = TypedDescriptor(
        'selected_region_complex_data', numpy.ndarray,
        docstring='')  # type: numpy.ndarray
    animation = TypedDescriptor(
        'animation', AnimationProperties,
        docstring='The animation configuration.')  # type: AnimationProperties

    def __init__(self):
        self.selected_region = None     # type: Union[None, Tuple]
        self.animation = AnimationProperties()


class ApertureTool(WidgetPanel):
    _widget_list = ("frequency_vs_degree_panel", "filtered_panel")

    frequency_vs_degree_panel = widget_descriptors.ImagePanelDescriptor(
        "frequency_vs_degree_panel")  # type: ImagePanel
    filtered_panel = widget_descriptors.ImagePanelDescriptor(
        "filtered_panel")  # type: ImagePanel

    image_info_panel = widget_descriptors.PanelDescriptor("image_info_panel", ImageInfoPanel)  # type: ImageInfoPanel
    metaicon = widget_descriptors.PanelDescriptor("metaicon", MetaIcon)  # type: MetaIcon
    phase_history = widget_descriptors.PanelDescriptor("phase_history", PhaseHistoryPanel)  # type: PhaseHistoryPanel
    metaviewer = widget_descriptors.PanelDescriptor("metaviewer", Metaviewer)  # type: Metaviewer
    animation_panel = widget_descriptors.PanelDescriptor("animation_panel", AnimationPanel)   # type: AnimationPanel

    def __init__(self, primary):
        self.app_variables = AppVariables()
        self.primary = primary

        primary_frame = basic_widgets.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_horizontal_layout()

        # define some informational popups
        self.image_info_popup_panel = tkinter.Toplevel(self.primary)
        self.image_info_panel = ImageInfoPanel(self.image_info_popup_panel)
        self.image_info_popup_panel.withdraw()

        self.image_info_panel.file_selector.select_file.config(command=self.select_file)

        self.ph_popup_panel = tkinter.Toplevel(self.primary)
        self.phase_history = PhaseHistoryPanel(self.ph_popup_panel)
        self.ph_popup_panel.withdraw()

        self.metaicon_popup_panel = tkinter.Toplevel(self.primary)
        self.metaicon = MetaIcon(self.metaicon_popup_panel)
        self.metaicon_popup_panel.withdraw()

        self.metaviewer_popup_panel = tkinter.Toplevel(self.primary)
        self.metaviewer = Metaviewer(self.metaviewer_popup_panel)
        self.metaviewer_popup_panel.withdraw()

        self.animation_popup_panel = tkinter.Toplevel(self.primary)
        self.animation_panel = AnimationPanel(self.animation_popup_panel)
        self.animation_popup_panel.withdraw()

        # callbacks for animation
        self.animation_panel.animation_settings.play.config(command=self.callback_play_animation)
        self.animation_panel.animation_settings.step_forward.config(command=self.callback_step_forward)
        self.animation_panel.animation_settings.step_back.config(command=self.callback_step_back)
        self.animation_panel.animation_settings.stop.config(command=self.callback_stop_animation)
        self.animation_panel.save.config(command=self.callback_save_animation)

        menubar = tkinter.Menu()

        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.select_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        # create more pulldown menus
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Main Controls", command=self.main_controls_popup)
        popups_menu.add_command(label="Phase History", command=self.ph_popup)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        popups_menu.add_command(label="Animation", command=self.animation_fast_slow_popup)

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Popups", menu=popups_menu)

        primary.config(menu=menubar)

        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        # configure our panels
        self.frequency_vs_degree_panel.hide_tools()
        self.frequency_vs_degree_panel.hide_shapes()
        self.frequency_vs_degree_panel.hide_select_index()

        self.frequency_vs_degree_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        self.frequency_vs_degree_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)

        self.filtered_panel.hide_tools()
        self.filtered_panel.hide_shapes()
        self.filtered_panel.hide_select_index()

        # TODO: is this necessary?
        # self.frequency_vs_degree_panel.pack(expand=True, fill=tkinter.BOTH)
        # self.filtered_panel.pack(expand=True, fill=tkinter.BOTH)

        self.image_info_panel.phd_options.uniform_weighting.config(command=self.callback_update_weighting)
        self.image_info_panel.phd_options.apply_deskew.config(command=self.callback_update_apply_deskew)
        self.image_info_panel.phd_options.deskew_fast_slow.slow.config(command=self.callback_update_deskew_direction)
        self.image_info_panel.phd_options.deskew_fast_slow.fast.config(command=self.callback_update_deskew_direction)

        self.filtered_panel.canvas.set_canvas_size(600, 400)

        self.frequency_vs_degree_panel.canvas.disable_mouse_zoom()
        self.filtered_panel.canvas.disable_mouse_zoom()

        self.metaicon.hide_on_close()

    def callback_update_deskew_direction(self):
        if self.image_info_panel.phd_options.deskew_fast_slow.selection() == self.image_info_panel.phd_options.deskew_fast_slow.slow:
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

    def exit(self):
        self.quit()

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

    def callback_step_forward(self):
        self.step_animation("forward")

    def callback_step_back(self):
        self.step_animation("back")

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
        fft_canvas_bounds = self.frequency_vs_degree_panel.canvas.image_coords_to_canvas_coords(
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
                canvas_yul_stop, canvas_ylr_stop  = yul, ylr
            else:
                canvas_yul_start, canvas_ylr_start = mid_y - max_y_width, mid_y + max_y_width
                canvas_yul_stop, canvas_ylr_stop = mid_y - min_y_width, mid_y + min_y_width

            x_uls = numpy.linspace(canvas_xul_start, canvas_xul_stop, self.app_variables.animation.n_frames)
            x_lrs = numpy.linspace(canvas_xlr_start, canvas_xlr_stop, self.app_variables.animation.n_frames)
            y_uls = numpy.linspace(canvas_yul_start, canvas_yul_stop, self.app_variables.animation.n_frames)
            y_lrs = numpy.linspace(canvas_ylr_start, canvas_ylr_stop, self.app_variables.animation.n_frames)

            frame_num = self.app_variables.animation.current_position
            new_rect = (x_uls[frame_num], y_uls[frame_num], x_lrs[frame_num], y_lrs[frame_num])

        self.frequency_vs_degree_panel.canvas.modify_existing_shape_using_canvas_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid, new_rect)
        self.update_filtered_image()
        self.update_phase_history_selection()

    def callback_stop_animation(self):
        self.app_variables.animation.stop_pressed = True
        self.animation_panel.animation_settings.unpress_all_buttons()

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
                self.frequency_vs_degree_panel.update()
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
        self.animation_panel.unpress_all_buttons()

    def animation_fast_slow_popup(self):
        self.animation_popup_panel.deiconify()

    def metaviewer_popup(self):
        self.metaviewer_popup_panel.deiconify()

    def main_controls_popup(self):
        self.image_info_popup_panel.deiconify()

    def ph_popup(self):
        self.ph_popup_panel.deiconify()

    def metaicon_popup(self):
        self.metaicon_popup_panel.deiconify()

    def handle_selection_change(self, event):
        self.update_phase_history_selection()
        self.update_filtered_image()

    def update_fft_image(self):
        """
        This changes the underlying phase history data from the new aperture_filter object.
        """

        if self.app_variables.aperture_filter is not None:
            fft_complex_data = self.app_variables.aperture_filter.normalized_phase_history
            self.app_variables.fft_complex_data = fft_complex_data

            # self.app_variables.fft_display_data = remap.density(fft_complex_data)
            fft_display_data = numpy.abs(fft_complex_data)
            fft_display_data = fft_display_data - fft_display_data.min()
            fft_display_data = fft_display_data / fft_display_data.max() * 255
            self.app_variables.fft_display_data = fft_display_data
            if not self.app_variables.aperture_filter.flip_x_axis:
                self.app_variables.fft_display_data = numpy.fliplr(self.app_variables.fft_display_data)
            fft_reader = NumpyImageReader(self.app_variables.fft_display_data)
            self.frequency_vs_degree_panel.set_image_reader(fft_reader)
            # self.frequency_vs_degree_panel.update_everything()

    def select_file(self):
        sicd_fname = self.image_info_panel.file_selector.select_file_command()
        if sicd_fname == '':
            # no file was selected
            return
        self.app_variables.sicd_reader_object = ComplexImageReader(sicd_fname)

        dim = 1
        if self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Row.DeltaKCOAPoly:
            if self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Row.DeltaKCOAPoly.Coefs == [[0]]:
                dim = 0

        self.app_variables.aperture_filter = \
            ApertureFilter(self.app_variables.sicd_reader_object.base_reader,
                           dimension=dim,
                           apply_deskew=True,
                           apply_deweighting=True)
        self.image_info_panel.phd_options.uniform_weighting.value.set(True)
        self.image_info_panel.phd_options.apply_deskew.value.set(True)
        if dim == 0:
            self.image_info_panel.phd_options.deskew_fast_slow.set_selection(0)
        else:
            self.image_info_panel.phd_options.deskew_fast_slow.set_selection(1)

        # handle the case of no deskew:
        if not self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Row.DeltaKCOAPoly and \
                not self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Col.DeltaKCOAPoly:
            self.image_info_panel.phd_options.deskew_fast_slow.fast.configure(state="disabled")
            self.image_info_panel.phd_options.deskew_fast_slow.slow.configure(state="disabled")
            self.image_info_panel.phd_options.apply_deskew.config(state="disabled")
            self.image_info_panel.phd_options.uniform_weighting.config(state="disabled")

        # TODO: Check for default deweight value in Grid.Col/Row.WgtType

        # TODO: handle index, and generalize what sicd_reader_object could be...
        self.metaicon.create_from_reader(self.app_variables.sicd_reader_object.base_reader, index=0)

        popup = tkinter.Toplevel(self.primary)
        selected_region_popup = SelectedRegionPanel(popup, self.app_variables)
        selected_region_popup.image_panel.set_image_reader(self.app_variables.sicd_reader_object)
        popup.geometry("1000x1000")
        popup.after(200, selected_region_popup.image_panel.update_everything)

        self.primary.wait_window(popup)

        selected_region_complex_data = self.app_variables.aperture_filter.normalized_phase_history

        self.update_fft_image()

        # TODO: move this into update_fft_image...
        self.frequency_vs_degree_panel.canvas.set_current_tool_to_edit_shape()
        self.frequency_vs_degree_panel.canvas.variables.current_shape_id = \
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid
        self.frequency_vs_degree_panel.canvas.modify_existing_shape_using_image_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid, self.get_fft_image_bounds())
        vector_object = self.frequency_vs_degree_panel.canvas.get_vector_object(
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid)
        vector_object.image_drag_limits = self.get_fft_image_bounds()
        self.frequency_vs_degree_panel.canvas.show_shape(
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid)

        filtered_numpy_reader = NumpyImageReader(self.get_filtered_image())
        self.filtered_panel.set_image_reader(filtered_numpy_reader)

        self.image_info_panel.chip_size_panel.nx.set_text(numpy.shape(selected_region_complex_data)[1])
        self.image_info_panel.chip_size_panel.ny.set_text(numpy.shape(selected_region_complex_data)[0])

        self.update_phase_history_selection()

        self.metaviewer.populate_from_reader(self.app_variables.sicd_reader_object.base_reader)

        self.callback_resize(None)

    def get_fft_image_bounds(self):
        # type: (...) -> (int, int, int, int)
        meta = self.app_variables.sicd_reader_object.base_reader.sicd_meta

        row_ratio = meta.Grid.Row.ImpRespBW * meta.Grid.Row.SS
        col_ratio = meta.Grid.Col.ImpRespBW * meta.Grid.Col.SS

        full_n_rows = self.frequency_vs_degree_panel.canvas.variables.canvas_image_object.image_reader.full_image_ny
        full_n_cols = self.frequency_vs_degree_panel.canvas.variables.canvas_image_object.image_reader.full_image_nx

        full_im_y_start = int(full_n_rows * (1 - row_ratio) / 2)
        full_im_y_end = full_n_rows - full_im_y_start

        full_im_x_start = int(full_n_cols * (1 - col_ratio) / 2)
        full_im_x_end = full_n_cols - full_im_x_start

        return full_im_y_start, full_im_x_start, full_im_y_end, full_im_x_end

    def update_filtered_image(self):
        """
        This updates the reconstructed image, from the selected filtered image area.
        """

        if self.get_filtered_image() is not None:
            self.filtered_panel.set_image_reader(NumpyImageReader(self.get_filtered_image()))

    def get_filtered_image(self):
        if self.app_variables.aperture_filter is None:
            return

        select_rect_id = self.frequency_vs_degree_panel.canvas.variables.select_rect.uid
        full_image_rect = self.frequency_vs_degree_panel.canvas.get_shape_image_coords(select_rect_id)

        if full_image_rect is not None:
            y1 = int(full_image_rect[0])
            x1 = int(full_image_rect[1])
            y2 = int(full_image_rect[2])
            x2 = int(full_image_rect[3])

            y_ul = min(y1, y2)
            y_lr = max(y1, y2)
            x_ul = min(x1, x2)
            x_lr = max(x1, x2)

            filtered_complex_image = self.app_variables.aperture_filter[y_ul:y_lr, x_ul:x_lr]
            filtered_display_image = remap.density(filtered_complex_image)
            return filtered_display_image

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
            self.frequency_vs_degree_panel.update()
        fps = float(self.animation_panel.animation_settings.frame_rate.get())
        frame_sequence_utils.save_numpy_frame_sequence_to_animated_gif(frame_sequence, filename, fps)
        self.animation_panel.animation_settings.enable_all_widgets()

    def update_phase_history_selection(self):
        """
        This updates the information in the various popups from the selected phase history information.
        """

        image_bounds = self.get_fft_image_bounds()
        current_bounds = self.frequency_vs_degree_panel.canvas.shape_image_coords_to_canvas_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect.uid)
        x_min = min(current_bounds[1], current_bounds[3])
        x_max = max(current_bounds[1], current_bounds[3])
        y_min = min(current_bounds[0], current_bounds[2])
        y_max = max(current_bounds[0], current_bounds[2])

        x_full_image_range = image_bounds[3] - image_bounds[1]
        y_full_image_range = image_bounds[2] - image_bounds[0]

        start_cross = (x_min - image_bounds[1]) / x_full_image_range * 100
        stop_cross = (x_max - image_bounds[1]) / x_full_image_range * 100
        fraction_cross = (x_max - x_min) / x_full_image_range * 100

        start_range = (y_min - image_bounds[0]) / y_full_image_range * 100
        stop_range = (y_max - image_bounds[0]) / y_full_image_range * 100
        fraction_range = (y_max - y_min) / y_full_image_range * 100

        self.phase_history.start_percent_cross.set_text("{:0.4f}".format(start_cross))
        self.phase_history.stop_percent_cross.set_text("{:0.4f}".format(stop_cross))
        self.phase_history.fraction_cross.set_text("{:0.4f}".format(fraction_cross))
        self.phase_history.start_percent_range.set_text("{:0.4f}".format(start_range))
        self.phase_history.stop_percent_range.set_text("{:0.4f}".format(stop_range))
        self.phase_history.fraction_range.set_text("{:0.4f}".format(fraction_range))

        # handle units
        self.phase_history.resolution_range_units.set_text("meters")
        self.phase_history.resolution_cross_units.set_text("meters")
        range_resolution = self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Row.ImpRespWid / \
                           (fraction_range / 100.0)
        cross_resolution = self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Col.ImpRespWid / \
                           (fraction_cross / 100.0)

        tmp_range_resolution = range_resolution
        tmp_cross_resolution = cross_resolution

        if self.phase_history.english_units_checkbox.is_selected():
            tmp_range_resolution = range_resolution / scipy_constants.foot
            tmp_cross_resolution = cross_resolution / scipy_constants.foot
            if tmp_range_resolution < 1:
                tmp_range_resolution = range_resolution / scipy_constants.inch
                self.phase_history.resolution_range_units.set_text("inches")
            else:
                self.phase_history.resolution_range_units.set_text("feet")
            if tmp_cross_resolution < 1:
                tmp_cross_resolution = cross_resolution / scipy_constants.inch
                self.phase_history.resolution_cross_units.set_text("inches")
            else:
                self.phase_history.resolution_cross_units.set_text("feet")
        else:
            if range_resolution < 1:
                tmp_range_resolution = range_resolution * 100
                self.phase_history.resolution_range_units.set_text("cm")
            if cross_resolution < 1:
                tmp_cross_resolution = cross_resolution * 100
                self.phase_history.resolution_cross_units.set_text("cm")

        self.phase_history.resolution_range.set_text("{:0.2f}".format(tmp_range_resolution))
        self.phase_history.resolution_cross.set_text("{:0.2f}".format(tmp_cross_resolution))

        cross_sample_spacing = self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Col.SS
        range_sample_spacing = self.app_variables.sicd_reader_object.base_reader.sicd_meta.Grid.Row.SS

        tmp_cross_ss = cross_sample_spacing
        tmp_range_ss = range_sample_spacing

        if self.phase_history.english_units_checkbox.is_selected():
            tmp_cross_ss = cross_sample_spacing / scipy_constants.foot
            tmp_range_ss = range_sample_spacing / scipy_constants.foot
            if tmp_cross_ss < 1:
                tmp_cross_ss = cross_sample_spacing / scipy_constants.inch
                self.phase_history.sample_spacing_cross_units.set_text("inches")
            else:
                self.phase_history.sample_spacing_cross_units.set_text("feet")
            if tmp_range_ss < 1:
                tmp_range_ss = range_sample_spacing / scipy_constants.inch
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
        if self.app_variables.sicd_reader_object.base_reader.sicd_meta.SCPCOA.TwistAng and \
                self.app_variables.sicd_reader_object.base_reader.sicd_meta.SCPCOA.GrazeAng:

            cross_ground_resolution = cross_resolution / numpy.cos(
                numpy.deg2rad(self.app_variables.sicd_reader_object.base_reader.sicd_meta.SCPCOA.TwistAng))
            range_ground_resolution = range_resolution / numpy.cos(
                numpy.deg2rad(self.app_variables.sicd_reader_object.base_reader.sicd_meta.SCPCOA.GrazeAng))

            tmp_cross_ground_res = cross_ground_resolution
            tmp_range_ground_res = range_ground_resolution

            if self.phase_history.english_units_checkbox.is_selected():
                tmp_cross_ground_res = cross_ground_resolution / scipy_constants.foot
                tmp_range_ground_res = range_ground_resolution / scipy_constants.foot
                if tmp_cross_ground_res < 1:
                    tmp_cross_ground_res = cross_ground_resolution / scipy_constants.inch
                    self.phase_history.ground_resolution_cross_units.set_text("inches")
                else:
                    self.phase_history.ground_resolution_cross_units.set_text("feet")
                if tmp_range_ground_res < 1:
                    tmp_range_ground_res = range_ground_resolution / scipy_constants.inch
                    self.phase_history.ground_resolution_range_units.set_text("inches")
                else:
                    self.phase_history.ground_resolution_range_units.set_text("feet")
            else:
                if cross_ground_resolution < 1:
                    tmp_cross_ground_res = cross_ground_resolution * 100
                    self.phase_history.ground_resolution_cross_units.set_text("cm")
                if range_ground_resolution < 1:
                    tmp_range_ground_res = range_ground_resolution * 100
                    self.phase_history.ground_resolution_range_units.set_text("cm")

            self.phase_history.ground_resolution_cross.set_text("{:0.2f}".format(tmp_cross_ground_res))
            self.phase_history.ground_resolution_range.set_text("{:0.2f}".format(tmp_range_ground_res))


if __name__ == '__main__':
    root = tkinter.Tk()
    app = ApertureTool(root)
    root.geometry("1200x600")
    root.mainloop()

