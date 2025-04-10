# MIT License
#
# Copyright (c) 2017 Gerard Marull-Paretas <gerardmarull@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This is a slightly modified version of qtmodern/style.py to point to a custom QSS file

from os.path import join, dirname, abspath
import sys

from qtpy.QtGui import QPalette, QColor

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return join(sys._MEIPASS, dirname(abspath(__file__)), relative_path)
    return join(dirname(abspath(__file__)), relative_path)

_STYLESHEET = resource_path('./../resources/style.qss')
""" str: Main stylesheet. """


def _apply_base_theme(app):
    """ Apply base theme to the application.

        Args:
            app (QApplication): QApplication instance.
    """

    app.setStyle('Fusion')

    with open(_STYLESHEET) as stylesheet:
        app.setStyleSheet(stylesheet.read())


def dark(app):
    """ Apply Dark Theme to the Qt application instance.

        Args:
            app (QApplication): QApplication instance.
    """

    darkPalette = QPalette()

    # base
    darkPalette.setColor(QPalette.WindowText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.Light, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Midlight, QColor(90, 90, 90))
    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Text, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.BrightText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.ButtonText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.HighlightedText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Link, QColor(56, 252, 196))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipText, QColor(180, 180, 180))

    # disabled
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Text,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                         QColor(80, 80, 80))
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                         QColor(127, 127, 127))

    app.setPalette(darkPalette)
    
    _apply_base_theme(app)


def light(app):
    """ Apply Light Theme to the Qt application instance.

        Args:
            app (QApplication): QApplication instance.
    """

    lightPalette = QPalette()

    # base
    lightPalette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Button, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Light, QColor(180, 180, 180))
    lightPalette.setColor(QPalette.Midlight, QColor(200, 200, 200))
    lightPalette.setColor(QPalette.Dark, QColor(225, 225, 225))
    lightPalette.setColor(QPalette.Text, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.BrightText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Base, QColor(237, 237, 237))
    lightPalette.setColor(QPalette.Window, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    lightPalette.setColor(QPalette.Highlight, QColor(76, 163, 224))
    lightPalette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Link, QColor(0, 162, 232))
    lightPalette.setColor(QPalette.AlternateBase, QColor(225, 225, 225))
    lightPalette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))

    # disabled
    lightPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                         QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.Text,
                         QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                         QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                         QColor(190, 190, 190))
    lightPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                         QColor(115, 115, 115))

    app.setPalette(lightPalette)

    _apply_base_theme(app)
    
