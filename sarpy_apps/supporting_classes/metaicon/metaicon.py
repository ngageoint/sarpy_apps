from tkinter import font

import numpy
from sarpy.io.complex.converter import open_complex
from sarpy.io.general.base import BaseReader
from sarpy.io.general.utils import string_types
from sarpy.io.product.sidd import SIDDReader
from sarpy.io.phase_history.cphd import CPHDReader

from tk_builder.panels.image_panel import ImagePanel
import tk_builder.utils.color_utils.color_converter as color_converter
from tk_builder.image_readers.numpy_image_reader import NumpyImageReader
from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer


class MetaIcon(ImagePanel):

    class Colors:
        layover = color_converter.rgb_to_hex((1, 0.65, 0))
        shadow = color_converter.rgb_to_hex((0, 0.65, 1))
        multipath = color_converter.rgb_to_hex((1, 0, 0))
        north = color_converter.rgb_to_hex((0.58, 0.82, 0.31))
        flight_direction = color_converter.rgb_to_hex((1, 1, 0))

    class ArrowWidths:
        layover_width = 2
        shadow_width = 2
        multipath_width = 2
        north_width = 2

    def __init__(self, master):
        super(MetaIcon, self).__init__(master)
        self.parent = master
        self._metadata_container = MetaIconDataContainer()

        self._margin_percent = 5  # TODO: is it more clear to use fraction versus percent?
        self._font_family = 'Times New Roman'
        self.resizeable = True
        self.on_resize(self.callback_resize)
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()

    def callback_resize(self, event):
        super().callback_resize(event)
        if self.data_container:
            self.canvas.delete("all")
            self.create_from_metaicon_data_container(self.data_container)

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
        # metaicon_background = numpy.zeros((400, 400))
        metaicon_background = numpy.zeros((self.canvas.variables.canvas_height, self.canvas.variables.canvas_width))
        numpy_reader = NumpyImageReader(metaicon_background)
        self.set_image_reader(numpy_reader)

        line_positions = self.line_positions

        self.canvas.create_new_text(
            line_positions[0], text=self.data_container.iid_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[1], text=self.data_container.geo_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[2], text=self.data_container.res_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[3], text=self.data_container.cdp_line, fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[4], text=self.data_container.get_angle_line('azimuth'),
            fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[5], text=self.data_container.get_angle_line('graze'),
            fill="white", anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[6], text=self.data_container.get_angle_line('layover'),
            fill=self.Colors.layover, anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[7], text=self.data_container.get_angle_line('shadow'),
            fill=self.Colors.shadow, anchor="nw", font=self.font)
        self.canvas.create_new_text(
            line_positions[8], text=self.data_container.get_angle_line('multipath'),
            fill=self.Colors.multipath, anchor="nw", font=self.font)

        self.draw_layover_arrow()
        self.draw_shadow_arrow()
        self.draw_multipath_arrow()
        self.draw_north_arrow()
        self.draw_direction_arrow()

    def create_from_reader(self, reader, index=0):
        """
        Reinitialize from a file name or reader object.

        Parameters
        ----------
        reader : BaseReader|str
            A file name or reader object.
        index : int
            The meta object index in the reader.

        Returns
        -------
        None
        """

        if isinstance(reader, string_types):
            reader = open_complex(reader)
        if not isinstance(reader, BaseReader):
            raise TypeError('Got unexpected type {}'.format(type(reader)))

        if reader.is_sicd_type:
            sicd = reader.get_sicds_as_tuple()[index]
            data_container = MetaIconDataContainer.from_sicd(sicd)
        elif isinstance(reader, CPHDReader):
            data_container = MetaIconDataContainer.from_cphd(reader.cphd_meta)
        elif isinstance(reader, SIDDReader):
            data_container = MetaIconDataContainer.from_sidd(reader.sidd_meta[index])
        else:
            raise TypeError('Got unhandled type {}'.format(type(reader)))

        self.create_from_metaicon_data_container(data_container)

    @property
    def margin_percent(self):
        """
        float: The margin size in percent.
        """

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
    def layover_arrow_angle(self):
        """
        None|float: The layover arrow angle.
        """

        azimuth = self.data_container.azimuth
        layover = self.data_container.layover

        if azimuth and layover:
            if self.data_container.is_grid or self.data_container.image_plane == 'SLANT':
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
        if self.data_container.is_grid or self.data_container.image_plane == 'SLANT':
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
        if self.data_container.is_grid or self.data_container.image_plane == 'SLANT':
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
        self.canvas.create_new_text((text_pos[0], text_pos[1]),
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
        if self.data_container.side_of_track == 'R':
            self.canvas.create_new_arrow((flight_direction_arrow_start[0],
                                          flight_direction_arrow_start[1],
                                          flight_direction_arrow_end[0],
                                          flight_direction_arrow_end[1]), fill=self.Colors.flight_direction, width=3)
        else:
            self.canvas.create_new_arrow((flight_direction_arrow_end[0],
                                          flight_direction_arrow_end[1],
                                          flight_direction_arrow_start[0],
                                          flight_direction_arrow_start[1]), fill=self.Colors.flight_direction, width=3)
        self.canvas.create_new_text((flight_direction_arrow_start[0] - self.canvas.variables.canvas_width * 0.04,
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

