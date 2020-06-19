from tkinter import font
import datetime
import numpy
from scipy.constants import constants

from tk_builder.panel_templates.image_canvas_panel.image_canvas_panel import ImageCanvasPanel
import tk_builder.utils.color_utils.color_converter as color_converter
from sarpy.geometry import latlon
from tk_builder.image_readers.numpy_image_reader import NumpyImageReader
from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer
from sarpy_apps.supporting_classes.metaicon.sicd_metaicon_helper import SicdMetaIconHelper


class MetaIcon(ImageCanvasPanel):
    __slots__ = ('fname', 'reader_object', "meta")  # TODO: this is incomplete. Omit?

    class AngleTypes:
        azimuth = "azimuth"
        graze = "graze"
        layover = "layover"
        shadow = "shadow"
        multipath = "multipath"

    class Colors:
        layover = color_converter.rgb_to_hex([1, 0.65, 0])
        shadow = color_converter.rgb_to_hex([0, 0.65, 1])
        multipath = color_converter.rgb_to_hex([1, 0, 0])
        north = color_converter.rgb_to_hex([0.58, 0.82, 0.31])
        flight_direction = color_converter.rgb_to_hex([1, 1, 0])

    class ArrowWidths:
        layover_width = 2
        shadow_width = 2
        multipath_width = 2
        north_width = 2

    def __init__(self, master):
        super(MetaIcon, self).__init__(master)
        self.parent = master
        self.fname = None                              # type: str
        self._metadata_container = MetaIconDataContainer()

        self._azimuth_decimals = 1
        self._graze_decimals = 1
        self._layover_decimals = 0
        self._shadow_decimals = 0
        self._multipath_decimals = 0

        self._margin_percent = 5
        self._font_family = 'Times New Roman'

        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    @property
    def font_family(self):
        """
        str: The font family name.
        """

        return self._font_family

    @property
    def font(self):
        """
        font.Font: The font object.
        """

        text_height = int((self.line_positions[1][1] - self.line_positions[0][1]) * 0.7)
        return font.Font(family=self._font_family, size=-text_height)

    @property
    def arrows_origin(self):
        """
        Tuple[float, float]: The arrow origin location.
        """

        return self.canvas.variables.canvas_width*0.75, self.canvas.variables.canvas_height*0.6

    @property
    def data_container(self):
        """
        MetaIconDataContainer: The data container object.
        """

        return self._metadata_container

    @data_container.setter
    def data_container(self, value):
        if not isinstance(value, MetaIconDataContainer):
            raise TypeError('Got unexpected type {}'.format(type(value)))
        self._metadata_container = value

    def close_window(self):
        """
        Close the meta-icon window.

        Returns
        -------
        None
        """

        self.parent.withdraw()

    def create_from_metaicon_data_container(self, data_container):
        """
        Reinitialize from a metaicon data container.

        Parameters
        ----------
        data_container : MetaIconDataContainer

        Returns
        -------
        None
        """

        self.data_container = data_container
        metaicon_background = numpy.zeros((self.canvas.variables.canvas_height, self.canvas.variables.canvas_width))
        numpy_reader = NumpyImageReader(metaicon_background)
        self.canvas.set_image_reader(numpy_reader)

        line_positions = self.line_positions

        self.canvas.create_text(line_positions[0], text=self.iid_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[1], text=self.geo_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[2], text=self.res_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[3], text=self.cdp_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[4], text=self.azimuth_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[5], text=self.graze_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[6], text=self.layover_line, fill=self.Colors.layover, anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[7], text=self.shadow_line, fill=self.Colors.shadow, anchor="nw", font=self.font)
        self.canvas.create_text(line_positions[8], text=self.multipath_line, fill=self.Colors.multipath, anchor="nw", font=self.font)

        # draw layover arrow
        self.draw_layover_arrow()
        self.draw_shadow_arrow()
        self.draw_multipath_arrow()
        self.draw_north_arrow()

        self.draw_direction_arrow()

    def create_from_fname(self, fname):
        helper = SicdMetaIconHelper(fname)
        self.create_from_metaicon_data_container(helper.data_container)

    @property
    def margin_percent(self):
        return self._margin_percent

    @property
    def line_positions(self):
        """
        List[Tuple[float, float]]: The line positions.
        """

        n_lines = 9
        height = self.canvas.variables.canvas_height
        width = self.canvas.variables.canvas_width
        margin = height * (self.margin_percent * 0.01 * 2)
        top_margin = margin/2
        height_w_margin = height - margin
        y_positions = numpy.linspace(0, height_w_margin, n_lines+1)
        y_positions = y_positions + top_margin
        y_positions = y_positions[0:-1]
        x_positions = width * self.margin_percent * 0.01

        xy_positions = []
        for pos in y_positions:
            xy_positions.append((x_positions, pos))
        return xy_positions

    @property
    def cdp_line(self):
        """
        str: The collection duration/polarization line value.
        """

        collect_duration = self.data_container.collect_duration
        cdp_line = "CDP: " + "{:.1f}".format(collect_duration) + " s"
        if self.data_container.polarization:
            cdp_line = cdp_line + " / POL: " + self.data_container.polarization[0] + self.data_container.polarization[2]
        return cdp_line

    @property
    def geo_line(self):
        """
        str: The geographic location line data.
        """

        lat, lon = self.data_container.lat, self.data_container.lon
        lat_str = latlon.string(lat, "lat", include_symbols=False)
        lon_str = latlon.string(lon, "lon", include_symbols=False)
        geo_line = "Geo: " + lat_str + "/" + lon_str
        return geo_line

    @property
    def res_line(self):
        """
        str: The impulse response data line.
        """

        res_line = "IPR: "
        if self.data_container.col_impulse_response_width:
            az_ipr = self.data_container.col_impulse_response_width / constants.foot
            rg_ipr = self.data_container.row_impulse_response_width / constants.foot
            if az_ipr/rg_ipr - 1 < 0.2:
                ipr = (az_ipr + rg_ipr)/2.0
                ipr_str = "{:.1f}".format(ipr)
                res_line = res_line + ipr_str + " ft"
            else:
                ipr_str = "{:.1f}".format(az_ipr) + "/" + "{:.1f}".format(rg_ipr)
                res_line = res_line + ipr_str + "ft(A/R)"
        else:
            if self.data_container.tx_rf_bandwidth is not None:
                bw = self.data_container.tx_rf_bandwidth / 1e6
                res_line = res_line + "{:.0f}".format(bw) + " MHz"
        if self.data_container.rniirs:
            res_line = res_line + " RNIIRS: " + str(self.data_container.rniirs)
        return res_line

    @property
    def iid_line(self):
        """
        str: The data/time data.
        """

        if self.data_container.collector_name:
            if self.data_container.collect_start:
                date_str_1 = self.data_container.collect_start.astype(datetime.datetime).strftime("%d%b%y").upper()
                date_str_2 = self.data_container.collect_start.astype(datetime.datetime).strftime("%H%MZ")
            else:
                date_str_1 = "DDMMMYY"
                date_str_2 = "HMZ"
            collector_name_str = self.data_container.collector_name
            if len(collector_name_str) > 4:
                collector_name_str = collector_name_str[0:4]
            iid_line = date_str_1 + " " + collector_name_str + " / " + date_str_2
        elif self.data_container.core_name:
            iid_line = self.meta.CollectionInfo.CoreName
            if len(iid_line) > 16:
                iid_line = iid_line[0:16]
        else:
            iid_line = "No iid"
        return iid_line

    @property
    def azimuth_line(self):
        """
        str: The azimuth angle line.
        """

        return self._angle_line(self.AngleTypes.azimuth)

    @property
    def graze_line(self):
        """
        str: The graze angle line.
        """

        return self._angle_line(self.AngleTypes.graze)

    @property
    def layover_line(self):
        """
        str: The layover angle line.
        """

        return self._angle_line(self.AngleTypes.layover)

    @property
    def shadow_line(self):
        """
        str: The shadow angle line.
        """

        return self._angle_line(self.AngleTypes.shadow)

    @property
    def multipath_line(self):
        """
        str: The multipath angle line.
        """

        return self._angle_line(self.AngleTypes.multipath)

    def _angle_line(self, angle_type):
        """
        Extracts proper angle line formatting.

        Parameters
        ----------
        angle_type : str

        Returns
        -------
        str
        """

        angle_description_text = angle_type.capitalize()
        n_decimals = getattr(self, "_" + angle_type + "_decimals")
        angle = getattr(self.data_container, angle_type)
        if angle is not None:
            if n_decimals > 0:
                return '{0:s}:{1:0.1f}\xB0'.format(angle_description_text, angle)
            else:
                return '{0:s}:{1:0.0f}\xB0'.format(angle_description_text, angle)
        else:
            return angle_description_text + ": No data"

    @property
    def azimuth_decimals(self):
        """
        int: The number of decimals to include in the azimuth angle formatting.
        """

        return self._azimuth_decimals

    @azimuth_decimals.setter
    def azimuth_decimals(self, value):
        self._azimuth_decimals = int(value)

    @property
    def graze_decimals(self):
        """
        int: The number of decimals to include in the graze angle formatting.
        """

        return self._graze_decimals

    @graze_decimals.setter
    def graze_decimals(self, value):
        self._graze_decimals = int(value)

    @property
    def layover_decimals(self):
        """
        int: The number of decimals to include in the azimuth angle formatting.
        """

        return self._layover_decimals

    @layover_decimals.setter
    def layover_decimals(self, value):
        self._layover_decimals = int(value)

    @property
    def shadow_decimals(self):
        """
        int: The number of decimals to include in the azimuth angle formatting.
        """

        return self._shadow_decimals

    @shadow_decimals.setter
    def shadow_decimals(self, value):
        self._shadow_decimals = int(value)

    @property
    def multipath_decimals(self):
        """
        int: The number of decimals to include in the azimuth angle formatting.
        """

        return self._multipath_decimals

    @multipath_decimals.setter
    def multipath_decimals(self, value):
        self._multipath_decimals = int(value)

    @property
    def layover_arrow_angle(self):
        """
        None|float: The layover arrow angle.
        """

        azimuth = self.data_container.azimuth
        layover = self.data_container.layover

        if azimuth and layover:
            if self.data_container.is_grid or \
                    self.data_container.image_plane == self.data_container.constants.ImagePlaneTypes.slant:
                layover = layover - self.data_container.multipath_ground
            layover = 90 - (layover - azimuth)
            return layover
        else:
            return None

    @property
    def shadow_arrow_angle(self):
        """
        None|float: The shadow arrow angle.
        """

        shadow = self.data_container.shadow
        azimuth = self.data_container.azimuth
        if self.data_container.is_grid or \
                self.data_container.image_plane == self.data_container.constants.ImagePlaneTypes.slant:
            shadow = azimuth - 180 - self.data_container.multipath_ground
        shadow = 90 - (shadow - azimuth)
        return shadow

    @property
    def multipath_arrow_angle(self):
        """
        None|float: The multipath arrow angle.
        """

        multipath = self.data_container.multipath
        azimuth = self.data_container.azimuth
        if self.data_container.is_grid or \
                self.data_container.image_plane == self.data_container.constants.ImagePlaneTypes.slant:
            multipath = azimuth - 180
        north = azimuth + 90
        multipath = north - multipath
        return multipath

    @property
    def north_arrow_angle(self):
        """
        float: The north arrow angle.
        """

        return self.data_container.azimuth + 90

    @property
    def arrow_lengths(self):
        """
        float: The arrow lengths in pixels.
        """

        return self.canvas.variables.canvas_width * 0.15

    @property
    def layover_arrow_coords(self):
        """
        Tuple[float, float, float, float]: The layover arrow coordinates.
        """

        return self._get_arrow_coords(self.layover_arrow_angle)

    @property
    def shadow_arrow_coords(self):
        """
        Tuple[float, float, float, float]: The shadow arrow coordinates.
        """

        return self._get_arrow_coords(self.shadow_arrow_angle)

    @property
    def multipath_arrow_coords(self):
        """
        Tuple[float, float, float, float]: The multipath arrow coordinates.
        """

        return self._get_arrow_coords(self.multipath_arrow_angle)

    @property
    def north_arrow_coords(self):
        """
        Tuple[float, float, float, float]: The north arrow coordinates.
        """

        return self._get_arrow_coords(self.north_arrow_angle)

    def _get_arrow_coords(self, arrow_angle):
        """
        Gets the arrow coordinates.

        Parameters
        ----------
        arrow_angle : float

        Returns
        -------
        Tuple[float, float, float, float]
        """

        arrow_rad = numpy.deg2rad(arrow_angle)
        x_end, y_end = self._adjust_arrow_aspect_ratio(self.arrow_lengths, arrow_rad)
        x_end = self.arrows_origin[0] + x_end
        y_end = self.arrows_origin[1] - y_end
        return self.arrows_origin[0], self.arrows_origin[1], x_end, y_end

    def draw_layover_arrow(self):
        """
        Render the layover arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(self.layover_arrow_coords,
                                     fill=self.Colors.layover,
                                     width=self.ArrowWidths.layover_width)

    def draw_shadow_arrow(self):
        """
        Render the shadow arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(self.shadow_arrow_coords,
                                     fill=self.Colors.shadow,
                                     width=self.ArrowWidths.shadow_width)

    def draw_multipath_arrow(self):
        """
        Render the multipath arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(self.multipath_arrow_coords,
                                     fill=self.Colors.multipath,
                                     width=self.ArrowWidths.multipath_width)

    def draw_north_arrow(self):
        """
        Render the north arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(self.north_arrow_coords,
                                     fill=self.Colors.north,
                                     width=self.ArrowWidths.north_width)
        # label the north arrow
        x_start = self.north_arrow_coords[0]
        x_end = self.north_arrow_coords[2]
        y_start = self.north_arrow_coords[1]
        y_end = self.north_arrow_coords[3]
        text_pos = x_end + (x_end - x_start) * 0.2, y_end + (y_end - y_start) * 0.2
        self.canvas.create_text(text_pos[0], text_pos[1],
                                text="N",
                                fill=self.Colors.north,
                                font=self.font)

    def draw_direction_arrow(self):
        """
        Render the direction arrow.

        Returns
        -------
        None
        """

        flight_direction_arrow_start = (
            self.canvas.variables.canvas_width * 0.65, self.canvas.variables.canvas_height * 0.9)
        flight_direction_arrow_end = (self.canvas.variables.canvas_width * 0.95, flight_direction_arrow_start[1])
        if self.data_container.side_of_track == self.data_container.constants.SideOfTrackTypes.R:
            self.canvas.create_new_arrow((flight_direction_arrow_start[0],
                                          flight_direction_arrow_start[1],
                                          flight_direction_arrow_end[0],
                                          flight_direction_arrow_end[1]), fill=self.Colors.flight_direction, width=3)
        else:
            self.canvas.create_new_arrow((flight_direction_arrow_end[0],
                                          flight_direction_arrow_end[1],
                                          flight_direction_arrow_start[0],
                                          flight_direction_arrow_start[1]), fill=self.Colors.flight_direction, width=3)
        self.canvas.create_text((flight_direction_arrow_start[0] - self.canvas.variables.canvas_width * 0.04,
                                 flight_direction_arrow_start[1]),
                                text="R",
                                fill=self.Colors.flight_direction,
                                font=self.font)

    def _adjust_arrow_aspect_ratio(self, arrow_length, arrow_angle_radians):
        """
        Adjust the arrow aspect ratios.

        Parameters
        ----------
        arrow_length : float
        arrow_angle_radians : float

        Returns
        -------
        Tuple[float, float]
        """

        # adjust aspect ratio in the case we're dealing with circular polarization from RCM
        aspect_ratio = 1.0
        if self.data_container.is_grid:
            pixel_aspect_ratio = self.data_container.grid_column_sample_spacing / self.data_container.grid_row_sample_spacing
            aspect_ratio = aspect_ratio * pixel_aspect_ratio

        if aspect_ratio > 1:
            new_length = numpy.sqrt(numpy.square(arrow_length * numpy.cos(arrow_angle_radians) / aspect_ratio) +
                                    numpy.square(arrow_length * numpy.sin(arrow_angle_radians)))
            arrow_length = arrow_length * arrow_length / new_length
            x_end = arrow_length * numpy.cos(arrow_angle_radians) / aspect_ratio
            y_end = arrow_length * numpy.sin(arrow_angle_radians)
        else:
            new_length = numpy.sqrt(numpy.square(arrow_length * numpy.cos(arrow_angle_radians)) +
                                    numpy.square(arrow_length * numpy.sin(arrow_angle_radians) * aspect_ratio))
            arrow_length = arrow_length * arrow_length / new_length
            x_end = arrow_length * numpy.cos(arrow_angle_radians)
            y_end = arrow_length * numpy.sin(arrow_angle_radians) * aspect_ratio
        return x_end, y_end
