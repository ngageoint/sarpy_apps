from PySide6.QtCore import (
    Qt,
    QDir,
    QMetaObject,
    Signal,
    QRect,
    QThread,
    QObject,
    QUrl,
    QFileInfo,
    QTimer
)
from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QWidget,
    QPushButton,
    QProgressBar,
    QFileDialog,
    QVBoxLayout,
    QSizePolicy,
    QDialogButtonBox,
    QSplitter,
    QLabel,
    QComboBox,
    QToolButton,
    QLineEdit,
    QListView,
    QFrame,
    QFileDialog,
    QStyle,
    QMessageBox,
    QApplication
)
from PySide6.QtGui import (
    QGuiApplication,
    QAction,
    QBrush,
    QColor,
    QIcon,
    QFont,
    QMouseEvent,
)
from PySide6.QtUiTools import QUiLoader
import pyqtgraph as pg
import numpy as np
import math
import os

from sarpy.visualization import remap

from PyMITM.ui_mitm_mainwindow import Ui_MainWindow
from PyMITM.ui_plot_widget_dock import Ui_DockWidget
from PyMITM.ui_metaicon_widget import Ui_MetaIcon
from PyMITM.utils.log_remap import Logarithmic
from PyMITM.utils.tooltips import ToolTips

import sys
import qdarkstyle.colorsystem 

class Viewer(QMainWindow, Ui_MainWindow):
    openMetaIcon       = Signal(str)
    fileDropped        = Signal(str, object)
    doubleClicked      = Signal(str, object)

    widget_creation_signal = Signal(object, name='widget_creation_signal')
    widget_interacted_signal = Signal(object, name='widget_interacted_signal')
    widget_changed_signal = Signal(object, name='widget_changed_signal')
    widget_closed_signal = Signal(object, name='widget_closed_signal')

    requestAspectRatio = Signal(object)
    windowClosed       = Signal(list, list)
    applicationStarted = Signal()

    def __init__(self, parent=None, fileopen=None):
        """
        Initialize the main viewer application window.

        Creates the main application window with dockable plot widgets, file navigation,
        and meta-icon display capabilities. Sets up the UI components, signal connections,
        and event handling for the entire application.

        Features include:
        - Multiple dockable plot widgets for viewing different images simultaneously
        - File browser with custom navigation controls
        - Directory breadcrumb navigation
        - Meta-icon display for NITF metadata visualization
        - Dark/light mode support
        - Drag and drop file loading
        - File open dialog integration

        The constructor displays a temporary notification during initialization and
        sets up the initial application state, including loading a file if specified
        via command line.

        Parameters
        ----------
        self : object
            The class instance.
        parent : QWidget or None, optional
            The parent widget. Default is None.
        fileopen : str or None, optional
            Path to a file to open on startup. Default is None.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        msgbox = self.notify_user_application_is_starting()

        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.remap_function = remap.Density()
        
        self.resize(1200, 700)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        self.plotWidgets = []
        self.directoryButtons = []
        self.darkMode = False
        self._currentPlotWidget = None
        
        self.fileopen = fileopen
        if(self.fileopen and os.path.isfile(self.fileopen)):
            self.currentDirectoryPath = os.path.dirname(self.fileopen)    
        else:
            self.currentDirectoryPath = QDir.currentPath()
        
        self.fileDialog = CustomFileDialog(self.dockWidgetContents_2, Qt.Widget)
        self.fileDialog.setDirectory(self.currentDirectoryPath)
        self.fileDialog.setWindowFlags(self.fileDialog.windowFlags() & ~Qt.Dialog)
        self.fileDialog.setViewMode(QFileDialog.Detail)
        self.fileDialog.setFileMode(QFileDialog.ExistingFile) # prevents selecting dirs or > 1 file
        self.fileDialog.setObjectName(u"fileDialog")
        self.fileDialog.setAcceptDrops(True)
        self.fileDialog.setProperty("showDropIndicator", True)
        self.fileDialog.accepted.connect(lambda: self.double_clicked_new_plot(self.fileDialog.selectedFiles()[0]))

        self.gridLayout_2.addWidget(self.fileDialog, 0, 0, 1, 1)

        self._add_directory_buttons(self.fileDialog.directory().path().split('/'))

        self.widget_interacted_signal.connect(self.handle_widget_interaction)
        self.widget_creation_signal.connect(self.handle_widget_interaction)
        self.widget_closed_signal.connect(self.check_if_current_widget_closed)

        # Build the metaicon
        self.metaicon_widget = MetaIconWidget()

        # Hide unused widgets
        self.plotDockWidgetLeft.hide()
        self.plotDockWidgetRight.hide()
        self.metaIconDock.hide()
        self.controlsWidget.hide()
        self.line.hide()
        self.fileLineEdit.hide()

        # add any tooltips
        self.directoryWidget.setToolTip(ToolTips.directories_buttons())
        self.newPlotButton.setToolTip(ToolTips.add_plot_button())

        # startup signal 
        self.appStarted = False
        QApplication.instance().applicationStateChanged.connect(self.handle_app_state_changed)
        self.applicationStarted.connect(self.create_plot_on_startup)

        msgbox.hide()
    
    def notify_user_application_is_starting(self):
        """
        Display a message box informing the user that the application is starting.
        
        Creates and configures a custom message box with a title indicating that
        the MITM Viewer is starting up.
        
        Parameters
        ----------
        self : object
            The class instance.
        
        Returns
        -------
        CustomMessageBox
            The displayed message box instance that can be referenced later to
            hide or close the notification when initialization completes.
        """

        titlestr = "   Starting MITM Viewer. Please wait..."
        msgBox = CustomMessageBox()
        msgBox.setWindowModality(Qt.WindowModal)
        msgBox.setWindowTitle(titlestr)
        msgBox.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        msgBox.show()
        return msgBox

    def display_metaicon(self, metaData):
        """
        Display relevant metadata information in a transparent metaicon window

        Creates a visual representation with directional arrows using the provided metadata.
        The visualization includes:
        - North (Green)
        - Layover Angle (Orange)
        - Shadow Angle (Blue)
        - Multipath Angle (Red)
        - Yellow arrow indicating side of track (left/right)
        Also populates upper and lower information tables with relevant metadata values.

        Parameters
        ----------
        self : object
            The class instance.
        metaData : list
            A list containing metadata values where:
            - metaData[0:4]: Values for the upper table
            - metaData[4:9]: Values for the lower table
            - metaData[9:13]: Angular positions for the directional arrows (in degrees)
            - metaData[13]: Side of track indicator

        Returns
        -------
        None
            This method updates the UI and doesn't return a value.
        """

        self.metaicon_widget.metaicon_plot.clear()

        # Green
        a1 = pg.ArrowItem(angle=-metaData[9]+90+180, tipAngle=30, baseAngle=0, headLen=15, tailLen=50, tailWidth=2, pen=None, brush='#8ED15A', pxMode=False)
        a1.setPos(65*math.cos(math.radians(-metaData[9]+90)), 65*math.sin(math.radians(-metaData[9]+90)))
        # Orange
        a2 = pg.ArrowItem(angle=-metaData[10]+90+180, tipAngle=30, baseAngle=0, headLen=15, tailLen=50, tailWidth=2, pen=None, brush='#FF8C00', pxMode=False)
        a2.setPos(65*math.cos(math.radians(-metaData[10]+90)), 65*math.sin(math.radians(-metaData[10]+90)))
        # Blue
        a3 = pg.ArrowItem(angle=-metaData[11]+90+180, tipAngle=30, baseAngle=0, headLen=15, tailLen=50, tailWidth=2, pen=None, brush='#00A6FB', pxMode=False)
        a3.setPos(65*math.cos(math.radians(-metaData[11]+90)), 65*math.sin(math.radians(-metaData[11]+90)))
        # Red
        a4 = pg.ArrowItem(angle=-metaData[12]+90+180, tipAngle=30, baseAngle=0, headLen=15, tailLen=50, tailWidth=2, pen=None, brush='#FF031C', pxMode=False)
        a4.setPos(65*math.cos(math.radians(-metaData[12]+90)), 65*math.sin(math.radians(-metaData[12]+90)))
        # Yellow
        if metaData[13] == 'L':
            a5 = pg.ArrowItem(angle=0, tipAngle=30, baseAngle=0, headLen=15, tailLen=95, tailWidth=2, pen=None, brush='#FFFF00', pxMode=False)
            a5.setPos(-55, -75)
        else:
            a5 = pg.ArrowItem(angle=180, tipAngle=30, baseAngle=0, headLen=15, tailLen=95, tailWidth=2, pen=None, brush='#FFFF00', pxMode=False)
            a5.setPos(55, -75)

        side_of_track_text = pg.TextItem(metaData[13], color='#FFFF00')
        side_of_track_text.setParentItem(a5)

        northText = pg.TextItem("N", color='#8ED15A')
        northText.setParentItem(a1)

        self.metaicon_widget.upper_table.item(0, 0).setText(metaData[0])
        self.metaicon_widget.upper_table.item(1, 0).setText(metaData[1])
        self.metaicon_widget.upper_table.item(2, 0).setText(metaData[2])
        self.metaicon_widget.upper_table.item(3, 0).setText(metaData[3])

        self.metaicon_widget.lower_table.item(0, 0).setText(metaData[4])
        self.metaicon_widget.lower_table.item(1, 0).setText(metaData[5])
        self.metaicon_widget.lower_table.item(2, 0).setText(metaData[6])
        self.metaicon_widget.lower_table.item(3, 0).setText(metaData[7])
        self.metaicon_widget.lower_table.item(4, 0).setText(metaData[8])

        self.metaicon_widget.upper_table.resizeColumnsToContents()
        self.metaicon_widget.lower_table.resizeColumnsToContents()

        self.metaicon_widget.metaicon_plot.addItem(a1)
        self.metaicon_widget.metaicon_plot.addItem(a2)
        self.metaicon_widget.metaicon_plot.addItem(a3)
        self.metaicon_widget.metaicon_plot.addItem(a4)
        self.metaicon_widget.metaicon_plot.addItem(a5)

        self.metaicon_widget.show()
        self.metaicon_widget.activateWindow()

    def change_appearance(self, darkMode):
        """
        Change the application's appearance between light and dark modes.

        Updates the visual appearance of all plot widgets and directory buttons based on
        the specified mode. The currently active plot widget receives special styling to
        indicate its selection status.

        Parameters
        ----------
        self : object
            The class instance.
        darkMode : bool
            Flag indicating whether to use dark mode (True) or light mode (False).

        Returns
        -------
        None
            This method updates the UI and doesn't return a value.
        """

        self.darkMode = darkMode

        for plot in self.plotWidgets:
            MITMStyleSheet.PlotWidgetDock.change_color(plot, False, darkMode)
        MITMStyleSheet.PlotWidgetDock.change_color(self._currentPlotWidget, True, darkMode)

        for button in self.directoryButtons:
            MITMStyleSheet.DirectoryButtons.change_color(button, darkMode)    
            
    def threaded_display_image(self, reader, plotWidgetDock):
        plotWidgetDock.threaded_display_image(reader)

    def add_plot(self):
        """
        Create and add a new plot widget to the application's dock area.

        Instantiates a new PlotWidgetDock with the current appearance mode, adds it to
        the collection of plot widgets, places it in the bottom dock widget area, and
        emits a signal to notify listeners about the widget creation.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        PlotWidgetDock
            The newly created plot widget instance that was added to the dock.
        """

        newPlot = PlotWidgetDock(self.darkMode, self)
        self.plotWidgets.append(newPlot)
        self.addDockWidget(Qt.BottomDockWidgetArea, newPlot)
        self.widget_creation_signal.emit(newPlot)
        return newPlot

    def double_clicked_new_plot(self, file):
        """
        Create a new plot widget and load a file into it when a file is double-clicked.

        Creates a new PlotWidgetDock with the current appearance mode, positions it in the 
        bottom dock widget area, and tabs it with existing plot widgets. The new plot is
        brought to the front, initialized with dimensions from the first plot widget, and
        populated with the selected file's data.

        This method handles only files, not directories, and updates the plot widget's
        title based on the selected file.

        Parameters
        ----------
        self : object
            The class instance.
        file : str
            Path to the file that was double-clicked.

        Returns
        -------
        None
            This method updates the UI and doesn't return a value.
        """

        fi = QFileInfo(file)
        if not fi.isDir():

            newPlot = PlotWidgetDock(self.darkMode, self)
            self.addDockWidget(Qt.BottomDockWidgetArea, newPlot)
            
            for pwIndex in range(len(self.plotWidgets) - 1, -1, -1):
                self.tabifyDockWidget(newPlot, self.plotWidgets[pwIndex])

            newPlot.show()
            newPlot.raise_()

            self.plotWidgets.append(newPlot)
            self.widget_creation_signal.emit(newPlot)

            newPlot.metaIconButton.setVisible(True)
            newPlot.windowWidth = self.plotWidgets[0].plotWidget.getPlotItem().mapRectToDevice(self.plotWidgets[0].plotWidget.getPlotItem().boundingRect()).width() - 5.0
            newPlot.windowHeight = self.plotWidgets[0].plotWidget.getPlotItem().mapRectToDevice(self.plotWidgets[0].plotWidget.getPlotItem().boundingRect()).height() - 5.0

            newPlot.metaIconButton.setVisible(False)

            self.doubleClicked.emit(file, newPlot)

            newPlot.droppedFile = file # TODO fix this mess
            newPlot.fileName = file.split('/')[-1]
            newPlot.setWindowTitle('  ' + newPlot.fileName)

            newPlot.metaIconButton.setVisible(True)

            newPlot.panZoomEnabled = True

    def move_down_directory(self):
        """
        Navigate down into a subdirectory when a directory is double-clicked in the file tree.

        Updates the current directory path to the selected directory and adds new
        directory buttons to the navigation bar representing the path hierarchy.
        The last button (representing the current directory) is styled differently
        to indicate it's the active directory.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI navigation and doesn't return a value.
        """

        self.currentDirectoryPath = self.fileDialog.directory().path()
        self._add_directory_buttons(self.fileDialog.directory().path().split('/'))
        self.directoryButtons[-1].setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(True, self.darkMode))

    def move_up_directory(self):
        """
        Navigate up to a parent directory when a directory button is clicked in the navigation bar.

        Changes the current directory to the selected parent directory based on which
        navigation button was clicked. Updates the file dialog to display the contents
        of the selected directory and applies appropriate styling to the directory buttons,
        highlighting the newly active directory.

        Platform-specific handling is implemented for root directory navigation
        on Windows vs. other operating systems.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI navigation and doesn't return a value.
        """

        sender = self.sender().text()
        if sender == '':
            newRootPath = 'root'
        else:
            newRootPath = self.currentDirectoryPath.split(self.sender().text())[0] + self.sender().text()
        if(newRootPath == 'root'):
            if(sys.platform == 'win32'):
                self.fileDialog.setDirectory('My Computer')
            else:
                self.fileDialog.setDirectory('/')  
        else:
            self.fileDialog.setDirectory(newRootPath)

        for button in self.directoryButtons:
            button.setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(False, self.darkMode))
            
        self.sender().setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(True, self.darkMode))

    def _add_directory_buttons(self, directories):
        """
        Create and configure the directory navigation buttons based on the current path.

        Clears existing directory buttons and rebuilds them according to the provided
        directory path. Handles platform-specific differences between Windows and Linux
        file systems, including special cases for network locations and root directories.
        Sets up event connections for each button and applies appropriate styling,
        with the current directory button highlighted.

        Parameters
        ----------
        self : object
            The class instance.
        directories : list
            List of directory names representing the path hierarchy to display as buttons.

        Returns
        -------
        None
            This method updates the UI navigation and doesn't return a value.
        """

        b = self.directoryWidget.layout().takeAt(0)
        while(b):
            b.widget().deleteLater()
            b = self.directoryWidget.layout().takeAt(0)
        self.directoryButtons.clear()

        if sys.platform == 'win32':
            if '' in directories:
            # network locations in Windows begin with '//' 
            # which results in two empty strings at the start of the list
                directories = list(filter(None, directories))
            
            if '.' in directories:
            # 'My Computer' shows up as '.' if navigated to from within filedialog (Windows)
                directories.remove('.')

            directories.insert(0, '')
        elif sys.platform == 'linux' or sys.platform == 'linux2':
            directories.insert(0, '/')

        computerIcon = QIcon.fromTheme(QIcon.ThemeIcon.Computer)

        for directory in directories:
            button = QPushButton()
            if directory == '':
                button.setIcon(computerIcon)
            else:
                button.setText(directory)
            button.setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(False, self.darkMode))
            self.directoryWidget.layout().addWidget(button)
            button.clicked.connect(self.move_up_directory)
            self.directoryButtons.append(button)

        self.directoryButtons[-1].setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(True, self.darkMode))

    def handle_app_state_changed(self, state):
        """
        Handle application state changes and detect the first activation.

        Monitors the application state and emits a signal when the application
        becomes active for the first time. Ignores state changes where the
        application is not becoming active.

        Parameters
        ----------
        self : object
            The class instance.
        state : Qt.ApplicationState
            The new state of the application. Only Qt.ApplicationState.ApplicationActive
            triggers further actions.

        Returns
        -------
        None
            This method tracks application state and doesn't return a value.
        """

        if(state != Qt.ApplicationState.ApplicationActive):
            return
        
        if(not self.appStarted):
            self.appStarted = True
            self.applicationStarted.emit()

    def create_plot_on_startup(self):
        """
        Create an initial plot widget when the application starts.

        If a file was specified to open during startup, attempts to load that file into a
        new plot widget. If the specified file doesn't exist, displays a warning message.
        If no file was specified, creates an empty plot widget.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method creates initial plot widgets and doesn't return a value.
        """

        if(not self.fileopen):
            self.add_plot()
            return
        
        if(not os.path.isfile(self.fileopen)):
            QMessageBox.information(None, "Warning", "File \'" + self.fileopen + "\' does not exist.")
            return

        self.double_clicked_new_plot(self.fileopen)

    def render_widget_selection(self, selected_widget):
        """
        Update widget styling to indicate which plot widget is currently selected.

        Applies the default styling to all plot widgets, then applies the selected
        styling to the specified widget. This provides a visual indication of which
        plot widget is currently active.

        Parameters
        ----------
        self : object
            The class instance.
        selected_widget : PlotWidgetDock
            The plot widget that is currently selected and should be highlighted.

        Returns
        -------
        None
            This method updates the UI styling and doesn't return a value.
        """

        for plot_widget in self.plotWidgets:
            MITMStyleSheet.PlotWidgetDock.change_color(plot_widget, False, self.darkMode)

        MITMStyleSheet.PlotWidgetDock.change_color(selected_widget, True, self.darkMode)

    def handle_widget_interaction(self, selected_widget):
        """
        Handle user interactions with plot widgets and update selection accordingly.

        Processes widget interaction events by attempting to set the specified widget
        as the current selection. If the selection actually changes, updates the
        visual styling to highlight the newly selected widget.

        Parameters
        ----------
        self : object
            The class instance.
        selected_widget : PlotWidgetDock
            The plot widget that the user interacted with and should be made current.

        Returns
        -------
        None
            This method updates the widget selection state and doesn't return a value.
        """

        changed = self.__set_current_widget(selected_widget)
        if(changed):
            self.render_widget_selection(selected_widget)
        
    def __set_current_widget(self, current_widget) -> None:
        """
        Set a new plot widget as the current selection.

        Updates the internal reference to the currently selected widget and emits
        a signal to notify listeners of the change. Only emits the signal if the
        widget actually changes.

        Parameters
        ----------
        self : object
            The class instance.
        current_widget : PlotWidgetDock or None
            The plot widget to set as current, or None if no widget is selected.

        Returns
        -------
        bool
            True if the current widget changed, False if it remained the same.
        """

        if(current_widget != self._currentPlotWidget):
            self._currentPlotWidget = current_widget
            self.widget_changed_signal.emit(self._currentPlotWidget)
            return True
        return False

    def check_if_current_widget_closed(self, widget):
        """
        Handle the case when the currently selected widget is closed.

        Checks if the closed widget is the currently selected one, and if so,
        clears the current selection and closes the meta-icon widget.

        Parameters
        ----------
        self : object
            The class instance.
        widget : PlotWidgetDock
            The plot widget that was closed.

        Returns
        -------
        None
            This method updates the widget selection state and doesn't return a value.
        """

        if(self._currentPlotWidget == widget):
            self.__set_current_widget(None)
            self.metaicon_widget.close()
    
    def closeEvent(self, event):
        """
        Handle application close events.

        Performs cleanup actions when the application is closing, including closing
        the meta-icon widget and emitting a signal with the current sidebar URLs and
        file filters to save application state.

        Parameters
        ----------
        self : object
            The class instance.
        event : QCloseEvent
            The close event object.

        Returns
        -------
        None
            This method handles the close event and doesn't return a value.
        """

        self.metaicon_widget.close()
        self.windowClosed.emit([x.path()+'\n' for x in self.fileDialog.sidebarUrls()], self.fileDialog.nameFilters())
        super().closeEvent(event)

class PlotWidgetDock(QDockWidget, Ui_DockWidget):   
    plot_widget_resize_finished_signal = Signal(object, name="plot_widget_resize_signal")

    def __init__(self, darkMode, parent=None):
        """
        Initialize a plot widget dock for displaying and manipulating images.

        Creates a dockable widget with an embedded PyQtGraph plot widget configured
        for image display. Sets up the UI components, event handling, and signal
        connections for image loading, viewing, and manipulation.

        Features include:
        - Progress bar for loading operations
        - Image display with pan/zoom capabilities
        - Coordinate display with multiple format options (DMS, DD, XY)
        - Drag and drop support for loading image files
        - Image remapping options (Density, Brightness, Contrast, etc.)
        - Aspect ratio control
        - Efficient image decimation for handling large images

        Parameters
        ----------
        self : object
        The class instance.
        darkMode : bool
        Flag indicating whether to use dark mode styling.
        parent : QWidget or None, optional
        The parent widget. Default is None.

        Returns
        -------
        None
        This is the constructor and doesn't return a value.
        """

        super(PlotWidgetDock, self).__init__(parent, focusPolicy=Qt.WheelFocus)
        self.setupUi(self)
        self.resize_event = 0
        self.reader = None
        self.remap_function = remap.Density()
        self.preRemappedData = []
        self.decimationFactor = 1
        self.panZoomEnabled = False
        self.xminMapToFullImage = 0
        self.yminMapToFullImage = 0
        self.fileName = ''
        self.size = 0

        self.plotWidget = pg.PlotWidget(self.dockWidgetContents, viewBox=CustomViewBox(self))
        self.gridLayout.addWidget(self.upperControlsWidget, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.plotWidget, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.controlsWidget, 2, 0, 1, 1)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.plotWidget.setLayout(layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(200)
        self.plotWidget.layout().addWidget(self.progress_bar)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setRange(0, 0)

        self.progress_bar.setStyleSheet(MITMStyleSheet.PlotWidgetDock.ProgressBar)
        self.progress_bar.hide()

        self.plotWidget.setAspectLocked()
        self.plotWidget.setAcceptDrops(True)
        self.plotWidget.getPlotItem().getViewBox().suggestPadding = lambda *_: 0.0
        self.plotWidget.getPlotItem().hideAxis('bottom')
        self.plotWidget.getPlotItem().hideAxis('left')
        self.plotWidget.getPlotItem().setMenuEnabled(enableMenu=False, enableViewBoxMenu=None)

        self.img = pg.ImageItem(axisOrder = 'row-major')
        self.img.hoverEvent = self.image_hover_event
        self.plotWidget.addItem(self.img)

        self._current_cursor_position = None

        self.plotWidget.dropEvent = self.drop_event
        self.plotWidget.dragMoveEvent = self.drag_move_event
        self.plotWidget.dragEnterEvent = self.drag_enter_event
        self.plotWidget.dragLeaveEvent = self.drag_leave_event

        self.plotWidget.mousePressEvent = self.mouse_press_event

        self.metaIconButton.clicked.connect(self.metaicon_button_pressed)
        self.metaIconButton.setToolTip(ToolTips.PlotWidgetDock.meta_icon_button())
        self.metaIconButton.setVisible(False)

        self.downsampleMethodComboBox.activated.connect(self.downsample_method_changed)
        self.downsampleMethodComboBox.setToolTip(ToolTips.PlotWidgetDock.downsample_method_combobox())
        
        self.remapMethodComboBox.currentTextChanged.connect(self.remap_method_changed)
        self.remapMethodComboBox.setToolTip(ToolTips.PlotWidgetDock.remap_method_combobox())

        self.aspectRatioComboBox.currentTextChanged.connect(self.aspect_ratio_changed)
        self.aspectRatioComboBox.setToolTip(ToolTips.PlotWidgetDock.aspect_ratio_combobox())
        
        self.plotWidget.sigRangeChanged.connect(self.update_region)
        self.enhancePushButton.setEnabled(False)

        self.plotWidget.getPlotItem().getViewBox().autoResample.connect(self.resample_image)

        self.windowWidth = 0
        self.windowHeight = 0

        self.coordinatesButton.setText("")
        self.coordinatesButton.setVisible(False)
        self.coordinatesButton.setToolTip(ToolTips.PlotWidgetDock.coordinates())
        self.coordinatesButton.clicked.connect(self.switch_coordinate_mode)
        self.coordinate_mode = "DMS"

        self.visibilityChanged.connect(self.dock_visibility_changed)
        self.dockLocationChanged.connect(self.dock_location_changed)

        # Removed controls
        self.enhancePushButton.hide()
        self.coordinatesLabel.hide()
        self.rois = []

        # Hide these controls until implemented
        self.indexSpinBox.hide()
        self.indexLabel.hide()
        self.debugPushButton.hide()
        
        self.plotWidget.resize_timer = QTimer(self.plotWidget) 
        self.plotWidget.resize_timer.setSingleShot(True)
        self.plotWidget.resize_timer.timeout.connect(self.__emit_resize_finished)    
    
    def resizeEvent(self, event):
        """
        Handle resize events for the plot widget.

        Overrides the parent class resize event handler and sets up a timer to debounce
        multiple consecutive resize events, preventing excessive computation during
        window resizing operations.

        Parameters
        ----------
        self : object
            The class instance.
        event : QResizeEvent
            The resize event object.

        Returns
        -------
        None
            This method handles the resize event and doesn't return a value.
        """

        super().resizeEvent(event)
        
        if not hasattr(self, 'resize_timer'):
            self.plotWidget.resize_timer = QTimer(self.plotWidget)
            self.plotWidget.resize_timer.setSingleShot(True)
            self.plotWidget.resize_timer.timeout.connect(self.__emit_resize_finished)

        self.plotWidget.resize_timer.start(1000)
    
    def __emit_resize_finished(self):
        """
        Handle the completion of a resize operation after the debounce period.

        Triggered when the resize timer expires, indicating that resizing has finished.
        Resamples the displayed image to match the new dimensions and notifies
        listeners that the resize operation is complete.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the image display and doesn't return a value.
        """

        self.resample_image() 
        self.plot_widget_resize_finished_signal.emit(self)
                
    def get_current_cursor_image_position(self) -> None:
        """
        Get the current cursor position within the image.

        Returns the stored cursor position coordinates from the last mouse hover event.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        list or None
            The current cursor position as [x, y] coordinates in the image, or None if not set.
        """

        return self._current_cursor_position
    
    def set_current_cursor_image_position(self, current_cursor_position) -> list:
        """
        Set the current cursor position within the image.

        Stores the cursor position coordinates for later reference.

        Parameters
        ----------
        self : object
            The class instance.
        current_cursor_position : list
            The cursor position as [x, y] coordinates in the image.

        Returns
        -------
        list
            The updated cursor position.
        """
        self._current_cursor_position = current_cursor_position

    def undecimate_pixel_coordinates(self, pixel_coords):
        """
        Convert pixel coordinates from decimated to full-resolution image space.

        Translates coordinates from the downsampled (decimated) representation back to their
        original positions in the full-resolution image, accounting for the current scaling
        and offsets.

        Parameters
        ----------
        self : object
            The class instance.
        pixel_coords : list
            A list of QPointF objects representing coordinates in the decimated image.

        Returns
        -------
        list or list of lists
            For a single coordinate: [y, x] in the full-resolution image.
            For multiple coordinates: A list of [y, x] coordinates in the full-resolution image.
        """

        undecimated_pixel_coords = []
        for pixel_coord in pixel_coords:
            undecimated_pixel_coords.append(
                [
                    int(
                        pixel_coord.y() * self.stepSize
                        + self.yminMapToFullImage
                    ),
                    int(
                        pixel_coord.x() * self.stepSize
                        + self.xminMapToFullImage
                    ),
                ]
            )
        if len(undecimated_pixel_coords) < 2:
            return undecimated_pixel_coords[0]
        else:
            return undecimated_pixel_coords

    def mousePressEvent(self, event):
        """
        Handle mouse press events on the dock widget.

        Notifies the parent about interaction with this widget before passing the
        event to the parent class for standard processing.

        Parameters
        ----------
        self : object
            The class instance.
        event : QMouseEvent
            The mouse press event object.

        Returns
        -------
        None
            This method handles the mouse press event and doesn't return a value.
        """

        self.parent().widget_interacted_signal.emit(self)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        """
        Handle close events for the dock widget.

        Notifies the parent that this widget is being closed before passing the
        event to the parent class for standard processing.

        Parameters
        ----------
        self : object
            The class instance.
        event : QCloseEvent
            The close event object.

        Returns
        -------
        None
            This method handles the close event and doesn't return a value.
        """

        self.parent().widget_closed_signal.emit(self)
        super().closeEvent(event)

    def threaded_display_image(self, reader):
        """
        Load and display an image using a worker thread to prevent UI freezing.

        Creates a worker thread to handle the potentially time-consuming operation of
        loading and displaying a large image file. Sets up signal connections to manage
        the UI state during loading and after completion.

        Parameters
        ----------
        self : object
            The class instance.
        reader : object
            The file reader object that provides access to the image data.

        Returns
        -------
        None
            This method initiates asynchronous image loading and doesn't return a value.
        """

        self.thread = QThread()

        self.worker = FileOpenWorker(reader, self)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.started.connect(self.reject_drops)
        self.worker.finished.connect(self.accept_drops)
        self.worker.finished.connect(self.update_aspect_ratio)

        self.thread.finished.connect(self.hide_progress_bar)

        self.thread.start()
        self.progress_bar.show()

    def reject_drops(self):
        """
        Disable drag and drop functionality during file loading operations.

        Called when a file load operation starts to prevent the user from dropping
        additional files while loading is in progress.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI state and doesn't return a value.
        """

        self.plotWidget.setAcceptDrops(False)

    def accept_drops(self):
        """
        Re-enable drag and drop functionality after file loading completes.

        Called when a file load operation finishes to allow the user to drop
        additional files again.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI state and doesn't return a value.
        """

        self.plotWidget.setAcceptDrops(True)

    def hide_progress_bar(self):
        """
        Hide the progress bar after an operation completes.

        Hides the progress bar widget that indicates file loading.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI and doesn't return a value.
        """

        self.progress_bar.hide()

    def set_file_name(self, file_name) -> None:
        """
        Set the file name for the current plot widget.

        Stores the file name for later reference.

        Parameters
        ----------
        self : object
            The class instance.
        file_name : str
            The name of the file being displayed.

        Returns
        -------
        None
            This method updates internal state and doesn't return a value.
        """

        self._file_name = file_name

    def get_file_name(self) -> str:
        """
        Retrieve the file name of the current plot widget.

        Returns the stored file name associated with this widget.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        str
            The name of the file being displayed.
        """

        return self._file_name

    def copy_coordinates(self):
        """
        Copy the current coordinates to the system clipboard.

        Copies the text from the coordinates button (which contains formatted 
        geographic or pixel coordinates) to the system clipboard.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method performs a clipboard operation and doesn't return a value.
        """

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.coordinatesButton.text())

    def metaicon_button_pressed(self):
        """
        Handle meta-icon button press events.

        Emits signals to open the meta-icon display for the current file and
        to indicate that this widget has been interacted with.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method emits signals and doesn't return a value.
        """

        self.parent().openMetaIcon.emit(self.fileName)
        self.parent().widget_interacted_signal.emit(self)

    def downsample_method_changed(self):
        """
        Handle changes to the downsample method.

        This is a placeholder method for future implementation.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method is a stub and doesn't return a value.
        """

        pass

    def remap_method_changed(self, method):
        """
        Update the image remapping function based on the selected method.

        Changes the remapping function used to display the image data based on the
        selected method name, and applies the new function to the current image data.
        Supports various remapping methods like Density, Brighter, Darker, etc.

        Parameters
        ----------
        self : object
            The class instance.
        method : str
            The name of the remapping method to use.

        Returns
        -------
        None
            This method updates the image display and doesn't return a value.
        """

        if   method == 'Density':       self.remap_function = remap.Density()
        elif method == 'Brighter':      self.remap_function = remap.Brighter()
        elif method == 'Darker':        self.remap_function = remap.Darker()
        elif method == 'High Contrast': self.remap_function = remap.High_Contrast()
        elif method == 'Linear':        self.remap_function = remap.Linear()
        elif method == 'Logarithmic':   self.remap_function = Logarithmic()
        elif method == 'PEDF':          self.remap_function = remap.PEDF()
        elif method == 'NRL':           self.remap_function = remap.NRL()

        if len(self.preRemappedData) > 0:
            remappedData = self.remap_function(self.preRemappedData)
            self.img.setImage(remappedData)
        self.parent().widget_interacted_signal.emit(self)

    def switch_coordinate_mode(self):
        """
        Toggle between different coordinate display formats.

        Cycles through three coordinate display modes:
        - DMS (Degrees, Minutes, Seconds)
        - DD (Decimal Degrees)
        - XY (Pixel Coordinates)
        Updates the coordinate button text to show the appropriate format.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the UI and doesn't return a value.
        """

        if self.coordinate_mode == 'DMS': 
            self.coordinate_mode = 'DD'
            self.coordinatesButton.setText('0.0000000°, 0.00000000°')
        elif self.coordinate_mode == 'DD': 
            self.coordinate_mode = 'XY'
            self.coordinatesButton.setText('0, 0')
        elif self.coordinate_mode == 'XY': 
            self.coordinate_mode = 'DMS'
            self.coordinatesButton.setText('0° 0′ 0.00000″ N, 0° 0′ 0.00000″ E')

    def update_aspect_ratio(self):
        """
        Update the aspect ratio based on the current selection in the combo box.

        Calls aspect_ratio_changed with the currently selected aspect ratio option.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the image aspect ratio and doesn't return a value.
        """

        self.aspect_ratio_changed(self.aspectRatioComboBox.currentText())

    def aspect_ratio_changed(self, ratio):
        """
        Change the image aspect ratio based on the selected option.

        Updates the aspect ratio locking of the plot widget based on the selected ratio.
        Supports 'Square' for 1:1 aspect ratio or 'Aspect' for requesting the actual
        image aspect ratio from the parent.

        Parameters
        ----------
        self : object
            The class instance.
        ratio : str
            The aspect ratio option to apply ('Square' or 'Aspect').

        Returns
        -------
        None
            This method updates the image display and doesn't return a value.
        """

        if self.reader:
            if   ratio == 'Square': self.plotWidget.setAspectLocked(ratio=1)
            elif ratio == 'Aspect': self.parent().requestAspectRatio.emit(self)
        self.parent().widget_interacted_signal.emit(self)

    def apply_aspect_ratio_to_image(self, aspectRatio):
        """
        Apply a specific aspect ratio to the image display.

        Sets the plot widget's aspect ratio locking to the specified value.

        Parameters
        ----------
        self : object
            The class instance.
        aspectRatio : float
            The aspect ratio value to apply.

        Returns
        -------
        None
            This method updates the image display and doesn't return a value.
        """

        self.plotWidget.setAspectLocked(ratio=aspectRatio)

    def update_region(self):     
        """
        This is a placeholder method for future implementation.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method is a stub and doesn't return a value.
        """

        pass

    def resample_image(self):
        """
        Resample the image data based on the current view and window size.

        Calculates appropriate decimation factors and view bounds to efficiently
        display large images at the current zoom level and window size. Only resamples
        if the window dimensions have changed or if the view range has changed.
        Uses adaptive sampling to balance detail level with performance.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the image display and doesn't return a value.
        """

        if not hasattr(self, 'dataShapeW'):
            return

        if (self.windowWidth != self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).width() - 5.0 or
            self.windowHeight != self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).height() - 5.0):

            xMinViewBox = self.plotWidget.getViewBox().viewRange()[0][0]
            xMaxViewBox = self.plotWidget.getViewBox().viewRange()[0][1]
            yMinViewBox = self.plotWidget.getViewBox().viewRange()[1][0]
            yMaxViewBox = self.plotWidget.getViewBox().viewRange()[1][1]

            self.windowWidth = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).width() - 5.0
            self.windowHeight = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).height() - 5.0

            stepW = self.dataShapeW / self.windowWidth
            stepH = self.dataShapeH / self.windowHeight

            self.decimationFactor = int(max(math.ceil(stepW), math.ceil(stepH)))

            xWidth = int(math.ceil(self.dataShapeW / self.decimationFactor))
            yHeight = int(math.ceil(self.dataShapeH / self.decimationFactor))

            self.img.setRect(QRect(0, 0, xWidth-1, yHeight-1))

        
        xMinViewBox = self.plotWidget.getViewBox().viewRange()[0][0]
        xMaxViewBox = self.plotWidget.getViewBox().viewRange()[0][1]
        yMinViewBox = self.plotWidget.getViewBox().viewRange()[1][0]
        yMaxViewBox = self.plotWidget.getViewBox().viewRange()[1][1]
        
        # Calculate the max decimated image width and height
        self.maxDecimatedImageWidth = int(math.ceil(self.dataShapeW / max( int(math.ceil(self.dataShapeW / self.windowWidth)), int(math.ceil(self.dataShapeH / self.windowHeight)) )))
        self.maxDecimatedImageHeight = int(math.ceil(self.dataShapeH / max( int(math.ceil(self.dataShapeW / self.windowWidth)), int(math.ceil(self.dataShapeH / self.windowHeight)) )))

        xmin = np.clip( math.floor( xMinViewBox ), 0, self.maxDecimatedImageWidth-1 )
        ymin = np.clip( math.floor( yMinViewBox ), 0, self.maxDecimatedImageHeight-1 )

        xmax = np.clip( math.ceil( xMaxViewBox ), 0, self.maxDecimatedImageWidth-1 )
        ymax = np.clip( math.ceil( yMaxViewBox ), 0, self.maxDecimatedImageHeight-1 )

        xminMapToFullImage = xmin * self.decimationFactor
        yminMapToFullImage = ymin * self.decimationFactor

        xmaxMapToFullImage = xmax * self.decimationFactor
        ymaxMapToFullImage = ymax * self.decimationFactor

        self.xminMapToFullImage = xminMapToFullImage
        self.yminMapToFullImage = yminMapToFullImage

        stepSize = int(math.ceil(max((xmaxMapToFullImage - xminMapToFullImage) / self.windowWidth,
                                     (ymaxMapToFullImage - yminMapToFullImage) / self.windowHeight)))
        stepSize = max(stepSize, 1)
        try:
            self.stepSize = stepSize
            #print('debug', self.reader[yminMapToFullImage:ymaxMapToFullImage:stepSize,xminMapToFullImage:xmaxMapToFullImage:stepSize])
            decimatedData = self.reader[yminMapToFullImage:ymaxMapToFullImage:stepSize,xminMapToFullImage:xmaxMapToFullImage:stepSize]
            self.preRemappedData = decimatedData
            remappedData = self.remap_function(decimatedData)
            self.img.setImage(remappedData)
            self.img.setRect(QRect(xmin, ymin, xmax-xmin, ymax-ymin))
        except:
            pass

        return

    def dock_visibility_changed(self, visible):
        """
        Handle visibility changes of the dock widget.

        When the widget becomes visible, emits a signal to notify the parent
        that this widget has been interacted with.

        Parameters
        ----------
        self : object
            The class instance.
        visible : bool
            Flag indicating whether the widget is now visible.

        Returns
        -------
        None
            This method emits a signal and doesn't return a value.
        """

        if visible:
            self.parent().widget_interacted_signal.emit(self)

    def dock_location_changed(self):
        """
        Handle changes to the dock widget's location.

        Adjusts the widget's size when it becomes a floating window to prevent
        geometry-related errors in the Qt framework.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the widget geometry and doesn't return a value.
        """

        if self.isFloating():
            self.adjustSize() # prevents "unable to set geometry" errors

    def image_hover_event(self, event):
        """
        Update coordinate display when the mouse hovers over the image.

        Calculates the corresponding coordinates (both pixel and geographic) for the
        current mouse position and updates the coordinate display. Also triggers
        resampling if the view has been zoomed.

        Parameters
        ----------
        self : object
            The class instance.
        event : QGraphicsSceneHoverEvent
            The hover event containing the mouse position.

        Returns
        -------
        None
            This method updates the coordinate display and doesn't return a value.
        """

        if event.isExit():
            return
        pos = event.pos()

        viewBox = self.plotWidget.getPlotItem().getViewBox()
        if viewBox.zoomed:
            viewBox.autoResample.emit()
            viewBox.zoomed = False
            self.parent().widget_interacted_signal.emit(self)

        i = int(np.clip(pos.x() * math.ceil(self.stepSize) + self.xminMapToFullImage, 0, self.dataShapeW - 1))
        j = int(np.clip(pos.y() * math.ceil(self.stepSize) + self.yminMapToFullImage, 0, self.dataShapeH - 1))

        pixel_image_coord = self.img.mapToView(pos)
        
        self.set_current_cursor_image_position([pixel_image_coord.x(), pixel_image_coord.y()])
        
        try:
            self.coordinatesButton.setVisible(True)
            geoCoords = self.structure.project_image_to_ground_geo((j, i), projection_type='HAE')
            if self.coordinate_mode == 'DMS':
                lat = self._deg_to_dms(geoCoords[0], 'latitude', 5)
                lon = self._deg_to_dms(geoCoords[1], 'longitude', 5)
            elif self.coordinate_mode == 'DD':
                lat = '{d:.8f}°'.format(d = geoCoords[0])
                lon = '{d:.8f}°'.format(d = geoCoords[1])
            elif self.coordinate_mode == 'XY':
                lat = str(i)
                lon = str(j)
            self.coordinatesButton.setText(lat + ', ' + lon)
        except:
            pass

    def drop_event(self, e):
        """
        Handle file drop events onto the plot widget.

        Processes dropped NITF/NTF files by updating the widget's dimensions,
        emitting signals to load the file, and updating the widget title with
        the file name. Only handles files with .nitf or .ntf extensions.

        Parameters
        ----------
        self : object
            The class instance.
        e : QDropEvent
            The drop event containing the file information.

        Returns
        -------
        None
            This method processes the dropped file and doesn't return a value.
        """

        droppedFile = e.mimeData().text()

        if droppedFile.endswith(".nitf") or droppedFile.endswith(".ntf"):
            self.metaIconButton.setVisible(True)
            self.windowWidth = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).width() - 5.0
            self.windowHeight = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).height() - 5.0

            self.metaIconButton.setVisible(False)

            self.parentWidget().fileDropped.emit(droppedFile, self)

            self.droppedFile = droppedFile # TODO fix this mess
            self.fileName = droppedFile.split('/')[-1]
            self.setWindowTitle('  ' + self.fileName)

            self.metaIconButton.setVisible(True)

            self.panZoomEnabled = True

            # Emit signal that a UI element has been updated
            self.parent().widget_interacted_signal.emit(self)

            e.acceptProposedAction()

    def drag_enter_event(self, e):
        e.acceptProposedAction()

    def drag_leave_event(self, e):
        e.accept()

    def drag_move_event(self, e):
        e.acceptProposedAction()

    def mouse_press_event(self, e):
        """
        Handle mouse press events for the plot widget.

        Notifies the parent that this widget has been interacted with before
        delegating to the standard PyQtGraph mouse press event handler.

        Parameters
        ----------
        self : object
            The class instance.
        e : QMouseEvent
            The mouse press event.

        Returns
        -------
        None
            This method processes the mouse press and doesn't return a value.
        """

        self.parent().widget_interacted_signal.emit(self)
        pg.PlotWidget.mousePressEvent(self.plotWidget, e)

    def get_plot_window_width(self):
        """
        Get the current width of the plot window.

        Calculates the width of the plotWidget's bounding rectangle in device
        coordinates, with a small margin adjustment.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        float
            The width of the plot window in pixels.
        """

        width = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).width() - 5.0
        return width

    def get_plot_window_height(self):
        """
        Get the current height of the plot window.

        Calculates the height of the plotWidget's bounding rectangle in device
        coordinates, with a small margin adjustment.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        float
            The height of the plot window in pixels.
        """

        height = self.plotWidget.getPlotItem().mapRectToDevice(self.plotWidget.getPlotItem().boundingRect()).height() - 5.0
        return height

    def _deg_to_dms(self, deg, axis=None, ndp=6):
        """
        Convert decimal degrees to degrees-minutes-seconds format.

        Transforms a decimal degree value into the traditional DMS format with
        appropriate hemisphere designation for geographic coordinates.

        Parameters
        ----------
        self : object
            The class instance.
        deg : float
            The angle in decimal degrees.
        axis : str or None, optional
            Specifies whether this is a 'latitude' or 'longitude' value for
            determining the hemisphere designation. If None, returns the
            components as a tuple.
        ndp : int, optional
            Number of decimal places for the seconds component. Default is 6.

        Returns
        -------
        str or tuple
            If axis is specified: Formatted string in DMS format with hemisphere.
            If axis is None: Tuple of (degrees, minutes, seconds).
        """

        m, s = divmod(np.abs(deg)*3600, 60)
        d, m = divmod(m, 60)
        if deg < 0:
            d = -d
        d, m = int(d), int(m)

        if axis:
            if axis=='latitude':
                hemi = 'N' if d>=0 else 'S'
            elif axis=='longitude':
                hemi = 'E' if d>=0 else 'W'
            else:
                hemi = '?'
            return '{d:d}° {m:d}′ {s:.{ndp:d}f}″ {hemi:1s}'.format(
                        d=np.abs(d), m=m, s=s, hemi=hemi, ndp=ndp)
        return d, m, s

class MetaIconWidget(QWidget, Ui_MetaIcon):

    def __init__(self, parent=None):
        """
        Initialize the MetaIconWidget.

        Sets up a frameless, translucent widget for displaying metadata icons and
        information tables. Configures window behavior, buttons, plot widgets, and
        styling according to the application's style guidelines.

        Parameters
        ----------
        self : object
            The class instance.
        parent : QWidget or None, optional
            The parent widget. Default is None.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        super(MetaIconWidget, self).__init__(parent, focusPolicy=Qt.WheelFocus)
        self.setupUi(self)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.closeButton.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.closeButton.clicked.connect(self.close)
        self.minimizeButton.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.minimizeButton.clicked.connect(self.showMinimized)

        self.setStyleSheet(MITMStyleSheet.MetaIcon.StyleSheet)

        self.metaicon_plot.getPlotItem().hideAxis('bottom')
        self.metaicon_plot.getPlotItem().hideAxis('left')
        self.metaicon_plot.setFixedSize(150, 170)
        self.metaicon_plot.hideButtons()
        self.metaicon_plot.getViewBox().setMouseEnabled(False, False)
        self.metaicon_plot.setAspectLocked(lock=True, ratio=1)
        self.metaicon_plot.setXRange(-75, 75, padding=0)
        self.metaicon_plot.setYRange(-95, 75, padding=0)
        self.metaicon_plot.setBackground(MITMStyleSheet.MetaIcon.PlotBackgroundColor)
        self.metaicon_plot.getPlotItem().getViewBox().setBorder(color=MITMStyleSheet.MetaIcon.ViewBoxBorderColor, width=2)

        self.lower_table.item(2, 0).setForeground(QBrush(QColor(MITMStyleSheet.MetaIcon.LayoverColor)))
        self.lower_table.item(3, 0).setForeground(QBrush(QColor(MITMStyleSheet.MetaIcon.ShadowColor)))
        self.lower_table.item(4, 0).setForeground(QBrush(QColor(MITMStyleSheet.MetaIcon.MultipathColor)))

        for i in range(4):
            self.upper_table.item(i, 0).setFont(QFont(MITMStyleSheet.MetaIcon.Font, pointSize=MITMStyleSheet.MetaIcon.FontSize))

        for j in range(5):
            self.lower_table.item(j, 0).setFont(QFont(MITMStyleSheet.MetaIcon.Font, pointSize=MITMStyleSheet.MetaIcon.FontSize))

        self.upper_table.mousePressEvent = self.mousePressEvent
        self.lower_table.mousePressEvent = self.mousePressEvent

        self.upper_table.mouseMoveEvent = self.mouseMoveEvent
        self.lower_table.mouseMoveEvent = self.mouseMoveEvent

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for dragging the widget.

        Captures the initial position when the left mouse button is pressed
        to support dragging the frameless window.

        Parameters
        ----------
        self : object
            The class instance.
        event : QMouseEvent
            The mouse press event.

        Returns
        -------
        None
            This method updates the drag position and doesn't return a value.
        """

        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events for dragging the widget.

        Moves the frameless window when dragged with the left mouse button.

        Parameters
        ----------
        self : object
            The class instance.
        event : QMouseEvent
            The mouse move event.

        Returns
        -------
        None
            This method updates the widget position and doesn't return a value.
        """

        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPosition)
            event.accept()

    def moveEvent(self, e):
        """
        Handle move events for the widget.

        Ensures the widget size is properly adjusted when moved to prevent
        geometry-related errors in the Qt framework.

        Parameters
        ----------
        self : object
            The class instance.
        e : QMoveEvent
            The move event.

        Returns
        -------
        None
            This method adjusts the widget size and doesn't return a value.
        """

        self.adjustSize() # prevents "unable to set geometry" errors and other weirdness
        super().moveEvent(e)

class CustomViewBox(pg.ViewBox):
    autoResample = Signal()

    def __init__(self, parent = None):
        """
        Custom ViewBox for image display with enhanced zoom and pan behavior.

        A specialized ViewBox that inverts the Y-axis and adds custom context menu
        options for coordinate copying. Signals when view changes to trigger image
        resampling and optimizes behavior for large images.

        Parameters
        ----------
        self : object
            The class instance.
        parent : PlotWidgetDock or None, optional
            The parent plot dock widget. Default is None.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        super(CustomViewBox, self).__init__(invertY=True)
        self.parentPlotDock = parent
        self.custom_menu_edit()
        self.zoomed = False
    
    def custom_menu_edit(self):
        """
        Customize the context menu for the ViewBox.

        Removes standard menu items that aren't needed for image viewing and
        adds a custom option to copy the current coordinates to the clipboard.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method modifies the context menu and doesn't return a value.
        """

        hiddenMenus = ["View All", "X axis", "Y axis", "Mouse Mode"]
        actions = self.menu.actions()
        for action in actions:
            for menuItem in hiddenMenus:
                if (action.text().startswith(menuItem)):
                    action.setVisible(False)
                    break

        # Add custom menu options
        copyCoords = QAction("Copy Coordinates", self.menu)
        copyCoords.triggered.connect(self.parentPlotDock.copy_coordinates)
        self.menu.addAction(copyCoords)

    def wheelEvent(self, e):
        """
        Handle mouse wheel events for zooming the image.

        Delegates to the parent ViewBox wheel event handler, then determines whether
        to immediately resample the image based on the image size. For very large
        images (over 5 GiB), sets a flag to defer resampling until explicitly triggered.

        Parameters
        ----------
        self : object
            The class instance.
        e : QWheelEvent
            The wheel event.

        Returns
        -------
        None
            This method handles zoom operations and doesn't return a value.
        """

        super().wheelEvent(e)
        if self.parentPlotDock.size > 5368709120: # 5 GiB
            self.zoomed = True
        else:
            self.autoResample.emit()
            self.parentPlotDock.parent().widget_interacted_signal.emit(self.parentPlotDock)

    def mouseDragEvent(self, e):
        """
        Handle mouse drag events for panning the image.

        Accepts all drag events and emits a signal to trigger image resampling
        when the drag operation finishes.

        Parameters
        ----------
        self : object
            The class instance.
        e : QMouseEvent
            The mouse drag event.

        Returns
        -------
        None
            This method handles pan operations and doesn't return a value.
        """

        e.accept()
        if e.isFinish():
            self.autoResample.emit()
        super().mouseDragEvent(e)

class FileOpenWorker(QObject):
    started = Signal()
    finished = Signal()

    def __init__(self, reader, plotWidgetDock):
        """
        Worker for asynchronously loading and processing image files.

        Creates a worker object that runs in a separate thread to load and process
        image data without freezing the UI. Handles initial decimation and remapping
        of the image data.

        Parameters
        ----------
        self : object
            The class instance.
        reader : object
            The file reader that provides access to the image data.
        plotWidgetDock : PlotWidgetDock
            The plot widget dock where the image will be displayed.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        super().__init__()
        self.reader = reader
        self.plotWidgetDock = plotWidgetDock

    def run(self):
        """
        Execute the file loading and processing operation.

        Emits signals at the start and end of the operation, loads the image data,
        calculates appropriate decimation factors based on image and window size,
        and updates the plot widget with the processed data.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method processes the image data and doesn't return a value.
        """

        self.started.emit()

        imageWidth = self.reader.get_data_size_as_tuple()[0][1]
        imageHeight = self.reader.get_data_size_as_tuple()[0][0]

        decimationFactor = max(imageWidth / self.plotWidgetDock.windowWidth,
                               imageHeight / self.plotWidgetDock.windowHeight)

        decimatedData = self.reader[::int(math.ceil(decimationFactor)), ::int(math.ceil(decimationFactor))]
        self.plotWidgetDock.preRemappedData = decimatedData

        self.plotWidgetDock.maxDecimatedImageWidth = len(decimatedData[0])
        self.plotWidgetDock.maxDecimatedImageHeight = len(decimatedData)

        remappedData = self.plotWidgetDock.remap_function(decimatedData)
        #self.data = remappedData

        self.plotWidgetDock.reader = self.reader
        self.plotWidgetDock.dataShapeH = imageHeight
        self.plotWidgetDock.dataShapeW = imageWidth
        self.plotWidgetDock.decimationFactor = int(math.ceil(decimationFactor))
        self.plotWidgetDock.stepSize = self.plotWidgetDock.decimationFactor

        self.plotWidgetDock.structure = self.reader.sicd_meta

        self.plotWidgetDock.img.setImage(remappedData)
        self.plotWidgetDock.enhancePushButton.setEnabled(True)
        self.plotWidgetDock.plotWidget.getPlotItem().getViewBox().autoRange()

        self.finished.emit()

class UiLoader(QUiLoader):

    def __init__(self, baseinstance, customWidgets=None):
        """
        Custom UI loader that supports loading UI files with custom widgets.

        Extends QUiLoader to bind loaded UI elements to an instance and to create
        custom widget types not natively supported by Qt.

        Parameters
        ----------
        self : object
            The class instance.
        baseinstance : QWidget
            The widget instance to which the UI elements will be bound.
        customWidgets : dict or None, optional
            A dictionary mapping custom widget class names to their implementations.
            Default is None.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets

    def createWidget(self, class_name, parent=None, name=''):
        """
        Create a widget of the specified class.

        Overrides the base class method to handle both standard Qt widgets and
        custom widgets defined in the customWidgets dictionary. Automatically
        sets attributes on the base instance for named widgets.

        Parameters
        ----------
        self : object
            The class instance.
        class_name : str
            The name of the widget class to create.
        parent : QWidget or None, optional
            The parent widget for the new widget. Default is None.
        name : str, optional
            The object name for the new widget. Default is an empty string.

        Returns
        -------
        QWidget
            The created widget instance.

        Raises
        ------
        Exception
            If the requested custom widget is not found in the customWidgets dictionary.
        """

        if parent is None and self.baseinstance:
            return self.baseinstance
        else:
            if class_name in self.availableWidgets():
                widget = QUiLoader.createWidget(self, class_name, parent, name)
            else:
                try:
                    widget = self.customWidgets[class_name](parent)
                except (TypeError, KeyError) as e:
                    raise Exception('No custom widget ' + class_name + ' found in customWidgets param of UiLoader __init__.')
            if self.baseinstance:
                setattr(self.baseinstance, name, widget)
            return widget

class CustomFileDialog(QFileDialog):

    def __init__(self, parent = None, f=None):
        """
        Initialize a custom file dialog with simplified UI and modified behavior.

        Creates a file dialog that doesn't use the native dialog and customizes various
        elements to better suit the application's needs. Removes standard buttons,
        rearranges the layout, and adds tooltips to help users navigate the dialog.

        Parameters
        ----------
        self : object
            The class instance.
        parent : QWidget or None, optional
            The parent widget. Default is None.
        f : Qt.WindowFlags or None, optional
            Window flags for the dialog. Default is None.

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        super(CustomFileDialog, self).__init__(parent, f)
        self.setOptions(QFileDialog.DontUseNativeDialog)

        # remove accept and reject buttons
        buttonBox = self.findChild(QDialogButtonBox)
        cancelButton = buttonBox.button(QDialogButtonBox.Cancel)
        openButton = buttonBox.button(QDialogButtonBox.Open)
        buttonBox.removeButton(cancelButton)
        buttonBox.removeButton(openButton)

        # repurpose lookInLabel
        lookInLabel = self.findChild(QLabel, 'lookInLabel')
        lookInLabel.setText('Favorites:')
        lookInLabel.setToolTip(ToolTips.FileDialog.favorite_directories_window())

        # make splitter vertical to conserve space
        splitter = self.findChild(QSplitter)
        splitter.setOrientation(Qt.Vertical)
        splitter.findChild(QListView).setToolTip(ToolTips.FileDialog.favorite_directories_window())
        
        # label directory contents section
        lowerSplitterFrame = splitter.findChild(QFrame)
        directoryBrowserVbox = lowerSplitterFrame.findChild(QVBoxLayout)
        currentDirLabel = QLabel('Current Directory')
        currentDirLabel.setObjectName('currentDirLabel')
        directoryBrowserVbox.insertWidget(0, QLabel('Current Directory Contents:'))
        lowerSplitterFrame.setToolTip(ToolTips.FileDialog.directory_contents_window())

        # repurpose lookInLabel
        lookInLabel = self.findChild(QLabel, 'lookInLabel')
        lookInLabel.setText('Favorites:')
    
        # get rid of fileName label
        fileNameLabel = self.findChild(QLabel, 'fileNameLabel')
        fileNameLabel.hide()

        # get rid of directory selector
        directoryDropDown = self.findChild(QComboBox)
        directoryDropDown.hide()

        # get rid of tool buttons
        toolButtons = self.findChildren(QToolButton)
        for button in toolButtons:
            button.hide()

        #get rid of file selector
        fileNameLine = self.findChild(QLineEdit)
        fileNameLine.hide()

        # add tooltips to filetype filter
        self.findChild(QComboBox, "fileTypeCombo").setToolTip(ToolTips.FileDialog.file_type_filter())
        self.findChild(QLabel, "fileTypeLabel").setToolTip(ToolTips.FileDialog.file_type_filter())

    def set_sidebar_directories(self, dirs):
        """
        Set the sidebar directories of the file dialog.

        Converts a list of directory paths to QUrl objects and sets them as the
        sidebar URLs in the file dialog.

        Parameters
        ----------
        self : object
            The class instance.
        dirs : list of str
            List of directory paths to display in the sidebar.

        Returns
        -------
        None
            This method updates the sidebar and doesn't return a value.
        """

        urls = []
        for x in dirs:
            urls.append(QUrl.fromLocalFile(x))
        self.setSidebarUrls(urls)

    def accept(self):
        """
        Handle the accept action for the dialog.

        Emits the accepted signal when the dialog is accepted, but does not close
        the dialog as the standard implementation would.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method emits a signal and doesn't return a value.
        """

        self.accepted.emit()

    def reject(self):
        """
        Handle the reject action for the dialog.

        Emits the rejected signal when the dialog is rejected, but does not close
        the dialog as the standard implementation would.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method emits a signal and doesn't return a value.
        """

        self.rejected.emit()

class CustomMessageBox(QMessageBox):

    def resizeEvent(self, event) :
        """
        Handle resize events for the message box.

        Overrides the default resize behavior to enforce a fixed size for the
        message box, ensuring a consistent and compact appearance.

        Parameters
        ----------
        self : object
            The class instance.
        event : QResizeEvent
            The resize event.

        Returns
        -------
        None
            This method enforces size constraints and doesn't return a value.
"""

        QMessageBox.resizeEvent(self, event)
        self.setFixedHeight(5)
        self.setFixedWidth(250) 

class MITMStyleSheet:
    """
    Manage stylesheet modifications that can't be handled by QSS files alone.

    This class provides static methods and nested classes to handle dynamic styling 
    of various UI components based on their state (selected/unselected) and the 
    application's appearance mode (light/dark). It centralizes styling logic and 
    color definitions to maintain consistency throughout the application.

    The class is organized into nested classes for different widget types:
    - PlotWidgetDock: Styles for plot widget docks, including progress bars,
    view boxes, and widget containers
    - DirectoryButtons: Styles for directory navigation buttons
    - MetaIcon: Styles for the meta-icon widget display

    Each nested class contains color definitions, style sheets, and helper methods
    to generate appropriate styles based on the current state and appearance mode.
    """

    class PlotWidgetDock:
        ProgressBar = ('QProgressBar {'
                       '    border: 1px solid black;'
                       '    border-top-right-radius: 7px;'
                       '    border-top-left-radius: 7px;'
                       '    border-bottom-right-radius: 7px;'
                       '    border-bottom-left-radius: 7px;'
                       '}'
                       'QProgressBar::chunk {'
                       '    background: QLinearGradient(spread:reflect, x1:0, y1:0, x2:0.5, y2:0, stop:0 #D3D3D3, stop:1 #4B9FC1);'
                       '    border-top-right-radius: 7px;'
                       '    border-top-left-radius: 7px;'
                       '    border-bottom-right-radius: 7px;'
                       '    border-bottom-left-radius: 7px;'
                       '    margin: 2px;'
                       '    color: white;'
                       '}')

        class ViewBox:
            Light = QColor(211, 211, 211)
            Dark = QColor(53, 53, 53)
            LightBlue = qdarkstyle.colorsystem.Blue.B90
            DarkBlue = qdarkstyle.colorsystem.Blue.B20

            def get_color(isSelected, darkMode):
                if(isSelected):
                    if(darkMode):
                        return MITMStyleSheet.PlotWidgetDock.ViewBox.DarkBlue
                    else: 
                        return MITMStyleSheet.PlotWidgetDock.ViewBox.LightBlue
                else:
                    if(darkMode):
                        return MITMStyleSheet.PlotWidgetDock.ViewBox.Dark
                    else: 
                        return MITMStyleSheet.PlotWidgetDock.ViewBox.Light
       
        class Widget:
            DockWidgetContents_Light = qdarkstyle.colorsystem.Blue.B110
            DockWidgetContents_Dark = '#12263b'

            UpperControlsWidget_Light = qdarkstyle.colorsystem.Blue.B100
            UpperControlsWidget_Dark = '#415A77'

            PushButton_Light = qdarkstyle.colorsystem.Blue.B100
            PushButton_Dark = '#1b263b'

            def selected_style_sheet(darkMode):
                dockWidgetContentsColor = MITMStyleSheet.PlotWidgetDock.Widget.DockWidgetContents_Light
                upperControlsWidgetColor = MITMStyleSheet.PlotWidgetDock.Widget.UpperControlsWidget_Light
                pushButtonColor = MITMStyleSheet.PlotWidgetDock.Widget.PushButton_Light

                if(darkMode): 
                    dockWidgetContentsColor = MITMStyleSheet.PlotWidgetDock.Widget.DockWidgetContents_Dark
                    upperControlsWidgetColor = MITMStyleSheet.PlotWidgetDock.Widget.UpperControlsWidget_Dark
                    pushButtonColor = MITMStyleSheet.PlotWidgetDock.Widget.PushButton_Dark

                return '''
                    QDockWidget::title {
                        background: palette(highlight);
                        border: 1px solid palette(midlight)
                    }

                    QWidget#dockWidgetContents {
                        background: %s
                    }

                    QWidget#upperControlsWidget {
                        background: %s   
                    }

                    QPushButton {
                        background: %s 
                    }

                    QComboBox {
                        background: %s
                    }
                ''' % (dockWidgetContentsColor, upperControlsWidgetColor, pushButtonColor, pushButtonColor)
        
        def change_color(plot_widget, isSelected, darkMode):
            plot_widget.setStyleSheet(MITMStyleSheet.PlotWidgetDock.Widget.selected_style_sheet(darkMode) if isSelected else "")
            plot_widget.plotWidget.getPlotItem().getViewBox().setBackgroundColor(MITMStyleSheet.PlotWidgetDock.ViewBox.get_color(isSelected, darkMode))
            plot_widget.plotWidget.getPlotItem().getViewBox().setBorder(color=MITMStyleSheet.PlotWidgetDock.ViewBox.get_color(isSelected, darkMode), width=2)

    class DirectoryButtons:
        SelectedButton_Light = '#c9c9c9'
        SelectedButton_Dark = '#202020'

        def get_style_sheet(selected, darkMode):
            color = MITMStyleSheet.DirectoryButtons.SelectedButton_Light 
            if darkMode :
                color = MITMStyleSheet.DirectoryButtons.SelectedButton_Dark

            fontstr = 'font-weight: bold;' if selected else ''
            colorstr = 'background: %s;' % color if selected else ''
            
            return '''
                QPushButton {
                    padding-left: 5px;
                    padding-right: 5px;
                    padding-top: 3px;
                    padding-bottom: 3px;
                    %s
                    %s
                }
            ''' % (fontstr, colorstr)
        
        def change_color(button, darkMode):
            if 'font-weight' in button.styleSheet():
                button.setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(True, darkMode))
            else:
                button.setStyleSheet(MITMStyleSheet.DirectoryButtons.get_style_sheet(False, darkMode))

    class MetaIcon:
        StyleSheet = ('PlotWidget { background: #00000000 }'
                       'QTableWidget { background: #1F1F1F }'
                       'QTableWidget { color: #FFFFFF }'
                       'QTableWidget { border: 2px solid #4B9FC1}')
        PlotBackgroundColor = '#00000000'
        ViewBoxBorderColor = '#4B9FC1'
        LayoverColor = '#FF8C00'
        ShadowColor = '#00A6FB'
        MultipathColor = '#FF031C'
        Font = 'Consolas'
        FontSize = 12

