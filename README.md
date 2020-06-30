SarPy_Apps
==========
This provides a set of GUI tools based on tkinter for visualizing and interacting 
with SAR imagery and related data.

Origins
-------
This was developed to enable simple prototyping of graphical user interfaces useful 
in conjunction with SarPy project, and was based on and motivated by the set of MATLAB 
tools developed by NGA/NRL referred to as TASER. This effort was developed at the 
National Geospatial-Intelligence Agency (NGA). The software use, modification, and 
distribution rights are stipulated within the MIT license.

Dependencies
------------
The core library functionality depends on the `sarpy` and `tk_builder` projects. 
These will be available in PyPI in early July 2020.

Python 2.7
----------
The development here has been geared towards Python 3.6 and above, but efforts have
been made towards remaining compatible with Python 2.7. If you are using the library
from Python 2.7, there is an additional dependencies for the `typing` package. A 
dependency for the `tk_builder` project (in turn for the `tkinter` package) is the 
`future` (not to be confused with the more widely known `futures`) package.
