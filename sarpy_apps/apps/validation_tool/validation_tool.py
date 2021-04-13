# -*- coding: utf-8 -*-
"""
This module provides a tool for doing some basic validation for a SICD file.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"


#   1.) Log location - When the image is selected, prompt for a log destination.
#       Drop other file handler from validation logger, and add this handler.

# logger = logging.getLogger("validation")
# handler = logging.FileHandler("output.log")  # save a reference to this, for removal
# logger.addHandler(handler)
##
# logger.removeHandler(handler)

#   2.) Perform sicd.is_valid(recursive=True, stack=True) (or False, try them out)

#   3.) the contents of fs_vis_test...MATLAB_SAR/IO/sicd/validation/fs_vis_test.m line 1625

#   4.) Create a kmz overlay - can we automatically open somehow? line 1630

#   5.) How to do sign verification? line 1656

#   6.) Frequency support analysis? line 1677. Does it really need to be "full"?

#   7.) Noise comparison? line 1914 - Just open rcs tool.

import sarpy.io.complex as sarpy_io

ro = sarpy_io.open(img_file)  # img_file is the input NITF
# ro.sicd_meta could be a single sicd structure, or a tuple of them (maybe with only one element)
sicd_meta = ro.get_sicds_as_tuple()[0]  # this will definitely be the first

# the coordinates are read from a csv file line - target
obj_lat = float(target[13])
obj_lon = float(target[14])
obj_hae = float(target[15])
find_pt = [obj_lat, obj_lon, obj_hae]

# to call right from the sicd structure - equivalent to the below
im_row, im_col = sicd_meta.project_ground_to_image_geo([obj_lat, obj_lon, obj_hae], ordering='latlong')

# to call using the point_projection module
import sarpy.geometry.point_projection as sarpy_geo
im_row, im_col = sarpy_geo.ground_to_image_geo(find_pt, sicd_meta, ordering='latlong')


