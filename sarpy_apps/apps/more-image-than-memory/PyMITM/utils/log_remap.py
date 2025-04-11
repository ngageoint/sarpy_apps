from sarpy.io.complex.base import SICDTypeReader
from sarpy.io.complex.utils import get_data_extrema
from typing import Dict, Union, Tuple, Type, List, Optional
import numpy

def clip_cast(
        array: numpy.ndarray,
        dtype: Union[str, numpy.dtype, numpy.number] = 'uint8',
        min_value: Union[None, int, float] = None,
        max_value: Union[None, int, float] = None) -> numpy.ndarray:
    """
    Cast by clipping values outside of valid range, rather than truncating.

    Parameters
    ----------
    array : numpy.ndarray
    dtype : str|numpy.dtype
    min_value : None|int|float
    max_value : None|int|float

    Returns
    -------
    numpy.ndarray
    """

    np_type = numpy.dtype(dtype)
    min_value = numpy.iinfo(np_type).min if min_value is None else max(min_value, numpy.iinfo(np_type).min)
    max_value = numpy.iinfo(np_type).max if max_value is None else min(max_value, numpy.iinfo(np_type).max)
    return numpy.clip(array, min_value, max_value).astype(np_type)

class RemapFunction(object):
    """
    Abstract remap class which is callable.

    See the :func:`call` implementation for the given class to understand
    what specific keyword arguments are allowed for the specific instance.
    """

    _name = '_RemapFunction'
    __slots__ = ('_override_name', '_bit_depth', '_dimension')
    _allowed_dimension = {0, 1, 2, 3, 4}

    def __init__(
            self,
            override_name: Optional[str] = None,
            bit_depth: int = 8,
            dimension: int = 0):
        """

        Parameters
        ----------
        override_name : None|str
            Override name for a specific class instance
        bit_depth : int
            Should be one of 8 or 16
        dimension : int
        """

        self._override_name = None
        self._bit_depth = None
        self._dimension = None
        self._set_name(override_name)
        self._set_bit_depth(bit_depth)
        self._set_dimension(dimension)

    @property
    def name(self) -> str:
        """
        str: The (read-only) name for the remap function. This will be the
        override_name if one has been provided for this instance, otherwise it
        will be the generic `_name` class value.
        """

        return self._name if self._override_name is None else self._override_name

    def _set_name(self, value: Optional[str]):
        if value is None or isinstance(value, str):
            self._override_name = value
        else:
            raise ValueError('Got incompatible name')

    @property
    def bit_depth(self) -> int:
        """
        int: The (read-only) bit depth, which should be either 8 or 16.
        This is expected to be enforced by the implementation directly.
        """

        return self._bit_depth

    def _set_bit_depth(self, value: int):
        """
        This is intended to be read-only.

        Parameters
        ----------
        value : int
        """

        value = int(value)

        if value not in [8, 16, 32]:
            raise ValueError(
                'Bit depth is required to be one of 8, 16, or 32 and we got `{}`'.format(value))
        self._bit_depth = value

    @property
    def dimension(self) -> int:
        """
        int: The (read-only) size of the (additional) output final dimension.
        The value 0 is monochromatic, where the retuned output will have identical
        shape as input. Any other value should have additional final dimension of this size.
        """

        return self._dimension

    def _set_dimension(self, value: int):
        """
        The property is intended to be read-only.

        Parameters
        ----------
        value : int
        """

        value = int(value)
        if self._allowed_dimension is not None and value not in self._allowed_dimension:
            raise ValueError(
                'Dimension is required to be one of `{}`, got `{}`'.format(self._allowed_dimension, value))
        self._dimension = value

    @property
    def output_dtype(self) -> numpy.dtype:
        """
        numpy.dtype: The output data type.
        """

        if self._bit_depth == 8:
            return numpy.dtype('u1')
        elif self._bit_depth == 16:
            return numpy.dtype('u2')
        elif self._bit_depth == 32:
            return numpy.dtype('u4')
        else:
            raise ValueError('Unhandled bit_depth `{}`'.format(self._bit_depth))

    @property
    def are_global_parameters_set(self) -> bool:
        """
        bool: Are (all) global parameters used for applying this remap function
        set? This should return `True` if there are no global parameters.
        """

        return True

    def raw_call(
            self,
            data: numpy.ndarray,
            **kwargs) -> numpy.ndarray:
        """
        This performs the mapping from input data to output floating point
        version, this is directly used by the :func:`call` method.

        Parameters
        ----------
        data : numpy.ndarray
            The (presumably) complex data to remap.
        kwargs
            Some keyword arguments may be allowed here

        Returns
        -------
        numpy.ndarray
            This should generally have `float64` dtype.
        """

        raise NotImplementedError

    def call(
            self,
            data: numpy.ndarray,
            **kwargs) -> numpy.ndarray:
        """
        This performs the mapping from input data to output discrete version.

        This method os directly called by the :func:`__call__` method, so the
        class instance (once constructed) is itself callable, as follows:

        >>> remap = RemapFunction()
        >>> discrete_data = remap(data, **kwargs)

        Parameters
        ----------
        data : numpy.ndarray
            The (presumably) complex data to remap.
        kwargs
            Some keyword arguments may be allowed here

        Returns
        -------
        numpy.ndarray
        """

        return clip_cast(self.raw_call(data, **kwargs), dtype=self.output_dtype)

    def __call__(
            self,
            data: numpy.ndarray,
            **kwargs) -> numpy.ndarray:
        return self.call(data, **kwargs)

    @staticmethod
    def _validate_pixel_bounds(
            reader: SICDTypeReader,
            index: int,
            pixel_bounds: Union[None, Tuple, List, numpy.ndarray]):
        data_size = reader.get_data_size_as_tuple()[index]
        if pixel_bounds is None:
            return 0, data_size[0], 0, data_size[1]

        if not (
                (-data_size[0] <= pixel_bounds[0] <= data_size[0]) and
                (-data_size[0] <= pixel_bounds[1] <= data_size[0]) and
                (-data_size[1] <= pixel_bounds[2] <= data_size[1]) and
                (-data_size[1] <= pixel_bounds[3] <= data_size[1])):
            raise ValueError('invalid pixel bounds `{}` for data of shape `{}`'.format(pixel_bounds, data_size))
        return pixel_bounds

    def calculate_global_parameters_from_reader(
            self,
            reader: SICDTypeReader,
            index: int = 0,
            pixel_bounds: Union[None, Tuple, List, numpy.ndarray] = None):
        """
        Calculates any useful global bounds for the specified reader, the given
        index, and inside the given pixel bounds.

        This is expected to save ny necessary state here.

        Parameters
        ----------
        reader : SICDTypeReader
        index : int
        pixel_bounds : None|tuple|list|numpy.ndarray
            If provided, is of the form `(row min, row max, column min, column max)`.

        Returns
        -------
        None
        """

        raise NotImplementedError

class MonochromaticRemap(RemapFunction):
    """
    Abstract monochromatic remap class.
    """

    _name = '_Monochromatic'
    __slots__ = ('_override_name', '_bit_depth', '_dimension', '_max_output_value')
    _allowed_dimension = {0, }

    def __init__(
            self,
            override_name: Optional[str] = None,
            bit_depth: int = 8,
            max_output_value: Optional[int] = None):
        r"""

        Parameters
        ----------
        override_name : None|str
            Override name for a specific class instance
        bit_depth : int
        max_output_value : None|int
            The maximum output value. If provided, this must be in the interval
            :math:`[0, 2^{bit\_depth}]`
        """

        self._max_output_value = None
        RemapFunction.__init__(self, override_name=override_name, bit_depth=bit_depth, dimension=0)
        self._set_max_output_value(max_output_value)

    @property
    def max_output_value(self) -> int:
        """
        int: The (read-only) maximum output value size.
        """

        return self._max_output_value

    def _set_max_output_value(self, value: Optional[int]):
        max_possible = numpy.iinfo(self.output_dtype).max
        if value is None:
            value = max_possible
        else:
            value = int(value)

        if 0 < value <= max_possible:
            self._max_output_value = value
        else:
            raise ValueError(
                'the max_output_value must be between 0 and {}, '
                'got {}'.format(max_possible, value))

    def raw_call(self, data, **kwargs):
        raise NotImplementedError

    def calculate_global_parameters_from_reader(self, reader, index=0, pixel_bounds=None):
        raise NotImplementedError

class Logarithmic(MonochromaticRemap):
    """
    A logarithmic remap function.
    """

    __slots__ = ('_override_name', '_bit_depth', '_dimension', '_max_value', '_min_value')
    _name = 'log'

    def __init__(
            self,
            override_name: Optional[str] = None,
            bit_depth: int = 8,
            max_output_value: Optional[int] = None,
            min_value: Optional[float] = None,
            max_value: Optional[float] = None):
        """

        Parameters
        ----------
        override_name : None|str
            Override name for a specific class instance
        bit_depth : int
        min_value : None|float
        max_value : None|float
        """

        MonochromaticRemap.__init__(self, override_name=override_name, bit_depth=bit_depth, max_output_value=max_output_value)

        if min_value is not None:
            min_value = float(min_value)
        if max_value is not None:
            max_value = float(max_value)
        self._min_value = min_value
        self._max_value = max_value

    @property
    def min_value(self) -> Optional[float]:
        """
        None|float: The minimum value allowed (clipped below this)
        """
        return self._min_value

    @min_value.setter
    def min_value(self, value: Optional[float]):
        if value is None:
            self._min_value = None
        else:
            value = float(value)
            if not numpy.isfinite(value):
                raise ValueError('Got unsupported minimum value `{}`'.format(value))
            self._min_value = value

    @property
    def max_value(self) -> Optional[float]:
        """
        None|float:  The minimum value allowed (clipped above this)
        """

        return self._max_value

    @max_value.setter
    def max_value(self, value: Optional[float]):
        if value is None:
            self._max_value = None
        else:
            value = float(value)
            if not numpy.isfinite(value):
                raise ValueError('Got unsupported maximum value `{}`'.format(value))
            self._max_value = value

    @property
    def are_global_parameters_set(self) -> bool:
        """
        bool: Are (all) global parameters used for applying this remap function
        set? In this case, this is the `min_value` and `max_value` properties.
        """

        return self._min_value is not None and self._max_value is not None

    def _get_extrema(
            self,
            amplitude: numpy.ndarray,
            min_value: Optional[float],
            max_value: Optional[float]) -> Tuple[float, float]:
        if min_value is not None:
            min_value = float(min_value)
        if max_value is not None:
            max_value = float(max_value)

        if min_value is None:
            min_value = self.min_value
        if min_value is None:
            min_value = numpy.min(amplitude)

        if max_value is None:
            max_value = self.max_value
        if max_value is None:
            max_value = numpy.max(amplitude)

        # sanity check
        if min_value > max_value:
            min_value, max_value = max_value, min_value

        return min_value, max_value

    def raw_call(
            self,
            data: numpy.ndarray,
            min_value: Optional[float] = None,
            max_value: Optional[float] = None) -> numpy.ndarray:
        """
        This performs the mapping from input data to output floating point
        version, this is directly used by the :func:`call` method.

        Parameters
        ----------
        data : numpy.ndarray
            The (presumably) complex data to remap.
        min_value : None|float
            A minimum threshold, or pre-calculated data minimum, for consistent
            global use. The order of preference is the value provided here, the
            class `min_value` property value, then calculated from the present
            sample.
        max_value : None|float
            A maximum value threshold, or pre-calculated data maximum, for consistent
            global use. The order of preference is the value provided here, the
            class `max_value` property value, then calculated from the present
            sample.

        Returns
        -------
        numpy.ndarray
        """

        amplitude = numpy.abs(data)

        out = numpy.empty(amplitude.shape, dtype='float64')
        max_output_value = self.max_output_value

        finite_mask = numpy.isfinite(amplitude)
        zero_mask = (amplitude == 0)
        use_mask = finite_mask & (~zero_mask)

        out[~finite_mask] = max_output_value
        out[zero_mask] = 0

        if numpy.any(use_mask):
            temp_data = amplitude[use_mask]
            min_value, max_value = self._get_extrema(temp_data, min_value, max_value)

            if min_value == max_value:
                out[use_mask] = 0
            else:
                #temp_data = (numpy.clip(temp_data, min_value, max_value) - min_value)/(max_value - min_value) + 1
                #out[use_mask] = max_output_value*numpy.log10(temp_data)
                #out[use_mask] = 20*numpy.log10(temp_data)
                #for x in range(5):
                #    print(temp_data[x])
                #    print(out[use_mask][x])
                temp_data = (10 * temp_data) / numpy.mean(temp_data)
                rcent = 10 * numpy.log10(numpy.sum(numpy.square(temp_data)) / temp_data.size)
                temp_data = temp_data + max(1 - numpy.min(temp_data), 0)
                temp_data = 20 * numpy.log10(temp_data)
                span_db = 50
                disp_min = max(numpy.min(temp_data), rcent - span_db/2)
                disp_max = min(numpy.max(temp_data), rcent + span_db/2)
                #out[use_mask] = numpy.uint8(255 * (temp_data - disp_min) / (disp_max - disp_min))
                out[use_mask] = 255 * (temp_data - disp_min) / (disp_max - disp_min)
        return out

        '''
        x = abs(single(x));
        x = 10*x./mean(x(:)); % Fixes very small data (<< 1)
        rcent  = 10*log10(sum(x(:).^2)/numel(x));
        % Make minimum at least one
        x = x + max(1 - min(x(:)),0);
        x = 20*log10(x);

        span_db = 50;
        disp_min = max(min(x(:)),rcent - span_db/2);
        disp_max = min(max(x(:)),rcent + span_db/2);

        out = uint8(255*(x-disp_min)/(disp_max-disp_min));
        '''


    def call(
            self,
            data: numpy.ndarray,
            min_value: Optional[float] = None,
            max_value: Optional[float] = None) -> numpy.ndarray:
        """
        This performs the mapping from input data to output discrete version.

        This method os directly called by the :func:`__call__` method, so the
        class instance (once constructed) is itself callable, as follows:

        >>> remap = Logarithmic()
        >>> discrete_data = remap(data, min_value=1.8, max_value=1.2e6)

        Parameters
        ----------
        data : numpy.ndarray
            The (presumably) complex data to remap.
        min_value : None|float
            A minimum threshold, or pre-calculated data minimum, for consistent
            global use. The order of preference is the value provided here, the
            class `min_value` property value, then calculated from the present
            sample.
        max_value : None|float
            A maximum value threshold, or pre-calculated data maximum, for consistent
            global use. The order of preference is the value provided here, the
            class `max_value` property value, then calculated from the present
            sample.

        Returns
        -------
        numpy.ndarray
        """

        return clip_cast(
            self.raw_call(data, min_value=min_value, max_value=max_value),
            dtype=self.output_dtype, min_value=0, max_value=self.max_output_value)

    def calculate_global_parameters_from_reader(
            self,
            reader: SICDTypeReader,
            index: int = 0,
            pixel_bounds: Union[None, tuple, list, numpy.ndarray] = None) -> None:
        pixel_bounds = self._validate_pixel_bounds(reader, index, pixel_bounds)
        self.min_value, self.max_value = get_data_extrema(
            pixel_bounds, reader, index, 25*1024*1024, percentile=None)