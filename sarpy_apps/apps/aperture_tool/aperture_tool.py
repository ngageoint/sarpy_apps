import os
import time
import numpy
from scipy.fftpack import fft2, ifft2, fftshift

import tkinter
from tkinter import filedialog
from tkinter import Menu
from tk_builder.panel_builder import WidgetPanel
from tk_builder.utils.image_utils import frame_sequence_utils
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.image_readers.numpy_image_reader import NumpyImageReader

from tk_builder.widgets import widget_descriptors

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


class ApertureTool(WidgetPanel):
    _widget_list = ("frequency_vs_degree_panel", "filtered_panel")

    frequency_vs_degree_panel = widget_descriptors.ImagePanelDescriptor(
        "frequency_vs_degree_panel")  # type: ImagePanel
    filtered_panel = widget_descriptors.ImagePanelDescriptor("filtered_panel")  # type: ImagePanel

    image_info_panel = widget_descriptors.PanelDescriptor("image_info_panel", ImageInfoPanel)  # type: ImageInfoPanel
    metaicon = widget_descriptors.PanelDescriptor("metaicon", MetaIcon)  # type: MetaIcon
    phase_history = widget_descriptors.PanelDescriptor("phase_history", PhaseHistoryPanel)  # type: PhaseHistoryPanel
    metaviewer = widget_descriptors.PanelDescriptor("metaviewer", Metaviewer)  # type: Metaviewer
    animation_panel = widget_descriptors.PanelDescriptor("animation_panel", AnimationPanel)   # type: AnimationPanel

    def __init__(self, primary):
        self.app_variables = AppVariables()
        self.primary = primary

        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_horizontal_layout()

        self.frequency_vs_degree_panel.canvas.on_left_mouse_motion(self.callback_frequency_vs_degree_left_mouse_motion)

        self.image_info_popup_panel = tkinter.Toplevel(self.primary)
        self.image_info_panel = ImageInfoPanel(self.image_info_popup_panel)
        self.image_info_popup_panel.withdraw()

        self.image_info_panel.file_selector.select_file.on_left_mouse_click(self.callback_select_file)

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
        self.animation_panel.animation_settings.play.on_left_mouse_click(self.callback_play_animation_fast_slow)
        self.animation_panel.animation_settings.step_forward.on_left_mouse_click(self.callback_step_forward)
        self.animation_panel.animation_settings.step_back.on_left_mouse_click(self.callback_step_back)
        self.animation_panel.animation_settings.stop.on_left_mouse_click(self.callback_stop_animation)

        menubar = Menu()

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.select_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        # create more pulldown menus
        popups_menu = Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Main Controls", command=self.main_controls_popup)
        popups_menu.add_command(label="Phase History", command=self.ph_popup)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        popups_menu.add_command(label="Animation", command=self.animation_fast_slow_popup)

        save_menu = Menu(menubar, tearoff=0)
        save_menu.add_command(label="Save Meticon", command=self.save_metaicon)

        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Popups", menu=popups_menu)
        menubar.add_cascade(label="Save", menu=save_menu)

        primary.config(menu=menubar)

        self.frequency_vs_degree_panel.toolbar.zoom_in.pack_forget()
        self.frequency_vs_degree_panel.toolbar.zoom_out.pack_forget()
        self.frequency_vs_degree_panel.toolbar.pan.pack_forget()
        self.frequency_vs_degree_panel.toolbar.margins_checkbox.pack_forget()
        self.frequency_vs_degree_panel.toolbar.axes_labels_checkbox.pack_forget()

        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.frequency_vs_degree_panel.resizeable = True
        self.filtered_panel.resizeable = True

    def save_metaicon(self):
        save_fname = asksaveasfilename(initialdir=os.path.expanduser("~"), filetypes=[("*.png", ".PNG")])
        self.metaicon.canvas.save_full_canvas_as_png(save_fname)

    def exit(self):
        self.quit()

    def update_animation_params(self):
        self.app_variables.animation_n_frames = int(self.animation_panel.animation_settings.number_of_frames.get())
        self.app_variables.animation_aperture_faction = \
            float(self.animation_panel.fast_slow_settings.aperture_fraction.get())
        self.app_variables.animation_frame_rate = float(self.animation_panel.animation_settings.frame_rate.get())
        self.app_variables.animation_cycle_continuously = \
            self.animation_panel.animation_settings.cycle_continuously.is_selected()
        self.app_variables.animation_min_aperture_percent = \
            float(self.animation_panel.resolution_settings.min_res.get()) * 0.01
        self.app_variables.animation_max_aperture_percent = \
            float(self.animation_panel.resolution_settings.max_res.get()) * 0.01

    # noinspection PyUnusedLocal
    def callback_step_forward(self, event):
        self.step_animation("forward")

    # noinspection PyUnusedLocal
    def callback_step_back(self, event):
        self.step_animation("back")

    def step_animation(self,
                       direction_forward_or_back,  # type: str
                       ):
        self.update_animation_params()
        fft_canvas_bounds = \
            self.frequency_vs_degree_panel.canvas.image_coords_to_canvas_coords(self.get_fft_image_bounds())
        full_canvas_x_aperture = fft_canvas_bounds[2] - fft_canvas_bounds[0]
        full_canvas_y_aperture = fft_canvas_bounds[3] - fft_canvas_bounds[1]

        mode = self.animation_panel.mode_panel.mode_selections.selection()

        if direction_forward_or_back == "forward":
            if self.app_variables.animation_current_position < self.app_variables.animation_n_frames - 1:
                self.app_variables.animation_current_position += 1
        elif direction_forward_or_back == "back":
            if self.app_variables.animation_current_position > 0:
                self.app_variables.animation_current_position -= 1
        if self.animation_panel.mode_panel.mode_selections.selection() == self.animation_panel.mode_panel.mode_selections.slow_time:
            aperture_distance = full_canvas_x_aperture * self.app_variables.animation_aperture_faction

            start_locs = numpy.linspace(fft_canvas_bounds[0],
                                        fft_canvas_bounds[2] - aperture_distance,
                                        self.app_variables.animation_n_frames)

            x_start = start_locs[self.app_variables.animation_current_position]
            new_rect = (x_start,
                        fft_canvas_bounds[1],
                        x_start + aperture_distance,
                        fft_canvas_bounds[3])
        elif mode == self.animation_panel.mode_panel.mode_selections.fast_time:
            aperture_distance = full_canvas_y_aperture * self.app_variables.animation_aperture_faction

            start_locs = numpy.linspace(fft_canvas_bounds[1],
                                        fft_canvas_bounds[3] - aperture_distance,
                                        self.app_variables.animation_n_frames)
            start_locs = numpy.flip(start_locs)
            y_start = start_locs[self.app_variables.animation_current_position]
            new_rect = (fft_canvas_bounds[0],
                        y_start,
                        fft_canvas_bounds[2],
                        y_start + aperture_distance)
        elif mode == self.animation_panel.mode_panel.mode_selections.aperture_percent:
            xul = fft_canvas_bounds[0]
            xlr = fft_canvas_bounds[2]
            yul = fft_canvas_bounds[1]
            ylr = fft_canvas_bounds[3]

            canvas_xul_start = \
                (xul + xlr) / 2 - full_canvas_x_aperture * self.app_variables.animation_max_aperture_percent / 2
            canvas_xlr_start = \
                (xul + xlr) / 2 + full_canvas_x_aperture * self.app_variables.animation_max_aperture_percent / 2
            canvas_yul_start = \
                (yul + ylr) / 2 - full_canvas_y_aperture * self.app_variables.animation_max_aperture_percent / 2
            canvas_ylr_start = \
                (yul + ylr) / 2 + full_canvas_y_aperture * self.app_variables.animation_max_aperture_percent / 2

            canvas_xul_stop = (canvas_xul_start + canvas_xlr_start) / 2 - full_canvas_x_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_xlr_stop = (canvas_xul_start + canvas_xlr_start) / 2 + full_canvas_x_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_yul_stop = (canvas_yul_start + canvas_ylr_start) / 2 - full_canvas_y_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_ylr_stop = (canvas_yul_start + canvas_ylr_start) / 2 + full_canvas_y_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2

            x_uls = numpy.linspace(canvas_xul_start, canvas_xul_stop, self.app_variables.animation_n_frames)
            x_lrs = numpy.linspace(canvas_xlr_start, canvas_xlr_stop, self.app_variables.animation_n_frames)
            y_uls = numpy.linspace(canvas_yul_start, canvas_yul_stop, self.app_variables.animation_n_frames)
            y_lrs = numpy.linspace(canvas_ylr_start, canvas_ylr_stop, self.app_variables.animation_n_frames)

            frame_num = self.app_variables.animation_current_position

            new_rect = (x_uls[frame_num], y_uls[frame_num], x_lrs[frame_num], y_lrs[frame_num])

        elif mode == self.animation_panel.mode_panel.mode_selections.full_range_bandwidth:
            xul = fft_canvas_bounds[0]
            xlr = fft_canvas_bounds[2]
            yul = fft_canvas_bounds[1]
            ylr = fft_canvas_bounds[3]

            canvas_xul_start = (xul + xlr) / 2 - full_canvas_x_aperture * \
                               self.app_variables.animation_max_aperture_percent / 2
            canvas_xlr_start = (xul + xlr) / 2 + full_canvas_x_aperture * \
                               self.app_variables.animation_max_aperture_percent / 2
            canvas_yul_start = yul
            canvas_ylr_start = ylr

            canvas_xul_stop = (canvas_xul_start + canvas_xlr_start) / 2 - full_canvas_x_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_xlr_stop = (canvas_xul_start + canvas_xlr_start) / 2 + full_canvas_x_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_yul_stop = yul
            canvas_ylr_stop = ylr

            x_uls = numpy.linspace(canvas_xul_start, canvas_xul_stop, self.app_variables.animation_n_frames)
            x_lrs = numpy.linspace(canvas_xlr_start, canvas_xlr_stop, self.app_variables.animation_n_frames)
            y_uls = numpy.linspace(canvas_yul_start, canvas_yul_stop, self.app_variables.animation_n_frames)
            y_lrs = numpy.linspace(canvas_ylr_start, canvas_ylr_stop, self.app_variables.animation_n_frames)

            frame_num = self.app_variables.animation_current_position

            new_rect = (x_uls[frame_num], y_uls[frame_num], x_lrs[frame_num], y_lrs[frame_num])

        elif mode == self.animation_panel.mode_panel.mode_selections.full_az_bandwidth:
            xul = fft_canvas_bounds[0]
            xlr = fft_canvas_bounds[2]
            yul = fft_canvas_bounds[1]
            ylr = fft_canvas_bounds[3]

            canvas_xul_start = xul
            canvas_xlr_start = xlr
            canvas_yul_start = \
                (yul + ylr) / 2 - full_canvas_y_aperture * self.app_variables.animation_max_aperture_percent / 2
            canvas_ylr_start = \
                (yul + ylr) / 2 + full_canvas_y_aperture * self.app_variables.animation_max_aperture_percent / 2

            canvas_xul_stop = xul
            canvas_xlr_stop = xlr
            canvas_yul_stop = (canvas_yul_start + canvas_ylr_start) / 2 - full_canvas_y_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2
            canvas_ylr_stop = (canvas_yul_start + canvas_ylr_start) / 2 + full_canvas_y_aperture * \
                              self.app_variables.animation_min_aperture_percent / 2

            x_uls = numpy.linspace(canvas_xul_start, canvas_xul_stop, self.app_variables.animation_n_frames)
            x_lrs = numpy.linspace(canvas_xlr_start, canvas_xlr_stop, self.app_variables.animation_n_frames)
            y_uls = numpy.linspace(canvas_yul_start, canvas_yul_stop, self.app_variables.animation_n_frames)
            y_lrs = numpy.linspace(canvas_ylr_start, canvas_ylr_stop, self.app_variables.animation_n_frames)

            frame_num = self.app_variables.animation_current_position

            new_rect = (x_uls[frame_num], y_uls[frame_num], x_lrs[frame_num], y_lrs[frame_num])

        self.frequency_vs_degree_panel.canvas.modify_existing_shape_using_canvas_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id, new_rect)
        self.update_filtered_image()
        self.update_phase_history_selection()

    # noinspection PyUnusedLocal
    def callback_stop_animation(self, event):
        self.app_variables.animation_stop_pressed = True
        self.animation_panel.animation_settings.unpress_all_buttons()

    # noinspection PyUnusedLocal
    def callback_play_animation_fast_slow(self, event):
        self.update_animation_params()

        direction_forward_or_back = "forward"
        if self.animation_panel.mode_panel.reverse.is_selected():
            direction_forward_or_back = "back"
        time_between_frames = 1 / self.app_variables.animation_frame_rate
        self.animation_panel.animation_settings.stop.config(state="normal")

        def play_animation():
            self.animation_panel.animation_settings.disable_all_widgets()
            self.animation_panel.animation_settings.stop.config(state="normal")
            if direction_forward_or_back == "forward":
                self.app_variables.animation_current_position = -1
            else:
                self.app_variables.animation_current_position = self.app_variables.animation_n_frames
            for i in range(self.app_variables.animation_n_frames):
                self.update_animation_params()
                if self.app_variables.animation_stop_pressed:
                    self.animation_panel.animation_settings.enable_all_widgets()
                    break
                tic = time.time()
                self.step_animation(direction_forward_or_back)
                self.frequency_vs_degree_panel.update()
                toc = time.time()
                if (toc - tic) < time_between_frames:
                    time.sleep(time_between_frames - (toc - tic))

        self.app_variables.animation_stop_pressed = False
        if self.animation_panel.animation_settings.cycle_continuously.is_selected():
            while not self.app_variables.animation_stop_pressed:
                play_animation()
        else:
            play_animation()
        self.app_variables.animation_stop_pressed = False
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

    def callback_frequency_vs_degree_left_mouse_motion(self, event):
        self.frequency_vs_degree_panel.canvas.callback_handle_left_mouse_motion(event)
        self.update_filtered_image()
        self.update_phase_history_selection()

    def select_file(self):
        self.callback_select_file(None)

    def callback_select_file(self, event):
        sicd_fname = self.image_info_panel.file_selector.event_select_file(event)
        self.app_variables.sicd_fname = sicd_fname
        self.app_variables.sicd_reader_object = ComplexImageReader(self.app_variables.sicd_fname)

        # TODO: handle index, and generalize what sicd_reader_object could be...
        self.metaicon.create_from_reader(self.app_variables.sicd_reader_object.base_reader, index=0)

        popup = tkinter.Toplevel(self.primary)
        selected_region_popup = SelectedRegionPanel(popup, self.app_variables)
        selected_region_popup.image_panel.set_image_reader(self.app_variables.sicd_reader_object)
        popup.geometry("1000x1000")
        popup.after(200, selected_region_popup.image_panel.update_everything)

        self.primary.wait_window(popup)

        selected_region_complex_data = self.app_variables.selected_region_complex_data

        fft_complex_data = \
            self.get_fft_complex_data(self.app_variables.sicd_reader_object.base_reader, selected_region_complex_data)
        self.app_variables.fft_complex_data = fft_complex_data

        self.app_variables.fft_display_data = remap.density(fft_complex_data)
        fft_reader = NumpyImageReader(self.app_variables.fft_display_data)
        self.frequency_vs_degree_panel.set_image_reader(fft_reader)

        self.frequency_vs_degree_panel.canvas.set_current_tool_to_edit_shape()
        self.frequency_vs_degree_panel.canvas.variables.current_shape_id = \
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id
        self.frequency_vs_degree_panel.canvas.modify_existing_shape_using_image_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id, self.get_fft_image_bounds())
        vector_object = self.frequency_vs_degree_panel.canvas.get_vector_object(
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id)
        vector_object.image_drag_limits = self.get_fft_image_bounds()
        self.frequency_vs_degree_panel.canvas.show_shape(
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id)

        filtered_numpy_reader = NumpyImageReader(self.get_filtered_image())
        self.filtered_panel.set_image_reader(filtered_numpy_reader)

        self.image_info_panel.chip_size_panel.nx.set_text(numpy.shape(selected_region_complex_data)[1])
        self.image_info_panel.chip_size_panel.ny.set_text(numpy.shape(selected_region_complex_data)[0])

        self.update_phase_history_selection()

        self.metaviewer.create_w_sicd(self.app_variables.sicd_reader_object.base_reader.sicd_meta)

        self.frequency_vs_degree_panel.axes_canvas.set_canvas_size(800, 600)

        self.frequency_vs_degree_panel.axes_canvas.x_label = "Polar Angle (degrees)"
        self.frequency_vs_degree_panel.axes_canvas.y_label = "Frequency (GHz)"

        polar_angle_min, polar_angle_max = self.get_polar_angle_bounds()

        self.frequency_vs_degree_panel.axes_canvas.image_x_min_val = polar_angle_min
        self.frequency_vs_degree_panel.axes_canvas.image_x_max_val = polar_angle_max

        min_frequency, max_frequency = self.get_frequency_bounds()
        self.frequency_vs_degree_panel.axes_canvas.image_y_min_val = max_frequency
        self.frequency_vs_degree_panel.axes_canvas.image_y_max_val = min_frequency

        self.frequency_vs_degree_panel.update_everything()

    def get_polar_angle_bounds(self):
        x1 = self.get_fft_image_bounds()[1]
        x2 = self.get_fft_image_bounds()[3]

        polar_angle_min = self.app_variables.sicd_reader_object.base_reader.sicd_meta.PFA.Kaz1
        polar_angle_max = self.app_variables.sicd_reader_object.base_reader.sicd_meta.PFA.Kaz2

        m = (polar_angle_max - polar_angle_min) / (x2 - x1)

        min_polar_angle = polar_angle_min - m * x1
        max_polar_angle = m * self.frequency_vs_degree_panel.canvas.variables.canvas_image_object.image_reader.full_image_nx + min_polar_angle

        return min_polar_angle, max_polar_angle

    def get_frequency_bounds(self):
        y1 = self.get_fft_image_bounds()[0]
        y2 = self.get_fft_image_bounds()[2]

        frequency_min = self.app_variables.sicd_reader_object.base_reader.sicd_meta.RadarCollection.TxFrequency.Min
        frequency_max = self.app_variables.sicd_reader_object.base_reader.sicd_meta.RadarCollection.TxFrequency.Max

        m = (frequency_max - frequency_min) / (y2 - y1)

        min_frequency = frequency_min - m * y1
        max_frequency = m * self.frequency_vs_degree_panel.canvas.variables.canvas_image_object.image_reader.full_image_ny + min_frequency

        min_frequency = min_frequency / 1e9
        max_frequency = max_frequency / 1e9

        return min_frequency, max_frequency

    def get_fft_image_bounds(self,
                             ):  # type: (...) -> (int, int, int, int)
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

    def callback_save_fft_panel_as_png(self, event):
        filename = filedialog.asksaveasfilename(initialdir=os.path.expanduser("~"), title="Select file",
                                                filetypes=(("png file", "*.png"), ("all files", "*.*")))
        self.frequency_vs_degree_panel.canvas.save_full_canvas_as_png(filename)

    def callback_get_adjusted_image(self, event):
        filtered_image = self.get_filtered_image()
        self.frequency_vs_degree_panel.set_image_reader(NumpyImageReader(filtered_image))

    def update_filtered_image(self):
        self.filtered_panel.set_image_reader(NumpyImageReader(self.get_filtered_image()))

    def get_filtered_image(self):
        select_rect_id = self.frequency_vs_degree_panel.canvas.variables.select_rect_id
        full_image_rect = self.frequency_vs_degree_panel.canvas.get_shape_image_coords(select_rect_id)

        y1 = int(full_image_rect[0])
        x1 = int(full_image_rect[1])
        y2 = int(full_image_rect[2])
        x2 = int(full_image_rect[3])

        y_ul = min(y1, y2)
        y_lr = max(y1, y2)
        x_ul = min(x1, x2)
        x_lr = max(x1, x2)

        ft_cdata = self.app_variables.fft_complex_data
        filtered_cdata = numpy.zeros(ft_cdata.shape, ft_cdata.dtype)
        filtered_cdata[y_ul:y_lr, x_ul:x_lr] = ft_cdata[y_ul:y_lr, x_ul:x_lr]
        filtered_cdata = fftshift(filtered_cdata)

        inverse_flag = False
        ro = self.app_variables.sicd_reader_object.base_reader
        if ro.sicd_meta.Grid.Col.Sgn > 0 and ro.sicd_meta.Grid.Row.Sgn > 0:
            pass
        else:
            inverse_flag = True

        if inverse_flag:
            cdata_clip = fft2(filtered_cdata)
        else:
            cdata_clip = ifft2(filtered_cdata)

        filtered_image = remap.density(cdata_clip)
        return filtered_image

    @staticmethod
    def get_fft_complex_data(ro,  # type: BaseReader
                             cdata,  # type: numpy.ndarray
                             ):
        # TODO: change this to a tuple sequence to get rid of FutureWarning
        if ro.sicd_meta.Grid.Col.Sgn > 0 and ro.sicd_meta.Grid.Row.Sgn > 0:
            # use fft2 to go from image to spatial freq
            ft_cdata = fft2(cdata)
        else:
            # flip using ifft2
            ft_cdata = ifft2(tuple(cdata))

        ft_cdata = fftshift(ft_cdata)
        return ft_cdata

    # noinspection PyUnusedLocal
    # TODO: update variables, some don't exist in the current form.
    def callback_save_animation(self, event):
        filename = filedialog.asksaveasfilename(initialdir=os.path.expanduser("~"), title="Select file",
                                                filetypes=(("animated gif", "*.gif"), ("all files", "*.*")))
        select_box_id = self.filtered_panel.canvas.variables.current_shape_id
        start_fft_select_box = self.filtered_panel.canvas.get_shape_canvas_coords(select_box_id)
        n_steps = int(self.animation_panel.animation_settings.number_of_frames.get())
        n_pixel_translate = int(self.filtered_panel.fft_button_panel.n_pixels_horizontal.get())
        step_factor = numpy.linspace(0, n_pixel_translate, n_steps)
        fps = float(self.filtered_panel.fft_button_panel.animation_fps.get())

        frame_sequence = []
        for step in step_factor:
            x1 = start_fft_select_box[0] + step
            y1 = start_fft_select_box[1]
            x2 = start_fft_select_box[2] + step
            y2 = start_fft_select_box[3]
            self.filtered_panel.image_canvas.modify_existing_shape_using_canvas_coords(
                select_box_id, (x1, y1, x2, y2), update_pixel_coords=True)
            self.filtered_panel.image_canvas.update()
            filtered_image = self.get_filtered_image()
            frame_sequence.append(filtered_image)
        frame_sequence_utils.save_numpy_frame_sequence_to_animated_gif(frame_sequence, filename, fps)
        self.filtered_panel.image_canvas.modify_existing_shape_using_canvas_coords(
            select_box_id, start_fft_select_box, update_pixel_coords=True)
        self.filtered_panel.image_canvas.update()

    def update_phase_history_selection(self):
        image_bounds = self.get_fft_image_bounds()
        current_bounds = self.frequency_vs_degree_panel.canvas.shape_image_coords_to_canvas_coords(
            self.frequency_vs_degree_panel.canvas.variables.select_rect_id)
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
    root.geometry("1200x1000")
    app.frequency_vs_degree_panel.canvas.set_canvas_size(500, 500)
    app.filtered_panel.canvas.set_canvas_size(500, 500)
    root.after(400, app.filtered_panel.update_everything)
    root.after(400, app.frequency_vs_degree_panel.update_everything)
    root.mainloop()

