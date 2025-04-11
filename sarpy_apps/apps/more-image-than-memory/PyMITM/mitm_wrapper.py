from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QMainWindow, QApplication
from PyMITM import mitm_controller
from PyMITM.utils import styleloader
from PyMITM.ui_wrapper import Ui_MainWindow
from PySide6.QtGui import QAction
import sys, subprocess, os

class Wrapper_Controller:
    '''
    A Wrapper class for MITM. Provides an interface between MITM and subapplications

    Attributes
    ----------
    model : ExampleApp_Model
        container for application logic
    viewer : ExampleApp_Viewer
        container for application GUI
    mitm_controller : mitm_controller.Controller
        main MITM application
    apps : dict{ str : AbstractApp }
        dictionary of subapplications. Lookup is by application name

    Methods
    -------
    setup_apps(apps)
        setup UI and data for each app in list

    '''

    def __init__(self,  apps=[]):
        '''
        Constructs necessary attributes for the Wrapper_Controller object

        Parameters
        -----------
        self : object
            The class instance.
        apps : list
            list of MITM subapplications to set up

        '''
        self.apps = {}
        self.mitm_controller = mitm_controller.Controller(sys.argv)
        self.model = Wrapper_Model()
        self.viewer = Wrapper_Viewer(self.mitm_controller.viewer)
        self.viewer.appearance_changed.connect(self.mitm_controller.viewer.change_appearance)
        self.viewer.window_closing.connect(self.mitm_controller.viewer.close)
        self.viewer.helpAction.triggered.connect(self.model.open_help_pdf)
        self.setup_apps(apps)

    def setup_apps(self, apps):  
        '''
        Setup UI and data for each app in list. 

        Creates a new entry in Tools menu for each app.
        Gives each app a copy of mitm_controller and apps dict.
        Obtains reference to each app's QDockWidget.
        Sets up connections to handle when MITM appearance changes and to cleanup app on exit.
        Sets up connections to hide and show app.

        Parameters
        -----------
        self : object
            The class instance.
        apps : list
            list of MITM subapplications to set up

        Returns
        -------
        None

        '''
        self.apps = {}

        for app in apps:
            # update dictionaries
            self.apps[app.get_name()] = app

            # give app info
            app.set_mitm_controller(self.mitm_controller)
            app.set_app_dict(self.apps)

            # setup toolbar action
            self.viewer.add_tools_action(app.get_name())

            #setup dock widget
            self.viewer.add_dock_widget(app.get_name(), app.get_dock_widget(), app.get_preferred_area())

            # connections
            self.viewer.appearance_changed.connect(app.change_appearance)
            self.viewer.window_closing.connect(app.exit_cleanup)
            self.viewer.connect_app_to_toolbar(app.get_name())

class Wrapper_Viewer(QMainWindow, Ui_MainWindow):
    '''
    The Viewer class for Wrapper.

    Attributes
    ----------
    toolsActions : dict{ str : QAction }
        dictionary of app name to QAction toggling the app's visiblity 
    dockWidgets : dict{ str : QDockWidget }
        dictionary of app name to QDockWidget providing app GUI

    Methods
    -------
    add_tools_action(name)
        set up a new QAction and add it to the Tools menu
    add_dock_widget(name, dockWidget, preferredArea)
        set up a new QDockWidget and add it to the MainWindow in its preferredArea
    connect_app_to_toolbar(name)
        connect a QDockWidget's visibility to the QAction's checkbox and vice versa
    show_or_hide_app(checked)
        changes application visibility to follow whether relevant QAction is checked
    uncheck_tool_application()
        unchecks relevant QAction when user closes QDockWidget

    '''
    appearance_changed = Signal(bool)
    window_closing = Signal()

    def __init__(self, centralWidget, parent=None):
        '''
        Constructs necessary attributes for the Wrapper_Viewer object

        Parameters
        -----------
        self : object
            The class instance.
        centralWidget : mitm_viewer.Viewer
           MITM Viewer object to set as Wrapper's central widget

        '''
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.setDockOptions(QMainWindow.AnimatedDocks|QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks)
        self.setWindowTitle("MITM Viewer")
        self.setCentralWidget(centralWidget)

        # start in light mode
        self.change_appearance(False)
        darkAction = QAction("Dark Mode", self)
        darkAction.setEnabled(True)
        darkAction.setCheckable(True)

        # help menu button
        self.helpAction = QAction("Help", self)
        self.helpAction.setEnabled(True)
        self.helpAction.setCheckable(False)

        self.menuMenu_Button.addAction(darkAction)
        self.menuMenu_Button.addAction(self.helpAction)
        darkAction.toggled.connect(self.change_appearance)  

        self.toolsActions = {}
        self.dockWidgets = {}

    def change_appearance(self, checked):
        '''
        Change the appearance of the app from light to dark or vice versa

        Parameters
        -----------
        self : object
            The class instance.
        checked : bool
            True if darkMode, else False

        Returns
        -------
        None

        '''
        if checked:
            styleloader.dark(QApplication.instance())
        else:
            styleloader.light(QApplication.instance())
        self.appearance_changed.emit(checked)

    def add_tools_action(self, name):
        '''
        Set up a new QAction and add it to the Tools menu

        Parameters
        -----------
        self : object
            The class instance.
        name : str
            name of app

        Returns
        -------
        None

        '''
        self.toolsActions[name] = (QAction(name, self))
        self.toolsActions[name].setCheckable(True)
        self.toolsActions[name].setEnabled(True)
        self.menuTools.addAction(self.toolsActions[name])

    def add_dock_widget(self, name, dockWidget, preferredArea):
        '''
        Set up a new QDockWidget and add it to the MainWindow in its preferredArea

        Parameters
        -----------
        self : object
            The class instance.
        name : str
            name of app
        dockWidget : QDockWidget
            app's QDockWidget
        preferredArea : Qt.DockWidgetAreas
            area to add app's QDockWidget

        Returns
        -------
        None

        '''
        self.dockWidgets[name] = dockWidget
        self.dockWidgets[name].setVisible(False)
        if self.dockWidgets[name].windowTitle() == "":
            self.dockWidgets[name].setWindowTitle(name)
        self.addDockWidget(preferredArea, self.dockWidgets[name])   
    
    def connect_app_to_toolbar(self, name):
        '''
        Connect a QDockWidget's visibility to the QAction's checkbox and vice versa

        Parameters
        -----------
        self : object
            The class instance.
        name : str
            name of app

        Returns
        -------
        None

        '''
        self.toolsActions[name].toggled.connect(self.show_or_hide_app)
        self.dockWidgets[name].visibilityChanged.connect(self.uncheck_tools_action)

    def show_or_hide_app(self, checked): 
        '''
        Changes application visibility to follow whether relevant QAction is checked

        Parameters
        -----------
        self : object
            The class instance.
        checked : bool
            state of sending QAction

        Returns
        -------
        None

        '''
        sender = self.sender()
        if sender:
            dock = self.dockWidgets[sender.text()]
            dock.setVisible(checked)
            if(checked and dock.isFloating()):
                dock.raise_()

    def uncheck_tools_action(self, checked):
        '''
        Unchecks relevant QAction when user closes QDockWidget

        Parameters
        -----------
        self : object
            The class instance.
        checked : bool
            whether or not sending dock is visible

        Returns
        -------
        None

        '''
        dock = self.sender()
        if dock:
            name = [key for key, value in self.dockWidgets.items() if value == dock][0]
            self.toolsActions[name].setChecked(checked)
       
    def closeEvent(self, event):
        '''
        Emits a signal upon application close to enable sub-applications to respond

        Parameters
        -----------
        self : object
            The class instance.
        event : QCloseEvent
            Qt close event object

        Returns
        -------
        None

        '''
        self.window_closing.emit()
        super().closeEvent(event)

class Wrapper_Model:
    '''
    The Model class for Wrapper.

    Attributes
    ----------
    pdf_path : os.path
        Path to location of PDF file containing help documentation

    Methods
    -------
    open_help_pdf()
        open the help pdf in the default pdf browser
    
    '''

    def __init__(self):
        '''
        Constructs necessary attributes for the Wrapper_Viewer object

        Parameters
        -----------
        self : object
            The class instance.

        '''
        self.pdf_path = styleloader.resource_path('./../resources/MITM-SoftwareUserManual.pdf')

    def open_help_pdf(self):
        '''
        Opens help pdf in default pdf viewer

        Parameters
        -----------
        self : object
            The class instance.

        Returns
        -------
        None

        '''
        subprocess.Popen([self.pdf_path],shell=True)