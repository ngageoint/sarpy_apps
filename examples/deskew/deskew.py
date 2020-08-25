import os
import sarpy.io.complex as sarpy_complex
import matplotlib.pyplot as plt
import sarpy.visualization.remap as remap
from sarpy.processing.aperture_filter import ApertureFilter

dim = 0

fname = os.path.expanduser("~/sicd_example_RMA_RGZERO_RE16I_IM16I.nitf")
reader = sarpy_complex.open(fname)
selected_region_image_coords = [3522.497816593887, 5701.362445414848, 3909.85152838428, 6088.716157205241]
complex_data = reader[3522:3900, 5701:6088]
complex_display = remap.density(complex_data)


aperture_filter = ApertureFilter(reader, dimension=dim)
aperture_filter.apply_deweighting = True
aperture_filter.set_sub_image_bounds((3522, 3900), (5701, 6088))
filtered_image = aperture_filter[:]
complex_image = aperture_filter.normalized_phase_history
complex_display = remap.density(complex_image)
filtered_display = remap.density(filtered_image)


plt.imshow(complex_display)
plt.show()
