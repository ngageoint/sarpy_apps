import numpy
import tkinter
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors

from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer


class MetaIconDemo(WidgetPanel):
    _widget_list = ("metaicon", )

    metaicon = widget_descriptors.PanelDescriptor("metaicon", MetaIcon)  # type: MetaIcon

    def __init__(self, primary):
        self.primary = primary

        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_horizontal_layout()

        lat = 35.05452800184999
        lon = -106.59258099877832
        collect_start = numpy.datetime64('2016-09-21T16:41:07.000000')
        collect_duration = 14.47132
        collector_name = 'Sandia FARAD X-band'
        core_name = '0508C01_PS0009_CC000000_N03_M1_PC054036_HH_wfcc_sv'
        azimuth = 241.15240495122976
        graze = 28.403774480669846
        layover = 263.96070589564016
        shadow = -90.0
        multipath = 66.5880303387554
        multipath_ground = 5.435625387525644
        side_of_track = 'R'
        col_impulse_response_width = 0.1903215223097113
        row_impulse_response_width = 0.1606955380577428
        grid_column_sample_spacing = 0.04462
        grid_row_sample_spacing = 0.03767
        image_plane = 'SLANT'
        tx_rf_bandwidth = 2843.7592056795997
        rniirs = None
        polarization = 'H:H'

        data_container = MetaIconDataContainer(lat=lat,
                                               lon=lon,
                                               collect_start=collect_start,
                                               collect_duration=collect_duration,
                                               collector_name=collector_name,
                                               core_name=core_name,
                                               azimuth=azimuth,
                                               graze=graze,
                                               layover=layover,
                                               shadow=shadow,
                                               multipath=multipath,
                                               multipath_ground=multipath_ground,
                                               side_of_track=side_of_track,
                                               col_impulse_response_width=col_impulse_response_width,
                                               row_impulse_response_width=row_impulse_response_width,
                                               grid_column_sample_spacing=grid_column_sample_spacing,
                                               grid_row_sample_spacing=grid_row_sample_spacing,
                                               image_plane=image_plane,
                                               tx_rf_bandwidth=tx_rf_bandwidth,
                                               rniirs=rniirs,
                                               polarization=polarization,
                                               )
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.metaicon.create_from_metaicon_data_container(data_container)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = MetaIconDemo(root)
    root.minsize(500, 500)
    root.mainloop()

