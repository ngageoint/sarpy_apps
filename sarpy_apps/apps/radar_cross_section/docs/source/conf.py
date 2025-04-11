# Configuration file for the Sphinx documentation builder.
import os
import sys
sys.path.insert(0, os.path.abspath('../src/PyRCS/'))
# -- Project information -----------------------------------------------------
project = 'RCS Tool'
author = 'Alex Parkison'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints'
]

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'

# -- Other Settings ----------------------------------------------------------
autodoc_member_order = 'bysource'
autoclass_content = 'both'