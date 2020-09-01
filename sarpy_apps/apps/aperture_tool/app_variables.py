from typing import Tuple

import numpy
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader
from tk_builder.base_elements import TypedDescriptor, IntegerTupleDescriptor, \
    IntegerDescriptor, BooleanDescriptor, FloatDescriptor, StringDescriptor
from sarpy.processing.aperture_filter import ApertureFilter



class AppVariables(object):
    sicd_reader_object = TypedDescriptor(
        'sicd_reader_object', ComplexImageReader,
        docstring='')  # type: ComplexImageReader
    aperture_filter = TypedDescriptor('aperture_filter',
                                      ApertureFilter,
                                      docstring='')  # type: ApertureFilter
    fft_complex_data = TypedDescriptor(
        'fft_complex_data', numpy.ndarray,
        docstring='')  # type: numpy.ndarray
    selected_region_complex_data = TypedDescriptor(
        'selected_region_complex_data', numpy.ndarray,
        docstring='')  # type: numpy.ndarray
    # animation properties
    animation_n_frames = IntegerDescriptor(
        'animation_n_frames', docstring='')  # type: int
    animation_aperture_faction = FloatDescriptor(
        'animation_aperture_faction', docstring='')  # type: float
    animation_cycle_continuously = BooleanDescriptor(
        'animation_cycle_continuously', default_value=False, docstring='')  # type: bool
    animation_current_position = IntegerDescriptor(
        'animation_current_position', default_value=0, docstring='')  # type: int
    animation_stop_pressed = BooleanDescriptor(
        'animation_stop_pressed', default_value=False, docstring='')  # type: bool
    animation_min_aperture_percent = FloatDescriptor(
        'animation_min_aperture_percent', docstring='')  # type: float
    animation_max_aperture_percent = FloatDescriptor(
        'animation_max_aperture_percent', docstring='')  # type: float

    def __init__(self):
        # TODO: what are the details here? Use a descriptor as above?
        self.selected_region = None     # type: tuple
