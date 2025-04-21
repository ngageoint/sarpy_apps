import numpy as np
from typing import List, Tuple, Dict, Union, Optional, Any, Set, Callable
from numpy.typing import NDArray

from sarpy.annotation.rcs import FileRCSCollection, RCSFeature, _get_polygon_bounds

from sarpy.geometry.geometry_elements import Polygon

from sarpy.geometry.geocoords import wgs_84_norm, geodetic_to_ecf, ecf_to_geodetic

import shapely

import scipy.io

from PySide6.QtGui import QColor

import warnings


class Model:
    """
    Model for Radar Cross Section (RCS) Analysis
    ------------------------------------------------------------------------
    This class implements the Model component in the MVC (Model-View-Controller) 
    architecture for radar cross section (RCS) analysis. It manages SAR (Synthetic 
    Aperture Radar) data processing, geometry handling, and RCS calculations.
    
    The Model provides functionality for:
    - RCS calculations with various calibration options
    - Geometry management (polygon creation, interior/exterior relationships)
    - File import/export (GeoJSON, MATLAB formats)
    - Data visualization preparation (slow/fast time profiles)
    - Coordinate transformations between image and geographic spaces
    - Calibration with different measurement units (RCS, σ₀, β₀, γ₀)
    
    Attributes
    -------------------------------------------------------------------------
    _file_rcs_collection : FileRCSCollection or None
        Collection for storing RCS features and annotations.
        
    _reference_azimuth_angle : float
        Reference angle in degrees for azimuth calculations.
        
    _include_voids : bool
        Flag determining whether to include void areas in calculations.
    """

    def __init__(self) -> None:
        """
        Initialize the Model class with default values.
        
        Sets up the file RCS collection, reference azimuth angle, and void inclusion flag.
        """
        self._file_rcs_collection: Optional[FileRCSCollection] = None
        self._reference_azimuth_angle: float = 0
        self._include_voids: bool = False  # default to false

    def set_include_voids(self, arg: bool) -> None:
        """
        Set whether to include voids in calculations.
        
        Parameters
        ----------
        arg : bool
            True to include voids, False to exclude them.
        """
        self._include_voids = arg

    def get_include_voids(self) -> bool:
        """
        Get whether voids are included in calculations.
        
        Returns
        -------
        bool
            True if voids are included, False otherwise.
        """
        return self._include_voids

    def check_for_interior_geometries(
        self, selected_widget: Any, current_geometry: Any, geometries: List[Any]
    ) -> bool:
        """
        Check if a geometry contains interior geometries.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        current_geometry : object
            The geometry to check for interior geometries.
        geometries : list
            List of all geometries to check against.
            
        Returns
        -------
        bool
            True if the current geometry contains interior geometries, False otherwise.
        """
        interior_geometries = self.get_interior_geometries(
            selected_widget, current_geometry, geometries
        )
        if len(interior_geometries) == 0:
            return False
        else:
            return True

    def set_reference_azimuth_angle(self, reference_azimuth_angle: float) -> None:
        """
        Set the reference azimuth angle for calculations.
        
        Parameters
        ----------
        reference_azimuth_angle : float
            The reference azimuth angle in degrees.
        """
        self._reference_azimuth_angle = reference_azimuth_angle

    def get_reference_azimuth_angle(self) -> float:
        """
        Get the current reference azimuth angle.
        
        Returns
        -------
        float
            The current reference azimuth angle in degrees.
        """
        return self._reference_azimuth_angle

    def get_interior_geometries(self, selected_widget: Any, current_geometry: Optional[Any], geometries: List[Any]) -> List[Any]:
        """
        Get geometries that are contained within the current geometry.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        current_geometry : object
            The geometry to check for interior geometries.
        geometries : list
            List of all geometries to check against.
            
        Returns
        -------
        list
            List of geometries contained within the current geometry.
        """
        if current_geometry is not None:
            exterior_geometry = current_geometry
            interior_geometries: List[Any] = []
            for geometry in geometries:
                if (
                    shapely.contains_properly(
                        shapely.Polygon(
                            self.get_pixel_vertex_image_coordinates(
                                selected_widget, exterior_geometry
                            )
                        ),
                        shapely.Polygon(
                            self.get_pixel_vertex_image_coordinates(
                                selected_widget, geometry
                            )
                        ),
                    )
                    == True
                ):
                    interior_geometries.append(geometry)
                else:
                    pass
        else:
            interior_geometries = []
        return interior_geometries

    def create_preview_image(
        self, 
        selected_widget: Any, 
        background_color: Union[List[int], Tuple[int, int, int]], 
        geometry: Any
    ) -> NDArray[np.uint8]:
        """
        Create a preview image of a geometry overlaid on the image data.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        background_color : list or tuple
            The RGB color for the background.
        geometry : object
            The geometry to visualize.
            
        Returns
        -------
        numpy.ndarray
            The preview image with the geometry overlaid.
        """
        reader = selected_widget.reader
        background_color = list(background_color)[:3]

        row_bounds, col_bounds, mask = _get_polygon_bounds(
            geometry, reader.get_data_size_as_tuple()[0]
        )

        data = reader[row_bounds[0] : row_bounds[1], col_bounds[0] : col_bounds[1]]
        image_data = selected_widget.remap_function(data)

        masked_image_data = np.where(mask, image_data, 0)

        background = np.full(
            (*masked_image_data.shape, 3), background_color, dtype=np.uint8
        )

        rgba_image = np.zeros((*masked_image_data.shape, 4), dtype=np.uint8)

        rgba_image[..., 0] = masked_image_data
        rgba_image[..., 1] = masked_image_data
        rgba_image[..., 2] = masked_image_data

        rgba_image[..., 3] = np.where(mask, 255, 0)

        final_image = background.copy()
        mask_3d = np.expand_dims(rgba_image[..., 3] > 0, axis=-1)
        final_image = np.where(mask_3d, rgba_image[..., :3], final_image)

        return final_image

    def get_image_center(self, selected_widget: Any) -> List[float]:
        """
        Get the center coordinates of the image in the selected widget.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
            
        Returns
        -------
        list
            The [x, y] coordinates of the center of the image.
        """
        center_coords = [
            selected_widget.plotWidget.getViewBox().viewRect().center().x(),
            selected_widget.plotWidget.getViewBox().viewRect().center().y(),
        ]

        return center_coords

    def get_size_ratio(self, selected_widget: Any) -> float:
        """
        Calculate the size ratio for the widget based on the view range.
        
        Parameters
        ----------
        selected_widget : object
            The widget to calculate the size ratio for.
            
        Returns
        -------
        float
            The calculated size ratio, with a minimum value of 0.25.
        """
        view_range = selected_widget.plotWidget.getViewBox().viewRange()
        size_ratio = (
            min(
                view_range[0][1] - view_range[0][0], view_range[1][1] - view_range[1][0]
            )
            // 4
        )

        if size_ratio < 0.25:  # prevents it from creating a tiny unselectable geometry
            size_ratio = 0.25
        else:
            pass

        return size_ratio

    def calculate_rcs(self, selected_widget: Any, geometry: Any) -> RCSFeature:
        """
        Calculate radar cross section for a given geometry.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        geometry : object
            The geometry to calculate RCS for.
            
        Returns
        -------
        RCSFeature
            An RCS feature object containing the calculated RCS parameters.
        """
        # # grabs the current selected widget so we know what image we are working with
        # selected_widget = self.mitm_controller.get_current_widget()
        reader = selected_widget.reader

        # have a check here to see if the geometry is an interior geometry
        # if so re-calculate any associated geometries
        # so find the exterior geometry associated, find all interior geometries,
        # then update thems

        rcs_feature = RCSFeature()
        # rcs_feature.geometry = self.create_geometry() # controller
        rcs_feature.geometry = geometry
        rcs_feature.set_rcs_parameters_from_reader(reader)

        # instead of returning only the rcs feature, we
        # can return entire rcs_feature list for said geometry

        return rcs_feature

    def parse_geojson(
        self, 
        selected_widget: Any, 
        filename: str
    ) -> Tuple[List[Any], List[str], List[str]]:
        """
        Parse a GeoJSON file and extract geometries, colors, and names.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        filename : str
            Path to the GeoJSON file to parse.
            
        Returns
        -------
        tuple
            A tuple containing:
            - List of undecimated geo geometries
            - List of geometry colors
            - List of geometry names
        """
        file_rcs_collection = FileRCSCollection()

        data = file_rcs_collection.from_file(filename)

        undecimated_geo_geometries_list = []
        geometry_colors = []
        geometry_names = []
        for feature in data.annotations.features:
            undecimated_geo_geometries_list.append(
                feature.geometry.get_coordinate_list()
            )
            geometry_colors.append(feature.properties.geometry_properties[0].color)
            geometry_names.append(feature.properties.geometry_properties[0].name)

        return undecimated_geo_geometries_list, geometry_colors, geometry_names

    def parse_matlab(
        self, 
        selected_widget: Any, 
        filename: str
    ) -> Tuple[List[List[List[float]]], List[str], List[str]]:
        """
        Parse a MATLAB file and extract geometries, colors, and names.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        filename : str
            Path to the MATLAB file to parse.
            
        Returns
        -------
        tuple
            A tuple containing:
            - List of geometries
            - List of geometry colors
            - List of geometry names
        """
        matlab_data = scipy.io.loadmat(filename)
        geometries = []
        geometry_colors = []
        geometry_names = []
        for i, data in enumerate(matlab_data["shape_struct"].tolist()[0]):
            geo_coords = []
            for lat, long, hav in zip(data[3][0], data[3][1], data[3][2]):
                geo_coord = [lat, long, hav]
                geo_coords.append(geo_coord)
            geometries.append([geo_coords])
            geometry_colors.append(QColor(data[1][0]).name())
            geometry_names.append(data[0][0])
        return geometries, geometry_colors, geometry_names

    def parse_import(
        self, 
        selected_widget: Any, 
        filename: str
    ) -> Tuple[List[List[List[List[float]]]], List[str], List[str]]:
        """
        Parse an imported file based on its extension and extract geometries.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        filename : str
            Path to the file to parse.
            
        Returns
        -------
        tuple
            A tuple containing:
            - List of decimated image geometries
            - List of geometry colors
            - List of geometry names
        
        Notes
        -----
        Supports GeoJSON, JSON, and MATLAB file formats.
        """
        file_exten = filename.split(".")[-1]
        if file_exten == "geojson" or file_exten == "json":
            undecimated_geo_geometries_list, geometry_colors, geometry_names = (
                self.parse_geojson(selected_widget, filename)
            )
        elif file_exten == "mat":
            undecimated_geo_geometries_list, geometry_colors, geometry_names = (
                self.parse_matlab(selected_widget, filename)
            )
        else:
            pass  # return error

        decimated_image_geometries_list = []

        for geometries in undecimated_geo_geometries_list:
            decimated_image_geometries = []
            for geometry in geometries:
                undecimated_image_coords = []
                for coord in geometry:
                    undecimated_image_coord = (
                        selected_widget.reader.sicd_meta.project_ground_to_image_geo(
                            coord, ordering="latlong"
                        )
                    )
                    undecimated_image_coords.append(undecimated_image_coord[0].tolist())

                # this coord adjustment seems to work consistently but is kinda hacky, but needed to match other legacy tools
                error_adjusted_coords = []
                adjustment_factor = 0.55
                for coord in undecimated_image_coords:
                    error_adjusted_coords.append(
                        [coord[0] + adjustment_factor, coord[1] + adjustment_factor]
                    )

                decimated_image_coords = [
                    [
                        i[1] / selected_widget.decimationFactor,
                        i[0] / selected_widget.decimationFactor,
                    ]
                    for i in error_adjusted_coords
                ]

                decimated_image_geometries.append(decimated_image_coords)
            decimated_image_geometries_list.append(decimated_image_geometries)

        return decimated_image_geometries_list, geometry_colors, geometry_names

    def check_geometry_void(
        self, 
        interior_geometry_list: List[List[Any]], 
        exterior_geometry: List[Any]
    ) -> bool:
        """
        Check if a geometry is a void of another geometry.
        
        Parameters
        ----------
        interior_geometry_list : list
            List of interior geometries to check against.
        exterior_geometry : list
            The exterior geometry to check.
            
        Returns
        -------
        bool
            True if the exterior geometry is a void of any interior geometry,
            False otherwise.
        """
        # this just searches one set of coordinates to see if its present in another set of coordinates
        # used to check if a geometry is a void of another geometry
        flattened_set = set(
            tuple(coord) for sublist in interior_geometry_list for coord in sublist[1:]
        )
        single_set = set(tuple(coord) for coord in exterior_geometry[1:])

        return single_set.issubset(flattened_set)

    def create_file_rcs_collection(
        self, 
        geometries: List[Any], 
        filename: str
    ) -> FileRCSCollection:
        """
        Create a file RCS collection from geometries.
        
        Parameters
        ----------
        geometries : list
            List of geometries to include in the collection.
        filename : str
            Name of the image file associated with the collection.
            
        Returns
        -------
        FileRCSCollection
            The created file RCS collection object.
        """
        file_rcs_collection = FileRCSCollection(image_file_name=filename)
        include_voids = self.get_include_voids()
        # might move most of this out to a separate method
        if include_voids:
            interior_geometries = []
            for geometry in geometries:
                if geometry.get_rcs_feature_w_voids().geometry.inner_rings:
                    for (
                        interior_geometry
                    ) in geometry.get_rcs_feature_w_voids().geometry.inner_rings:
                        interior_geometries.append(
                            interior_geometry.coordinates.tolist()
                        )
                else:
                    pass
            for geometry in geometries:
                exterior_geometry = (
                    geometry.get_rcs_feature_w_voids().geometry.outer_ring.coordinates.tolist()
                )
                if self.check_geometry_void(interior_geometries, exterior_geometry):
                    pass
                else:
                    file_rcs_collection.add_annotation(
                        geometry.get_rcs_feature_w_voids()
                    )
        else:
            for geometry in geometries:
                file_rcs_collection.add_annotation(geometry.get_rcs_feature_wo_voids())

        return file_rcs_collection

    def export_geometry(
        self, 
        selected_widget: Any, 
        filename: str, 
        file_rcs_collection: FileRCSCollection
    ) -> None:
        """
        Export geometry to a file.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        filename : str
            Path where the file will be saved.
        file_rcs_collection : FileRCSCollection
            The RCS collection containing the geometries to export.
            
        Notes
        -----
        This method handles exporting RCS geometry and calculated values to a GeoJSON file.
        It transforms image coordinates to geographic coordinates before exporting.
        """
        for feature in file_rcs_collection.annotations.features:

            undecimated_image_geometries = feature.geometry.get_coordinate_list()
            undecimated_geo_geometries = []
            for idx, geometry in enumerate(undecimated_image_geometries):
                undecimated_geo_coords = []
                for coord in geometry:
                    try:
                        undecimated_geo_coord = selected_widget.reader.sicd_meta.project_image_to_ground_geo(
                            coord, projection_type="PLANE"
                        ).tolist()
                    except:
                        undecimated_geo_coord = coord
                    undecimated_geo_coords.append(undecimated_geo_coord)
                undecimated_geo_geometries.append(undecimated_geo_coords)

            feature.geometry.set_outer_ring(undecimated_geo_geometries[0])
            feature.geometry._inner_rings = None

            for geometry in undecimated_geo_geometries[1:]:
                feature.geometry.add_inner_ring(geometry)

        file_rcs_collection.to_file(filename)

    def get_pixel_vertex_image_coordinates(
        self, 
        selected_widget: Any, 
        geometry: Any
    ) -> List[List[int]]:
        """
        Get pixel vertex coordinates in image space from scene coordinates.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        geometry : object
            The geometry to get coordinates for.
            
        Returns
        -------
        list
            List of pixel coordinates in image space.
        """
        # selected_widget = self.mitm_controller.get_current_widget() # adding this to be passed in
        scene_coordinates = geometry.getSceneHandlePositions()
        pixel_coordinates = []
        for scene_coord in scene_coordinates:
            pixel_coord = selected_widget.img.mapFromScene(scene_coord[1])
            # this converts from decimated to undecimated, eventually will be added to MITM api and called from there then passed into this method
            pixel_coordinates.append(
                [
                    int(
                        pixel_coord.y() * selected_widget.stepSize
                        + selected_widget.yminMapToFullImage
                    ),
                    int(
                        pixel_coord.x() * selected_widget.stepSize
                        + selected_widget.xminMapToFullImage
                    ),
                ]
            )
        return pixel_coordinates

    def create_geometry(
        self, 
        selected_widget: Any, 
        exterior_geometry: Optional[Any], 
        interior_geometries: List[Any]
    ) -> Optional[Polygon]:
        """
        Create a Polygon geometry from exterior and interior geometries.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        exterior_geometry : object
            The exterior geometry to use as the outer ring.
        interior_geometries : list
            List of interior geometries to use as inner rings.
            
        Returns
        -------
        Polygon or None
            The created Polygon geometry, or None if no exterior geometry was provided.
        """
        if exterior_geometry is not None:
            geometry = Polygon()
            exterior_ring_image_coords = self.get_pixel_vertex_image_coordinates(
                selected_widget, exterior_geometry
            )
            if self.get_polygon_orientation(exterior_ring_image_coords) == "ccw":
                geometry.set_outer_ring(exterior_ring_image_coords)
            else:
                geometry.set_outer_ring(exterior_ring_image_coords[::-1])
            for interior_geometry in interior_geometries:
                interior_ring_image_coords = self.get_pixel_vertex_image_coordinates(
                    selected_widget, interior_geometry
                )
                if self.get_polygon_orientation(interior_ring_image_coords) == "cw":
                    geometry.add_inner_ring(interior_ring_image_coords)
                else:
                    geometry.add_inner_ring(interior_ring_image_coords[::-1])
        else:
            geometry = None
        return geometry

    def get_polygon_orientation(self, coords: List[List[float]]) -> str:
        """
        Determine the orientation of a polygon (clockwise or counterclockwise).
        
        Parameters
        ----------
        coords : list
            List of coordinate pairs defining the polygon.
            
        Returns
        -------
        str
            'cw' for clockwise, 'ccw' for counterclockwise.
            
        Notes
        -----
        Uses the Jordan curve theorem to determine orientation.
        """
        # get polygon orientation, cw = clockwise, ccw = counterclockwise, based on jordan curve theorem
        # verify later that this is done efficiently (followed wikipedia https://en.wikipedia.org/wiki/Curve_orientation#Orientation_of_a_simple_polygon)
        coord_rows = [coord[0] for coord in coords]

        min_row = min(coord_rows)
        min_row_ind = [
            index for index, value in enumerate(coord_rows) if value == min_row
        ]

        min_coords = [coords[index] for index in min_row_ind]
        coord_cols = [coord[1] for coord in min_coords]
        max_col = max(coord_cols)
        max_col_ind = [
            index for index, value in enumerate(coord_cols) if value == max_col
        ]
        a_ind = coords.index([coord_rows[min_row_ind[0]], coord_cols[max_col_ind[0]]])

        a = coords[a_ind]

        try:
            b = coords[a_ind - 1]
        except:
            b = coords[-1]

        try:
            c = coords[a_ind + 1]
        except:
            c = coords[0]

        vect_ab = np.array(b) - np.array(a)
        vect_ac = np.array(c) - np.array(a)

        if np.cross(vect_ab, vect_ac) < 0:
            return "ccw"
        else:
            return "cw"

    def get_related_geometries(
        self, 
        selected_widget: Any, 
        current_geometry: Any, 
        geometries: List[Any]
    ) -> Tuple[Any, List[Any]]:
        """
        Get geometries related to the current geometry.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        current_geometry : object
            The geometry to find related geometries for.
        geometries : list
            List of all geometries to check against.
            
        Returns
        -------
        tuple
            A tuple containing:
            - The exterior geometry (either the current geometry or its container)
            - List of interior geometries
        """
        for geometry in geometries:
            interior_geometries = self.get_interior_geometries(
                selected_widget, geometry, geometries
            )

            # so now each time we will check to see if the current geometry is one of these interior geometries
            if current_geometry in interior_geometries:
                exterior_geometry = geometry
                break
            else:
                exterior_geometry = current_geometry
                interior_geometries = []

        return exterior_geometry, interior_geometries

    def update_geometry_features(
        self, 
        selected_widget: Any, 
        exterior_geometry: Any, 
        interior_geometries: List[Any]
    ) -> None:
        """
        Update RCS features for geometries with and without voids.
        
        Parameters
        ----------
        selected_widget : object
            The widget containing the image data.
        exterior_geometry : object
            The exterior geometry to update.
        interior_geometries : list
            List of interior geometries (voids).
        """
        geometry_w_voids = self.create_geometry(
            selected_widget, exterior_geometry, interior_geometries
        )

        geometry_wo_voids = self.create_geometry(selected_widget, exterior_geometry, [])

        rcs_feature_w_voids = self.calculate_rcs(selected_widget, geometry_w_voids)
        rcs_feature_wo_voids = self.calculate_rcs(selected_widget, geometry_wo_voids)

        exterior_geometry.set_rcs_feature_w_voids(rcs_feature_w_voids)
        exterior_geometry.set_rcs_feature_wo_voids(rcs_feature_wo_voids)
        
    def compute_slow_time_axis(self, meta_data, selected_widget, units, center_rowcol=None, relative_azimuth=None): #investigate where the center rowcol and relative azimuth are coming from
        azimuth_padding = 1/(meta_data['Grid']['Col']['ImpRespBW']*meta_data['Grid']['Col']['SS'])
        if units == "Collect Time":
            theta = meta_data['Grid']['Col']['ImpRespBW']/meta_data['Grid']['Row']['KCtr']
            velocity =  np.linalg.norm(np.array([meta_data['SCPCOA']['ARPVel']['X'], meta_data['SCPCOA']['ARPVel']['Y'], meta_data['SCPCOA']['ARPVel']['Z']]))
            effective_duration = theta * (meta_data['SCPCOA']['SlantRange']/velocity)/np.sin(np.radians(meta_data['SCPCOA']['DopplerConeAng']))

            image_formation = meta_data.get('ImageFormation', {})
            collection_info = meta_data.get('CollectionInfo', {})
            radar_mode = collection_info.get('RadarMode', {})

            if (
                image_formation.get('ImageFormAlgo') == 'PFA' and
                all(key in image_formation for key in ('TStartProc', 'TEndProc')) and
                radar_mode.get('ModeType') == 'SPOTLIGHT'
            ):
                effective_duration = image_formation['TEndProc'] - image_formation['TStartProc']

            axis_range = np.array([0, effective_duration]) + (
                np.array([-1, 1]) * 0.5 * effective_duration * (azimuth_padding - 1)
            )

            label = "Collection Time (sec)"

        elif units == "Polar Angle":
            orientation = np.array([1, -1])
            if meta_data['SCPCOA']['SideOfTrack'][0] != 'R':
                orientation = -1*orientation
            axis_range = np.degrees(np.arctan((orientation/(2*meta_data['Grid']['Col']['SS'])/meta_data['Grid']['Row']['KCtr']))) # FIXED
            label = 'Polar Angle <deg>'

        elif units == "Azimuth Angle":
            st_mid_end = self.compute_azimuth(meta_data, selected_widget, np.array([0, 50, 100]), center_rowcol)
            st_mid_end = np.unwrap(st_mid_end*np.pi/180)*180/np.pi # st_mid_end = np.unwrap((st_mid_end*np.pi/180)*180/np.pi) is wrong?
            relative_azimuth = 0
            label = "Azimuth Angle \u00B0"
            delta_azimuth = np.diff([st_mid_end[0], st_mid_end[-1]])[0]
            axis_range = (
                np.array([st_mid_end[0], st_mid_end[-1]])
                + np.array([-1, 1]) * 0.5 * delta_azimuth * (azimuth_padding - 1)
                - relative_azimuth
            )
        elif units == "Aperture Relative":
            st_mid_end = self.compute_azimuth(meta_data, selected_widget, np.array([0, 50, 100]), center_rowcol)
            st_mid_end = np.unwrap((st_mid_end*np.pi/180))*180/np.pi
            relative_azimuth = st_mid_end[1]
            label = "Azimuth Angle Relative To Aperture Center \u00B0"
            delta_azimuth = np.diff([st_mid_end[0], st_mid_end[-1]])[0]
            axis_range = (
                np.array([st_mid_end[0], st_mid_end[-1]])
                + np.array([-1, 1]) * 0.5 * delta_azimuth * (azimuth_padding - 1)
                - relative_azimuth
            )
        elif units == "Target Relative":
            relative_azimuth = self.get_reference_azimuth_angle()
            st_mid_end = self.compute_azimuth(meta_data, selected_widget, np.array([0, 50, 100]), center_rowcol)
            st_mid_end = np.unwrap((st_mid_end*np.pi/180))*180/np.pi
            label = ('Azimuth Angle Relative To Target @ ' + str(relative_azimuth) + ' <deg>')
            delta_azimuth = np.diff([st_mid_end[0], st_mid_end[-1]])[0]
            axis_range = (
                np.array([st_mid_end[0], st_mid_end[-1]])
                + np.array([-1, 1]) * 0.5 * delta_azimuth * (azimuth_padding - 1)
                - relative_azimuth
            )
        else:
            print("Error: Wrong plotting units selected for slow time axis.")

        return axis_range, label

    def compute_fast_time_axis(self, meta: Dict[str, Any]) -> Tuple[List[float], str]:
        """
        Compute information needed for annotating fast time axis based on data.

        Parameters
        ----------
        meta : dict
            Metadata dictionary containing Grid and Row information.

        Returns
        -------
        tuple
            A tuple containing:
            - Array of range values [min, max] in GHz
            - String label for the axis
        """
        SPEED_OF_LIGHT = 299792458  # meters per second

        # Check if all required nested keys exist
        has_grid = "Grid" in meta
        has_row = has_grid and "Row" in meta.get("Grid", {})
        has_required_fields = has_row and all(
            key in meta.get("Grid", {}).get("Row", {}) for key in ["SS", "KCtr"]
        )

        if has_required_fields:
            # Frequency calculations
            bw_rg = SPEED_OF_LIGHT / (2 * meta["Grid"]["Row"]["SS"])
            vfrq_c = meta["Grid"]["Row"]["KCtr"] * SPEED_OF_LIGHT / 2

            range_vals = [
                (vfrq_c + sign * bw_rg / 2)
                / 1e9  # Convert to GHz (changed from 10e8 to 1e9)
                for sign in [-1, 1]
            ]

            return range_vals, "Frequency (GHz)"
        else:
            # Resort to unitless axis and warn the user
            warnings.warn(
                "Insufficient metadata to determine receive frequencies.", UserWarning
            )
            return [0, 1], ""

    def compute_azimuth(self, meta, selected_widget, percent=None, pixel_coords=None):
        """
        Compute azimuth angle (angle from north) across spatial frequency.

        Parameters
        ----------
        meta : dict
            SICD metadata structure.
        percent : array-like, optional
            Array of values from 0 to 100. Indicates the fraction across 
            the spatial frequency in azimuth for which to compute azimuth angle.
        pixel_coords : list/tuple, optional
            [column_index, row_index] (az,rng) index to point of interest.

        Returns
        -------
        numpy.ndarray
            Computed azimuth angle for each percent value.
            
        Notes
        -----
        Should work generically for many types of SAR complex data, not just
        spotlight collects. Default for percent is just SCPCOA azimuth.
        If pixel_coords is None, defaults to scene center point (SCP).
        
        Should work generically for many types of SAR complex data, not just
        spotlight collects.
        
        Parameters:
            meta (dict): SICD metadata structure
            selected_widget: Widget containing the reader
            percent (array-like, optional): Array of values from 0 to 100. Indicates the
                fraction across the spatial frequency in azimuth for which to compute
                azimuth angle (not including zeropad). Default is scene center point
                center of aperture.
            pixel_coords (list/tuple, optional): [column_index, row_index] (az,rng) index to
                point of interest. Default is scene center point (SCP).
        
        Returns:
            numpy.ndarray: Computed azimuth angle for each percent value
        """
        # Handle default values for input parameters
        # Default for percent is just SCPCOA azimuth
        if percent is None:
            # SCPCOA.AzimAng is an actual field in latest SICD spec
            if "SCPCOA" in meta and "AzimAng" in meta["SCPCOA"]:
                return meta["SCPCOA"]["AzimAng"]
            percent = 50  # If SCPCOA.AzimAng not available, we will compute it.
        
        # Ensure percent is a numpy array
        percent = np.asarray(percent)
        original_percent_shape = percent.shape
        percent = percent.flatten()  # Flatten for calculations, we'll reshape at the end
        
        if 'Grid' not in meta or 'TimeCOAPoly' not in meta['Grid']:
            # For spotlight, we can take some shortcuts with missing metadata
            if ('CollectionInfo' in meta and 
                'RadarMode' in meta['CollectionInfo'] and
                'ModeType' in meta['CollectionInfo']['RadarMode'] and
                meta['CollectionInfo']['RadarMode']['ModeType'].upper() == 'SPOTLIGHT'):
                
                if ('SCPCOA' in meta and 'SCPTime' in meta['SCPCOA'] and
                    'Position' in meta and 'ARPPoly' in meta['Position']):
                    meta['Grid'] = {'TimeCOAPoly': meta['SCPCOA']['SCPTime']}
                
                elif ('SCPCOA' in meta and 'ARPPos' in meta['SCPCOA'] and
                    'ARPVel' in meta['SCPCOA']):
                    meta['Grid'] = {'TimeCOAPoly': 0}
                    meta['Position'] = {
                        'ARPPoly': {
                            'X': {'Coefs': [meta['SCPCOA']['ARPPos']['X'], meta['SCPCOA']['ARPVel']['X']]},
                            'Y': {'Coefs': [meta['SCPCOA']['ARPPos']['Y'], meta['SCPCOA']['ARPVel']['Y']]},
                            'Z': {'Coefs': [meta['SCPCOA']['ARPPos']['Z'], meta['SCPCOA']['ARPVel']['Z']]}
                        }
                    }
            
            if 'Grid' not in meta or 'TimeCOAPoly' not in meta['Grid']:
                raise ValueError('Unable to compute SICD Grid.TimeCOAPoly field from complex data.')

        # Point of interest (POI) only required for spatially variant COA
        if pixel_coords is not None:
            # Convention for point_slant_to_ground() pixel coordinates is reverse
            # of what is passed to this function (column/row), so we have to swap values.
            undecimated_geo_coord = (
                selected_widget.reader.sicd_meta.project_image_to_ground_geo(
                    pixel_coords, projection_type="PLANE"
                ).tolist()
            )
            
            poi_ecf = geodetic_to_ecf(undecimated_geo_coord).transpose()
            
            # Calculate center of aperture (COA) for given point
            # IMPORTANT: When calling sicd_polyval2d with a single point, we need scalar values
            # for both coordinates, not arrays
            time_coa = self.sicd_polyval2d(
                meta['Grid']['TimeCOAPoly'], 
                pixel_coords[0],  # Single scalar value for column
                pixel_coords[1],  # Single scalar value for row
                meta
            )
            
            # If the result is an array with multiple values but we only need one, take the first element
            if hasattr(time_coa, '__len__') and len(time_coa) > 0:
                time_coa = time_coa.item() if time_coa.size == 1 else time_coa[0]
        else:
            # Default to SCP
            poi_ecf = np.array([
                meta['GeoData']['SCP']['ECF']['X'],
                meta['GeoData']['SCP']['ECF']['Y'],
                meta['GeoData']['SCP']['ECF']['Z']
            ])
            
            # Handle both cases where TimeCOAPoly might be a number or a nested dictionary
            if isinstance(meta["Grid"]["TimeCOAPoly"], (int, float)):
                time_coa = meta["Grid"]["TimeCOAPoly"]
            else:
                if 'Coefs' in meta['Grid']['TimeCOAPoly']:
                    time_coa = meta['Grid']['TimeCOAPoly']['Coefs'][0][0]
                else:
                    # Assuming it's just a scalar value in this case
                    time_coa = meta['Grid']['TimeCOAPoly']
                
            # Check for spatially variant COA
            if isinstance(meta['Grid']['TimeCOAPoly'], dict) and 'Coefs' in meta['Grid']['TimeCOAPoly']:
                coefs = np.array(meta['Grid']['TimeCOAPoly']['Coefs'])
                if np.any(coefs[1:] != 0):
                    print(
                        "Warning: For non-spotlight data, point of interest must be specified for accurate azimuth angles."
                    )

        # Calculate geometry info for center of aperture
        # Extract coefficients from the nested structure
        if 'Coefs' in meta['Position']['ARPPoly']['X']:
            pos_x = np.array(meta['Position']['ARPPoly']['X']['Coefs'])[::-1]
            pos_y = np.array(meta['Position']['ARPPoly']['Y']['Coefs'])[::-1]
            pos_z = np.array(meta['Position']['ARPPoly']['Z']['Coefs'])[::-1]
        else:
            pos_x = np.array(meta['Position']['ARPPoly']['X'])[::-1]
            pos_y = np.array(meta['Position']['ARPPoly']['Y'])[::-1]
            pos_z = np.array(meta['Position']['ARPPoly']['Z'])[::-1]
        
        pos_coefs = np.column_stack([pos_x, pos_y, pos_z])

        # Position at COA
        ARP = np.array(
            [
                np.polyval(pos_coefs[:, 0], time_coa),
                np.polyval(pos_coefs[:, 1], time_coa),
                np.polyval(pos_coefs[:, 2], time_coa),
            ]
        )

        # Velocity polynomial is derivative of position polynomial
        vel_coefs = (
            pos_coefs[:-1, :] * np.arange(len(pos_coefs) - 1, 0, -1)[:, np.newaxis]
        )

        # Aperture velocity at COA
        ARV = np.array(
            [
                np.polyval(vel_coefs[:, 0], time_coa),
                np.polyval(vel_coefs[:, 1], time_coa),
                np.polyval(vel_coefs[:, 2], time_coa),
            ]
        )

        # Line of sight vector at COA
        LOS = poi_ecf - ARP

        # Range from sensor to POI at COA
        R = np.linalg.norm(LOS)

        # Speed at COA
        V = np.linalg.norm(ARV)

        # Doppler Cone Angle to POI at COA
        DCA = np.arccos(np.dot(ARV / V, LOS / R))

        # Compute effective aperture positions for each percentage
        Theta = meta["Grid"]["Col"]["ImpRespBW"] / meta["Grid"]["Row"]["KCtr"]
        EffectiveDuration = (Theta * R / V) / np.sin(DCA)


        # Convert percent to numpy array if it isn't already
        percent = np.asarray(percent)

        # Compute time offsets
        t = EffectiveDuration * ((-1/2) + (percent / 100))

        # Compute positions - each row is a position for a different percent value
        pos = np.column_stack([
            ARP[0] + (t * ARV[0]),
            ARP[1] + (t * ARV[1]),
            ARP[2] + (t * ARV[2])
        ])

        # Calculate actual azimuth angles
        gpn = wgs_84_norm(poi_ecf)  # Ground plane normal

        
        # Project north onto ground plane
        north_ground = np.array([0, 0, 1]) - (np.dot([0, 0, 1], gpn) * gpn)

        # Range vectors for each time
        range_vec = pos - np.tile(poi_ecf, (len(t), 1))
        
        # Project range vector onto ground plane
        range_ground = range_vec - np.outer(np.dot(range_vec, gpn), gpn)

        # Cross products for each range ground vector with north ground
        cross_products = np.cross(range_ground, np.tile(north_ground, (len(t), 1)))

        # Angle calculation
        dot_products = np.sum(range_ground * np.tile(north_ground, (len(t), 1)), axis=1)
        cross_dot = np.sum(cross_products * gpn, axis=1)

        Az = np.arctan2(cross_dot, dot_products) * 180/np.pi
        
        # Ensure angles are in [0, 360]
        Az[Az < 0] += 360

        # Reform to shape of original input

        return Az.reshape(original_percent_shape)
    
        return Az.reshape(np.shape(percent))

    def sicd_polyval2d(self, poly_coefs, dim1_ind, dim2_ind, sicd_meta=None):
        """
        Evaluate a SICD field of type 2D_POLY.

        Parameters
        ----------
        poly_coefs : array-like
            A SICD field of type 2D_POLY.
        dim1_ind : array-like
            Vector of value(s) in the first dimension (azimuth).
        dim2_ind : array-like
            Vector of value(s) in the second dimension (range).
        sicd_meta : dict, optional
            SICD metadata structure. If provided, dim1_ind and dim2_ind will be 
            converted from image indices to image coordinates (meters from SCP).

        Returns
        -------
        numpy.ndarray
            Array with the result values of the evaluated polynomial.
            
        Notes
        -----
        Python doesn't have a builtin function for evaluating 2D polynomials, so
        this is the function we use for evaluating the 2D polynomials in SICD
        over a grid of input values.
        
        Parameters:
            poly_coefs (array-like): A SICD field of type 2D_POLY.
            dim1_ind (array-like): Vector of value(s) in the first dimension (azimuth).
            dim2_ind (array-like): Vector of value(s) in the second dimension (range).
            sicd_meta (dict, optional): SICD metadata structure. If provided,
                dim1_ind and dim2_ind will be converted from image indices
                to image coordinates (meters from SCP).
        
        Returns:
            numpy.ndarray: Array with the result values of the evaluated polynomial.
        """
        # Convert inputs to numpy arrays for consistent handling
        dim1_ind = np.asarray(dim1_ind)
        dim2_ind = np.asarray(dim2_ind)

        # Handle poly_coefs based on input type
        if isinstance(poly_coefs, (int, float)):
            # If poly_coefs is a scalar, just return it
            return poly_coefs
        elif isinstance(poly_coefs, dict) and 'Coefs' in poly_coefs:
            # If poly_coefs is a SICD structure with 'Coefs' field
            poly_coefs = np.array(poly_coefs["Coefs"])
        else:
            # Otherwise, convert to numpy array
            poly_coefs = np.asarray(poly_coefs)

        # SICD uses the first dimension of its polynomials to refer to the "row"
        # index (range) and the second dimension to refer to the "column" index
        # (azimuth). Transpose to match this convention.
        poly_coefs = poly_coefs.T
        
        # Convert inputs to numpy arrays for consistent handling
        dim1_ind = np.asarray(dim1_ind, dtype=float)
        dim2_ind = np.asarray(dim2_ind, dtype=float)
        
        if sicd_meta is not None:
            # Convert image indices to image coordinates (meters from SCP)
            dim1_vals = (dim1_ind - 1 + 
                        float(sicd_meta['ImageData']['FirstCol']) - 
                        float(sicd_meta['ImageData']['SCPPixel']['Col'])) * \
                        float(sicd_meta['Grid']['Col']['SS'])
            
            dim2_vals = (dim2_ind - 1 + 
                        float(sicd_meta['ImageData']['FirstRow']) - 
                        float(sicd_meta['ImageData']['SCPPixel']['Row'])) * \
                        float(sicd_meta['Grid']['Row']['SS'])
        else:
            # No conversion requested
            dim1_vals = dim1_ind
            dim2_vals = dim2_ind
        
        # Handle the special case where both inputs are scalar
        if np.isscalar(dim1_vals) and np.isscalar(dim2_vals):
            result = 0.0
            for i in range(poly_coefs.shape[0]):
                for j in range(poly_coefs.shape[1]):
                    result += poly_coefs[i, j] * (dim1_vals ** i) * (dim2_vals ** j)
            return result
        
        # Handle the case where one input is scalar and the other is an array
        if np.isscalar(dim1_vals) and not np.isscalar(dim2_vals):
            dim2_vals = np.asarray(dim2_vals)
            result = np.zeros_like(dim2_vals, dtype=float)
            for i in range(poly_coefs.shape[0]):
                for j in range(poly_coefs.shape[1]):
                    result += poly_coefs[i, j] * (dim1_vals ** i) * (dim2_vals ** j)
            return result
        
        if not np.isscalar(dim1_vals) and np.isscalar(dim2_vals):
            dim1_vals = np.asarray(dim1_vals)
            result = np.zeros_like(dim1_vals, dtype=float)
            for i in range(poly_coefs.shape[0]):
                for j in range(poly_coefs.shape[1]):
                    result += poly_coefs[i, j] * (dim1_vals ** i) * (dim2_vals ** j)
            return result
        
        # Both are arrays - if they have the same length, evaluate point-by-point
        if len(dim1_vals) == len(dim2_vals):
            result = np.zeros_like(dim1_vals, dtype=float)
            for i in range(poly_coefs.shape[0]):
                for j in range(poly_coefs.shape[1]):
                    result += poly_coefs[i, j] * (dim1_vals ** i) * (dim2_vals ** j)
            return result
        
        # If dimensions don't match, create a mesh grid
        dim1_vals = np.asarray(dim1_vals)
        dim2_vals = np.asarray(dim2_vals)
        
        # Create 2D meshgrid
        x_2d, y_2d = np.meshgrid(dim1_vals, dim2_vals, indexing='ij')
        
        # Initialize output array
        output = np.zeros((len(dim1_vals), len(dim2_vals)))

        # Evaluate polynomial
        for i in range(poly_coefs.shape[0]):
            for j in range(poly_coefs.shape[1]):
                output += poly_coefs[i, j] * (x_2d ** i) * (y_2d ** j)
        
        return output

    def rcs_st_ft(self, complex_data, lookdir='R', oversample_ratio=None, cal_sf=None, mask=None, meta=None):
        """
        Computes total calibrated RCS for an ROI and slow/fast time RCS data profiles.
        
        Parameters:
            complex_data (ndarray): Complex valued SAR dataset in the image domain.
                                First dimension is azimuth, second range.
                                Third dimension could be for multi-channel data.
            lookdir (str): "Left" or "Right"
            oversample_ratio (array-like): Oversample or zeropad factor.
                                        Required for calibrated RCS.
            cal_sf (float or ndarray): Calibration scale factor (linear).
                                    Either a constant or an array the same size
                                    as complex_data with per-pixel values.
            mask (ndarray): Binary image which is ones over the region of interest.
            meta (dict): SICD metadata structure
        
        Returns:
            tuple: (profile_slow, profile_fast)
                - profile_slow (ndarray): Slow-time profile
                - profile_fast (ndarray): Fast-time profile
        """
        # Default parameter values
        if oversample_ratio is None:
            oversample_ratio = np.array([1, 1])  # RCS values will be uncalibrated
        else:
            oversample_ratio = np.asarray(oversample_ratio)

        if cal_sf is None:
            cal_sf = 1  # RCS values will be uncalibrated

        if mask is None:
            mask = np.ones_like(complex_data, dtype=complex_data.dtype)

        # Apply shape mask to rectangular data
        if complex_data.ndim == 3:
            filtimg = complex_data * np.repeat(
                mask[:, :, np.newaxis], complex_data.shape[2], axis=2
            )
        else:
            filtimg = complex_data * mask

        if not np.isscalar(cal_sf):
            # Only works if the radiometric scale factors are same for both channels
            if complex_data.ndim == 3:
                cal_sf = np.repeat(
                    cal_sf[:, :, np.newaxis], complex_data.shape[2], axis=2
                )

        # Inverse polar formatting breaks on some data, so it is disabled
        inverse_polar = False

        # Determine fft size to use based on size of imagery
        data_size = complex_data.shape
        fftsize = (2 ** np.ceil(np.log2(data_size[:2])) * 4).astype(int)

        if inverse_polar:  # Inverse polar formatting is the most precise way
            # Placeholder for future implementation

            # totalRCS = self.rcs_compute(complex_data, oversample_ratio, cal_sf, mask)
            # # TODO: Handle multi-channel (polarimetric) datasets
            # # TODO: Check automatically for whether data is suitable for inverse polar formatting
            # # TODO: Pass k_a and k_r back out so that slow time axes can be computed with them
            # # TODO: Show inverse polar format grid in figure if asked

            # ss = [meta.Grid.Col.SS, meta.Grid.Row.SS]
            # imp_resp_bw = [meta.Grid.Col.ImpRespBW, meta.Grid.Row.ImpRespBW]

            # angle_rf_domain, k_a, k_r = pfa_inv_mem(filtimg, meta.Grid.Row.KCtr, ss, imp_resp_bw, fftsize, -1) # need to figure out what pfa_inv_mem is and how to implement our own

            # # Sum over constant angle
            # profile_slow = np.sum(np.abs(angle_rf_domain)**2, axis=1)

            # # Sum over constant RF frequency
            # profile_fast = np.sum(np.abs(angle_rf_domain)**2, axis=0)

            # # Set the mean to be equal to the image domain computed RCS
            # profile_slow = profile_slow * totalRCS / np.mean(profile_slow)
            # profile_fast = profile_fast * totalRCS / np.mean(profile_fast)

            raise NotImplementedError("Inverse polar formatting not yet implemented")
        else:
            # Use polar format approximation
            # Columns approximate time/azimuth angle and rows approximate receive frequency
            nz_data_points = (fftsize / oversample_ratio).astype(int)

            rgcomp = np.fft.fftshift(
                np.fft.fft(filtimg , fftsize[0], axis=0, norm='backward'),
                axes=0) / np.sqrt(fftsize[0])

            azcomp = np.fft.fftshift(
                np.fft.fft(filtimg , fftsize[1], axis=1, norm='backward'),
                axes=1) / np.sqrt(fftsize[1])

            profile_slow = np.sum(np.abs(rgcomp) ** 2, axis=1) * nz_data_points[0] ** 2 / oversample_ratio[1]
            profile_fast = np.sum(np.abs(azcomp) ** 2, axis=0) * nz_data_points[1] ** 2 / oversample_ratio[0]
        
        # Handle look direction
        if lookdir.upper().startswith("R"):
            profile_slow = profile_slow[::-1]

        # Handle multi-channel data
        profile_slow = np.squeeze(profile_slow)

        if profile_fast.ndim == 1:
            profile_fast = (
                profile_fast.flatten()
            )  # Just flatten, don't reshape to column
        else:
            profile_fast = np.squeeze(profile_fast)
        
        return profile_slow, profile_fast

    def rcs_range_profile(
        self, 
        complex_data: NDArray[np.complex128], 
        oversample_ratio: Optional[Union[List[float], NDArray[np.float64]]] = None, 
        cal_sf: Optional[Union[float, NDArray[np.float64]]] = None, 
        mask: Optional[NDArray[np.bool_]] = None
    ) -> NDArray[np.float64]:
        """
        Compute calibrated range profile.

        Parameters
        ----------
        complex_data : ndarray
            Complex valued SAR dataset in the image domain.
            First dimension is azimuth, second range.
            Third dimension could be for multi-channel data.
        oversample_ratio : array-like, optional
            Oversample or zeropad factor. Required for calibrated RCS.
        cal_sf : float or ndarray, optional
            Calibration scale factor (linear). Either a constant or an array 
            the same size as complex_data with per-pixel values.
        mask : ndarray, optional
            Binary image which is ones over the region of interest.
            Default is an image of all ones.

        Returns
        -------
        ndarray
            Range profile
        """
        # Handle default parameters
        if oversample_ratio is None:
            oversample_ratio = np.array([1, 1])
        if cal_sf is None:
            cal_sf = 1
        if mask is None:
            mask = np.ones_like(complex_data)

        # Apply shape mask to rectangular data
        if complex_data.ndim == 3:
            filtimg = complex_data * np.repeat(
                mask[:, :, np.newaxis], complex_data.shape[2], axis=2
            )
        else:
            filtimg = complex_data * mask

        # Handle calibration scale factor for multi-channel data
        if not np.isscalar(cal_sf) and complex_data.ndim == 3:
            cal_sf = np.repeat(cal_sf[:, :, np.newaxis], complex_data.shape[2], axis=2)

        # Compute range profile
        range_profile = (1 / np.prod(oversample_ratio)) * np.sum(
            cal_sf * np.abs(filtimg) ** 2, axis=0
        )

        # Format output
        if range_profile.ndim == 1:
            range_profile = range_profile.reshape(-1, 1)  # Ensure in first dimension
        else:
            range_profile = np.squeeze(range_profile)  # For multi-channel data

        return range_profile

    def rcs_compute(
        self, 
        complex_data: NDArray[np.complex128], 
        oversample_ratio: Optional[Union[List[float], NDArray[np.float64]]] = None, 
        cal_sf: Optional[Union[float, NDArray[np.float64]]] = None, 
        mask: Optional[NDArray[np.bool_]] = None
    ) -> Union[float, NDArray[np.float64]]:
        """
        Compute area-based calibrated RCS for a region of interest.

        Parameters
        ----------
        complex_data : ndarray
            Complex valued SAR dataset in the image domain.
            First dimension is azimuth, second range.
            Third dimension could be for multi-channel data.
        oversample_ratio : array-like, optional
            Oversample or zeropad factor. Required for calibrated RCS.
        cal_sf : float or ndarray, optional
            Calibration scale factor (linear). Either a constant or an array 
            the same size as complex_data with per-pixel values.
        mask : ndarray, optional
            Binary image which is ones over the region of interest.
            Default is an image of all ones.

        Returns
        -------
        float or ndarray
            Total calibrated RCS of ROI. Returns array for multi-channel data.
        """
        # Handle default parameters
        if oversample_ratio is None:
            oversample_ratio = np.array([1, 1])  # RCS values will be uncalibrated
        else:
            oversample_ratio = np.asarray(oversample_ratio)

        if cal_sf is None:
            cal_sf = 1  # RCS values will be uncalibrated

        if mask is None:
            mask = np.ones_like(complex_data)

        # Apply shape mask to rectangular data
        if complex_data.ndim == 3:
            filtimg = complex_data * np.repeat(
                mask[:, :, np.newaxis], complex_data.shape[2], axis=2
            )
        else:
            filtimg = complex_data * mask

        # Handle calibration scale factor for multi-channel data
        if not np.isscalar(cal_sf) and complex_data.ndim == 3:
            cal_sf = np.repeat(cal_sf[:, :, np.newaxis], complex_data.shape[2], axis=2)

        # Image domain computation of total RCS
        # The oversample ratio (or zeropad) factor is the ratio between the sum of
        # squared (power detected) samples of an ideal sinc function and the peak
        # of that ideal sinc^2 function
        totalRCS = (1 / np.prod(oversample_ratio)) * np.sum(
            np.sum(cal_sf * np.abs(filtimg) ** 2, axis=0), axis=0
        )

        # Handle multi-channel data
        totalRCS = np.squeeze(totalRCS)

        return totalRCS

    def compute_rcs_figures(self, selected_widget, meta_data, geometry, slow_units, measure_units):
        
        bounding_box = geometry.get_bbox()
        central_row_col = [
            (bounding_box[1] + bounding_box[3]) / 2,
            (bounding_box[0] + bounding_box[2]) / 2,
        ]

        look_direction = meta_data["SCPCOA"]["SideOfTrack"]

        oversample_ratio = [
            1.0
            / (meta_data["Grid"]["Col"]["SS"] * meta_data["Grid"]["Col"]["ImpRespBW"]),
            1.0
            / (meta_data["Grid"]["Row"]["SS"] * meta_data["Grid"]["Row"]["ImpRespBW"]),
        ]

        cal_sf = self.get_calibration_scale_factor(meta_data, measure_units)

        row_bounds, col_bounds, mask = _get_polygon_bounds(
            geometry, selected_widget.reader.get_data_size_as_tuple()[0]
        )

        complex_data = selected_widget.reader[
            row_bounds[0] : row_bounds[1], col_bounds[0] : col_bounds[1]
        ]

        # Transpose the complex data to account for MATLAB's column-major vs Python's row-major order
        complex_data = complex_data.T
        mask = mask.T if mask is not None else None

        # If cal_sf is a 2D array, it needs to be transposed too
        if isinstance(cal_sf, np.ndarray) and cal_sf.ndim == 2:
            cal_sf = cal_sf.T

        slow_data, fast_data = self.rcs_st_ft(
            complex_data, look_direction, oversample_ratio, cal_sf, mask, meta_data
        )

        range_data = self.rcs_range_profile(
            complex_data, oversample_ratio, cal_sf, mask
        )
        total_rcs = self.rcs_compute(complex_data, oversample_ratio, cal_sf, mask)

        scale_factor = self.compute_scale_factor(
            meta_data, measure_units, mask, oversample_ratio
        )

        slow_data = 10 * np.log10(slow_data * scale_factor)
        fast_data = 10 * np.log10(fast_data * scale_factor)
        total_rcs = 10 * np.log10(total_rcs * scale_factor)
        # range_data = 10 * np.log10(range_data*scale_factor)

        relative_azimuth = self.get_reference_azimuth_angle()
        slow_range, slow_axis_label = self.compute_slow_time_axis(meta_data, selected_widget, slow_units, central_row_col, relative_azimuth)
        fast_range, fast_axis_label = self.compute_fast_time_axis(meta_data)

        # reversed the data to account for differences in plotting matlab vs pyqtgraph
        slow_x_data = np.linspace(slow_range[0], slow_range[1], len(slow_data))
        fast_x_data = np.linspace(fast_range[0], fast_range[1], len(fast_data))

        return (
            (self.ensure_1d_array(slow_data)),
            (self.ensure_1d_array(fast_data)),
            self.ensure_1d_array(slow_x_data),
            self.ensure_1d_array(fast_x_data),
            slow_axis_label,
            fast_axis_label,
        )

    def ensure_1d_array(self, arr: Union[List[Any], NDArray]) -> NDArray:
        """
        Convert array to 1D shape that pyqtgraph expects.
        
        Parameters
        ----------
        arr : array-like
            The array to convert.
            
        Returns
        -------
        numpy.ndarray
            The flattened 1D array.
        """
        arr = np.asarray(arr)
        if arr.ndim > 1:
            return arr.flatten()
        return arr

    def get_calibration_scale_factor(
        self, 
        meta_data: Dict[str, Any], 
        measure_units: str
    ) -> Optional[Union[float, NDArray[np.float64]]]:
        """
        Get calibration scale factor based on desired measurement units.
        
        Parameters
        ----------
        meta_data : dict
            Metadata dictionary containing Radiometric information.
        measure_units : str
            Units for the measurements (e.g., 'Pixel Power', 'RCS', 'σ₀', 'β₀', 'γ₀').
            
        Returns
        -------
        float or ndarray
            The calibration scale factor.
        """
        if measure_units == "Pixel Power":
            cal_sf = 1
        elif measure_units == "RCS":
            cal_sf = meta_data["Radiometric"]["RCSSFPoly"]["Coefs"][0][0]
        elif measure_units == "σ\u2080":
            cal_sf = meta_data["Radiometric"]["SigmaZeroSFPoly"]["Coefs"][0][0]
        elif measure_units == "β\u2080":
            cal_sf = meta_data["Radiometric"]["BetaZeroSFPoly"]["Coefs"][0][0]
        elif measure_units == "γ\u2080":
            cal_sf = meta_data["Radiometric"]["GammaZeroSFPoly"]["Coefs"][0][0]
        else:
            print("Error: Invalid units provided.")
            cal_sf = None
        return cal_sf

    def compute_scale_factor(
        self, 
        meta_data: Dict[str, Any], 
        units: str, 
        mask: NDArray[np.bool_], 
        oversample_ratio: Union[List[float], NDArray[np.float64]]
    ) -> float:
        """
        Compute scale factor based on measurement type.
        
        Parameters
        ----------
        meta_data : dict
            Metadata dictionary containing Grid and SCPCOA information.
        units : str
            Units for the measurements (e.g., 'RCS', 'σ₀', 'β₀', 'γ₀', 'Pixel Power').
        mask : ndarray
            Binary image which is ones over the region of interest.
        oversample_ratio : array-like
            Oversample or zeropad factor.
            
        Returns
        -------
        float
            The computed scale factor.
        """
        # Check for and compute range weighting factor
        if "WgtFunct" in meta_data["Grid"]["Row"]:
            rng_wgt = np.array(meta_data["Grid"]["Row"]["WgtFunct"])
            rng_wght_f = np.mean(rng_wgt**2) / (np.mean(rng_wgt) ** 2)
        else:
            # If no weight in metadata, assume uniform weighting
            rng_wght_f = 1.0

        # Check for and compute azimuth weighting factor
        if "WgtFunct" in meta_data["Grid"]["Col"]:
            az_wgt = np.array(meta_data["Grid"]["Col"]["WgtFunct"])
            az_wght_f = np.mean(az_wgt**2) / (np.mean(az_wgt) ** 2)
        else:
            # If no weight in metadata, assume uniform weighting
            az_wght_f = 1.0

        # Compute area with weighting factors
        area_sp = (
            np.sum(mask)
            * meta_data["Grid"]["Row"]["SS"]
            * meta_data["Grid"]["Col"]["SS"]
            * (rng_wght_f * az_wght_f)
        )

        # Compute scale factor based on measurement type
        if units == "RCS":
            # No weighting compensation here since totalRCS was computed
            # with weighting, although slow/fast-time curves removed
            # weighting (but were then scaled appropriately).
            scale_factor = 1

        elif units == "σ\u2080":
            # Normalize by ground area if sigma-0 requested
            scale_factor = np.cos(np.radians(meta_data["SCPCOA"]["SlopeAng"])) / area_sp

        elif units == "β\u2080":
            scale_factor = 1 / area_sp

        elif units == "γ\u2080":
            slope_ang = meta_data["SCPCOA"]["SlopeAng"]
            graze_ang = meta_data["SCPCOA"]["GrazeAng"]
            scale_factor = np.cos(np.radians(slope_ang)) / (
                np.sin(np.radians(graze_ang)) * area_sp
            )

        elif units == "Pixel Power":
            # Raw pixel power
            scale_factor = np.prod(oversample_ratio) / np.sum(mask)

        else:
            raise ValueError(f"Unknown measurement type: {units}")

        return scale_factor