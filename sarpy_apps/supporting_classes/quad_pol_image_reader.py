from tk_builder.image_readers.image_reader import ImageReader
import sarpy.io.complex as sarpy_complex
from sarpy.io.general.base import BaseReader
import sarpy.visualization.remap as remap
import numpy


# TODO use properties for remap, and SICD
class QuadPolImageReader(ImageReader):
    base_readers = []           # type: [BaseReader]
    remap_type = "density"

    def __init__(self,
                 fnames,            # type: [str]
                 ):
        self.base_readers = []
        self.base_readers.append(sarpy_complex.open(fnames[0]))
        self.base_readers.append(sarpy_complex.open(fnames[1]))
        self.base_readers.append(sarpy_complex.open(fnames[2]))
        self.base_readers.append(sarpy_complex.open(fnames[3]))

        self.full_image_nx = self.base_readers[0].sicd_meta.ImageData.FullImage.NumCols
        self.full_image_ny = self.base_readers[0].sicd_meta.ImageData.FullImage.NumRows

    def __getitem__(self, key):
        cdata_1 = self.base_readers[0][key]
        cdata_2 = self.base_readers[1][key]
        cdata_3 = self.base_readers[2][key]
        cdata_4 = self.base_readers[3][key]

        decimated_red = self.remap_complex_data(cdata_1)
        decimated_blue = (self.remap_complex_data(cdata_2) + self.remap_complex_data(cdata_3))/2
        decimated_green = self.remap_complex_data(cdata_4)

        rgb_image = numpy.zeros((decimated_red.shape[0], decimated_red.shape[1], 3), dtype=decimated_red.dtype)
        rgb_image[:, :, 0] = decimated_red
        rgb_image[:, :, 1] = decimated_blue
        rgb_image[:, :, 2] = decimated_green

        return rgb_image

    # TODO get rid of strings, make these methods
    def remap_complex_data(self,
                           complex_data,    # type: numpy.ndarray
                           ):
        if self.remap_type == 'density':
            pix = remap.density(complex_data)
        elif self.remap_type == 'brighter':
            pix = remap.brighter(complex_data)
        elif self.remap_type == 'darker':
            pix = remap.darker(complex_data)
        elif self.remap_type == 'highcontrast':
            pix = remap.highcontrast(complex_data)
        elif self.remap_type == 'linear':
            pix = remap.linear(complex_data)
        elif self.remap_type == 'log':
            pix = remap.log(complex_data)
        elif self.remap_type == 'pedf':
            pix = remap.pedf(complex_data)
        elif self.remap_type == 'nrl':
            pix = remap.nrl(complex_data)
        else:
            raise ValueError('Got unexpected remap_type {}'.format(self.remap_type))
        return pix

    def set_remap_type(self,
                       remap_type,          # type: str
                       ):
        self.remap_type = remap_type
