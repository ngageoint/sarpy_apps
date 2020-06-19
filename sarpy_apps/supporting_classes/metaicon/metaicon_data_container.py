"""
The container object for the metaicon object.
"""

import logging
from datetime import datetime
from scipy.constants import foot

from sarpy.geometry import latlon
from sarpy.io.complex.sicd_elements.SICD import SICDType
from sarpy.io.complex.sidd_elements.SIDD import SIDDType  # version 2.0
from sarpy.io.complex.sidd_elements.sidd1_elements.SIDD import SIDDType as SIDDType1  # version 1.0
from sarpy.io.complex.cphd_elements.CPHD import CPHDType  # version 1.0
from sarpy.io.complex.cphd_elements.cphd0_3.CPHD import CPHDType as CPHDType0_3  # version 0.3

ANGLE_DECIMALS = {'azimuth': 1, 'graze': 1, 'layover': 0, 'shadow': 0, 'multipath': 0}


class Constants:  # TODO: what role does this play?
    class ImagePlaneTypes:
        slant = "slant"

    class SideOfTrackTypes:
        R = "R"


class MetaIconDataContainer(object):
    """
    Container object for rendering the metaicon element.
    """

    def __init__(self,
                 iid=None,
                 lat=None,
                 lon=None,
                 collect_start=None,
                 collect_duration=None,
                 collector_name=None,
                 core_name=None,
                 azimuth=None,
                 graze=None,
                 layover=None,
                 shadow=None,
                 multipath=None,
                 multipath_ground=None,
                 side_of_track=None,
                 col_impulse_response_width=None,
                 row_impulse_response_width=None,
                 tx_rf_bandwidth=None,
                 rniirs=None,
                 polarization=None,
                 image_plane=None,  # TODO: what are these last 4?
                 is_grid=None,
                 grid_column_sample_spacing=None,
                 grid_row_sample_spacing=None):
        """

        Parameters
        ----------
        iid
        lat : None|float
        lon : None|float
        collect_start : None|numpy.datetime64
        collect_duration : None|float
        collector_name : None|str
        core_name : None|str
        azimuth : None|float
        graze : None|float
        layover : None|float
        shadow : None|float
        multipath : None|float
        multipath_ground : None|float
        side_of_track : None|str
            One of `('L', 'R')`.
        col_impulse_response_width : None|float
            In feet.
        row_impulse_response_width : None|float
            In feet.
        tx_rf_bandwidth : None|float
            In MHz.
        rniirs : None|str
        polarization : None|str

        image_plane : None|str
        is_grid : None|bool
        grid_column_sample_spacing : None|float
        grid_row_sample_spacing : None|float
        """
        # TODO: beef up the documentation describing the above variables

        # TODO: is this variable overtaken by events?
        self.iid = iid

        self.lat = lat
        self.lon = lon

        self.collect_start = collect_start
        self.collect_duration = collect_duration

        self.collector_name = collector_name
        self.core_name = core_name

        self.azimuth = azimuth
        self.graze = graze
        self.layover = layover
        self.shadow = shadow
        self.multipath = multipath
        self.multipath_ground = multipath_ground
        self.side_of_track = side_of_track

        self.col_impulse_response_width = col_impulse_response_width
        self.row_impulse_response_width = row_impulse_response_width
        self.tx_rf_bandwidth = tx_rf_bandwidth

        self.rniirs = rniirs
        self.polarization = polarization

        # TODO: these last 4 need to be set for sicd
        self.image_plane = image_plane
        self.is_grid = is_grid
        self.grid_column_sample_spacing = grid_column_sample_spacing
        self.grid_row_sample_spacing = grid_row_sample_spacing

        self.constants = Constants()  # TODO: what role does this play?

    @property
    def cdp_line(self):
        """
        str: The collection duration/polarization line value.
        """

        cdp_line = 'CDP: No data'
        if self.collect_duration is not None:
            cdp_line = "CDP: {0:0.1f} s".format(self.collect_duration)

        if self.polarization is not None:
            cdp_line += ' / POL: {0:s}'.format(self.polarization)
        return cdp_line

    @property
    def geo_line(self):
        """
        str: The geographic location line data.
        """

        lat, lon = self.lat, self.lon
        if lat is not None:
            return 'Geo: {0:s}/{1:s}'.format(
                latlon.string(lat, "lat", include_symbols=False),
                latlon.string(lon, "lon", include_symbols=False))
        return 'Geo: No data'

    @property
    def res_line(self):
        """
        str: The impulse response data line.
        """

        if self.col_impulse_response_width is not None:
            az_ipr = self.col_impulse_response_width
            rg_ipr = self.row_impulse_response_width
            if az_ipr/rg_ipr - 1 < 0.2:
                res_line = 'IPR: {0:0.1f} ft'.format(0.5*(az_ipr + rg_ipr))
            else:
                res_line = 'IPR: {0:0.1f}/{1:0.1f} ft(A/R)'.format(az_ipr, rg_ipr)
        elif self.tx_rf_bandwidth is not None:
            res_line = 'IPR: {0:0.0f} MHz'.format(self.tx_rf_bandwidth)
        else:
            res_line = 'IPR: No data'
        if self.rniirs:
            res_line += " RNIIRS: " + self.rniirs
        return res_line

    @property
    def iid_line(self):
        """
        str: The data/time data.
        """

        if self.collector_name is not None:
            if self.collect_start is not None:
                dt = self.collect_start.astype(datetime)
                date_str_1, date_str_2 = dt.strftime("%d%b%y").upper(), dt.strftime("%H%MZ")
            else:
                date_str_1, date_str_2 = "DDMMMYY", "HMZ"
            return '{} {} / {}'.format(date_str_1, self.collector_name[:4], date_str_2)
        elif self.core_name is not None:
            return self.core_name[:16]
        return "No iid"

    def get_angle_line(self, angle_type, symbol='\xB0'):
        """
        Extracts proper angle line formatting.

        Parameters
        ----------
        angle_type : str
            The name of the angle type.
        symbol : str
            The degree symbol string, if any.

        Returns
        -------
        str
        """

        value = getattr(self, angle_type, None)
        if value is None:
            return "{}: No data".format(angle_type.capitalize())

        decimals = ANGLE_DECIMALS.get(angle_type, 0)
        frm_str = '{0:s}:{1:0.'+str(decimals)+'f}{2:s}'
        return frm_str.format(angle_type.capitalize(), value, symbol)

    @classmethod
    def from_sicd(cls, sicd):
        """
        Create an instance from a SICD object.

        Parameters
        ----------
        sicd : SICDType

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(sicd, SICDType):
            raise TypeError(
                'sicd is expected to be an instance of SICDType, got type {}'.format(type(sicd)))

        def extract_scp():
            try:
                llh = sicd.GeoData.SCP.LLH.get_array()
                vars['lat'] = float(llh[0])
                vars['lon'] = float(llh[1])
            except AttributeError:
                pass

        def extract_timeline():
            try:
                vars['collect_start'] = sicd.Timeline.CollectStart
            except AttributeError:
                pass

            try:
                vars['collect_duration'] = sicd.Timeline.CollectDuration
            except AttributeError:
                pass

        def extract_collectioninfo():
            try:
                vars['collector_name'] = sicd.CollectionInfo.CollectorName
                vars['core_name'] = sicd.CollectionInfo.CoreName
            except AttributeError:
                pass

        def extract_scpcoa():
            try:
                vars['azimuth'] = sicd.SCPCOA.AzimAng
                vars['graze'] = sicd.SCPCOA.GrazeAng
                vars['layover'] = sicd.SCPCOA.LayoverAng
                vars['shadow'] = sicd.SCPCOA.Shadow
                vars['multipath'] = sicd.SCPCOA.Multipath
                vars['multipath_ground'] = sicd.SCPCOA.MultipathGround
                vars['side_of_track'] = sicd.SCPCOA.SideOfTrack
            except AttributeError:
                pass

        def extract_imp_resp():
            try:
                vars['row_impulse_response_width'] = sicd.Grid.Row.ImpRespWid/foot
                vars['col_impulse_response_width'] = sicd.Grid.Col.ImpRespWid/foot
            except AttributeError:
                pass

            try:
                vars['tx_rf_bandwidth'] = sicd.RadarCollection.Waveform[0].TxRFBandwidth*1e-6
            except AttributeError:
                pass

        def extract_rniirs():
            try:
                vars['rniirs'] = sicd.CollectionInfo.Parameters.get('PREDICTED_RNIIRS', None)
            except AttributeError:
                pass

        def extract_polarization():
            try:
                proc_pol = sicd.ImageFormation.TxRcvPolarizationProc
                if proc_pol is not None:
                    vars['polarization'] = proc_pol
                return
            except AttributeError:
                pass

            try:
                vars['polarization'] = sicd.RadarCollection.TxPolarization
            except AttributeError:
                logging.error('No polarization found.')

        vars = {}
        extract_scp()
        extract_timeline()
        extract_collectioninfo()
        extract_scpcoa()
        extract_imp_resp()
        extract_rniirs()
        extract_polarization()
        return cls(**vars)

    @classmethod
    def from_cphd(cls, cphd):
        """
        Create an instance from a CPHD object.

        Parameters
        ----------
        cphd : CPHDType|CPHDType0_3

        Returns
        -------
        MetaIconDataContainer
        """

        if isinstance(cphd, CPHDType):
            return cls._from_cphd1_0(cphd)
        elif isinstance(cphd, CPHDType0_3):
            return cls._from_cphd0_3(cphd)
        else:
            raise TypeError('Expected a CPHD type, and got type {}'.format(type(cphd)))

    @classmethod
    def _from_cphd1_0(cls, cphd):
        """
        Create an instance from a CPHD version 1.0 object.

        Parameters
        ----------
        cphd : CPHDType

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(cphd, CPHDType):
            raise TypeError(
                'cphd is expected to be an instance of CPHDType, got type {}'.format(type(cphd)))

        # TODO: finish this
        raise NotImplementedError

    @classmethod
    def _from_cphd0_3(cls, cphd):
        """
        Create an instance from a CPHD version 0.3 object.

        Parameters
        ----------
        cphd : CPHDType0_3

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(cphd, CPHDType0_3):
            raise TypeError(
                'cphd is expected to be an instance of CPHDType version 0.3, got type {}'.format(type(cphd)))

        # TODO: finish this
        raise NotImplementedError

    @classmethod
    def from_sidd(cls, sidd):
        """
        Create an instance from a SIDD object.

        Parameters
        ----------
        cphd : SIDDType|SIDDType1

        Returns
        -------
        MetaIconDataContainer
        """

        if isinstance(sidd, SIDDType):
            return cls._from_sidd2(sidd)
        elif isinstance(sidd, SIDDType1):
            return cls._from_sidd1(sidd)
        else:
            raise TypeError('Expected a SIDD type, and got type {}'.format(type(sidd)))

    @classmethod
    def _from_sidd2(cls, sidd):
        """
        Create an instance from a SIDD 2.0 object.

        Parameters
        ----------
        cphd : SIDDType

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(sidd, SIDDType):
            raise TypeError(
                'sidd is expected to be an instance of SIDDType, got type {}'.format(type(sidd)))

        # TODO: finish this
        raise NotImplementedError

    @classmethod
    def _from_sidd1(cls, sidd):
        """
        Create an instance from a SIDD version 1.0 object.

        Parameters
        ----------
        cphd : SIDDType1

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(sidd, SIDDType1):
            raise TypeError(
                'sidd is expected to be an instance of SIDDType version 1.0, got type {}'.format(type(sidd)))

        # TODO: finish this
        raise NotImplementedError
