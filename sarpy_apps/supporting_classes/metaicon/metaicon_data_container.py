class Constants:
    class ImagePlaneTypes:
        slant = "slant"

    class SideOfTrackTypes:
        R = "R"


class MetaIconDataContainer:
    def __init__(self,
                 iid=None,
                 lat=None,
                 lon=None,
                 col_impulse_response_width=None,
                 row_impulse_response_width=None,
                 collect_start=None,
                 collect_duration=None,
                 azimuth=None,
                 polarization=None,
                 graze=None,
                 layover=None,
                 shadow=None,
                 multipath=None,
                 multipath_ground=None,
                 tx_rf_bandwidth=None,
                 rniirs=None,           # type: float
                 image_plane=None,      # type: str
                 is_grid=None,         # type: bool
                 side_of_track=None,    # type: str
                 grid_column_sample_spacing=None,       # type: float
                 grid_row_sample_spacing=None,          # type: float
                 collector_name=None,           # type: str
                 core_name=None,                # type: str
                 ):
        self.iid = iid
        self.lat = lat
        self.lon = lon
        self.col_impulse_response_width = col_impulse_response_width
        self.row_impulse_response_width = row_impulse_response_width
        self.collect_start = collect_start
        self.collect_duration = collect_duration
        self.azimuth = azimuth
        self.graze = graze
        self.layover = layover
        self.shadow = shadow
        self.multipath = multipath
        self.multipath_ground = multipath_ground
        self.tx_rf_bandwidth = tx_rf_bandwidth
        self.rniirs = rniirs
        self.polarization = polarization
        self.image_plane = image_plane
        self.is_grid = is_grid
        self.side_of_track = side_of_track
        self.grid_column_sample_spacing = grid_column_sample_spacing
        self.grid_row_sample_spacing = grid_row_sample_spacing
        self.collector_name = collector_name
        self.core_name = core_name

        self.constants = Constants()
