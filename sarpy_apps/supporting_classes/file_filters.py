"""
Collection of convenience tkinter format file filter definitions. Extends the
similar module found in tk_builder.
"""

__author__ = "Thomas McCullough"
__classification__ = "UNCLASSIFIED"

from tk_builder.file_filters import *

# filter element
sar_images = ('SAR Images', nitf_files[1] + hdf5_files[1] + tiff_files[1])

# filter collection
common_use_collection = [sar_images, nitf_files, hdf5_files, tiff_files, all_files]
nitf_preferred_collection = [nitf_files, sar_images, hdf5_files, tiff_files, all_files]
