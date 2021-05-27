"""
Helper classes fulfilling the ImageReader pattern.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import logging
import numpy
from typing import Union, List, Tuple

from sarpy.compliance import string_types, int_func
from sarpy.io.general.base import BaseReader
from sarpy.io.complex.base import SICDTypeReader
from tk_builder.image_reader import ImageReader
import sarpy.visualization.remap as remap

from sarpy.io.complex.converter import open_complex
from sarpy.io.complex.aggregate import AggregateComplexReader
from sarpy.io.complex.sicd_elements.SICD import SICDType
from sarpy.io.product.converter import open_product


class ComplexImageReader(ImageReader):
    __slots__ = ('_base_reader', '_chippers', '_index', '_data_size', '_remap_function')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|BaseReader
            The complex valued reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._chippers = None
        self._data_size = None
        self._index = None
        self._remap_function = remap.density
        # set the reader
        self.base_reader = reader

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def base_reader(self):
        # type: () -> BaseReader
        """
        BaseReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_complex(value)
        elif isinstance(value, (tuple, list)):
            value = AggregateComplexReader(value)

        if not isinstance(value, BaseReader):
            raise TypeError('base_reader must be of type BaseReader, got type {}'.format(type(value)))
        if value.reader_type not in ["SICD", "CPHD"]:
            raise ValueError('base_reader.reader_type must be "SICD" or "CPHD", got {}'.format(value.reader_type))
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
                'The index property for ComplexImageReader must be 0 <= index < {}, '
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
        elif hasattr(remap, remap_type):
            self._remap_function = getattr(remap, remap_type)
        else:
            logging.error('Got unexpected value for remap {}'.format(remap_type))
            self._remap_function = remap.density

    def get_sicd(self):
        """
        Gets the relevant SICD structure.

        Returns
        -------
        None|SICDType
        """

        if self._index is None or not isinstance(self.base_reader, SICDTypeReader):
            return None
        return self.base_reader.get_sicds_as_tuple()[self._index]


class QuadPolImageReader(ImageReader):
    __slots__ = (
        '_base_reader', '_chippers', '_sicd_partitions', '_index', '_index_ordering',
        '_data_size', '_remap_function')

    def __init__(self, reader):
        # initialize required elements
        self._base_reader = None
        self._chippers = None
        self._sicd_partitions = None
        self._index = None
        self._index_ordering = None
        self._data_size = None
        self._remap_function = remap.density
        # set the reader
        self.base_reader = reader

    @property
    def file_name(self):
        return None if self.base_reader is None else self.base_reader.file_name

    @property
    def base_reader(self):
        # type: () -> BaseReader
        """
        BaseReader: The complex-valued reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_complex(value)
        elif isinstance(value, (list, tuple)):
            value = AggregateComplexReader(value)
        if not isinstance(value, BaseReader):
            raise TypeError('Requires that the input is a reader object. Got type {}'.format(type(value)))
        if value.reader_type != 'SICD':
            raise ValueError('Requires that the reader.reader_type == "SICD", got {}'.format(value.reader_type))

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

    @property
    def remapable(self):
        return True

    @property
    def remap_function(self):
        return self._remap_function

    @property
    def image_count(self):
        return 0 if self._chippers is None else len(self.sicd_partition)

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
            except:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0])
                rgb_image[:, :, 2] = self._remap_function(complex_data[1])
        elif len(self._index_ordering) == 4:
            try:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0], data_mean=data_mean)
                rgb_image[:, :, 1] = self._remap_function(complex_data[1], data_mean=data_mean)/2 + \
                                     self._remap_function(complex_data[2], data_mean=data_mean)/2
                rgb_image[:, :, 2] = self._remap_function(complex_data[3], data_mean=data_mean)
            except:
                rgb_image[:, :, 0] = self._remap_function(complex_data[0])
                rgb_image[:, :, 1] = self._remap_function(complex_data[1])/2 + \
                                     self._remap_function(complex_data[2])/2
                rgb_image[:, :, 2] = self._remap_function(complex_data[3])
        else:
            raise ValueError('Got unhandled case for collection {}'.format(self._index_ordering))
        return rgb_image

    def set_remap_type(self, remap_type):
        if callable(remap_type):
            self._remap_function = remap_type
        elif hasattr(remap, remap_type):
            self._remap_function = getattr(remap, remap_type)
        else:
            logging.error('Got unexpected value for remap {}'.format(remap_type))
            self._remap_function = remap.density


class DerivedImageReader(ImageReader):
    __slots__ = ('_base_reader', '_chippers', '_index', '_data_size')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|BaseReader
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
        # type: () -> BaseReader
        """
        BaseReader: The SIDD based reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, string_types):
            value = open_product(value)
        if not isinstance(value, BaseReader):
            raise TypeError('base_reader must be of type BaseReader, got type {}'.format(type(value)))
        if value.reader_type != "SIDD":
            raise ValueError('base_reader.reader_type must be "SIDD", got {}'.format(value.reader_type))
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
                'The index property for DerivedImageReader must be 0 <= index < {}, '
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
