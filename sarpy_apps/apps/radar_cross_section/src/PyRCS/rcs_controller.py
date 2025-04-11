from PyRCS.rcs_viewer import Viewer
from PyRCS.rcs_model import Model
from typing import List, Tuple, Any, Optional, Dict, Union
import numpy as np
from PyMITM.mitm_subapplication import AbstractApp


class Controller(AbstractApp):
    """
    Controller for the Radar Cross Section (RCS) analysis tool.
    
    This class implements the controller component in the MVC (Model-View-Controller) 
    architecture for the RCS tool. It orchestrates the interaction between the RCS Model 
    (which handles data processing and RCS calculations) and the Viewer (which provides 
    the user interface).
    
    The controller coordinates:
    1. Geometry creation, manipulation, and visualization
    2. RCS calculations for selected geometries
    3. Signal processing for radar data visualization
    4. Import/export functionality for RCS data
    5. User interface interactions such as unit selection and display options
    
    The Controller integrates with the PyMITM application framework through the AbstractApp
    inheritance, which provides access to the underlying SAR (Synthetic Aperture Radar) data
    and visualization tools.
    
    Attributes
    ----------
    model : Model
        RCS tool Model class that performs data processing and calculations.
    viewer : Viewer
        RCS tool Viewer class that provides the graphical user interface components.
    mitm_controller : PyMITM.Controller
        The Controller instance from PyMITM application, providing access to SAR data
        and visualization infrastructure.
    
    Notes
    -----
    This class uses an event-driven architecture with signal connections between
    UI components and controller methods, allowing for reactive updates to user
    interactions.
    """

    def __init__(self, id: str) -> None:
        """
        Initialize the RCS Controller.
        
        Parameters
        ----------
        id : str
            Identifier for this controller instance used for registration within
            the PyMITM framework.
        """
        super().__init__()
        self.model = Model()
        self.viewer = Viewer()

        # Connect signals for geometry manipulation
        self.viewer.add_geometry_signal.connect(self.geometry_add_controller)

        self.viewer.rcs_geometry_table.name_changed_signal.connect(
            self.geometry_name_changed_controller
        )
        self.viewer.rcs_geometry_table.cell_changed_signal.connect(
            self.geometry_clicked_controller
        )

        # Connect import/export signals
        self.viewer.rcs_import.import_signal.connect(self.import_controller)
        self.viewer.rcs_export.export_signal.connect(self.export_controller)
        self.viewer.geometry_view_widget.update_background_color_signal.connect(
            self.background_color_controller
        )

        # Connect unit selection signals
        self.viewer.rcs_measure_units_combo_box.currentIndexChanged.connect(
            self.measure_units_combo_box_controller
        )
        self.viewer.rcs_measure_units_combo_box.currentIndexChanged.connect(
            self.calculate_rcs_controller
        )
        self.viewer.rcs_slow_time_units_combo_box.currentIndexChanged.connect(
            self.slow_time_units_combo_box_controller
        )

        # Connect void toggle signals
        self.viewer.voids_toggle_signal.connect(self.model.set_include_voids)
        self.viewer.voids_toggle_signal.connect(self.calculate_rcs_controller)
        self.viewer.voids_toggle_signal.connect(self.update_geometry_table)
        
        # Connect geometry add buttons
        self.viewer.rcs_add_geometry_button.clicked.connect(
            self.main_geometry_add_handler
        )
        self.viewer.right_click_add_geometry.triggered.connect(
            self.right_click_geometry_add_handler
        )

    def set_mitm_controller(self, controller: Any) -> None:
        """
        Set the MITM controller and connect signals between frameworks.
        
        This method establishes the connection between the RCS tool and the
        main MITM application, allowing access to plot widgets and data.
        
        Parameters
        ----------
        controller : PyMITM.Controller
            The MITM controller instance to connect with.
        """
        super().set_mitm_controller(controller)

        self.mitm_controller.viewer.widget_interacted_signal.connect(
            self.plot_widget_interaction_controller
        )
        self.mitm_controller.viewer.widget_changed_signal.connect(
            self.update_geometry_table
        )
        self.mitm_controller.viewer.widget_creation_signal.connect(
            self.widget_creation_controller
        )  # whenever a new plot widget is added

        # Handle widgets that were added before the RCS tool was activated
        # Widgets created later will be handled by widget_creation_controller
        for widget in self.mitm_controller.viewer.plotWidgets:
            if not hasattr(widget, "canvas"):
                widget.canvas = self.viewer.canvas()
            widget.plotWidget.getViewBox().menu.addAction(
                self.viewer.right_click_add_geometry
            )
            widget.plot_widget_resize_finished_signal.connect(
                self.plot_widget_resize_controller
            )

    def plot_widget_resize_controller(self, plot_widget_dock: Any) -> None:
        """
        Handle plot widget resize events.
        
        Sets a flag on the widget that will be used by the interaction controller
        to update geometry positions.
        
        Parameters
        ----------
        plot_widget_dock : PyMITM.PlotWidgetDock
            The plot widget dock that was resized.
        """
        plot_widget_dock.resize_event = 1  # set resize event flag to 1

    def plot_widget_interaction_controller(self, plot_widget_dock: Any) -> None:
        """
        Handle plot widget interaction events.
        
        Detects resize events and recreates geometries with updated positions
        to maintain proper scaling and placement.
        
        Parameters
        ----------
        plot_widget_dock : PyMITM.PlotWidgetDock
            The plot widget dock that was interacted with.
        """
        # A lot of this should probably not be in the controller, move out into model
        # Check for resize events
        if plot_widget_dock.resize_event == 1:
            plot_widget_dock.resize_event = 0  # Reset the flag

            # Get all geometries (copy to avoid issues during updates)
            geometries = plot_widget_dock.canvas.get_geometries().copy()

            # Process one geometry at a time
            def process_next_geometry(index: int = 0) -> None:
                if index >= len(geometries):
                    return

                geometry = geometries[index]

                try:
                    # Skip if we can't get coordinates
                    if (
                        not hasattr(geometry, "get_rcs_feature_wo_voids")
                        or not geometry.get_rcs_feature_wo_voids()
                    ):
                        process_next_geometry(index + 1)
                        return

                    # Get undecimated coordinates
                    undecimated_pixel_coords = (
                        geometry.get_rcs_feature_wo_voids().geometry.get_coordinate_list()
                    )
                    if (
                        not undecimated_pixel_coords
                        or len(undecimated_pixel_coords[0]) < 3
                    ):
                        process_next_geometry(index + 1)
                        return

                    # Convert to decimated coordinates
                    decimated_coords = [
                        [
                            i[1] / plot_widget_dock.decimationFactor,
                            i[0] / plot_widget_dock.decimationFactor,
                        ]
                        for i in undecimated_pixel_coords[0]
                    ]

                    # Remember original properties
                    original_color = geometry.get_color()
                    original_name = geometry.get_name()
                    original_rcs_w_voids = geometry.get_rcs_feature_w_voids()
                    original_rcs_wo_voids = geometry.get_rcs_feature_wo_voids()

                    # Remove the old geometry
                    plot_widget_dock.plotWidget.removeItem(geometry)
                    plot_widget_dock.canvas.remove_geometry(geometry)

                    # Create a completely new geometry
                    new_geometry = self.viewer.geometry_roi(
                        positions=decimated_coords,
                        closed=True,
                        removable=True,
                        movable=True,
                        snapSize=1,
                        rotateSnap=False,
                        translateSnap=False,
                        scaleSnap=False,
                        rotatable=False,
                    )

                    # Restore properties
                    new_geometry.set_color(original_color)
                    new_geometry.set_name(original_name)
                    new_geometry.set_rcs_feature_w_voids(original_rcs_w_voids)
                    new_geometry.set_rcs_feature_wo_voids(original_rcs_wo_voids)

                    # Add to plot and connect signals
                    plot_widget_dock.plotWidget.addItem(new_geometry)
                    self.connect_geometry(new_geometry)
                    plot_widget_dock.canvas.add_geometry(new_geometry)
                    plot_widget_dock.canvas.set_current_geometry(new_geometry)

                    # Process the next geometry
                    process_next_geometry(index + 1)
                except Exception as e:
                    print(f"Error processing geometry {index+1}: {e}")
                    process_next_geometry(index + 1)

            process_next_geometry()

        if plot_widget_dock.canvas.get_current_geometry():
            plot_widget_dock.canvas.render_geometry_selection()
            self.update_geometry_preview_controller()
            self.update_geometry_table()
        else:
            pass

    def main_geometry_add_handler(self) -> None:
        """
        Handle adding geometry from the main add button.
        
        Gets the center position of the current view and initiates
        geometry creation at that position.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        self.viewer.add_geometry_signal.emit(
            self.model.get_image_center(selected_widget)
        )

    def right_click_geometry_add_handler(self) -> None:
        """
        Handle adding geometry from right-click menu.
        
        Gets the current cursor position and initiates
        geometry creation at that position.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        self.viewer.add_geometry_signal.emit(
            selected_widget.get_current_cursor_image_position()
        )

    def get_name(self) -> str:
        """
        Get the name of this application.
        
        Returns
        -------
        str
            The application name ("RCS Tool").
        """
        return "RCS Tool"

    def get_dock_widget(self) -> Any:
        """
        Get the dock widget for this application.
        
        Returns
        -------
        QDockWidget
            The main dock widget containing the RCS Tool UI.
        """
        return self.viewer

    def slow_time_units_combo_box_controller(self) -> None:
        """
        Handle changes to the slow time units combo box.
        
        Displays a dialog for entering a reference azimuth angle if 'Target Relative'
        is selected, then triggers RCS recalculation.
        """
        # Allow user input for reference azimuth angle if target relative is selected
        if self.viewer.rcs_slow_time_units_combo_box.currentText() == "Target Relative":
            reference_azimuth_angle = self.viewer.azimuth_reference_angle_dialog()
            self.model.set_reference_azimuth_angle(reference_azimuth_angle)

        self.calculate_rcs_controller()

    def plot_rcs_controller(self, geometry: Any) -> None:
        """
        Update RCS plots for a given geometry.
        
        Calculates and displays RCS data for both slow time and fast time responses.
        
        Parameters
        ----------
        geometry : sarpy.geometry.geometry_elements.Polygon
            The geometry to plot RCS data for.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        meta_data = selected_widget.reader.get_sicds_as_tuple()[0].to_dict()

        slow_units = self.viewer.rcs_slow_time_units_combo_box.currentText()
        measure_units = self.viewer.rcs_measure_units_combo_box.currentText()
        measure_units_label = measure_units + " (dBsm)"
        
        (
            slow_data,
            fast_data,
            slow_x_data,
            fast_x_data,
            slow_axis_label,
            fast_axis_label,
        ) = self.model.compute_rcs_figures(
            selected_widget, meta_data, geometry, slow_units, measure_units
        )

        # Update the plot widgets
        self.viewer.rcs_slow_plot_widget.populate_plot(
            slow_x_data,
            slow_data,
            slow_axis_label,
            measure_units_label,
            "Slow Time Response",
        )
        self.viewer.rcs_fast_plot_widget.populate_plot(
            fast_x_data,
            fast_data,
            fast_axis_label,
            measure_units_label,
            "Fast Time Response",
        )

    def measure_units_combo_box_controller(self, index: int) -> None:
        """
        Handle changes to the measure units combo box.
        
        Updates the display units for RCS values in the geometry table.
        
        Parameters
        ----------
        index : int
            The index of the selected item in the combo box.
        """
        self.viewer.rcs_geometry_table.set_rcs_display_units(index)
        self.update_geometry_table()

    def geometry_name_changed_controller(self, geometry: Any, geometry_name: str) -> None:
        """
        Handle geometry name changes.
        
        Updates the name property of the specified geometry.
        
        Parameters
        ----------
        geometry : pyqtgraph.ROI
            The geometry whose name changed.
        geometry_name : str
            The new name to assign to the geometry.
        """
        geometry.set_name(geometry_name)

    def update_geometry_table(self) -> None:
        """
        Update the geometry table with current geometries.
        
        Retrieves geometries from the current canvas and updates
        the table display with their properties.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        if hasattr(selected_widget, "canvas"):
            geometries = selected_widget.canvas.get_geometries()
            self.viewer.rcs_geometry_table.populate_geometries(
                geometries, self.model.get_include_voids()
            )

    def background_color_controller(self) -> None:
        """
        Handle background color changes.
        
        Updates the geometry preview display when the background color changes.
        """
        self.update_geometry_preview_controller()

    def export_controller(self, filename: str) -> None:
        """
        Handle exporting RCS data.
        
        Creates an RCS collection and saves it to the specified file.
        
        Parameters
        ----------
        filename : str
            Path to save the exported file.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        geometries = selected_widget.canvas.get_geometries()
        file_rcs_collection = self.model.create_file_rcs_collection(
            geometries, filename
        )

        self.model.export_geometry(selected_widget, filename, file_rcs_collection)

    def import_controller(self, filename: str) -> None:
        """
        Handle importing RCS data.
        
        Reads geometry data from a file and creates corresponding
        visualizations in the current view.
        
        Parameters
        ----------
        filename : str
            Path to the file to import.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        geometries_list, geometry_colors, geometry_names = self.model.parse_import(
            selected_widget, filename
        )
        
        for geometries, geometry_color, geometry_name in zip(
            geometries_list, geometry_colors, geometry_names
        ):
            for image_geometry_coords in geometries:
                geometry = self.viewer.geometry_roi(
                    positions=image_geometry_coords,
                    closed=True,
                    removable=True,
                    movable=True,
                    snapSize=1,
                    rotateSnap=False,
                    translateSnap=False,
                    scaleSnap=False,
                    rotatable=False,
                )
                geometry.set_color(geometry_color)
                geometry.set_name(geometry_name)
                selected_widget.plotWidget.addItem(geometry)
                self.connect_geometry(geometry)
                selected_widget.canvas.add_geometry(geometry)
                selected_widget.canvas.set_current_geometry(geometry)
                self.calculate_rcs_controller()
            
            selected_widget.canvas.render_geometry_selection()
            self.update_geometry_preview_controller()
            self.update_geometry_table()
            self.viewer.rcs_geometry_table.image_geometry_select(geometry)

    def widget_creation_controller(self, new_widget: Any) -> None:
        """
        Handle creation of new plot widgets.
        
        Sets up canvas and connects signals for newly created widgets.
        
        Parameters
        ----------
        new_widget : PyMITM.PlotWidgetDock
            The newly created widget to set up.
        """
        new_widget.canvas = self.viewer.canvas()
        new_widget.plotWidget.getViewBox().menu.addAction(
            self.viewer.right_click_add_geometry
        )
        new_widget.plot_widget_resize_finished_signal.connect(
            self.plot_widget_resize_controller
        )

    def connect_geometry(self, geometry: Any) -> None:
        """
        Connect signals for a geometry.
        
        Sets up signal connections to handle various geometry events.
        
        Parameters
        ----------
        geometry : pyqtgraph.ROI
            The geometry to connect signals for.
        """
        # Connect UI interaction signals
        geometry.geometry_clicked_signal.connect(
            self.viewer.rcs_geometry_table.image_geometry_select
        )
        geometry.geometry_changed_signal.connect(
            self.viewer.rcs_geometry_table.image_geometry_select
        )
        
        # Connect controller signals
        geometry.geometry_clicked_signal.connect(self.geometry_clicked_controller)
        geometry.geometry_changed_signal.connect(self.geometry_changed_controller)
        geometry.geometry_clicked_signal.connect(self.calculate_rcs_controller)
        geometry.geometry_changed_signal.connect(self.calculate_rcs_controller)
        geometry.geometry_color_signal.connect(self.calculate_rcs_controller)
        geometry.geometry_name_signal.connect(self.calculate_rcs_controller)
        geometry.geometry_removed_signal.connect(self.geometry_removed_controller)
        geometry.geometry_removed_signal.connect(self.calculate_rcs_controller)
        geometry.geometry_color_signal.connect(self.geometry_color_controller)
        geometry.geometry_duplicate_signal.connect(self.geometry_duplicate_controller)

    def geometry_clicked_controller(self, geometry: Any) -> None:
        """
        Handle geometry click events.
        
        Updates the current selection and checks for interior geometries.
        
        Parameters
        ----------
        geometry : pyqtgraph.ROI
            The geometry that was clicked.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        
        # Check for interior geometries and update ordering if needed
        if self.model.check_for_interior_geometries(
            selected_widget, geometry, selected_widget.canvas.get_geometries()
        ):
            selected_widget.canvas.update_geometry_ordering()
        
        # Update selection and UI
        selected_widget.canvas.set_current_geometry(geometry)
        selected_widget.canvas.render_geometry_selection()
        self.update_geometry_preview_controller()
        self.calculate_rcs_controller()

    def geometry_changed_controller(self, geometry: Any) -> None:
        """
        Handle geometry change events.
        
        Updates the UI and recalculates RCS when a geometry is modified.
        
        Parameters
        ----------
        geometry : pyqtgraph.ROI
            The geometry that was changed.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        selected_widget.canvas.set_current_geometry(geometry)
        selected_widget.canvas.render_geometry_selection()
        self.update_geometry_preview_controller()
        self.calculate_rcs_controller()
        self.update_geometry_table()

    def geometry_removed_controller(self, geometry: Any) -> None:
        """
        Handle geometry removal events.
        
        Updates related geometries and UI components when a geometry is removed.
        
        Parameters
        ----------
        geometry : pyqtgraph.ROI
            The geometry that was removed.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        geometries = selected_widget.canvas.get_geometries()
        
        # Check for associated exterior geometry before removal
        exterior_geometry, interior_geometries = self.model.get_related_geometries(
            selected_widget, geometry, geometries
        )

        selected_widget.canvas.set_current_geometry(exterior_geometry)
        selected_widget.canvas.render_geometry_selection()
        selected_widget.plotWidget.removeItem(geometry)
        selected_widget.canvas.remove_geometry(geometry)
        self.update_geometry_preview_controller()
        self.update_geometry_table()

    def geometry_add_controller(self, spawn_image_coords: List[float]) -> None:
        """
        Handle geometry addition events.
        
        Creates a new geometry at the specified coordinates.
        
        Parameters
        ----------
        spawn_image_coords : List[float]
            [x, y] coordinates where the geometry should be added.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        size_ratio = self.model.get_size_ratio(selected_widget)

        # Create geometry with triangle shape initially
        geometry = self.viewer.geometry_roi(
            [
                [0 * size_ratio, -1 * size_ratio],
                [1 * size_ratio, 1 * size_ratio],
                [-1 * size_ratio, 1 * size_ratio],
            ],
            pos=spawn_image_coords,
            closed=True,
            removable=True,
            movable=True,
            snapSize=1,
            rotateSnap=False,
            translateSnap=False,
            scaleSnap=False,
            rotatable=False,
        )

        # Add to plot and connect signals
        selected_widget.plotWidget.addItem(geometry)
        self.connect_geometry(geometry)
        selected_widget.canvas.add_geometry(geometry)
        selected_widget.canvas.set_current_geometry(geometry)
        selected_widget.canvas.render_geometry_selection()
        
        # Update UI and calculate RCS
        self.calculate_rcs_controller()
        self.update_geometry_table()
        self.update_geometry_preview_controller()
        self.viewer.rcs_geometry_table.image_geometry_select(geometry)

    def update_geometry_preview_controller(self) -> None:
        """
        Update the geometry preview display.
        
        Creates a preview image based on the current geometry and background color.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        background_color = self.viewer.geometry_view_widget.get_background_color()
        geometries = selected_widget.canvas.get_geometries()
        exterior_geometry = selected_widget.canvas.get_current_geometry()

        if exterior_geometry:
            # Get interior geometries for the current geometry
            interior_geometries = self.model.get_interior_geometries(
                selected_widget, exterior_geometry, geometries
            )

            # Create a combined geometry with interiors
            geometry = self.model.create_geometry(
                selected_widget, exterior_geometry, interior_geometries
            )

            # Create and display preview image
            preview_image = self.model.create_preview_image(
                selected_widget, background_color, geometry
            )
        else:
            # No geometry selected, clear the preview
            preview_image = np.zeros((1, 1))
            self.viewer.rcs_table_view.clearContents()

        self.viewer.geometry_view_widget.update_geometry_view(
            selected_widget, preview_image
        )

    def geometry_color_controller(self) -> None:
        """
        Handle geometry color change events.
        
        Updates the visual appearance of geometries when their colors change.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        selected_widget.canvas.render_geometry_selection()

    def geometry_duplicate_controller(self, duplicated_geometry: Any) -> None:
        """
        Handle geometry duplication events.
        
        Sets up a duplicated geometry and updates the UI.
        
        Parameters
        ----------
        duplicated_geometry : pyqtgraph.ROI
            The duplicated geometry to set up.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        selected_widget.plotWidget.addItem(duplicated_geometry)

        # Add to canvas and connect signals
        selected_widget.canvas.add_geometry(duplicated_geometry)
        self.connect_geometry(duplicated_geometry)
        selected_widget.canvas.set_current_geometry(duplicated_geometry)
        selected_widget.canvas.render_geometry_selection()
        
        # Update UI and calculate RCS
        self.calculate_rcs_controller()
        self.update_geometry_table()
        self.viewer.rcs_geometry_table.image_geometry_select(duplicated_geometry)
        self.update_geometry_preview_controller()

    def calculate_rcs_controller(self) -> None:
        """
        Calculate RCS for all geometries.
        
        Updates RCS features for all geometries and refreshes the RCS table and plots.
        This is a core function that processes geometries and updates the UI with 
        calculated radar cross section values.
        """
        selected_widget = self.mitm_controller.get_current_widget()
        geometries = selected_widget.canvas.get_geometries()
        current_geometry = selected_widget.canvas.get_current_geometry()

        # Process all geometries except current_geometry first
        for geometry in geometries:
            if geometry == current_geometry:
                continue  # Skip current_geometry for now

            interior_geometries = self.model.get_interior_geometries(
                selected_widget, geometry, geometries
            )

            exterior_geometry = geometry

            # Create geometries with and without voids
            geometry_w_voids = self.model.create_geometry(
                selected_widget, exterior_geometry, interior_geometries
            )
            geometry_wo_voids = self.model.create_geometry(
                selected_widget, exterior_geometry, []
            )

            # Calculate RCS for both versions
            rcs_feature_w_voids = self.model.calculate_rcs(
                selected_widget, geometry_w_voids
            )
            rcs_feature_wo_voids = self.model.calculate_rcs(
                selected_widget, geometry_wo_voids
            )

            # Store results on the geometry
            exterior_geometry.set_rcs_feature_w_voids(rcs_feature_w_voids)
            exterior_geometry.set_rcs_feature_wo_voids(rcs_feature_wo_voids)

        # Now process current_geometry last to ensure its display is prioritized
        if current_geometry in geometries:
            geometry = current_geometry
            interior_geometries = self.model.get_interior_geometries(
                selected_widget, geometry, geometries
            )
            exterior_geometry = geometry

            # Create geometries with and without voids
            geometry_w_voids = self.model.create_geometry(
                selected_widget, exterior_geometry, interior_geometries
            )
            geometry_wo_voids = self.model.create_geometry(
                selected_widget, exterior_geometry, []
            )

            # Calculate RCS for both versions
            rcs_feature_w_voids = self.model.calculate_rcs(
                selected_widget, geometry_w_voids
            )
            rcs_feature_wo_voids = self.model.calculate_rcs(
                selected_widget, geometry_wo_voids
            )

            # Store results on the geometry
            exterior_geometry.set_rcs_feature_w_voids(rcs_feature_w_voids)
            exterior_geometry.set_rcs_feature_wo_voids(rcs_feature_wo_voids)

        # Update UI with current geometry's RCS data
        if current_geometry is not None:
            if self.model.get_include_voids():
                self.viewer.rcs_table_view.populate_rcs_table(rcs_feature_w_voids)
                self.plot_rcs_controller(geometry_w_voids)
            else:
                self.viewer.rcs_table_view.populate_rcs_table(rcs_feature_wo_voids)
                self.plot_rcs_controller(geometry_wo_voids)
        else:
            pass
