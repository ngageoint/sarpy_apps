from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QMainWindow,
    QDockWidget,
    QGridLayout,
    QTabWidget,
    QLabel,
    QToolBar,
    QFileDialog,
    QColorDialog,
    QListWidget,
    QStatusBar,
    QComboBox,
    QMenu,
    QMenuBar,
    QTableWidgetItem,
    QTableWidget,
    QColorDialog,
    QSizePolicy,
    QAbstractItemView,
    QListWidgetItem,
    QInputDialog,
)

from PySide6.QtGui import (
    QPalette,
    QColor,
    QPixmap,
    QMouseEvent,
    QPen,
    QAction,
    QActionGroup,
    QKeySequence,
)

from PySide6.QtCore import (
    Qt,
    QDir,
    QFile,
    QCoreApplication,
    QMetaObject,
    Signal,
    QModelIndex,
    QDirIterator,
    QEvent,
)

from typing import List, Dict, Tuple, Optional, Union, Any, Callable, TypeVar, Type, cast, Set
import numpy as np
from numpy.typing import NDArray

from PySide6.QtUiTools import QUiLoader

import pyqtgraph as pg

from PyRCS.ui_rcs_tool import Ui_RCSTool


pg.setConfigOptions(imageAxisOrder="row-major")  # needed to display image properly


class Viewer(QDockWidget, Ui_RCSTool):
    """
    Viewer class for the RCS (radar cross section) tool.
    
    This class serves as the core viewer in the MVC (Model-View-Controller) architecture
    for the RCS tool. It provides the graphical user interface that the user
    directly interacts with, and emits signals to inform the controller of user actions.
    
    Signals
    -------
    add_geometry_signal : Signal(list)
        Emitted when a new geometry is to be added, providing spawn coordinates.
    voids_toggle_signal : Signal(bool)
        Emitted when the void inclusion toggle is changed.
    app_state_signal : Signal()
        Emitted when the application state changes.
    
    Attributes
    ----------
    geometry_view_widget : GeometryViewWidget
        Widget for displaying the geometry preview.
    geometry_roi : Type[GeometryROI]
        Class for creating ROI objects.
    canvas : Type[Canvas]
        Class for managing the canvas display.
    rcs_export : ExportGEOJSON
        Dialog for exporting RCS data.
    rcs_import : ImportGEOJSON
        Dialog for importing RCS data.
    rcs_slow_plot_widget : RCSPlotWidget
        Widget for displaying slow-time RCS plots.
    rcs_fast_plot_widget : RCSPlotWidget
        Widget for displaying fast-time RCS plots.
    """

    # signals
    add_geometry_signal = Signal(list, name="add_geometry_signal")
    voids_toggle_signal = Signal(bool, name="voids_toggle_signal")
    app_state_signal = Signal(name="app_state_signal")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the RCS Viewer.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget, defaults to None.
        """
        QDockWidget.__init__(self, parent)
        self.setupUi(self)
        # loadUi(sys.argv[0].replace('main.py', '') + 'rcs_ui/rcs_tool.ui', self)

        # loading some of our externally defined GUI shiz
        self.geometry_view_widget = GeometryViewWidget()
        self.geometry_roi = GeometryROI
        self.canvas = Canvas
        self.rcs_export = ExportGEOJSON()
        self.rcs_import = ImportGEOJSON()

        self.rcs_table_view.update_headers()

        self.rcs_slow_plot_widget = RCSPlotWidget(parent=self)
        self.rcs_slow_plot_view.addWidget(self.rcs_slow_plot_widget)
        self.rcs_fast_plot_widget = RCSPlotWidget(parent=self)
        self.rcs_fast_plot_view.addWidget(self.rcs_fast_plot_widget)

        self.rcs_import_button.clicked.connect(self.rcs_import.import_clicked)
        self.rcs_export_button.clicked.connect(self.rcs_export.export_clicked)

        self.right_click_add_geometry = QAction("Add Geometry", self)

        self.rcs_measure_units_combo_box.setItemText(2, "β\u2080")
        self.rcs_measure_units_combo_box.setItemText(3, "γ\u2080")
        self.rcs_measure_units_combo_box.setItemText(4, "σ\u2080")

        self.rcs_toggle_voids_button.stateChanged.connect(self.voids_toggle_handler)

        self.rcs_roi_view.addWidget(
            self.geometry_view_widget
        )  # can rename to rcs_geometry_view later

    def voids_toggle_handler(self) -> None:
        """
        Handle toggling of the void inclusion setting.
        
        Emits a signal with the current state of the toggle button.
        """
        self.voids_toggle_signal.emit(self.rcs_toggle_voids_button.isChecked())

    def azimuth_reference_angle_dialog(self) -> int:
        """
        Display a dialog for entering a reference azimuth angle.
        
        Returns
        -------
        int
            The reference angle in degrees, or 0 if canceled.
        """
        # Open an input dialog for integer input between 0 and 180 degrees
        value, ok = QInputDialog.getInt(
            self,
            "Reference Azimuth Angle",  # Dialog title
            "Enter a reference azimuth angle between 0 and 180 degrees.",  # Label text
            value=0,  # Default value
            minValue=0,  # Minimum value
            maxValue=180,  # Maximum value
        )

        if ok:  # If the user clicked OK
            return value
        else:  # If the user clicked Cancel
            return 0


class GeometryColorSelect(QColorDialog):
    """
    Dialog for selecting colors for geometries.
    
    Inherits from QColorDialog to provide color selection functionality.
    """
    
    def __init__(self) -> None:
        """Initialize the color selection dialog."""
        super().__init__()


class ExportGEOJSON(QFileDialog):
    """
    Dialog for exporting RCS data to GeoJSON format.
    
    Provides a file dialog for saving RCS data and emits a signal with the selected file path.
    
    Signals
    -------
    export_signal : Signal(str)
        Emitted when an export location is selected, containing the file path.
    """
    
    export_signal = Signal(str, name="export_signal")

    def __init__(self) -> None:
        """Initialize the export dialog."""
        super().__init__()

    def export_clicked(self) -> None:
        """
        Handle the export button click.
        
        Opens a save file dialog and emits a signal with the selected file path.
        """
        rcs_export_file_name = self.getSaveFileName(
            parent=None,
            caption="Select the export location.",
            filter="RCS collections (*.nitf.rcs.json)",
        )
        if rcs_export_file_name:
            self.export_signal.emit(str(rcs_export_file_name[0]))
        else:
            pass


class ImportGEOJSON(QFileDialog):
    """
    Dialog for importing RCS data from GeoJSON or MATLAB format.
    
    Provides a file dialog for opening RCS data files and emits a signal with the selected file path.
    
    Signals
    -------
    import_signal : Signal(str)
        Emitted when an import file is selected, containing the file path.
    """
    
    import_signal = Signal(str, name="import_signal")

    def __init__(self) -> None:
        """Initialize the import dialog."""
        super().__init__()

    def import_clicked(self) -> None:
        """
        Handle the import button click.
        
        Opens a file dialog and emits a signal with the selected file path.
        """
        rcs_import_file_name = self.getOpenFileNames(
            parent=None,
            caption="Select geojson to import.",
            filter="geojson (*.geojson *.json *.mat)",
        )[0]
        if rcs_import_file_name:
            self.import_signal.emit(str(rcs_import_file_name[0]))
        else:
            pass


# Type alias for ROI object
GeometryType = TypeVar('GeometryType', bound='GeometryROI')

class GeometryTableWidget(QTableWidget):
    """
    Table widget for displaying geometry information.
    
    Displays geometry names and RCS values, and handles selection and editing of geometries.
    
    Signals
    -------
    name_changed_signal : Signal(object, str)
        Emitted when a geometry name is changed, containing the geometry and new name.
    cell_changed_signal : Signal(object)
        Emitted when a cell in the table is changed, containing the selected geometry.
    
    Attributes
    ----------
    _rcs_display_units : int
        Index representing current display units (0=RCS, 1=PixelPower, 2=BetaZero, etc.).
    _units_header : str
        String representation of current units for table header.
    _geometries : List[GeometryROI]
        List of geometry objects displayed in the table.
    """
    
    name_changed_signal = Signal(object, str, name="named_changed_signal")
    cell_changed_signal = Signal(object, name="cell_changed_signal")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the geometry table widget.
        
        Parameters
        ----------
        *args : tuple
            Positional arguments passed to QTableWidget.
        **kwargs : dict
            Keyword arguments passed to QTableWidget.
        """
        super().__init__(*args, **kwargs)
        self._rcs_display_units: int = (
            0  # 0 RCS, 1 PixelPower, 2 BetaZero, 3 GammaZero, 4 SigmaZero
        )
        self._units_header: str = "RCS"  # default
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Geometry", self.get_units_header()])

        self._geometries: List[GeometryROI] = []
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # currently using the widget_changed_controller in the rcs_controller
        # only using populate geometries inside there to handle all updating,
        # in future use the add, remove and set to properly handle geometries more efficiently
        self.cellChanged.connect(self.name_changed)
        self.currentItemChanged.connect(self.table_geometry_select)

    def set_units_header(self, units_header: str) -> None:
        """
        Set the units header text.
        
        Parameters
        ----------
        units_header : str
            The new header text.
        """
        self._units_header = units_header

    def get_units_header(self) -> str:
        """
        Get the current units header text.
        
        Returns
        -------
        str
            The current header text.
        """
        return self._units_header

    def set_rcs_display_units(self, display_index: int) -> None:
        """
        Set the RCS display units based on the given index.
        
        Parameters
        ----------
        display_index : int
            Index representing the units (0=RCS, 1=PixelPower, 2=BetaZero, etc.).
            
        Raises
        ------
        Exception
            If an invalid display index is given.
        """
        # +1 is added to the indexs after pixel power because we are skipping the RCS value to match matlab implementation
        if display_index == 0:
            self.set_units_header("RCS")
            self._rcs_display_units = 0
        elif display_index == 1:
            self.set_units_header("PixelPower")
            self._rcs_display_units = 1
        elif display_index == 2:
            self.set_units_header("β\u2080")
            self._rcs_display_units = 3
        elif display_index == 3:
            self.set_units_header("γ\u2080")
            self._rcs_display_units = 4
        elif display_index == 4:
            self.set_units_header("σ\u2080")
            self._rcs_display_units = 5
        else:
            raise Exception("Error: Invalid display index given for RCS geometry table")

    def get_rcs_display_units(self) -> int:
        """
        Get the current RCS display units index.
        
        Returns
        -------
        int
            The current units index.
        """
        return self._rcs_display_units

    def name_changed(self, row: int, col: int) -> None:
        """
        Handle when a geometry name is changed in the table.
        
        Emits a signal with the geometry and new name when the name column is edited.
        
        Parameters
        ----------
        row : int
            The row index of the changed cell.
        col : int
            The column index of the changed cell.
        """
        if col == 0:
            self.name_changed_signal.emit(
                self._geometries[row], self.item(row, col).text()
            )
        else:
            pass

    def table_geometry_select(self) -> None:
        """
        Handle selection of a geometry in the table.
        
        Emits a signal with the selected geometry.
        """
        if self.get_geometries():
            self.cell_changed_signal.emit(self.get_geometries()[self.currentRow()])

    def image_geometry_select(self, geometry: GeometryType) -> None:
        """
        Select a geometry in the table based on an image selection.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry selected in the image.
        """
        geometries = self.get_geometries()
        selected_index = geometries.index(geometry)
        self.setCurrentCell(selected_index, 0)

    def add_geometry(self, geometry: GeometryType) -> None:
        """
        Add a geometry to the table.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry to add.
        """
        self.insertRow(self.rowCount())
        self._geometries.append(geometry)

    def remove_geometry(self, geometry: GeometryType) -> None:
        """
        Remove a geometry from the table.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry to remove.
        """
        geometries = self.get_geometries()
        self.removeRow((geometries.index(geometry)))
        del geometries[geometries.index(geometry)]

    def set_geometries(self, geometries: List[GeometryType]) -> None:
        """
        Set the list of geometries.
        
        Parameters
        ----------
        geometries : List[GeometryROI]
            List of geometry objects.
        """
        self._geometries = geometries

    def get_geometries(self) -> List[GeometryType]:
        """
        Get the list of geometries.
        
        Returns
        -------
        List[GeometryROI]
            List of geometry objects.
        """
        return self._geometries

    def populate_geometries(self, geometries: List[GeometryType], include_voids: bool) -> None:
        """
        Populate the table with geometries.
        
        Parameters
        ----------
        geometries : List[GeometryROI]
            List of geometry objects.
        include_voids : bool
            Whether to include voids in RCS calculations.
        """
        self.clear()
        self.setRowCount(0)
        self.set_geometries(geometries)
        for i, geometry in enumerate(geometries):
            if include_voids:
                rcs_feature = geometry.get_rcs_feature_w_voids()
            else:
                rcs_feature = geometry.get_rcs_feature_wo_voids()

            self.insertRow(self.rowCount())
            name_item = QTableWidgetItem(geometry.get_name())
            self.setItem(i, 0, name_item)
            # the rcs_item is currently only showing rcs values not including voids bugfix
            rcs_item = QTableWidgetItem(
                f"{(10 * np.log10(rcs_feature.properties.parameters[self.get_rcs_display_units()].value.mean)):.2f}"
            )
            rcs_item.setFlags(rcs_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 1, rcs_item)
        self.setHorizontalHeaderLabels(["Geometry", self.get_units_header()])


# Type alias for RCS feature
RCSFeatureType = Any

class RCSTableWidget(QTableWidget):
    """
    Table widget for displaying detailed RCS values.
    
    Displays RCS values in various units with statistical information.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the RCS table widget.
        
        Parameters
        ----------
        *args : tuple
            Positional arguments passed to QTableWidget.
        **kwargs : dict
            Keyword arguments passed to QTableWidget.
        """
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def show_context_menu(self, pos: Any) -> None:
        """
        Show a context menu for the table.
        
        Parameters
        ----------
        pos : QPoint
            Position where the context menu was requested.
        """
        context_menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        context_menu.addAction(copy_action)
        context_menu.exec_(self.mapToGlobal(pos))

    def keyPressEvent(self, event: QEvent) -> None:
        """
        Handle key press events.
        
        Implements copy functionality for Ctrl+C.
        
        Parameters
        ----------
        event : QKeyEvent
            The key press event.
        """
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def copy_selection(self) -> None:
        """
        Copy selected cells to clipboard.
        
        Formats selected data as tab-separated text.
        """
        selected_ranges = self.selectedRanges()
        if not selected_ranges:
            return

        copied_text = []
        for sel_range in selected_ranges:
            for row in range(sel_range.topRow(), sel_range.bottomRow() + 1):
                row_data = []
                for col in range(sel_range.leftColumn(), sel_range.rightColumn() + 1):
                    item = self.item(row, col)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        row_data.append("")
                copied_text.append("\t".join(row_data))

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(copied_text))

    def populate_rcs_table(self, rcs_feature: RCSFeatureType) -> None:
        """
        Populate the table with RCS feature data.
        
        Parameters
        ----------
        rcs_feature : RCSFeatureType
            Feature containing RCS data.
        """
        i = 0
        table_params = [
            item for i, item in enumerate(rcs_feature.properties.parameters) if i != 2
        ]

        def format_value(value: Optional[float], is_db: bool = False) -> str:
            if value is None:
                return ""
            if is_db:
                return f"{10 * np.log10(value):.2f}"
            return f"{value:.2f}"

        for parameters in table_params:
            self.setItem(i, 0, QTableWidgetItem(str(parameters.polarization)))
            self.setItem(
                i, 1, QTableWidgetItem(format_value(parameters.value.mean, is_db=True))
            )
            self.setItem(i, 2, QTableWidgetItem(format_value(parameters.value.mean)))
            self.setItem(i, 3, QTableWidgetItem(format_value(parameters.value.std)))
            self.setItem(i, 4, QTableWidgetItem(format_value(parameters.value.min)))
            self.setItem(i, 5, QTableWidgetItem(format_value(parameters.value.max)))
            i += 1

    def update_headers(self) -> None:
        """
        Update table headers with appropriate labels.
        
        Sets row count and vertical header labels.
        """
        self.setRowCount(5)
        self.setVerticalHeaderLabels(
            ["RCS", "Pixel Power", "β\u2080", "γ\u2080", "σ\u2080"]
        )


class GeometryViewWidget(pg.ImageView):
    """
    Widget for displaying geometry previews.
    
    Provides a view of geometries with customizable background color.
    
    Signals
    -------
    update_background_color_signal : Signal()
        Emitted when the background color is changed.
    """

    update_background_color_signal = Signal(name="update_background_color_signal")

    def __init__(self) -> None:
        """Initialize the geometry view widget."""
        super().__init__()

        self.ui.histogram.hide()
        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()
        self._background_color: Tuple[int, int, int] = (0, 0, 0)  # default
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos: Any) -> None:
        """
        Show a context menu for the view.
        
        Parameters
        ----------
        pos : QPoint
            Position where the context menu was requested.
        """
        context_menu = QMenu(self)

        background_color_select_action = context_menu.addAction("Background Color")
        background_color_select_action.triggered.connect(self.background_color_select)

        context_menu.addSeparator()
        default_actions = self.view.menu.actions()
        context_menu.addActions(default_actions)
        context_menu.exec_(self.mapToGlobal(pos))

    def update_background_color(self) -> None:
        """Emit signal indicating background color has changed."""
        self.update_background_color_signal.emit()

    def background_color_select(self) -> None:
        """Open a color dialog to select background color."""
        color = QColorDialog.getColor().getRgb()
        self.set_background_color(color)
        self.update_background_color()

    def set_background_color(self, background_color: Tuple[int, int, int, int]) -> None:
        """
        Set the background color.
        
        Parameters
        ----------
        background_color : Tuple[int, int, int, int]
            RGB color tuple.
        """
        self._background_color = background_color

    def get_background_color(self) -> Tuple[int, int, int, int]:
        """
        Get the current background color.
        
        Returns
        -------
        Tuple[int, int, int, int]
            RGB color tuple.
        """
        return self._background_color

    def update_geometry_view(self, selected_widget: Any, preview_image: NDArray) -> None:
        """
        Update the geometry view with a new preview image.
        
        Parameters
        ----------
        selected_widget : object
            The currently selected widget from MITM.
        preview_image : ndarray
            Image data to display.
        """
        background_color = list(self.get_background_color())[:3]

        aspect_ratio = selected_widget.plotWidget.getViewBox().getAspectRatio()

        self.view.setAspectLocked(lock=True, ratio=aspect_ratio)
        self.setImage(preview_image)
        self.getView().setBackgroundColor(
            QColor(background_color[0], background_color[1], background_color[2])
        )


class GeometryROI(pg.PolyLineROI):
    """
    Region of Interest class for polygonal geometries.
    
    Extends pyqtgraph's PolyLineROI with additional functionality for RCS calculations.
    
    Signals
    -------
    geometry_clicked_signal : Signal(object)
        Emitted when geometry is clicked.
    geometry_changed_signal : Signal(object)
        Emitted when geometry is modified.
    geometry_removed_signal : Signal(object)
        Emitted when geometry is removed.
    geometry_duplicate_signal : Signal(object)
        Emitted when geometry is duplicated.
    geometry_color_signal : Signal(object)
        Emitted when geometry color is changed.
    geometry_name_signal : Signal(object)
        Emitted when geometry name is changed.
        
    Attributes
    ----------
    duplicatable : bool
        Whether the geometry can be duplicated.
    colorable : bool
        Whether the geometry color can be changed.
    _color : str
        Hex color string.
    _name : str
        Name of the geometry.
    _rcs_feature_w_voids : RCSFeatureType or None
        RCS feature with voids included.
    _rcs_feature_wo_voids : RCSFeatureType or None
        RCS feature without voids included.
    view_box : pg.ViewBox or None
        The view box containing the ROI.
    """

    # Signals
    geometry_clicked_signal = Signal(object, name="geometry_clicked_signal")
    geometry_changed_signal = Signal(object, name="geometry_changed_signal")
    geometry_removed_signal = Signal(object, name="geometry_removed_signal")
    geometry_duplicate_signal = Signal(object, name="geometry_duplicate_signal")
    geometry_color_signal = Signal(object, name="geometry_color_signal")
    geometry_name_signal = Signal(object, name="geometry_name_signal")

    def __init__(self, positions: List[List[float]], closed: bool = False, **kwargs: Any) -> None:
        """
        Initialize the geometry ROI.
        
        Parameters
        ----------
        positions : List[List[float]]
            List of [x, y] coordinates for ROI vertices.
        closed : bool, optional
            Whether the ROI is closed (polygon), defaults to False.
        **kwargs : dict
            Additional arguments passed to pg.PolyLineROI.
        """
        super().__init__(positions, closed=closed, **kwargs)
        self.duplicatable: bool = True
        self.colorable: bool = True
        self._color: str = "#FFFFFF"  # white is default
        self._name: str = "None"  # default name

        self._rcs_feature_w_voids: Optional[RCSFeatureType] = None
        self._rcs_feature_wo_voids: Optional[RCSFeatureType] = None

        self._rcs_display_value: str = "rcs display value?"
        self.sigClicked.connect(self.geometry_clicked)
        self.sigRegionChangeFinished.connect(self.geometry_changed)
        self.sigRemoveRequested.connect(self.geometry_removed)

        self.geometry_color_signal.connect(self._update_geometry_properties)
        self.geometry_name_signal.connect(self._update_geometry_properties)

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        self.improve_handle_selectability()

        self.view_box: Optional[pg.ViewBox] = None

    def set_view_box(self, view_box: pg.ViewBox) -> None:
        """
        Set the view box for this ROI.
        
        Disconnects from previous view box if one exists, and connects to the new one.
        
        Parameters
        ----------
        view_box : pg.ViewBox
            The view box to connect to.
        """
        if self.view_box is not None:
            self.view_box.sigRangeChanged.disconnect(self.update_handle_positions)

        self.view_box = view_box
        if view_box is not None:
            view_box.sigRangeChanged.connect(self.update_handle_positions)

    def update_handle_positions(self) -> None:
        """Update handle positions when view range changes."""
        self.stateChanged()

    def improve_handle_selectability(self) -> None:
        """Make ROI handles easier to select by increasing size and visibility."""
        handles = self.getHandles()
        for handle in handles:
            # Increase the size of the handle
            if hasattr(handle, "setSize"):
                handle.setSize(12)  # Larger size

            if hasattr(handle, "setPen"):
                handle.setPen(pg.mkPen("y", width=3))
            if hasattr(handle, "setBrush"):
                handle.setBrush(pg.mkBrush(255, 255, 0, 180))

            if hasattr(handle, "setClickRadius"):
                handle.setClickRadius(10)

            if hasattr(handle, "setZValue"):
                handle.setZValue(self.zValue() + 1000)

    def addHandle(self, *args: Any, **kwargs: Any) -> Any:
        """
        Add a handle to the ROI with improved selectability.
        
        Parameters
        ----------
        *args : tuple
            Positional arguments passed to pg.PolyLineROI.addHandle.
        **kwargs : dict
            Keyword arguments passed to pg.PolyLineROI.addHandle.
            
        Returns
        -------
        Any
            The created handle.
        """
        handle = super().addHandle(*args, **kwargs)

        if hasattr(handle, "setSize"):
            handle.setSize(12)
        if hasattr(handle, "setPen"):
            handle.setPen(pg.mkPen("y", width=3))
        if hasattr(handle, "setBrush"):
            handle.setBrush(pg.mkBrush(255, 255, 0, 180))
        if hasattr(handle, "setClickRadius"):
            handle.setClickRadius(10)
        if hasattr(handle, "setZValue"):
            handle.setZValue(self.zValue() + 1000)

        return handle

    def setZValue(self, z: float) -> None:
        """
        Set Z-value for ROI and handles.
        
        Parameters
        ----------
        z : float
            Z-value to set.
        """
        super().setZValue(z)

        # Update handle z-values to stay above the ROI
        handles = self.getHandles()
        for handle in handles:
            if hasattr(handle, "setZValue"):
                handle.setZValue(z + 1000)

    def set_rcs_feature_wo_voids(self, feature_wo_voids: RCSFeatureType) -> None:
        """
        Set the RCS feature without voids.
        
        Parameters
        ----------
        feature_wo_voids : RCSFeatureType
            RCS feature without voids.
        """
        self._rcs_feature_wo_voids = feature_wo_voids
        self._update_geometry_properties(feature_wo_voids)

    def get_rcs_feature_wo_voids(self) -> RCSFeatureType:
        """
        Get the RCS feature without voids.
        
        Returns
        -------
        RCSFeatureType
            RCS feature without voids.
        """
        return self._rcs_feature_wo_voids

    def set_rcs_feature_w_voids(self, feature_w_voids: RCSFeatureType) -> None:
        """
        Set the RCS feature with voids.
        
        Parameters
        ----------
        feature_w_voids : RCSFeatureType
            RCS feature with voids.
        """
        self._rcs_feature_w_voids = feature_w_voids
        self._update_geometry_properties(feature_w_voids)

    def get_rcs_feature_w_voids(self) -> RCSFeatureType:
        """
        Get the RCS feature with voids.
        
        Returns
        -------
        RCSFeatureType
            RCS feature with voids.
        """
        return self._rcs_feature_w_voids

    def get_name(self) -> str:
        """
        Get the geometry name.
        
        Returns
        -------
        str
            The geometry name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """
        Set the geometry name.
        
        Parameters
        ----------
        name : str
            The new name.
        """
        self._name = name

    def get_color(self) -> str:
        """
        Get the geometry color.
        
        Returns
        -------
        str
            Hex color string.
        """
        return self._color

    def set_color(self, color: str) -> None:
        """
        Set the geometry color.
        
        Parameters
        ----------
        color : str
            Hex color string.
        """
        self._color = color

    def _update_geometry_properties(self, feature: RCSFeatureType) -> None:
        """
        Update geometry properties in the RCS feature.
        
        Parameters
        ----------
        feature : RCSFeatureType
            Feature to update.
        """
        geometry_properties = {
            "type": "GeometryProperties",
            "color": str(self.get_color()),
            "type": "GeometryProperties",
            "name": str(self.get_name()),
        }
        feature.properties.add_geometry_property(geometry_properties)

    def set_rcs_data(self, rcs_data: Any) -> None:
        """
        Set RCS data for the geometry.
        
        Parameters
        ----------
        rcs_data : Any
            RCS data to set.
        """
        pass

    def get_rcs_display_value(self) -> str:
        """
        Get the RCS display value.
        
        Returns
        -------
        str
            RCS display value.
        """
        return self._rcs_display_value

    def duplicate_geometry_clicked(self) -> None:
        """
        Handle duplicate geometry request.
        
        Creates a duplicate of this geometry and emits a signal with the new geometry.
        """
        positions = [point.copy() for point in self.getState()["points"]]
        loc = self.getState()["pos"]
        duplicated_geometry = GeometryROI(
            positions=positions,
            pos=loc,
            closed=True,
            removable=True,
            movable=True,
            snapSize=1,
            rotateSnap=False,
            translateSnap=False,
            scaleSnap=False,
            rotatable=False,
        )

        self.geometry_duplicate_signal.emit(duplicated_geometry)

    def color_geometry_clicked(self) -> None:
        """
        Handle color geometry request.
        
        Opens a color dialog and emits a signal when a color is selected.
        """
        color = GeometryColorSelect.getColor().name()
        self.set_color(color)
        self.geometry_color_signal.emit(self)

    def getMenu(self) -> QMenu:
        """
        Get the context menu for this geometry.
        
        Returns
        -------
        QMenu
            The context menu.
        """
        if self.menu is None:
            self.menu = QMenu()
            self.menu.setTitle(QCoreApplication.translate("Geometry", "Geometry"))
            if self.removable:
                remAct = QAction(
                    QCoreApplication.translate("Geometry", "Remove Geometry"), self.menu
                )
                remAct.triggered.connect(self.geometry_removed)
                self.menu.addAction(remAct)
                self.menu.remAct = remAct
            if self.duplicatable:
                dupAct = QAction(
                    QCoreApplication.translate("Geometry", "Duplicate Geometry"),
                    self.menu,
                )
                dupAct.triggered.connect(self.duplicate_geometry_clicked)
                self.menu.addAction(dupAct)
                self.menu.dupAct = dupAct
            if self.colorable:
                colAct = QAction(
                    QCoreApplication.translate("Geometry", "Color Geometry"), self.menu
                )
                colAct.triggered.connect(self.color_geometry_clicked)
                self.menu.addAction(colAct)
                self.menu.colAct = colAct
        return self.menu

    def geometry_clicked(self) -> None:
        """Handle geometry clicked event by emitting a signal."""
        self.geometry_clicked_signal.emit(self)

    def geometry_changed(self) -> None:
        """Handle geometry changed event by emitting a signal."""
        self.geometry_changed_signal.emit(self)

    def geometry_removed(self) -> None:
        """Handle geometry removed event by emitting a signal."""
        self.geometry_removed_signal.emit(self)


class Canvas:
    """
    Canvas for managing geometries.
    
    Provides methods for tracking and manipulating geometries on the plot canvas.
    
    Attributes
    ----------
    _current_geometry : GeometryROI or None
        The currently selected geometry.
    _previous_geometry : GeometryROI or None
        The previously selected geometry.
    _current_related_geometries : List[GeometryROI] or None
        List of geometries related to the current geometry.
    _previous_related_geometries : List[GeometryROI] or None
        List of geometries related to the previous geometry.
    _geometries : List[GeometryROI]
        List of all geometries on the canvas.
    _plotWidget : pg.PlotWidget or None
        The plot widget containing the canvas.
    """
    
    def __init__(self) -> None:
        """Initialize the canvas."""
        self._current_geometry: Optional[GeometryROI] = None
        self._previous_geometry: Optional[GeometryROI] = None
        self._current_related_geometries: Optional[List[GeometryROI]] = None
        self._previous_related_geometries: Optional[List[GeometryROI]] = None
        self._geometries: List[GeometryROI] = []
        self._plotWidget: Optional[pg.PlotWidget] = None

    def set_current_geometry(self, geometry: Optional[GeometryROI]) -> None:
        """
        Set the current geometry.
        
        Parameters
        ----------
        geometry : GeometryROI or None
            The geometry to set as current.
        """
        if self.get_current_geometry() is not None:
            self._set_previous_geometry(self.get_current_geometry())
        self._current_geometry = geometry

    def _set_previous_geometry(self, geometry: GeometryROI) -> None:
        """
        Set the previous geometry.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry to set as previous.
        """
        self._previous_geometry = geometry

    def get_previous_geometry(self) -> Optional[GeometryROI]:
        """
        Get the previous geometry.
        
        Returns
        -------
        GeometryROI or None
            The previous geometry.
        """
        return self._previous_geometry

    def get_current_geometry(self) -> Optional[GeometryROI]:
        """
        Get the current geometry.
        
        Returns
        -------
        GeometryROI or None
            The current geometry.
        """
        return self._current_geometry

    def set_current_related_geometries(self, related_geometries: Optional[List[GeometryROI]]) -> None:
        """
        Set the current related geometries.
        
        Parameters
        ----------
        related_geometries : List[GeometryROI] or None
            List of related geometries.
        """
        if self.get_current_related_geometries() is not None:
            self._set_previous_related_geometries(self.get_current_related_geometries())
        self._current_related_geometries = related_geometries

    def get_current_related_geometries(self) -> Optional[List[GeometryROI]]:
        """
        Get the current related geometries.
        
        Returns
        -------
        List[GeometryROI] or None
            List of related geometries.
        """
        return self._current_related_geometries

    def _set_previous_related_geometries(self, related_geometries: List[GeometryROI]) -> None:
        """
        Set the previous related geometries.
        
        Parameters
        ----------
        related_geometries : List[GeometryROI]
            List of related geometries.
        """
        self._previous_related_geometries = related_geometries

    def get_previous_related_geometries(self) -> Optional[List[GeometryROI]]:
        """
        Get the previous related geometries.
        
        Returns
        -------
        List[GeometryROI] or None
            List of related geometries.
        """
        return self._previous_related_geometries

    def get_geometries(self) -> List[GeometryROI]:
        """
        Get all geometries on the canvas.
        
        Returns
        -------
        List[GeometryROI]
            List of all geometries.
        """
        geometries = self._geometries
        return geometries

    def set_geometries(self, geometries: List[GeometryROI]) -> None:
        """
        Set the list of geometries.
        
        Parameters
        ----------
        geometries : List[GeometryROI]
            List of geometries.
        """
        self._geometries = geometries

    def add_geometry(self, geometry: GeometryROI) -> None:
        """
        Add a geometry to the canvas.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry to add.
        """
        self._geometries.append(geometry)

    def remove_geometry(self, geometry: GeometryROI) -> None:
        """
        Remove a geometry from the canvas.
        
        Parameters
        ----------
        geometry : GeometryROI
            The geometry to remove.
        """
        del self._geometries[self._geometries.index(geometry)]
        self.set_current_geometry(None)

    def update_geometry_ordering(self) -> None:
        """
        Update the Z-ordering of geometries.
        
        Sets the current geometry to the lowest Z-value and orders other geometries above it.
        """
        # Get the current selected geometry (exterior ROI)
        current_geometry = self.get_current_geometry()

        # Get all geometries on screen
        all_geometries = self.get_geometries()

        # Filter out the current geometry
        other_geometries = [
            geometry for geometry in all_geometries if geometry != current_geometry
        ]

        # First, increment all other geometries' z-values to avoid conflicts
        for geometry in other_geometries:
            geometry.setZValue(geometry.zValue() + len(all_geometries))

        # Set the current (exterior) geometry to lowest z-value
        current_geometry.setZValue(0)

        # Now set incrementing z-values for other geometries
        for i, geometry in enumerate(other_geometries):
            geometry.setZValue(i + 1)

    def render_geometry_selection(self) -> None:
        """
        Update the visual appearance of geometries based on selection state.
        
        The selected geometry gets a solid line, while others get dashed lines.
        """
        geometries = self.get_geometries()
        selected_geometry = self.get_current_geometry()
        for geometry in geometries:
            geometry.setPen(
                pg.mkPen(color=geometry.get_color(), width=1, style=Qt.DashLine)
            )
        selected_geometry.setPen(
            pg.mkPen(color=selected_geometry.get_color(), width=2, style=Qt.SolidLine)
        )


class RCSPlotWidget(pg.GraphicsLayoutWidget):
    """
    Widget for displaying RCS plots.
    
    Provides functionality for plotting RCS data with statistical markers.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the RCS plot widget.
        
        Parameters
        ----------
        *args : tuple
            Positional arguments passed to pg.GraphicsLayoutWidget.
        **kwargs : dict
            Keyword arguments passed to pg.GraphicsLayoutWidget.
        """
        super().__init__(*args, **kwargs)

        pg.setConfigOptions(antialias=True)
        self.default_plot = self.addPlot(title="")
        self.default_plot.showGrid(x=True, y=True)
        self.default_plot.setLabel("bottom", "")
        self.default_plot.setLabel("left", "")
        self.default_plot.plot([], [], pen="b", name="")
        self.addItem(self.default_plot, row=0, col=0)

    def populate_plot(self, x_data: NDArray, y_data: NDArray, 
                     x_axis_label: str, y_axis_label: str, plot_title: str) -> None:
        """
        Populate the plot with data.
        
        Parameters
        ----------
        x_data : ndarray
            X-axis data.
        y_data : ndarray
            Y-axis data.
        x_axis_label : str
            Label for the X-axis.
        y_axis_label : str
            Label for the Y-axis.
        plot_title : str
            Title for the plot.
        """
        if self.ci.getItem(0, 0) is not None:
            self.ci.removeItem(self.ci.getItem(0, 0))
        else:
            pass
        # now we can safely add the new plot item.

        plot = self.addPlot(title=plot_title)
        plot.showGrid(x=True, y=True)
        plot.setLabel("bottom", x_axis_label)
        plot.setLabel("left", y_axis_label)

        # Plot slow-time data
        plot.plot(x_data, y_data, pen="b", name=plot_title)

        if x_data.ndim == 1:
            # Add statistical lines for slow-time data
            valid_data = y_data[~np.isinf(y_data)]
            avg_slow = np.mean(valid_data)
            max_slow = np.max(valid_data)
            min_slow = np.min(valid_data)

            # Add horizontal lines for statistics
            plot.addLine(y=avg_slow, pen=pg.mkPen("r", style=Qt.DashLine))
            plot.addLine(y=max_slow, pen=pg.mkPen("r", style=Qt.DotLine))
            plot.addLine(y=min_slow, pen=pg.mkPen("r", style=Qt.DotLine))

            # Add legend
            legend1 = plot.addLegend()
            legend1.addItem(
                pg.PlotDataItem(pen=pg.mkPen("r", style=Qt.DashLine)), "Average"
            )
            legend1.addItem(
                pg.PlotDataItem(pen=pg.mkPen("r", style=Qt.DotLine)), "Min/Max"
            )

        self.addItem(plot, row=0, col=0)


class UiLoader(QUiLoader):
    """
    Custom UI loader for loading Qt UI files.
    
    This class inherits from PySide6.QtUiTools.QUiLoader and is used to
    load UI files generated from Qt Designer, allowing them to be connected
    to existing instances.
    
    Attributes
    ----------
    baseinstance : object
        The instance to set as the parent for all widgets.
    customWidgets : dict or None
        Dictionary of custom widgets to register.
    """

    def __init__(self, baseinstance: Optional[QWidget], customWidgets: Optional[Dict[str, Type]] = None) -> None:
        """
        Initialize the UI loader.
        
        Parameters
        ----------
        baseinstance : object or None
            The instance to set as the parent for all widgets.
        customWidgets : dict, optional
            Dictionary of custom widgets to register.
        """
        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets


def load_ui(uifile: str, baseinstance: Optional[QWidget] = None, 
            customWidgets: Optional[Dict[str, Type]] = None, 
            workingDirectory: Optional[str] = None) -> QWidget:
    """
    Load a Qt Designer UI file and connect it to an existing instance.
    
    Parameters
    ----------
    uifile : str
        Path to the UI file.
    baseinstance : QWidget, optional
        Instance to set as the parent for all widgets.
    customWidgets : dict, optional
        Dictionary of custom widgets to register.
    workingDirectory : str, optional
        Working directory for relative paths.
        
    Returns
    -------
    QWidget
        The loaded UI widget.
    """
    loader = UiLoader(baseinstance, customWidgets)
    # loader.registerCustomWidget(pg.PlotWidget)
    if workingDirectory is not None:
        loader.setWorkingDirectory(workingDirectory)
    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget