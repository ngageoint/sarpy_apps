import logging
import numpy

from tk_builder.image_readers.image_reader import ImageReader
from sarpy.io.complex.converter import open_complex
from sarpy.io.general.base import BaseReader
import sarpy.visualization.remap as remap
from sarpy.compliance import string_types


__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class ComplexImageReader(ImageReader):
    __slots__ = ('_base_reader', '_index', '_data_size', '_remap_function')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|BaseReader
            The complex valued reader, or path to appropriate data file.
        """

        # initialize
        self._base_reader = None
        self._data_size = None
        self._index = None
        self._remap_function = remap.density
        # set the reader
        self.base_reader = reader

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
        if not isinstance(value, BaseReader):
            raise TypeError('base_reader must be of type BaseReader, got type {}'.format(type(value)))
        if value.reader_type != "SICD":
            raise ValueError('base_reader.reader_type must be "SICD", got {}'.format(value.reader_type))
        self._base_reader = value
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
                'The index property for complex_image_reader must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(data_sizes), value))
            value = 0
        self._index = value
        self._data_size = data_sizes[value]

    @property
    def data_size(self):
        # type: () -> (int, int)
        return self._data_size

    @property
    def full_image_nx(self):
        return self._data_size[0]

    @property
    def full_image_ny(self):
        return self._data_size[1]

    def __getitem__(self, item):
        # noinspection PyProtectedMember
        if isinstance(self.base_reader._chipper, tuple):
            # noinspection PyProtectedMember
            cdata = self.base_reader._chipper[self.index].__getitem__(item)
        else:
            cdata = self.base_reader.__getitem__(item)
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
        """
        Set the remap value.

        Parameters
        ----------
        remap_type : str|callable

        Returns
        -------
        None
        """

        if callable(remap_type):
            self._remap_function = remap_type
        elif hasattr(remap, remap_type):
            self._remap_function = getattr(remap, remap_type)
        else:
            logging.error('Got unexpected value for remap {}'.format(remap_type))
            self._remap_function = remap.density
