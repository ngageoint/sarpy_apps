import os
import sarpy.io.complex as sarpy_complex
import matplotlib.pyplot as plt
import sarpy.visualization.remap as remap
from sarpy.processing.aperture_filter import ApertureFilter

fname = os.path.expanduser("~/sicd_example_RMA_RGZERO_RE16I_IM16I.nitf")
reader = sarpy_complex.open(fname)

y_start = 5100
y_end = 5500
x_start = 5200
x_end = 5600

complex_data = reader[y_start:y_end, x_start:x_end]
complex_display = remap.density(complex_data)

print("Image subsection")
plt.imshow(complex_display)
plt.show()

aperture_filter = ApertureFilter(reader, dimension=0)
aperture_filter.set_sub_image_bounds((y_start, y_end), (x_start, x_end))
aperture_filter.apply_deweighting = False
phase_data = aperture_filter.normalized_phase_history
phase_display = remap.density(phase_data)
filtered_image = aperture_filter[:, 0:100]
filtered_display = remap.density(filtered_image)

print("phase data, no deweighting, dim=0")
plt.imshow(phase_display)
plt.show()

print("filtered image")
plt.imshow(filtered_display)
plt.show()

aperture_filter = ApertureFilter(reader, dimension=0)
aperture_filter.set_sub_image_bounds((y_start, y_end), (x_start, x_end))
aperture_filter.apply_deweighting = True
phase_data = aperture_filter.normalized_phase_history
phase_display = remap.density(phase_data)
filtered_image = aperture_filter[:, 0:100]
filtered_display = remap.density(filtered_image)

print("phase data, with deweighting, dim=0")
plt.imshow(phase_display)
plt.show()

print("filtered image")
plt.imshow(filtered_display)
plt.show()

aperture_filter = ApertureFilter(reader, dimension=1)
aperture_filter.set_sub_image_bounds((y_start, y_end), (x_start, x_end))
aperture_filter.apply_deweighting = False
phase_data = aperture_filter.normalized_phase_history
phase_display = remap.density(phase_data)
filtered_image = aperture_filter[:, 0:100]
filtered_display = remap.density(filtered_image)

print("phase data, no deweighting, dim=1")
plt.imshow(phase_display)
plt.show()

print("filtered image")
plt.imshow(filtered_display)
plt.show()

aperture_filter = ApertureFilter(reader, dimension=1)
aperture_filter.set_sub_image_bounds((y_start, y_end), (x_start, x_end))
aperture_filter.apply_deweighting = True
phase_data = aperture_filter.normalized_phase_history
phase_display = remap.density(phase_data)
filtered_image = aperture_filter[:, 0:100]
filtered_display = remap.density(filtered_image)

print("phase data, with deweighting, dim=1")
plt.imshow(phase_display)
plt.show()

print("filtered image")
plt.imshow(filtered_display)
plt.show()
