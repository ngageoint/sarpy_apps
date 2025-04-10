from PyMITM.mitm_viewer import Viewer, MITMStyleSheet
from PyMITM.mitm_model  import Model

from urllib.parse import unquote, urlparse
import sys

class Controller():

    def __init__(self, sys_args=None):
        """
        Main controller class that connects the viewer UI and data model.

        Establishes the application's MVC (Model-View-Controller) architecture by
        connecting the Viewer (UI) and Model (data) components through signal handlers
        and callback methods. The controller handles all interactions between the UI
        and the underlying data.

        Responsibilities include:
        - Initial setup of application components
        - Configuration loading and saving
        - File loading and processing
        - Event handling for UI interactions
        - Metadata extraction and display
        - Plot widget management
        - Aspect ratio calculation and application

        The controller is responsible for the core application logic, translating
        user interactions in the viewer into data operations in the model, and
        updating the UI based on the results of those operations.

        Parameters
        ----------
        self : object
            The class instance.
        sys_args : list or None, optional
            Command line arguments passed to the application. Default is None.
            sys_args[0] is used for configuration file path
            sys_args[1] is used for initial file to open

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        self.viewer = Viewer(fileopen=sys_args[1] if sys_args is not None and len(sys_args) >= 2 else None)
        self.model  = Model(sys_args[0] if sys_args is not None and len(sys_args) > 0 else None)

        self.viewer.fileDropped.connect(self.file_dropped_handler)
        self.viewer.doubleClicked.connect(self.file_double_clicked_handler)
        self.viewer.openMetaIcon.connect(self.open_metaicon_handler)
        self.viewer.newPlotButton.clicked.connect(self.plot_button_handler)
        self.viewer.fileDialog.directoryEntered.connect(self.double_clicked_handler)
        self.viewer.widget_changed_signal.connect(self.update_ui_element_handler)
        self.viewer.requestAspectRatio.connect(self.get_aspect_ratio)
        self.viewer.windowClosed.connect(self.model.config.write_config_file)

        self.model.setup_config('mitm.cfg')
        self.viewer.fileDialog.setNameFilters(self.model.config.fileFormats)
        self.viewer.fileDialog.set_sidebar_directories(self.model.config.favoriteDirs)

    def file_dropped_handler(self, fileName, plotWidgetDock):
        """
        Handle files dropped onto a plot widget.

        Processes files dropped via drag and drop operations by parsing the URL,
        adjusting for platform-specific path formatting, reading the file using
        the model, and displaying it in the specified plot widget.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            URL or path of the dropped file.
        plotWidgetDock : PlotWidgetDock
            The plot widget that received the dropped file.

        Returns
        -------
        None
            This method processes the file and updates the UI.
        """

        filePath = unquote(urlparse(fileName).path)

        if sys.platform == 'win32':
            filePath = filePath[1:]

        reader, size = self.model.basic_file_read(filePath)
        plotWidgetDock.set_file_name(fileName.split('/')[-1])
        plotWidgetDock.size = size
        self.viewer.threaded_display_image(reader, plotWidgetDock)

    def file_double_clicked_handler(self, fileName, plotWidgetDock):
        """
        Handle files selected via double-click in the file browser.

        Reads the selected file using the model and displays it in the
        specified plot widget. Updates the widget's filename property.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Path of the selected file.
        plotWidgetDock : PlotWidgetDock
            The plot widget where the file should be displayed.

        Returns
        -------
        None
            This method processes the file and updates the UI.
        """

        plotWidgetDock.set_file_name(fileName.split('/')[-1])
        reader, size = self.model.basic_file_read(fileName)
        plotWidgetDock.size = size
        self.viewer.threaded_display_image(reader, plotWidgetDock)

    def open_metaicon_handler(self, fileName):
        """
        Handle requests to open the meta-icon display.

        Retrieves metadata for the specified file and passes it to the
        viewer to display in the meta-icon widget.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Name of the file whose metadata should be displayed.

        Returns
        -------
        None
            This method updates the meta-icon display.
        """

        metaData = self.model.get_metadata_from_open_reader(fileName)
        self.viewer.display_metaicon(metaData)

    def update_ui_element_handler(self, plot):
        """
        Update UI elements when the current plot widget changes.

        If the plot has a file loaded and the meta-icon widget is visible,
        updates the meta-icon to display metadata for the current file.

        Parameters
        ----------
        self : object
            The class instance.
        plot : PlotWidgetDock
            The plot widget that was interacted with or changed.

        Returns
        -------
        None
            This method updates the meta-icon if needed.
        """

        if plot and plot.fileName and self.viewer.metaicon_widget.isVisible():
            self.open_metaicon_handler(plot.fileName)

    def plot_button_handler(self):
        """
    Handle clicks on the "New Plot" button.

    Creates a new plot widget via the viewer.

    Parameters
    ----------
    self : object
        The class instance.

    Returns
    -------
    None
        This method adds a new plot widget to the UI.
    """

        self.viewer.add_plot()

    def double_clicked_handler(self):
        """
        Handle directory double-click events in the file browser.

        Navigates down into the selected directory by updating the
        directory path and navigation controls.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the file browser directory.
        """

        self.viewer.move_down_directory()

    def get_aspect_ratio(self, plotWidgetDock):
        """
        Get and apply the aspect ratio for an image.

        Retrieves the correct aspect ratio for the image from the model
        and applies it to the specified plot widget.

        Parameters
        ----------
        self : object
            The class instance.
        plotWidgetDock : PlotWidgetDock
            The plot widget whose image aspect ratio should be set.

        Returns
        -------
        None
            This method updates the image aspect ratio.
        """

        aspectRatio = self.model.get_aspect_ratio(plotWidgetDock.fileName)
        plotWidgetDock.apply_aspect_ratio_to_image(aspectRatio)

    def create_plot_on_startup(self, state):
        """
        Handle application startup to create the initial plot.

        Delegates to the viewer to create a plot widget during application
        startup, optionally loading an initial file.

        Parameters
        ----------
        self : object
            The class instance.
        state : Qt.ApplicationState
            The current state of the application.

        Returns
        -------
        None
            This method initializes the first plot widget.
        """

        self.viewer.create_plot_on_startup(state)

    def get_current_file_name(self):
        """
        Get the file name of the current plot widget.

        Retrieves the current plot widget and returns its file name.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        str
            The name of the file in the current plot widget.
        """

        current_widget = self.get_current_widget()
        file_name = current_widget.get_file_name()
        return file_name
    
    def get_current_widget(self):
        """
        Get the currently active plot widget.

        Returns the plot widget that is currently selected in the viewer.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        PlotWidgetDock
            The currently active plot widget.
        """

        return self.viewer._currentPlotWidget