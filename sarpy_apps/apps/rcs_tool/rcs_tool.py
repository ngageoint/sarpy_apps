import os
import time
import numpy
from scipy.fftpack import fft2, ifft2, fftshift

import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import filedialog
from tkinter import Menu
from tk_builder.panel_builder import WidgetPanel
from tk_builder.utils.image_utils import frame_sequence_utils
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.image_readers.numpy_image_reader import NumpyImageReader
from tk_builder.utils.color_utils.color_cycler import ColorCycler

from tk_builder.widgets import widget_descriptors
from tk_builder.widgets import basic_widgets
from tk_builder.panel_builder import RadioButtonPanel

import sarpy.visualization.remap as remap
from sarpy_apps.apps.aperture_tool.panels.image_info_panel.image_info_panel import ImageInfoPanel
from sarpy_apps.apps.aperture_tool.panels.selected_region_popup.selected_region_popup import SelectedRegionPanel
from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from sarpy_apps.apps.aperture_tool.panels.phase_history_selecion_panel.phase_history_selection_panel \
    import PhaseHistoryPanel
from sarpy_apps.supporting_classes.metaviewer import Metaviewer
from sarpy_apps.apps.aperture_tool.panels.animation_popup.animation_panel import AnimationPanel

from sarpy.io.general.base import BaseReader
import scipy.constants.constants as scipy_constants
from tkinter.filedialog import asksaveasfilename
from sarpy_apps.apps.aperture_tool.app_variables import AppVariables


class ControlsPanel(WidgetPanel):
    class RoiControls(WidgetPanel):
        class RoiRadiobuttons(RadioButtonPanel):
            _widget_list = ("rectangle", "polygon", "ellipse",)
            rectangle = widget_descriptors.RadioButtonDescriptor("rectangle")  # type: basic_widgets.RadioButton
            polygon = widget_descriptors.RadioButtonDescriptor("polygon")  # type: basic_widgets.RadioButton
            ellipse = widget_descriptors.RadioButtonDescriptor("ellipse")  # type: basic_widgets.RadioButton

            def __init__(self, parent):
                RadioButtonPanel.__init__(self, parent)
                self.parent = parent
                self.init_w_vertical_layout()

        _widget_list = ("roi_radiobuttons", "draw", "select_closest", "edit")

        roi_radiobuttons = widget_descriptors.PanelDescriptor("roi_radiobuttons", RoiRadiobuttons)  # type: ControlsPanel.RoiControls.RoiRadiobuttons
        draw = widget_descriptors.ButtonDescriptor("draw")  # type: basic_widgets.Button
        select_closest = widget_descriptors.ButtonDescriptor("select_closest")  # type: basic_widgets.Button
        edit = widget_descriptors.ButtonDescriptor("edit")  # type: basic_widgets.Button

        def __init__(self, parent):
            WidgetPanel.__init__(self, parent)
            self.parent = parent
            self.init_w_vertical_layout()

    class DataGenerationOptions(WidgetPanel):
        _widget_list = ("measure_label", "measure_dropdown",
                        "slow_time_units", "slow_time_dropdown",
                        "target_azimuth_label", "target_azimuth",
                        "use_cal_constant", "db", "db_label",
                        "plot_in_db", "exclude_zeropad")

        measure_label = widget_descriptors.LabelDescriptor(
            "measure_label", default_text="Measure: ")  # type: basic_widgets.Label
        measure_dropdown = widget_descriptors.ComboboxDescriptor(
            "measure_dropdown")  # type: basic_widgets.Combobox

        slow_time_units = widget_descriptors.LabelDescriptor(
            "slow_time_units", default_text="Slow-Time Units: ")  # type: basic_widgets.Label
        slow_time_dropdown = widget_descriptors.ComboboxDescriptor(
            "slow_time_dropdown")  # type: basic_widgets.Combobox

        target_azimuth_label = widget_descriptors.LabelDescriptor(
            "target_azimuth_label", default_text="Target Azimuth")  # type: basic_widgets.Label
        target_azimuth = widget_descriptors.EntryDescriptor(
            "target_azimuth", default_text="0")  # type: basic_widgets.Entry

        use_cal_constant = widget_descriptors.CheckButtonDescriptor(
            "use_cal_constant", default_text="Use cal constant")  # type: basic_widgets.Combobox
        db = widget_descriptors.EntryDescriptor(
            "db", default_text="0")  # type: basic_widgets.Entry
        db_label = widget_descriptors.LabelDescriptor(
            "db_label", default_text="db")  # type: basic_widgets.Label

        plot_in_db = widget_descriptors.CheckButtonDescriptor(
            "plot_in_db", default_text="Plot in dB")  # type: basic_widgets.CheckButton
        exclude_zeropad = widget_descriptors.CheckButtonDescriptor(
            "exclude_zeropad", default_text="Exclude zeropad")  # type: basic_widgets.CheckButton

        class MeasureOptions:
            rcs = "RCS"
            sigma_0 = "Sigma-0"
            beta_0 = "Beta-0"
            gamma_0 = "Gamma-0"
            avg_pixel_power = "avg. Pixel Power"

        class SlowTimeUnits:
            azimuth_angle = "Azimuth Angle"
            aperture_relative = "Aperture Relative"
            collect_time = "Collect Time"
            polar_angle = "Polar Angle"
            target_relative = "Target Relative"

        def __init__(self, parent):
            WidgetPanel.__init__(self, parent)
            self.parent = parent
            self.init_w_basic_widget_list(5, [2, 2, 2, 3, 2])

            self.measure_dropdown.pack(expand=tkinter.YES, fill=tkinter.X)
            self.slow_time_dropdown.pack(expand=tkinter.YES, fill=tkinter.X)
            self.target_azimuth.pack(expand=tkinter.YES, fill=tkinter.X)
            self.db.pack(expand=tkinter.YES, fill=tkinter.X)

            self.measure_dropdown.update_combobox_values([self.MeasureOptions.rcs,
                                                          self.MeasureOptions.sigma_0,
                                                          self.MeasureOptions.beta_0,
                                                          self.MeasureOptions.gamma_0,
                                                          self.MeasureOptions.avg_pixel_power])

    class PlotButtons(WidgetPanel):
        _widget_list = ("plot", "save_kml", "image_profile", "save_as_text")

        plot = widget_descriptors.ButtonDescriptor("plot", default_text="Plot")  # type: basic_widgets.Button
        save_kml = widget_descriptors.ButtonDescriptor("save_kml", default_text="Save KML")  # type: basic_widgets.Button
        image_profile = widget_descriptors.ButtonDescriptor("image_profile", default_text="Image Profile")  # type: basic_widgets.Button
        save_as_text = widget_descriptors.ButtonDescriptor("save_as_text", default_text="Save As Text")  # type: basic_widgets.Button

        def __init__(self, parent):
            WidgetPanel.__init__(self, parent)
            self.parent = parent
            self.init_w_box_layout(2, 10, 10)

    _widget_list = ("roi_controls", "data_generation_options", "plot_buttons")

    roi_controls = widget_descriptors.PanelDescriptor("roi_controls", RoiControls)  # type: ControlsPanel.RoiControls
    data_generation_options = widget_descriptors.PanelDescriptor("data_generation_options", DataGenerationOptions)  # type: DataGenerationOptions
    plot_buttons = widget_descriptors.PanelDescriptor("plot_buttons", PlotButtons)  # type: PlotButtons

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()


class RcsTable(WidgetPanel):
    _widget_list = ("table", )

    table = widget_descriptors.TreeviewDescriptor("table")  # type: basic_widgets.Treeview

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()

        self.table.config(columns=("shape", "color", "use", "rel_sigma", "pred_noise"))
        self.table.heading("shape", text="Shape")
        self.table.heading("color", text="Color")
        self.table.heading("use", text="Use")
        self.table.heading("rel_sigma", text="Relative Sigma-0 (dB)")
        self.table.heading("pred_noise", text="Pred. Noise")
        self._current_index = 0

    # def insert(self, values):
    #     self.table.insert(self._current_index)


class RcsTool(WidgetPanel):
    __slots__ = (
        '_sicd_reader', '_color_cycler')
    _widget_list = ("controls", "image_panel", "treeview")

    controls = widget_descriptors.PanelDescriptor("controls", ControlsPanel)  # type: ControlsPanel
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")  # type:  ImagePanel
    rcs_table = widget_descriptors.PanelDescriptor("treeview", RcsTable, default_text="RCS Table")  # type: RcsTable

    def __init__(self, primary):

        # define variables
        self.sicd_reader = None
        self._color_cycler = ColorCycler(n_colors=10)

        self.primary = primary
        primary_frame = tkinter.Frame(primary)

        WidgetPanel.__init__(self, primary_frame)
        self.init_w_basic_widget_list(2, [2, 1])

        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        menubar = Menu()

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.select_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        menubar.add_cascade(label="File", menu=filemenu)

        primary.config(menu=menubar)

        # callbacks
        self.controls.roi_controls.draw.config(command=self.set_tool)
        self.controls.roi_controls.select_closest.config(command=self.select_closest)
        self.controls.roi_controls.edit.config(command=self.edit_shape)

        self.image_panel.canvas.on_left_mouse_release(self.handle_canvas_left_mouse_release)

    def handle_canvas_left_mouse_release(self, event):
        self.image_panel.canvas.callback_handle_left_mouse_release(event)
        self.rcs_table.table.insert(("1", "2", "3"))

    @property
    def color_cycler(self):
        return self._color_cycler

    def set_color_cycler(self, n_colors, hex_color_palette):
        self._color_cycler = ColorCycler(n_colors, hex_color_palette)

    def set_tool(self):
        self.image_panel.canvas.variables.foreground_color = self.color_cycler.next_color
        if self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.rectangle:
            self.image_panel.canvas.set_current_tool_to_draw_rect()
        elif self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.polygon:
            self.image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()
        else:
            self.image_panel.canvas.set_current_tool_to_draw_ellipse()

    def select_closest(self):
        self.image_panel.canvas.set_current_tool_to_select_closest_shape()

    def edit_shape(self):
        self.image_panel.canvas.set_current_tool_to_edit_shape()

    def select_file(self):
        fname_filters = [("NITF", ".nitf .NITF .ntf .NTF"), ('All files', '*')]
        fname = askopenfilename(initialdir=os.path.expanduser("~"), filetypes=fname_filters)
        self.sicd_reader = ComplexImageReader(fname)
        self.image_panel.set_image_reader(self.sicd_reader)
        self.image_panel.update_everything()

    def exit(self):
        self.quit()


if __name__ == '__main__':
    root = tkinter.Tk()
    app = RcsTool(root)
    root.geometry("1200x1000")
    app.image_panel.canvas.set_canvas_size(500, 500)
    root.after(400, app.image_panel.update_everything)
    root.mainloop()

