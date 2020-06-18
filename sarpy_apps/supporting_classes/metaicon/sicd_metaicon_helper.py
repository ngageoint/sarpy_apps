import logging

import sarpy.io.complex as sarpy_complex
from sarpy.io.complex.sicd import SICDType
from sarpy.geometry import geocoords
from scipy.constants import constants
from typing import Union
from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer


class SicdMetaIconHelper:
    def __init__(self,
                 sicd_meta,     # type: Union[SICDType, str]
                 ):
        if isinstance(sicd_meta, str):
            self.meta = sarpy_complex.open(sicd_meta).sicd_meta
        else:
            self.meta = sicd_meta

    @property
    def data_container(self):
        metaicon_data_container = MetaIconDataContainer()
        metaicon_data_container.lat = self.lat_lon[0]
        metaicon_data_container.lon = self.lat_lon[1]
        metaicon_data_container.collect_start = self.collect_start
        metaicon_data_container.collect_duration = self.collect_duration
        metaicon_data_container.azimuth = self.azimuth
        metaicon_data_container.graze = self.graze
        metaicon_data_container.layover = self.layover
        metaicon_data_container.shadow = self.shadow
        metaicon_data_container.multipath = self.multipath
        metaicon_data_container.collector_name = self.collector_name
        metaicon_data_container.col_impulse_response_width = self.column_impulse_response_width
        metaicon_data_container.row_impulse_response_width = self.row_impulse_response_width
        return metaicon_data_container

    @property
    def column_impulse_response_width(self):
        return self.meta.Grid.Col.ImpRespWid

    @property
    def row_impulse_response_width(self):
        return self.meta.Grid.Row.ImpRespWid

    @property
    def collector_name(self):
        return self.meta.CollectionInfo.CollectorName

    @property
    def azimuth(self):
        return self.meta.SCPCOA.AzimAng

    @property
    def graze(self):
        return self.meta.SCPCOA.GrazeAng

    @property
    def layover(self):
        return self.meta.SCPCOA.LayoverAng

    @property
    def shadow(self):
        return self.meta.SCPCOA.Shadow

    @property
    def multipath(self):
        return self.meta.SCPCOA.Multipath

    @property
    def lat_lon(self):
        if hasattr(self.meta, "GeoData"):
            try:
                scp = [self.meta.GeoData.SCP.ECF.X, self.meta.GeoData.SCP.ECF.Y, self.meta.GeoData.SCP.ECF.Z]
            except Exception as e:
                logging.error("Unable to get geolocation data in ECF form {}".format(e))
        # TODO: might take this out if it's not part of the SICD standard
        elif hasattr(self.meta, "SRP"):
            if self.meta.SRP.SRPType == "FIXEDPT":
                scp = self.meta.SRP.FIXEDPT.SRPPT
                scp = [scp.X, scp.Y, scp.Z]
            elif self.meta.SRP.SRPType == "PVTPOLY":
                # TODO: implement this for the case where we need to do a polynomial
                pass
        try:
            lla = geocoords.ecf_to_geodetic(scp)
            lat = lla[0]
            lon = lla[1]
        except Exception as e:
            logging.error("could not find latitude and longitude information in the SICD metadata. {}".format(e))
        return lat, lon
        # TODO: implement vbmeta version
        # TODO: implement a version of latlonstr from the MATLAB repo in sarpy Geometry, if this is important.

    def _create_angle_line_text(self,
                                angle_type,  # type: str
                                n_decimals,  # type: int
                                ):
        if angle_type.lower() == "layover":
            angle = self.meta.SCPCOA.LayoverAng
        elif angle_type.lower() == "shadow":
            angle = self.meta.SCPCOA.Shadow
        elif angle_type.lower() == "multipath":
            angle = self.meta.SCPCOA.Multipath
        elif angle_type.lower() == "azimuth":
            angle = self.meta.SCPCOA.AzimAng
        elif angle_type.lower() == "graze":
            angle = self.meta.SCPCOA.GrazeAng

        angle_description_text = angle_type.lower().capitalize()

        if n_decimals > 0:
            return angle_description_text + ": " + str(round(angle, n_decimals)) + "\xB0"
        else:
            return angle_description_text + ": " + str(int(round(angle))) + "\xB0"

    @property
    def collect_start(self):
        if hasattr(self.meta, "Timeline"):
            if hasattr(self.meta.Timeline, "CollectStart"):
                return self.meta.Timeline.CollectStart
        elif hasattr(self.meta, "Global"):
            try:
                return self.meta.Global.CollectStart
            except Exception as e:
                logging.error("No field found in Global.CollectStart.  {}".format(e))
            # TODO: implement collect duration for the case where vbmeta.TxTime is used.
        else:
            return None

    @property
    def collect_duration(self):
        if hasattr(self.meta, "Timeline"):
            if hasattr(self.meta.Timeline, "CollectDuration"):
                return self.meta.Timeline.CollectDuration
        else:
            return None

    @property
    def res(self):
        res_line = "IPR: "
        if hasattr(self.meta, "Grid"):
            az_ipr = self.meta.Grid.Col.ImpRespWid / constants.foot
            rg_ipr = self.meta.Grid.Row.ImpRespWid / constants.foot
            if az_ipr/rg_ipr - 1 < 0.2:
                ipr = (az_ipr + rg_ipr)/2.0
                ipr_str = "{:.1f}".format(ipr)
                res_line = res_line + ipr_str + " ft"
            else:
                ipr_str = "{:.1f}".format(az_ipr) + "/" + "{:.1f}".format(rg_ipr)
                res_line = res_line + ipr_str + "ft(A/R)"
        else:
            try:
                bw = self.meta.RadarCollection.Waveform.WFParameters.TxRFBandwidth / 1e6
                res_line = res_line + "{:.0f}".format(bw) + " MHz"
            except Exception as e:
                logging.error("no bandwidth field {}".format(e))
        if self.rniirs:
            res_line = res_line + " RNIIRS: " + str(self.rniirs)
        return res_line

    @property
    def polarization(self):
        pol = None
        if hasattr(self.meta, "ImageFormation"):
            try:
                pol = self.meta.ImageFormation.TxRcvPolarizationProc
            except Exception as e:
                logging.error("Polarization not found {}".format(e))
        elif hasattr(self.meta, "RadarCollection"):
            try:
                pol = self.meta.RadarCollection.TxPolarization
            except Exception as e:
                logging.error("Polarization not found {}".format(e))
        return pol

    @property
    def rniirs(self):
        if hasattr(self.meta, 'CollectionInfo') and hasattr(self.meta.CollectionInfo, 'Parameter'):
            return self.meta.CollectionInfo.Parameters['RNIIRS']
        else:
            return None

    @property
    def arrow_multipath_angle(self):
        # TODO: check additional parameter for GroundProject and ensure it's false
        multipath = self.meta.SCPCOA.Multipath
        azimuth = self.meta.SCPCOA.AzimAng
        if hasattr(self.meta, "Grid") or self.meta.Grid.ImagePlane == 'SLANT':
            multipath = azimuth - 180
        north = azimuth + 90
        multipath = north - multipath
        return multipath

    @property
    def arrow_layover_angle(self):
        # TODO: check additional parameter for GroundProject and ensure it's false
        azimuth = self.meta.SCPCOA.AzimAng
        layover = self.meta.SCPCOA.LayoverAng
        if hasattr(self.meta, "Grid") or self.meta.Grid.ImagePlane == 'SLANT':
            layover = layover - self.meta.SCPCOA.MultipathGround
        layover = 90 - (layover - azimuth)
        return layover

    @property
    def arrow_shadow_angle(self):
        # TODO: check additional parameter for GroundProject and ensure it's false
        shadow = self.meta.SCPCOA.Shadow
        azimuth = self.meta.SCPCOA.AzimAng
        layover = self.meta.SCPCOA.LayoverAng
        if hasattr(self.meta, "Grid") or self.meta.Grid.ImagePlane == 'SLANT':
            shadow = azimuth - 180 - self.meta.SCPCOA.MultipathGround
        shadow = 90 - (shadow - azimuth)
        return shadow

    @property
    def arrow_north_angle(self):
        # TODO: check additional parameter for GroundProject and ensure it's false
        azimuth = self.meta.SCPCOA.AzimAng
        north = azimuth + 90
        return north
