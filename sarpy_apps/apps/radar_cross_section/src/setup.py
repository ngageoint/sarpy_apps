from distutils.core import setup

setup(
    name="python-rcs",
    version="1.0",
    description="Python Radar Cross Section Tool",
    author="N-ASK Incorporated",
    author_email="parkison-alex@n-ask.com",
    url="local repo",
    packages=["PyRCS"],
    py_modules=["rcs_model", "rcs_controller", "rcs_viewer", "ui_rcs_tool"],
)
