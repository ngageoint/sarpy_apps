import os

import numpy
import tkinter
from tkinter.filedialog import askopenfilename

from tk_builder.panel_builder import WidgetPanel
from tk_builder.panels.image_panel import ImagePanel

from tk_builder.widgets import widget_descriptors
from tk_builder.widgets import basic_widgets
from tk_builder.panel_builder import RadioButtonPanel
from tk_builder.widgets.image_canvas import ToolConstants

from sarpy_apps.supporting_classes.image_reader import ComplexImageReader
from sarpy_apps.supporting_classes import file_filters

from sarpy_apps.apps.rcs_tool.popups.rcs_plot import RcsPlot

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


###########
# associated GUI elements

class RoiRadiobuttons(RadioButtonPanel):
    _widget_list = ("rectangle", "polygon",)
    rectangle = widget_descriptors.RadioButtonDescriptor("rectangle")  # type: basic_widgets.RadioButton
    polygon = widget_descriptors.RadioButtonDescriptor("polygon")  # type: basic_widgets.RadioButton
    ellipse = widget_descriptors.RadioButtonDescriptor("ellipse")  # type: basic_widgets.RadioButton

    def __init__(self, parent):
        RadioButtonPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_vertical_layout()


class RoiControls(WidgetPanel):
    _widget_list = ("roi_radiobuttons", "draw", "edit", "delete")
    roi_radiobuttons = widget_descriptors.PanelDescriptor(
        "roi_radiobuttons", RoiRadiobuttons)  # type: RoiRadiobuttons
    draw = widget_descriptors.ButtonDescriptor("draw")  # type: basic_widgets.Button
    edit = widget_descriptors.ButtonDescriptor("edit")  # type: basic_widgets.Button
    delete = widget_descriptors.ButtonDescriptor("delete")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_vertical_layout()


class DataGenerationOptions(WidgetPanel):
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

    _widget_list = (
        "measure_label", "measure_dropdown", "slow_time_units",
        "slow_time_dropdown", "target_azimuth_label", "target_azimuth",
        "use_cal_constant", "db", "db_label", "plot_in_db", "exclude_zeropad")

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

        self.slow_time_dropdown.update_combobox_values([self.SlowTimeUnits.azimuth_angle,
                                                        self.SlowTimeUnits.aperture_relative,
                                                        self.SlowTimeUnits.collect_time,
                                                        self.SlowTimeUnits.polar_angle,
                                                        self.SlowTimeUnits.target_relative])


class PlotButtons(WidgetPanel):
    _widget_list = (
        "plot", "save_kml", "image_profile", "save_as_text")
    plot = widget_descriptors.ButtonDescriptor("plot", default_text="Plot")  # type: basic_widgets.Button
    save_kml = widget_descriptors.ButtonDescriptor("save_kml", default_text="Save KML")  # type: basic_widgets.Button
    image_profile = widget_descriptors.ButtonDescriptor("image_profile", default_text="Image Profile")  # type: basic_widgets.Button
    save_as_text = widget_descriptors.ButtonDescriptor("save_as_text", default_text="Save As Text")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.parent = parent
        self.init_w_box_layout(2, 10, 1)


class ControlsPanel(WidgetPanel):
    _widget_list = ("roi_controls", "data_generation_options", "plot_buttons")

    roi_controls = widget_descriptors.PanelDescriptor("roi_controls", RoiControls)  # type: RoiControls
    data_generation_options = widget_descriptors.PanelDescriptor("data_generation_options", DataGenerationOptions)  # type: DataGenerationOptions
    plot_buttons = widget_descriptors.PanelDescriptor("plot_buttons", PlotButtons)  # type: PlotButtons

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()


class Buttons(WidgetPanel):
    _widget_list = ("edit", )
    edit = widget_descriptors.ButtonDescriptor("edit")  # type: basic_widgets.Button

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_horizontal_layout()


class RcsTable(WidgetPanel):

    _widget_list = ("table", "buttons", )
    table = widget_descriptors.TreeviewDescriptor("table")  # type: basic_widgets.Treeview
    buttons = widget_descriptors.PanelDescriptor("buttons", Buttons)  # type: Buttons

    def __init__(self, parent):
        WidgetPanel.__init__(self, parent)
        self.init_w_vertical_layout()

        self.table.config(columns=("name", "shape", "color", "use", "rel_sigma", "pred_noise"))
        self.table.heading("#0", text="Shape ID")
        self.table.heading("name", text="Name")
        self.table.heading("shape", text="Shape")
        self.table.heading("color", text="Color")
        self.table.heading("use", text="Use")
        self.table.heading("rel_sigma", text="Relative Sigma-0 (dB)")
        self.table.heading("pred_noise", text="Pred. Noise")
        self._shape_name_to_shape_id_dict = {}

    @property
    def n_entries(self):
        return len(self.table.get_children())

    def insert_row(self, shape_id, vals):
        self._shape_name_to_shape_id_dict[str(shape_id)] = str(shape_id)
        vals = tuple([str(shape_id)] + list(vals))
        self.table.insert('',
                          'end',
                          iid=shape_id,
                          text=str(shape_id),
                          values=vals)

    def delete(self, shape_id):
        self.table.delete(str(shape_id))


class RcsTool(WidgetPanel):
    _widget_list = ("controls",  "image_panel", "rcs_table",)

    controls = widget_descriptors.PanelDescriptor("controls", ControlsPanel)  # type: ControlsPanel
    image_panel = widget_descriptors.ImagePanelDescriptor("image_panel")  # type:  ImagePanel
    rcs_table = widget_descriptors.PanelDescriptor("rcs_table", RcsTable, default_text="RCS Table")  # type: RcsTable

    def __init__(self, primary):
        # define variables
        self._browse_directory = os.path.expanduser('~')
        self.primary = primary
        primary_frame = tkinter.Frame(primary)

        WidgetPanel.__init__(self, primary_frame)
        self.init_w_basic_widget_list(2, [2, 1])
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.controls.pack(fill=tkinter.X, expand=False)
        self.rcs_table.pack(fill=tkinter.X, expand=True)

        menubar = tkinter.Menu()
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.select_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)

        menubar.add_cascade(label="File", menu=filemenu)

        primary.config(menu=menubar)

        # callbacks
        self.controls.roi_controls.draw.config(command=self.set_tool)
        self.controls.roi_controls.edit.config(command=self.edit_shape)
        self.controls.roi_controls.delete.config(command=self.delete_shape)

        self.controls.plot_buttons.plot.config(command=self.plot_popups)

        self.image_panel.canvas.on_left_mouse_release(self.handle_canvas_left_mouse_release)
        self.image_panel.pack(expand=True, fill=tkinter.BOTH)
        self.rcs_table.buttons.edit.config(command=self.edit_rcs_table)

        self.rcs_table.table.on_left_mouse_click(self.handle_table_selection)
        self.rcs_table.table.on_selection(self.handle_table_selection)
        self.image_panel.update_everything()

    def handle_table_left_mouse_click(self, event):
        item = self.rcs_table.table.identify('item', event.x, event.y)
        if item != "":
            item = int(item)
            self.image_panel.canvas.variables.current_shape_id = item
            self.image_panel.canvas.set_current_tool_to_edit_shape()

    def handle_table_selection(self, event):
        item = self.rcs_table.table.selection()
        if item == ():
            item = self.rcs_table.table.identify('item', event.x, event.y)
        if type("") == type(item):
            pass
        else:
            item = item[0]
        if item != "":
            item = int(item)
            self.image_panel.canvas.variables.current_shape_id = item
            self.image_panel.canvas.set_current_tool_to_edit_shape()

    def handle_canvas_left_mouse_release(self, event):
        self.image_panel.canvas.callback_handle_left_mouse_release(event)
        n_shapes_on_canvas = len(self.image_panel.canvas.get_non_tool_shape_ids())

        if self.image_panel.current_tool == ToolConstants.DRAW_RECT_BY_DRAGGING or \
           self.image_panel.current_tool == ToolConstants.DRAW_POLYGON_BY_CLICKING or \
           self.image_panel.current_tool == ToolConstants.DRAW_ELLIPSE_BY_DRAGGING:

            shape = "Rectangle"
            if self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.polygon:
                shape = "Polygon"
            if self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.ellipse:
                shape = "Ellipse"
            if self.rcs_table.n_entries == n_shapes_on_canvas - 1:
                table_vals = (shape, self.image_panel.canvas.variables.foreground_color, "yes", "0", "0")
                self.rcs_table.insert_row(self.image_panel.canvas.variables.current_shape_id, table_vals)
            else:
                pass

        if self.image_panel.canvas.variables.current_shape_id is not None:
            self.rcs_table.table.selection_set(self.image_panel.canvas.variables.current_shape_id)

    # commands for controls.plot_buttons
    def plot_popups(self):
        popup = tkinter.Toplevel(self.primary)
        plot_panel = RcsPlot(popup)
        popup.geometry("1000x1000")
        plot_panel.azimuth_plot.set_data(numpy.linspace(0, 100))
        plot_panel.azimuth_plot.title = "Slow Time Response: "
        plot_panel.azimuth_plot.y_label = "Relative RCS (dB)"
        plot_panel.azimuth_plot.x_label = "Azimuth Angle (deg)"

        plot_panel.range_plot.set_data(numpy.linspace(100, 50))
        plot_panel.range_plot.title = "Fast Time Response: "
        plot_panel.range_plot.y_label = "Relative RCS (dB)"
        plot_panel.range_plot.x_label = "Frequency (GHz)"

    def edit_rcs_table(self):
        current_item = self.rcs_table.table.focus()
        print(self.rcs_table.table.item(current_item))  # TODO: what is this for?

    def set_tool(self):
        if self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.rectangle:
            self.image_panel.canvas.set_current_tool_to_draw_rect()
        elif self.controls.roi_controls.roi_radiobuttons.selection() == self.controls.roi_controls.roi_radiobuttons.polygon:
            self.image_panel.canvas.set_current_tool_to_draw_polygon_by_clicking()
        else:
            self.image_panel.canvas.set_current_tool_to_draw_ellipse()

    def edit_shape(self):
        self.image_panel.canvas.set_current_tool_to_edit_shape(select_closest_first=True)

    def delete_shape(self):
        current_shape_id = self.image_panel.canvas.variables.current_shape_id
        if current_shape_id in self.image_panel.canvas.get_non_tool_shape_ids():
            self.image_panel.canvas.delete_shape(current_shape_id)
            self.rcs_table.delete(current_shape_id)

    def select_file(self):
        fname = askopenfilename(initialdir=self._browse_directory, filetypes=file_filters.common_use_filter)
        if fname is None or fname == '':
            return
        self._browse_directory = os.path.split(fname)[0]
        # TODO: what all file types to support? Create a more common use way of dealing with this.
        reader = ComplexImageReader(fname)

        self.image_panel.set_image_reader(reader)
        self.image_panel.update_everything()

    def exit(self):
        self.quit()


def main():
    """
    Run a RcsTool application.

    Returns
    -------
    None
    """

    root = tkinter.Tk()
    app = RcsTool(root)
    root.mainloop()


if __name__ == '__main__':
    main()
