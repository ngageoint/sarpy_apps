import os
import numpy
import sarpy.io.complex as sarpy_complex
import matplotlib.pyplot as plt
from scipy.fftpack import fft2, ifft2, fftshift, ifftshift
import sarpy.visualization.remap as remap
from sarpy.processing.normalize_sicd import DeskewCalculator
import sarpy.processing.normalize_sicd as normalize_sicd


def get_fft_complex_data(ro,  # type: BaseReader
                         cdata,  # type: numpy.ndarray
                         ):
    if ro.sicd_meta.Grid.Col.Sgn > 0 and ro.sicd_meta.Grid.Row.Sgn > 0:
        # use fft2 to go from image to spatial freq
        ft_cdata = fft2(cdata)
        ft_cdata = fftshift(ft_cdata)
    else:
        # flip using ifft2
        ft_cdata = ifft2(cdata)
        ft_cdata = ifftshift(ft_cdata)

    return ft_cdata

dim = 1

fname = os.path.expanduser("~/sicd_example_RMA_RGZERO_RE16I_IM16I.nitf")
reader = sarpy_complex.open(fname)
selected_region_image_coords = [3522.497816593887, 5701.362445414848, 3909.85152838428, 6088.716157205241]
complex_data = reader[3522:3900, 5701:6088]
complex_display = remap.density(complex_data)

deskew_calc = DeskewCalculator(reader, dim)
deskewed = deskew_calc[3522:3900, 5701:6088]
deskewed_display = remap.density(deskewed)


DeltaKCOAPoly, rg_coords_m, az_coords_m, fft_sgn = normalize_sicd.deskewparams(reader.sicd_meta, dim)

fft_complex_data = get_fft_complex_data(reader, deskewed)
fft_display_data = remap.density(fft_complex_data)

plt.imshow(fft_display_data)
plt.show()
