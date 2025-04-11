import sys

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication
from PyMITM.mitm_wrapper import Wrapper_Controller
from PyRCS.rcs_controller import Controller

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    controller = Wrapper_Controller([Controller(1)])
    window = controller.viewer
    window.show()

    result = app.exec()
    sys.exit(result)
