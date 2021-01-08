"""
Collection of convenience tkinter format file filter definitions. Extends the
similar module found in tk_builder.
"""

__author__ = "Thomas McCullough"
__classification__ = "UNCLASSIFIED"

from tk_builder.file_filters import *


# sar type images
sar_images = ('SAR Images', nitf_files[1] + hdf5_files[1] + tiff_files[1])

common_use_filter = [sar_images, nitf_files, hdf5_files, tiff_files, all_files]
nitf_preferred_filter = [nitf_files, sar_images, hdf5_files, tiff_files, all_files]
