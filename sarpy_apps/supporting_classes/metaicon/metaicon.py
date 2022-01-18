"""
The metaicon widget.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"

import logging
from typing import Tuple, List
from tkinter import font
import tkinter

import numpy

from sarpy.io.complex.converter import open_complex
from sarpy.io.general.base import AbstractReader

from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.product.base import SIDDTypeReader
from sarpy.io.phase_history.base import CPHDTypeReader
from sarpy.io.received.base import CRSDTypeReader

from tk_builder.panels.image_panel import ImagePanel
from tk_builder.utils.color_utils import rgb_to_hex
from tk_builder.image_reader import NumpyCanvasImageReader
from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer

logger = logging.getLogger(__name__)


class Colors(object):
    layover = rgb_to_hex((1, 0.65, 0))
    shadow = rgb_to_hex((0, 0.65, 1))
    multipath = rgb_to_hex((1, 0, 0))
    north = rgb_to_hex((0.58, 0.82, 0.31))
    flight_direction = rgb_to_hex((1, 1, 0))


class ArrowWidths(object):
    layover_width = 2
    shadow_width = 2
    multipath_width = 2
    north_width = 2


class MetaIcon(ImagePanel):
    """
    The metaicon widget.
    """

    def __init__(self, parent, **kwargs):
        self.parent = parent
        ImagePanel.__init__(self, parent, **kwargs)
        self._metadata_container = MetaIconDataContainer()

        self._margin_percent = 5
        self._font_family = 'Times New Roman'
        self.canvas.set_canvas_size(10, 10)

        self.hide_tools()
        self.hide_shapes()
        self.hide_remap_combo()
        self.hide_select_index()

        self.toolbar.save_canvas.config(text="save metaicon")
        self.on_resize(self.callback_resize)

        self.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.parent.minsize(600, 450)

    def hide_on_close(self):
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()

    # noinspection PyUnusedLocal
    def callback_resize(self, event):
        if self.data_container:
            self.canvas.reinitialize_shapes()
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
        # type: () -> (float, float)
        """
        Tuple[float, float]: The arrow origin location.
        """

        return self.canvas.variables.state.canvas_width*0.75, self.canvas.variables.state.canvas_height*0.6

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

    def make_empty(self):
        """
        Reinitialize as an empty metaicon.

        Returns
        -------
        None
        """

        self.create_from_metaicon_data_container(MetaIconDataContainer())

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
        metaicon_background = numpy.zeros(
            (self.canvas.variables.state.canvas_height, self.canvas.variables.state.canvas_width),
            dtype=numpy.uint8)
        numpy_reader = NumpyCanvasImageReader(metaicon_background)
        self.set_image_reader(numpy_reader)

        line_positions = self.line_positions

        self.canvas.create_new_text(
            line_positions[0], self.data_container.iid_line, color='white',
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[1], self.data_container.geo_line, color="white",
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[2], data_container.res_line, color="white",
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[3], self.data_container.cdp_line, color="white",
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[4], self.data_container.get_angle_line('azimuth'), color="white",
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[5], self.data_container.get_angle_line('graze'), color="white",
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[6], self.data_container.get_angle_line('layover'), color=Colors.layover,
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[7], self.data_container.get_angle_line('shadow'), color=Colors.shadow,
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})
        self.canvas.create_new_text(
            line_positions[8], self.data_container.get_angle_line('multipath'), color=Colors.multipath,
            regular_options={'anchor': 'nw', 'font': self.font}, highlight_options={'anchor': 'nw', 'font': self.font})

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
        reader : str|AbstractReader
            A file name or reader object.
        index : int
            The meta object index in the reader.

        Returns
        -------
        None
        """

        if isinstance(reader, str):
            reader = open_complex(reader)

        if not isinstance(reader, AbstractReader):
            raise TypeError('Got unexpected type {}'.format(type(reader)))

        if isinstance(reader, SICDTypeReader):
            # noinspection PyUnresolvedReferences
            sicd = reader.get_sicds_as_tuple()[index]
            data_container = MetaIconDataContainer.from_sicd(sicd)
        elif isinstance(reader, SIDDTypeReader):
            # noinspection PyUnresolvedReferences
            sidd = reader.get_sidds_as_tuple()[index]
            data_container = MetaIconDataContainer.from_sidd(sidd)
        elif isinstance(reader, CPHDTypeReader):
            # noinspection PyUnresolvedReferences
            data_container = MetaIconDataContainer.from_cphd(reader.cphd_meta, index)
        elif isinstance(reader, CRSDTypeReader):
            # noinspection PyUnresolvedReferences
            data_container = MetaIconDataContainer.from_crsd(reader.crsd_meta)
        else:
            data_container = MetaIconDataContainer()

            logger.warning('Cannot render a metaicon from unhandled reader type {}'.format(type(reader)))

        self.create_from_metaicon_data_container(data_container)

    @property
    def margin_percent(self):
        """
        float: The margin size in percent.
        """
        return self._margin_percent

    @property
    def line_positions(self):
        # type: () -> List[Tuple[float, float]]
        """
        List[Tuple[float, float]]: The line positions.
        """

        n_lines = 9
        height = self.canvas.variables.state.canvas_height
        width = self.canvas.variables.state.canvas_width
        margin = height * (self.margin_percent * 0.01 * 2)
        top_margin = margin/2
        height_w_margin = height - margin
        y_positions = numpy.linspace(0, height_w_margin, n_lines+1)
        y_positions = y_positions + top_margin
        y_positions = y_positions[0:-1]
        x_positions = width * self.margin_percent * 0.01

        xy_positions = []
        for pos in y_positions:
            xy_positions.append((x_positions, float(pos)))
        return xy_positions

    @property
    def layover_arrow_angle(self):
        """
        None|float: The layover arrow angle.
        """

        return self.data_container.layover

    @property
    def shadow_arrow_angle(self):
        """
        None|float: The shadow arrow angle.
        """

        return self.data_container.shadow

    @property
    def multipath_arrow_angle(self):
        """
        None|float: The multipath arrow angle.
        """

        return self.data_container.multipath

    @property
    def north_arrow_angle(self):
        """
        float: The north arrow angle.
        """

        return self.data_container.north

    @property
    def arrow_lengths(self):
        """
        float: The arrow lengths in pixels.
        """

        return self.canvas.variables.state.canvas_width * 0.15

    @property
    def layover_arrow_coords(self):
        # type: () -> Tuple[float, float, float, float]
        """
        Tuple[float, float, float, float]: The layover arrow coordinates.
        """

        # noinspection PyTypeChecker
        return self._get_arrow_coords(self.layover_arrow_angle)

    @property
    def shadow_arrow_coords(self):
        # type: () -> Tuple[float, float, float, float]
        """
        Tuple[float, float, float, float]: The shadow arrow coordinates.
        """

        # noinspection PyTypeChecker
        return self._get_arrow_coords(self.shadow_arrow_angle)

    @property
    def multipath_arrow_coords(self):
        # type: () -> Tuple[float, float, float, float]
        """
        Tuple[float, float, float, float]: The multipath arrow coordinates.
        """

        # noinspection PyTypeChecker
        return self._get_arrow_coords(self.multipath_arrow_angle)

    @property
    def north_arrow_coords(self):
        # type: () -> Tuple[float, float, float, float]
        """
        Tuple[float, float, float, float]: The north arrow coordinates.
        """

        # noinspection PyTypeChecker
        return self._get_arrow_coords(self.north_arrow_angle)

    def _get_arrow_coords(self, arrow_angle):
        # type: (float) -> Tuple[float, float, float, float]
        """
        Gets the arrow coordinates.

        Parameters
        ----------
        arrow_angle : None|float

        Returns
        -------
        (float, float, float, float)
        """

        if arrow_angle is None:
            return 0., 0., 0., 0.

        # noinspection PyTypeChecker
        return self._adjust_arrow_aspect_ratio(self.arrows_origin, self.arrow_lengths, arrow_angle)

    def draw_layover_arrow(self):
        """
        Render the layover arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(
            self.layover_arrow_coords, make_current=False, increment_color=False, color=Colors.layover,
            regular_options={'width': ArrowWidths.layover_width}, highlight_options={'width': ArrowWidths.layover_width})

    def draw_shadow_arrow(self):
        """
        Render the shadow arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(
            self.shadow_arrow_coords, increment_color=False, make_current=False, color=Colors.shadow,
            regular_options={'width': ArrowWidths.shadow_width}, highlight_options={'width': ArrowWidths.shadow_width})

    def draw_multipath_arrow(self):
        """
        Render the multipath arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(
            self.multipath_arrow_coords, make_current=False, increment_color=False, color=Colors.multipath,
            regular_options={'width': ArrowWidths.multipath_width}, highlight_options={'width': ArrowWidths.multipath_width})

    def draw_north_arrow(self):
        """
        Render the north arrow.

        Returns
        -------
        None
        """

        self.canvas.create_new_arrow(
            self.north_arrow_coords, make_current=False, increment_color=False, color=Colors.north,
            regular_options={'width': ArrowWidths.north_width}, highlight_options={'width': ArrowWidths.north_width})
        # label the north arrow
        x_start = self.north_arrow_coords[0]
        x_end = self.north_arrow_coords[2]
        y_start = self.north_arrow_coords[1]
        y_end = self.north_arrow_coords[3]
        text_pos = x_end + (x_end - x_start) * 0.2, y_end + (y_end - y_start) * 0.2
        self.canvas.create_new_text(
            (text_pos[0], text_pos[1]), 'N', color=Colors.north,
            regular_options={'font': self.font}, highlight_options={'font': self.font})

    def draw_direction_arrow(self):
        """
        Render the direction arrow.

        Returns
        -------
        None
        """

        flight_direction_arrow_start = (
            self.canvas.variables.state.canvas_width*0.65, self.canvas.variables.state.canvas_height*0.9)
        flight_direction_arrow_end = (
            self.canvas.variables.state.canvas_width * 0.95, flight_direction_arrow_start[1])
        if self.data_container.side_of_track is None:
            return

        if self.data_container.side_of_track.upper()[0] == 'R':
            text = 'R'
            self.canvas.create_new_arrow(
                flight_direction_arrow_start + flight_direction_arrow_end,
                make_current=False, increment_color=False, color=Colors.flight_direction,
                regular_options={'width': 3}, highlight_options={'width': 3})
        else:
            text = 'L'
            self.canvas.create_new_arrow(
                flight_direction_arrow_end + flight_direction_arrow_start,
                make_current=False, increment_color=False, color=Colors.flight_direction,
                regular_options={'width': 3}, highlight_options={'width': 3})

        self.canvas.create_new_text(
            (flight_direction_arrow_start[0] - self.canvas.variables.state.canvas_width * 0.04,
             flight_direction_arrow_start[1]),
            text, make_current=False, color=Colors.flight_direction,
            regular_options={'font': self.font}, highlight_options={'font': self.font})

    def _adjust_arrow_aspect_ratio(self, origin, arrow_length, arrow_angle):
        """
        Adjust the arrow aspect ratios, for non-square grids.

        Parameters
        ----------
        origin : (float, float)
            The arrow origin coordinates in x/y coordinates.
        arrow_length : float
            The pixel length of the arrow.
        arrow_angle : None|float
            The raw arrow angle in degrees.

        Returns
        -------
        (float, float, float, float)
            The arrow pixel coordinates.
        """

        if arrow_angle is None:
            return 0., 0., 0., 0.
        if arrow_length <= 0.0:
            return origin[0], origin[1], origin[0], origin[1]

        rad_angle = numpy.deg2rad(arrow_angle) - 0.5*numpy.pi

        row_adjust = 1.0
        col_adjust = 1.0
        if self.data_container.is_grid:
            row_adjust *= self.data_container.grid_row_sample_spacing
            col_adjust *= self.data_container.grid_column_sample_spacing

        # tese are canvas coords, so rows and columns roles are switched
        vector = numpy.array([numpy.cos(rad_angle)/col_adjust, numpy.sin(rad_angle)/row_adjust], dtype='float64')
        vector *= arrow_length/numpy.linalg.norm(vector)
        return origin[0], origin[1], float(origin[0] + vector[0]), float(origin[1] + vector[1])
