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


