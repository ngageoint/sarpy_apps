"""
Helper classes mapping the sarpy readers into the CanvasImageReader pattern.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import logging
import numpy
from typing import List, Tuple

from tk_builder.image_reader import CanvasImageReader

from sarpy.io.general.base import BaseReader, SarpyIOError
from sarpy.visualization.remap import get_remap_list, get_registered_remap, RemapFunction

from sarpy.io.complex.converter import open_complex
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.complex.aggregate import AggregateComplexReader
from sarpy.io.complex.sicd_elements.SICD import SICDType

from sarpy.io.product.converter import open_product
from sarpy.io.product.base import SIDDTypeReader
from sarpy.io.product.sidd1_elements.SIDD import SIDDType as SIDDType1
from sarpy.io.product.sidd2_elements.SIDD import SIDDType as SIDDType2


from sarpy.io.phase_history.converter import open_phase_history
from sarpy.io.phase_history.base import CPHDTypeReader
from sarpy.io.phase_history.cphd1_elements.CPHD import CPHDType as CPHDType1
from sarpy.io.phase_history.cphd0_3_elements.CPHD import CPHDType as CPHDType0_3

from sarpy.io.received.converter import open_received
from sarpy.io.received.base import CRSDTypeReader
from sarpy.io.received.crsd1_elements.CRSD import CRSDType

from sarpy.io.general.converter import open_general


def _get_default_remap():
    """
    Gets the default remap function.

    Returns
    -------
    RemapFunction
    """

    return get_remap_list()[0][1]


#######
# general reader

class GeneralCanvasImageReader(CanvasImageReader):
    """
    This is a general image reader of unknown type. There may be trouble
    with the image segments of unexpected type.
    """

    __slots__ = ('_base_reader', '_data_segments', '_index', '_data_size', '_remap_function')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|BaseReader
            The reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._data_segments = None
        self._data_size = None
        self._index = None
        self._remap_function = _get_default_remap()
        # set the reader
        self.base_reader = reader

    @property
    def base_reader(self):
        # type: () -> BaseReader
        """
        BaseReader: The reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            value = open_general(value)
        if not isinstance(value, BaseReader):
            raise TypeError('base_reader must be of type BaseReader, got type {}'.format(type(value)))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0

    @property
    def reader_type(self):
        """
        str: The reader type.
        """

        return self.base_reader.reader_type

    @property
    def index(self):
        """
        int: The reader index.
        """

        return self._index

    @index.setter
    def index(self, value):
        value = int(value)
        data_sizes = self.base_reader.get_data_size_as_tuple()
        if not (0 <= value < len(data_sizes)):
            logging.error(
                'The index property must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(data_sizes), value))
            value = 0
        self._index = value
        self._data_size = data_sizes[value]

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def remapable(self):
        return True

    @property
    def remap_function(self):
        return self._remap_function

    @property
    def image_count(self):
        return 0 if self._data_segments is None else len(self._data_segments)

    def get_meta_data(self):
        """
        Gets one of a varieties of metadata structure.

        Returns
        -------
        Any
        """

        if isinstance(self.base_reader, SICDTypeReader):
            if self._index is None:
                return None
            # noinspection PyUnresolvedReferences
            return self.base_reader.get_sicds_as_tuple()[self._index]
        elif isinstance(self.base_reader, SIDDTypeReader):
            if self._index is None:
                return None
            # noinspection PyUnresolvedReferences
            return self.base_reader.get_sidds_as_tuple()[self._index]
        elif isinstance(self.base_reader, CPHDTypeReader):
            # noinspection PyUnresolvedReferences
            return self.base_reader.cphd_meta
        elif isinstance(self.base_reader, CRSDTypeReader):
            # noinspection PyUnresolvedReferences
            return self.base_reader.crsd_meta
        return None

    def __getitem__(self, subscript):
        data = self._data_segments[self.index].__getitem__(subscript)
        return self.remap_data(data)

    def __del__(self):
        self._data_segments = None

    def remap_data(self, data):
        """
        Remap the given data according to the current remap function, unless it has
        dtype uint8.

        Parameters
        ----------
        data : numpy.ndarray

        Returns
        -------
        numpy.ndarray
        """

        if self._remap_function is None or data.dtype.name == 'uint8':
            return data
        return self._remap_function(data)

    def set_remap_type(self, remap_type):
        if callable(remap_type):
            self._remap_function = remap_type
        elif isinstance(remap_type, str):
            self._remap_function = get_registered_remap(remap_type, _get_default_remap())
        else:
            default_remap = _get_default_remap()
            logging.error(
                'Got unexpected value for remap `{}`, using `{}`'.format(remap_type, default_remap.name))
            self._remap_function = default_remap


########
# general complex type reader structure - really just sets the remap

class ComplexCanvasImageReader(GeneralCanvasImageReader):

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|BaseReader
            The complex valued reader, or path to appropriate data file.
        """

        self._remap_function = _get_default_remap()
        GeneralCanvasImageReader.__init__(self, reader)

    @property
    def base_reader(self):
        # type: () -> BaseReader
        """
        BaseReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            reader = None

            # try to open as sicd type
            try:
                reader = open_complex(value)
            except SarpyIOError:
                pass

            # try to open as phase_history
            if reader is None:
                try:
                    reader = open_phase_history(value)
                except SarpyIOError:
                    pass

            if reader is None:
                try:
                    reader = open_received(value)
                except SarpyIOError:
                    pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a one of the complex type readers'.format(value))
            value = reader
        elif isinstance(value, (tuple, list)):
            value = AggregateComplexReader(value)

        if not isinstance(value, BaseReader):
            raise TypeError('base_reader must be of type BaseReader, got type {}'.format(type(value)))
        if value.reader_type not in ["SICD", "CPHD", "CRSD"]:
            raise SarpyIOError(
                'base_reader.reader_type must be "SICD", "CPHD", or "CRSD", got {}'.format(value.reader_type))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0


########
# SICD specific type readers

class SICDTypeCanvasImageReader(ComplexCanvasImageReader):

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|SICDTypeReader
            The sicd type reader, or path to appropriate data file.
        """

        ComplexCanvasImageReader.__init__(self, reader)

    @property
    def base_reader(self):
        # type: () -> SICDTypeReader
        """
        SICDTypeReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            reader = None
            try:
                reader = open_complex(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a SICD type reader'.format(value))
            value = reader
        elif isinstance(value, (tuple, list)):
            value = AggregateComplexReader(value)

        if not isinstance(value, SICDTypeReader):
            raise TypeError('base_reader must be a SICDTypeReader, got type {}'.format(type(value)))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0

    def get_sicd(self):
        """
        Gets the relevant SICD structure.

        Returns
        -------
        None|SICDType
        """

        if self._index is None:
            return None
        return self.base_reader.get_sicds_as_tuple()[self._index]

    def transform_coordinates(self, image_coordinates):
        sicd = self.get_sicd()
        if sicd is None:
            return None, 'NONE'

        return sicd.project_image_to_ground_geo(image_coordinates, projection_type='HAE'), 'LLH_HAE'


class QuadPolCanvasImageReader(ComplexCanvasImageReader):
    __slots__ = (
        '_base_reader', '_data_segments', '_sicd_partitions', '_index', '_index_ordering',
        '_data_size', '_remap_function')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|SICDTypeReader
            The sicd type reader, or path to appropriate data file.
        """

        ComplexCanvasImageReader.__init__(self, reader)

    @property
    def base_reader(self):
        # type: () -> SICDTypeReader
        """
        SICDTypeReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            value = open_complex(value)
        elif isinstance(value, (list, tuple)):
            value = AggregateComplexReader(value)
        if not isinstance(value, SICDTypeReader):
            raise TypeError('Requires that the input is a sicd type reader object. Got type {}'.format(type(value)))

        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self._sicd_partitions = value.get_sicd_partitions()
        try:
            self.index = 0
        except ValueError:
            # the index will be uninitialized
            pass

    @property
    def sicd_partition(self):
        """
        Tuple[Tuple[int]]: The partitioning of the reader indices into matching components.
        """

        return self._sicd_partitions

    @property
    def index(self):
        """
        int: the SICD partition index.
        """

        return self._index

    @index.setter
    def index(self, value):
        if self._sicd_partitions is None:
            return

        value = int(value)
        if not (0 <= value < len(self.sicd_partition)):
            raise ValueError('index must be on the range 0 <= index < {}'.format(len(self.sicd_partition)))
        indices = self.sicd_partition[value]
        # determine appropriate ordering for index collection
        data_sizes = self.base_reader.get_data_size_as_tuple()
        data_size = data_sizes[indices[0]]
        for entry in indices:
            if data_sizes[entry] != data_size:
                raise ValueError(
                    'All entries of sicd partition {} do not yield sicd elements of '
                    'the same row/column size.'.format(value))
        self._index = value
        self._data_size = data_size
        self._order_indices(value, indices)

    def _order_indices(self, index, indices):
        """
        Determine the appropriate ordering for indices.

        Parameters
        ----------
        index : int
        indices : Tuple[int]

        Returns
        -------
        None
        """

        def revert():
            self._index = None
            self._index_ordering = None
            self._data_size = None

        if len(indices) == 1:
            self._index_ordering = indices
            return

        sicds = self.base_reader.get_sicds_as_tuple()
        our_sicds = [sicds[entry] for entry in indices]  # type: List[SICDType]
        pols = [entry.ImageFormation.TxRcvPolarizationProc for entry in our_sicds]
        if len(indices) == 2:
            pols_set = set(pols)
            if len(pols_set) != 2:
                ordered_indices = None
            else:
                ordered_indices = None
                for desired_order in [['CV', 'CH'], ['VV', 'HH']]:
                    if pols_set == set(desired_order):
                        ordered_indices = [pols.index(entry) for entry in desired_order]
                        break
        elif len(indices) == 4:
            pols_set = set(pols)
            if len(pols_set) != 4:
                ordered_indices = None
            else:
                ordered_indices = None
                for desired_order in [['VV', 'VH', 'HV', 'HH'], ]:
                    if pols_set == set(desired_order):
                        ordered_indices = [pols.index(entry) for entry in desired_order]
                        break
        else:
            ordered_indices = None

        if ordered_indices is None:
            revert()
            raise ValueError(
                'Got unhandled polarization states for partition {}'.format(pols, index))
        self._index_ordering = ordered_indices

    def __getitem__(self, subscript):
        def get_cdata(the_index):
            return self._data_segments[the_index].__getitem__(subscript)

        if self._index_ordering is None:
            return None
        if len(self._index_ordering) == 1:
            complex_data = get_cdata(self._index_ordering[0])
            return self._remap_function(complex_data)

        complex_data = [get_cdata(entry) for entry in self._index_ordering]
        out_size = complex_data[0].shape
        for entry in complex_data:
            if entry.shape != out_size:
                raise ValueError('Got unexpected mismatch in sizes {} and {}'.format(entry.shape, out_size))
        data_mean = float(max(numpy.mean(numpy.abs(entry)) for entry in complex_data))
        rgb_image = numpy.zeros(out_size + (3, ), dtype='uint8')
        if len(self._index_ordering) == 2:
            # noinspection PyBroadException
            try:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0], data_mean=data_mean)
                rgb_image[:, :, 2] = self._remap_function(complex_data[1], data_mean=data_mean)
            except Exception:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0])
                rgb_image[:, :, 2] = self._remap_function(complex_data[1])
        elif len(self._index_ordering) == 4:
            # noinspection PyBroadException
            try:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0], data_mean=data_mean)
                rgb_image[:, :, 1] = self._remap_function(complex_data[1], data_mean=data_mean)/2 + \
                    self._remap_function(complex_data[2], data_mean=data_mean)/2
                rgb_image[:, :, 2] = self._remap_function(complex_data[3], data_mean=data_mean)
            except Exception:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0])
                rgb_image[:, :, 1] = self._remap_function(complex_data[1])/2 + \
                    self._remap_function(complex_data[2])/2
                rgb_image[:, :, 2] = self._remap_function(complex_data[3])
        else:
            raise ValueError('Got unhandled case for collection {}'.format(self._index_ordering))
        return rgb_image

    def get_sicd(self):
        """
        Gets the relevant SICD structure.

        Returns
        -------
        None|SICDType
        """

        if self._index is None:
            return None
        return self.base_reader.get_sicds_as_tuple()[self._index]

    def transform_coordinates(self, image_coordinates):
        sicd = self.get_sicd()
        if sicd is None:
            return None, 'NONE'

        return sicd.project_image_to_ground_geo(image_coordinates, projection_type='HAE'), 'LLH_HAE'


#######
# Phase history specific type reader

class CPHDTypeCanvasImageReader(ComplexCanvasImageReader):

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|CPHDTypeReader
            The cphd type reader, or path to appropriate data file.
        """

        ComplexCanvasImageReader.__init__(self, reader)

    @property
    def base_reader(self):
        # type: () -> CPHDTypeReader
        """
        CPHDTypeReader: The cphd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            reader = None
            try:
                reader = open_phase_history(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a CPHD reader'.format(value))
            value = reader

        if not isinstance(value, CPHDTypeReader):
            raise TypeError('base_reader must be a CPHDReader, got type {}'.format(type(value)))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0

    def get_cphd(self):
        """
        Gets the relevant CPHD structure.

        Returns
        -------
        None|CPHDType1|CPHDType0_3
        """

        return self.base_reader.cphd_meta


#######
# Received data specific type reader

class CRSDTypeCanvasImageReader(ComplexCanvasImageReader):

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|CRSDTypeReader
            The crsd type reader, or path to appropriate data file.
        """

        ComplexCanvasImageReader.__init__(self, reader)

    @property
    def channel_id(self):
        """
        str: Get the selected channel id
        """

        return self.get_crsd().Channel.Parameters[self.index].Identifier

    @property
    def base_reader(self):
        # type: () -> CRSDTypeReader
        """
        CRSDTypeReader: The crsd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            reader = None
            try:
                reader = open_received(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a CRSD reader'.format(value))
            value = reader

        if not isinstance(value, CRSDTypeReader):
            raise TypeError('base_reader must be a CRSDReader, got type {}'.format(type(value)))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0

    def get_crsd(self):
        """
        Gets the relevant CRSD structure.

        Returns
        -------
        None|CRSDType
        """

        return self.base_reader.crsd_meta


######
# SIDD specific type reader

class DerivedCanvasImageReader(GeneralCanvasImageReader):

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|SIDDTypeReader
            The sidd type reader, or path to appropriate data file.
        """

        GeneralCanvasImageReader.__init__(self, reader)

    @property
    def base_reader(self):
        # type: () -> SIDDTypeReader
        """
        SIDDTypeReader: The SIDD based reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            value = open_product(value)
        if not isinstance(value, SIDDTypeReader):
            raise TypeError('base_reader must be a SIDDTypeReader, got type {}'.format(type(value)))
        self._base_reader = value
        self._data_segments = value.get_data_segment_as_tuple()
        self.index = 0

    def get_sidd(self):
        """
        Gets the relevant SIDD structure.

        Returns
        -------
        None|SIDDType1|SIDDType2
        """

        if self._index is None:
            return None
        return self.base_reader.get_sidds_as_tuple()[self._index]

    def transform_coordinates(self, image_coordinates):
        sidd = self.get_sidd()
        if sidd is None:
            return None, 'NONE'

        return sidd.project_image_to_ground_geo(image_coordinates, projection_type='HAE'), 'LLH_HAE'
