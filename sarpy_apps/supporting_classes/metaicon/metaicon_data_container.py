"""
The container object for the metaicon object.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")


import logging
from datetime import datetime

import numpy
from scipy.constants import foot

from sarpy.geometry import latlon
from sarpy.geometry.geocoords import ecf_to_geodetic, geodetic_to_ecf, ecf_to_ned
from sarpy.io.complex.sicd_elements.SICD import SICDType
from sarpy.io.product.sidd2_elements.SIDD import SIDDType  # version 2.0
from sarpy.io.product.sidd1_elements.SIDD import SIDDType as SIDDType1  # version 1.0
from sarpy.io.phase_history.cphd1_elements.CPHD import CPHDType  # version 1.0
from sarpy.io.phase_history.cphd0_3_elements.CPHD import CPHDType as CPHDType0_3  # version 0.3
from sarpy.io.phase_history.crsd1_elements.CRSD import CRSDType  # version 1.0
from sarpy.io.complex.sicd_elements.SCPCOA import GeometryCalculator
from sarpy.io.product.sidd2_elements.ExploitationFeatures import ExploitationCalculator


ANGLE_DECIMALS = {'azimuth': 1, 'graze': 1, 'layover': 0, 'shadow': 0, 'multipath': 0}


class MetaIconDataContainer(object):
    """
    Container object for rendering the metaicon element.
    """

    def __init__(self,
                 lat=None,
                 lon=None,
                 collect_start=None,
                 collect_duration=None,
                 collector_name=None,
                 core_name=None,
                 azimuth=None,
                 north=None,
                 graze=None,
                 layover=None,
                 layover_display=None,
                 shadow=None,
                 shadow_display=None,
                 multipath=None,
                 multipath_display=None,
                 side_of_track=None,
                 col_impulse_response_width=None,
                 row_impulse_response_width=None,
                 grid_column_sample_spacing=None,
                 grid_row_sample_spacing=None,
                 image_plane=None,
                 tx_rf_bandwidth=None,
                 rniirs=None,
                 polarization=None):
        """

        Parameters
        ----------
        lat : None|float
        lon : None|float
        collect_start : None|numpy.datetime64
        collect_duration : None|float
        collector_name : None|str
        core_name : None|str
        azimuth : None|float
            This should be clockwise relative to True North.
        north : None|float
            Clockwise relative to decreasing row direction (i.e. "up").
        graze : None|float
            The graze angle, in degree.
        layover : None|float
            Clockwise relative to decreasing row direction (i.e. "up").
        layover_display : None|float
            The angle value for display. The meaning of this varies between different
            structure types.
        shadow : None|float
            Clockwise relative to decreasing row direction (i.e. "up").
        shadow_display : None|float
            The angle value for display. The meaning of this varies between different
            structure types.
        multipath : None|float
            Clockwise relative to decreasing row direction (i.e. "up").
        multipath_display : None|float
            The angle value for display. The meaning of this varies between different
            structure types.
        side_of_track : None|str
            One of `('L', 'R')`.
        col_impulse_response_width : None|float
            In meters.
        row_impulse_response_width : None|float
            In meters.
        grid_column_sample_spacing : None|float
            Assumed to be in meters, but the units are not important provided
            that they are the same for row and column.
        grid_row_sample_spacing : None|float
            Assumed to be in meters, but the units are not important provided
            that they are the same for row and column.
        image_plane : None|str
            The image plane value.
        tx_rf_bandwidth : None|float
            In MHz.
        rniirs : None|str
            RNIIRS value.
        polarization : None|str
            The polarization string.
        """

        self.lat = lat
        self.lon = lon

        self.collect_start = collect_start
        self.collect_duration = collect_duration

        self.collector_name = collector_name
        self.core_name = core_name

        self.azimuth = azimuth
        self.north = north
        self.graze = graze
        self.layover = layover
        self.layover_display = layover_display
        self.shadow = shadow
        self.shadow_display = shadow_display
        self.multipath = multipath
        self.multipath_display = multipath_display

        self.side_of_track = side_of_track

        self.col_impulse_response_width = col_impulse_response_width
        self.row_impulse_response_width = row_impulse_response_width
        self.grid_column_sample_spacing = grid_column_sample_spacing
        self.grid_row_sample_spacing = grid_row_sample_spacing
        self.image_plane = image_plane
        self.tx_rf_bandwidth = tx_rf_bandwidth

        self.rniirs = rniirs
        self.polarization = polarization

    @property
    def is_grid(self):
        """
        bool: This is a grid collection
        """

        return self.grid_row_sample_spacing is not None

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
            az_ipr = self.col_impulse_response_width/foot
            rg_ipr = self.row_impulse_response_width/foot
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
                dt_in_seconds = self.collect_start.astype('datetime64[s]')
                dt = dt_in_seconds.astype(datetime)
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

        value = getattr(self, angle_type+'_display', None)
        if value is None:
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
                variables['lat'] = float(llh[0])
                variables['lon'] = float(llh[1])
            except AttributeError:
                pass

        def extract_timeline():
            try:
                variables['collect_start'] = sicd.Timeline.CollectStart
            except AttributeError:
                pass

            try:
                variables['collect_duration'] = sicd.Timeline.CollectDuration
            except AttributeError:
                pass

        def extract_collectioninfo():
            try:
                variables['collector_name'] = sicd.CollectionInfo.CollectorName
                variables['core_name'] = sicd.CollectionInfo.CoreName
            except AttributeError:
                pass

        def extract_scpcoa():
            if sicd.SCPCOA is None:
                return

            variables['side_of_track'] = sicd.SCPCOA.SideOfTrack
            azimuth = sicd.SCPCOA.AzimAng
            if azimuth is None:
                return

            north = ((360 - azimuth) % 360)
            variables['azimuth'] = azimuth
            variables['north'] = north
            variables['graze'] = sicd.SCPCOA.GrazeAng

            layover = sicd.SCPCOA.LayoverAng
            if layover is not None:
                variables['layover'] = ((layover-azimuth + 360) % 360)
                variables['layover_display'] = layover

            variables['shadow'] = 180

            multipath = sicd.SCPCOA.Multipath
            if multipath is not None:
                variables['multipath'] = ((multipath - azimuth + 360) % 360)
                variables['multipath_display'] = multipath

        def extract_imp_resp():
            if sicd.Grid is not None:
                try:
                    variables['image_plane'] = sicd.Grid.ImagePlane
                except AttributeError:
                    pass

                try:
                    variables['row_impulse_response_width'] = sicd.Grid.Row.ImpRespWid
                    variables['col_impulse_response_width'] = sicd.Grid.Col.ImpRespWid
                except AttributeError:
                    pass

                try:
                    variables['grid_row_sample_spacing'] = sicd.Grid.Row.SS
                    variables['grid_column_sample_spacing'] = sicd.Grid.Col.SS
                except AttributeError:
                    pass
            try:
                variables['tx_rf_bandwidth'] = sicd.RadarCollection.Waveform[0].TxRFBandwidth*1e-6
            except AttributeError:
                pass

        def extract_rniirs():
            try:
                variables['rniirs'] = sicd.CollectionInfo.Parameters.get('PREDICTED_RNIIRS', None)
            except AttributeError:
                pass

        def extract_polarization():
            try:
                proc_pol = sicd.ImageFormation.TxRcvPolarizationProc
                if proc_pol is not None:
                    variables['polarization'] = proc_pol
                return
            except AttributeError:
                pass

            try:
                variables['polarization'] = sicd.RadarCollection.TxPolarization
            except AttributeError:
                logging.error('No polarization found.')

        variables = {}
        extract_scp()
        extract_timeline()
        extract_collectioninfo()
        extract_scpcoa()
        extract_imp_resp()
        extract_rniirs()
        extract_polarization()
        return cls(**variables)

    @classmethod
    def from_cphd(cls, cphd, index):
        """
        Create an instance from a CPHD object.

        Parameters
        ----------
        cphd : CPHDType|CPHDType0_3
        index
            The index for the data channel.

        Returns
        -------
        MetaIconDataContainer
        """

        if isinstance(cphd, CPHDType):
            return cls._from_cphd1_0(cphd, index)
        elif isinstance(cphd, CPHDType0_3):
            return cls._from_cphd0_3(cphd, index)
        else:
            raise TypeError('Expected a CPHD type, and got type {}'.format(type(cphd)))

    @classmethod
    def _from_cphd1_0(cls, cphd, index):
        """
        Create an instance from a CPHD version 1.0 object.

        Parameters
        ----------
        cphd : CPHDType
        index
            The index of the data channel.

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(cphd, CPHDType):
            raise TypeError(
                'cphd is expected to be an instance of CPHDType, got type {}'.format(type(cphd)))

        def extract_collection_id():
            if cphd.CollectionID is None:
                return

            try:
                variables['collector_name'] = cphd.CollectionID.CollectorName
            except AttributeError:
                pass

            try:
                variables['core_name'] = cphd.CollectionID.CoreName
            except AttributeError:
                pass

        def extract_coords():
            try:
                coords = cphd.SceneCoordinates.IARP.LLH.get_array()
                variables['lat'] = coords[0]
                variables['lon'] = coords[1]
            except AttributeError:
                pass

        def extract_global():
            if cphd.Global is None:
                return

            try:
                variables['collect_start'] = cphd.Global.Timeline.CollectionStart
            except AttributeError:
                pass

            try:
                variables['collect_duration'] = (cphd.Global.Timeline.TxTime2 - cphd.Global.Timeline.TxTime1)
            except AttributeError:
                pass

        def extract_reference_geometry():
            if cphd.ReferenceGeometry is None:
                return

            if cphd.ReferenceGeometry.Monostatic is not None:
                mono = cphd.ReferenceGeometry.Monostatic
                variables['azimuth'] = mono.AzimuthAngle
                variables['graze'] = mono.GrazeAngle
                variables['layover'] = mono.LayoverAngle
                variables['shadow'] = mono.Shadow
                variables['multipath'] = mono.Multipath
                variables['side_of_track'] = mono.SideOfTrack
            elif cphd.ReferenceGeometry.Bistatic is not None:
                bi = cphd.ReferenceGeometry.Bistatic
                variables['azimuth'] = bi.AzimuthAngle
                variables['graze'] = bi.GrazeAngle
                variables['layover'] = bi.LayoverAngle

        def extract_channel():
            if cphd.TxRcv is None:
                return

            try:
                tx = cphd.TxRcv.TxWFParameters[index]
                rcv = cphd.TxRcv.RcvParameters[index]
                variables['tx_rf_bandwidth'] = tx.RFBandwidth*1e-6
                variables['polarization'] = tx.Polarization + ":" + rcv.Polarization
            except AttributeError:
                pass

        variables = {}
        extract_collection_id()
        extract_coords()
        extract_global()
        extract_reference_geometry()
        extract_channel()
        return cls(**variables)

    @classmethod
    def _from_cphd0_3(cls, cphd, index):
        """
        Create an instance from a CPHD version 0.3 object.

        Parameters
        ----------
        cphd : CPHDType0_3
        index
            The index of the data channel.

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(cphd, CPHDType0_3):
            raise TypeError(
                'cphd is expected to be an instance of CPHDType version 0.3, got type {}'.format(type(cphd)))

        def extract_collection_info():
            if cphd.CollectionInfo is None:
                return

            try:
                variables['collector_name'] = cphd.CollectionInfo.CollectorName
            except AttributeError:
                pass

            try:
                variables['core_name'] = cphd.CollectionInfo.CoreName
            except AttributeError:
                pass

        def extract_global():
            if cphd.Global is None:
                return

            try:
                variables['collect_start'] = cphd.Global.CollectStart
            except AttributeError:
                pass

            try:
                variables['collect_duration'] = cphd.Global.CollectDuration
            except AttributeError:
                pass

            try:
                llh_coords = cphd.Global.ImageArea.Corner.get_array(dtype=numpy.dtype('float64'))
                ecf_coords = geodetic_to_ecf(llh_coords)
                coords = ecf_to_geodetic(numpy.mean(ecf_coords, axis=0))
                variables['lat'] = coords[0]
                variables['lon'] = coords[1]
            except AttributeError:
                pass

        def extract_channel():
            if cphd.RadarCollection is not None:
                rc = cphd.RadarCollection
                try:
                    variables['tx_rf_bandwidth'] = (rc.TxFrequency.Max - rc.TxFrequency.Min)*1e-6
                    variables['polarization'] = rc.RcvChannels[index].TxRcvPolarization
                except AttributeError:
                    pass
            elif cphd.Channel is not None:
                try:
                    variables['tx_rf_bandwidth'] = cphd.Channel.Parameters[index].BWSavedNom*1e-6
                except AttributeError:
                    pass

        variables = {}
        extract_collection_info()
        extract_global()
        extract_channel()
        return cls(**variables)

    @classmethod
    def from_sidd(cls, sidd):
        """
        Create an instance from a SIDD object.

        Parameters
        ----------
        sidd : SIDDType|SIDDType1

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(sidd, (SIDDType, SIDDType1)):
            raise TypeError(
                'sidd is expected to be an instance of SIDD type, got type {}'.format(type(sidd)))

        def extract_location():
            ll_coords = None
            if isinstance(sidd, SIDDType):
                try:
                    ll_coords = sidd.GeoData.ImageCorners.get_array(dtype=numpy.dtype('float64'))
                except AttributeError:
                    pass
            elif isinstance(sidd, SIDDType1):
                try:
                    ll_coords = sidd.GeographicAndTarget.GeographicCoverage.Footprint.get_array(
                        dtype=numpy.dtype('float64'))
                except AttributeError:
                    pass
            if ll_coords is not None:
                llh_coords = numpy.zeros((ll_coords.shape[0], 3), dtype=numpy.float64)
                llh_coords[:, :2] = ll_coords
                ecf_coords = geodetic_to_ecf(llh_coords)
                coords = ecf_to_geodetic(numpy.mean(ecf_coords, axis=0))
                variables['lat'] = coords[0]
                variables['lon'] = coords[1]

        def extract_exploitation_features():
            if sidd.ExploitationFeatures is None:
                return

            try:
                exp_info = sidd.ExploitationFeatures.Collections[0].Information
                variables['collect_start'] = exp_info.CollectionDateTime
                variables['collect_duration'] = exp_info.CollectionDuration
                variables['collector_name'] = exp_info.SensorName
                if len(exp_info.Polarizations) == 1:
                    variables['polarization'] = exp_info.Polarizations[0].TxPolarization + ':' + \
                                                exp_info.Polarizations[0].RcvPolarization
            except AttributeError:
                pass

            try:
                exp_geom = sidd.ExploitationFeatures.Collections[0].Geometry
                variables['azimuth'] = exp_geom.Azimuth
                variables['graze'] = exp_geom.Graze
            except AttributeError:
                pass

            if isinstance(sidd, SIDDType1):
                north = sidd.ExploitationFeatures.Product.North
            elif isinstance(sidd, SIDDType):
                north = sidd.ExploitationFeatures.Products[0].North
            else:
                raise TypeError('Unhandled sidd type `{}`'.format(sidd.__class__))
            if north is None:
                if sidd.Measurement.PlaneProjection is None:
                    return

                ref_point = sidd.Measurement.PlaneProjection.ReferencePoint
                ref_time = sidd.Measurement.PlaneProjection.TimeCOAPoly(ref_point.Point.Row, ref_point.Point.Col)
                plane = sidd.Measurement.PlaneProjection.ProductPlane
                geom_calculator = GeometryCalculator(
                    ref_point.ECEF.get_array(dtype='float64'),
                    sidd.Measurement.ARPPoly(ref_time),
                    sidd.Measurement.ARPPoly.derivative_eval(ref_time, der_order=1))
                calculator = ExploitationCalculator(
                    geom_calculator,
                    plane.RowUnitVector.get_array(dtype='float64'),
                    plane.ColUnitVector.get_array(dtype='float64'))
                north = calculator.North
            variables['north'] = ((north + 180.0) % 360)

            try:
                exp_phen = sidd.ExploitationFeatures.Collections[0].Phenomenology
                variables['layover'] = ((exp_phen.Layover.Angle + 180) % 360)
                variables['layover_display'] = exp_phen.Layover.Angle
                variables['shadow'] = ((exp_phen.Shadow.Angle + 180) % 360)
                variables['shadow_display'] = exp_phen.Shadow.Angle
                variables['multipath'] = exp_phen.MultiPath
                variables['multipath_display'] = ((exp_phen.MultiPath + 180) % 360)

            except AttributeError:
                pass

        def extract_spacing():
            if sidd.Measurement is None:
                return
            meas = sidd.Measurement
            if meas.PlaneProjection is not None:
                variables['grid_row_sample_spacing'] = meas.PlaneProjection.SampleSpacing.Row
                variables['grid_column_sample_spacing'] = meas.PlaneProjection.SampleSpacing.Col
            elif meas.CylindricalProjection is not None:
                variables['grid_row_sample_spacing'] = meas.CylindricalProjection.SampleSpacing.Row
                variables['grid_column_sample_spacing'] = meas.CylindricalProjection.SampleSpacing.Col
            elif meas.GeographicProjection is not None:
                variables['grid_row_sample_spacing'] = meas.GeographicProjection.SampleSpacing.Row
                variables['grid_column_sample_spacing'] = meas.GeographicProjection.SampleSpacing.Col

        variables = {'image_plane': 'GROUND'}
        extract_location()
        extract_exploitation_features()
        extract_spacing()
        return cls(**variables)

    @classmethod
    def from_crsd(cls, crsd):
        """
        Create an instance from a CRSD version 1.0 object.

        Parameters
        ----------
        crsd : CRSDType

        Returns
        -------
        MetaIconDataContainer
        """

        if not isinstance(crsd, CRSDType):
            raise TypeError(
                'Got unhandled crsd type `{}`'.format(type(crsd)))

        def extract_collection_id():
            if crsd.CollectionID is None:
                return

            try:
                variables['collector_name'] = crsd.CollectionID.CollectorName
            except AttributeError:
                pass

            try:
                variables['core_name'] = crsd.CollectionID.CoreName
            except AttributeError:
                pass

        def extract_coords():
            try:
                coords = crsd.SceneCoordinates.IARP.LLH.get_array()
                variables['lat'] = coords[0]
                variables['lon'] = coords[1]
            except AttributeError:
                pass

        def extract_global():
            if crsd.Global is None:
                return

            try:
                variables['collect_start'] = crsd.Global.Timeline.CollectionRefTime
            except AttributeError:
                pass

            try:
                variables['collect_duration'] = (crsd.Global.Timeline.RcvTime2 - crsd.Global.Timeline.RcvTime1)
            except AttributeError:
                pass

        def extract_reference_geometry():
            if crsd.ReferenceGeometry is None or \
                    crsd.ReferenceGeometry.RcvParameters is None:
                return
            rcv = crsd.ReferenceGeometry.RcvParameters
            variables['azimuth'] = rcv.AzimuthAngle
            variables['graze'] = rcv.GrazeAngle
            variables['side_of_track'] = rcv.SideOfTrack

        variables = {}
        extract_collection_id()
        extract_coords()
        extract_global()
        extract_reference_geometry()
        return cls(**variables)
