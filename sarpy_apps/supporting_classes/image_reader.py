"""
Helper classes mapping the sarpy readers into the CanvasImageReader pattern.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


import logging
import numpy
from typing import List, Tuple, Union
import gc

from sarpy.compliance import string_types, int_func
from sarpy.io.general.base import AbstractReader, SarpyIOError
from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.product.base import SIDDTypeReader
from tk_builder.image_reader import CanvasImageReader
from sarpy.visualization.remap import get_remap_list, get_registered_remap, RemapFunction

from sarpy.io.complex.converter import open_complex
from sarpy.io.complex.aggregate import AggregateComplexReader
from sarpy.io.complex.sicd_elements.SICD import SICDType
from sarpy.io.product.converter import open_product

from sarpy.io.phase_history.converter import open_phase_history
from sarpy.io.phase_history.cphd import CPHDReader
from sarpy.io.phase_history.cphd1_elements.CPHD import CPHDType as CPHDType1
from sarpy.io.phase_history.cphd0_3_elements.CPHD import CPHDType as CPHDType0_3
from sarpy.io.phase_history.crsd import CRSDReader
from sarpy.io.phase_history.crsd1_elements.CRSD import CRSDType

from sarpy.io.general.converter import open_general


def _get_default_remap():
    """
    Gets the default remap function.

    Returns
    -------
    RemapFunction
    """

    return get_remap_list()[0][1]


class ComplexCanvasImageReader(CanvasImageReader):
    __slots__ = ('_base_reader', '_chippers', '_index', '_data_size', '_remap_function')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|AbstractReader
            The complex valued reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._chippers = None
        self._data_size = None
        self._index = None
        self._remap_function = _get_default_remap()
        # set the reader
        self.base_reader = reader

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def base_reader(self):
        # type: () -> AbstractReader
        """
        AbstractReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            reader = None
            try:
                reader = open_complex(value)
            except SarpyIOError:
                pass
            if reader is None:
                try:
                    reader = open_phase_history(value)
                except SarpyIOError:
                    pass
            if reader is None:
                raise SarpyIOError('Could not open file {} as a SICD or CPHD type reader'.format(value))
            value = reader
        elif isinstance(value, (tuple, list)):
            value = AggregateComplexReader(value)

        if not isinstance(value, AbstractReader):
            raise TypeError('base_reader must be of type AbstractReader, got type {}'.format(type(value)))
        if value.reader_type not in ["SICD", "CPHD", "CRSD"]:
            raise SarpyIOError(
                'base_reader.reader_type must be "SICD", "CPHD", or "CRSD", got {}'.format(value.reader_type))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

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
                'The index property for ComplexCanvasImageReader must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(data_sizes), value))
            value = 0
        self._index = value
        self._data_size = data_sizes[value]

    @property
    def remapable(self):
        return True

    @property
    def remap_function(self):
        return self._remap_function

    @property
    def image_count(self):
        return 0 if self._chippers is None else len(self._chippers)

    def __getitem__(self, item):
        cdata = self._chippers[self.index].__getitem__(item)
        decimated_image_data = self.remap_complex_data(cdata)
        return decimated_image_data

    def remap_complex_data(self, complex_data):
        """
        Perform the remap on the complex data.

        Parameters
        ----------
        complex_data : numpy.ndarray

        Returns
        -------
        numpy.ndarray
        """

        return self._remap_function(complex_data)

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

    def __del__(self):
        # noinspection PyBroadException
        try:
            del self._chippers
            gc.collect()
        except Exception:
            pass

########
# SICD specific type readers

class SICDTypeCanvasImageReader(ComplexCanvasImageReader):

    @property
    def base_reader(self):
        # type: () -> SICDTypeReader
        """
        SICDTypeReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
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
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

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


class QuadPolCanvasImageReader(ComplexCanvasImageReader):
    __slots__ = (
        '_base_reader', '_chippers', '_sicd_partitions', '_index', '_index_ordering',
        '_data_size', '_remap_function')

    @property
    def base_reader(self):
        # type: () -> SICDTypeReader
        """
        SICDTypeReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_complex(value)
        elif isinstance(value, (list, tuple)):
            value = AggregateComplexReader(value)
        if not isinstance(value, SICDTypeReader):
            raise TypeError('Requires that the input is a sicd type reader object. Got type {}'.format(type(value)))

        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
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

        value = int_func(value)
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

    def __getitem__(self, item):
        def get_cdata(the_index):
            return self._chippers[the_index].__getitem__(item)

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
            try:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0], data_mean=data_mean)
                rgb_image[:, :, 2] = self._remap_function(complex_data[1], data_mean=data_mean)
            except Exception:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0])
                rgb_image[:, :, 2] = self._remap_function(complex_data[1])
        elif len(self._index_ordering) == 4:
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


#######
# Phase history specific type reader

class CPHDTypeCanvasImageReader(ComplexCanvasImageReader):

    @property
    def base_reader(self):
        # type: () -> CPHDReader
        """
        CPHDReader: The cphd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            reader = None
            try:
                reader = CPHDReader(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a CPHD reader'.format(value))
            value = reader

        if not isinstance(value, CPHDReader):
            raise TypeError('base_reader must be a CPHDReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

    def get_cphd(self):
        """
        Gets the relevant CPHD structure.

        Returns
        -------
        None|CPHDType1|CPHDType0_3
        """

        return self.base_reader.cphd_meta


class CRSDTypeCanvasImageReader(ComplexCanvasImageReader):

    @property
    def base_reader(self):
        # type: () -> CRSDReader
        """
        CRSDReader: The crsd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            reader = None
            try:
                reader = CRSDReader(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a CRSD reader'.format(value))
            value = reader

        if not isinstance(value, CRSDReader):
            raise TypeError('base_reader must be a CRSDReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

    def get_crsd(self):
        """
        Gets the relevant CRSD structure.

        Returns
        -------
        None|CRSDType
        """

        return self.base_reader.crsd_meta


class PhaseHistoryCanvasImageReader(ComplexCanvasImageReader):

    @property
    def base_reader(self):
        # type: () -> Union[CPHDReader, CRSDReader]
        """
        CPHDReader|CRSDReader: The cphd or crsd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            reader = None
            try:
                reader = open_phase_history(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a phase history reader'.format(value))
            value = reader

        if not isinstance(value, (CPHDReader, CRSDReader)):
            raise TypeError('base_reader must be a CPHDReader or CRSDReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

    def get_cphd(self):
        """
        Gets the relevant CPHD structure.

        Returns
        -------
        None|CPHDType1|CPHDType0_3
        """

        if not isinstance(self.base_reader, CPHDReader):
            return None
        return self.base_reader.cphd_meta

    def get_crsd(self):
        """
        Gets the relevant CRSD structure.

        Returns
        -------
        None|CRSDType
        """

        if not isinstance(self.base_reader, CRSDReader):
            return None
        return self.base_reader.crsd_meta


######
# SIDD specific type reader

class DerivedCanvasImageReader(CanvasImageReader):
    __slots__ = ('_base_reader', '_chippers', '_index', '_data_size')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|SIDDTypeReader
            The sidd based reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._chippers = None
        self._data_size = None
        self._index = None
        # set the reader
        self.base_reader = reader

    @property
    def base_reader(self):
        # type: () -> SIDDTypeReader
        """
        SIDDTypeReader: The SIDD based reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_product(value)
        if not isinstance(value, SIDDTypeReader):
            raise TypeError('base_reader must be a SIDDTypeReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

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
                'The index property for DerivedCanvasImageReader must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(data_sizes), value))
            value = 0
        self._index = value
        self._data_size = data_sizes[value]

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def remapable(self):
        return False

    @property
    def remap_function(self):
        return None

    @property
    def image_count(self):
        return 0 if self._chippers is None else len(self._chippers)

    def __getitem__(self, item):
        return self._chippers[self.index].__getitem__(item)

    def __del__(self):
        # noinspection PyBroadException
        try:
            del self._chippers
            gc.collect()
        except Exception:
            pass


#######
# general reader

class GeneralCanvasImageReader(CanvasImageReader):
    """
    This is a general image reader of unknown type. There may be trouble
    with the image segments of unexpected type.
    """

    __slots__ = ('_base_reader', '_chippers', '_index', '_data_size')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|AbstractReader
            The sidd based reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._chippers = None
        self._data_size = None
        self._index = None
        # set the reader
        self.base_reader = reader

    @property
    def base_reader(self):
        # type: () -> AbstractReader
        """
        AbstractReader: The reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_general(value)
        if not isinstance(value, AbstractReader):
            raise TypeError('base_reader must be of type AbstractReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self._index = 0
        self._data_size = value.get_data_size_as_tuple()[0]

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
                'The index property for DerivedCanvasImageReader must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(data_sizes), value))
            value = 0
        self._index = value
        self._data_size = data_sizes[value]

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def remapable(self):
        return False

    @property
    def remap_function(self):
        return None

    @property
    def image_count(self):
        return 0 if self._chippers is None else len(self._chippers)

    def __getitem__(self, item):
        return self._chippers[self.index].__getitem__(item)

    def __del__(self):
        # noinspection PyBroadException
        try:
            del self._chippers
            gc.collect()
        except Exception:
            pass
