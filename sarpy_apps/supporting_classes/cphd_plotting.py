"""
Utilities for plotting CPHD metadata
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Valkyrie Systems Corporation"

import functools
import itertools
import pathlib
import tkinter
from tkinter import ttk

import matplotlib.backends.backend_tkagg as mpl_tk
import matplotlib.figure as mpl_fig
import numpy as np
import plotly.colors
import plotly.graph_objects as go
import scipy.signal


def plot_image_area(reader):
    """
    Create a plot of a CPHD's ImageArea
    """
    cphd_meta = reader.cphd_meta
    fig = go.Figure()
    color_set = itertools.cycle(zip(plotly.colors.qualitative.Pastel2, plotly.colors.qualitative.Set2))

    im_rect, im_poly = _make_image_area(cphd_meta.SceneCoordinates.ImageArea,
                                        name='Scene', colors=next(color_set))

    iacp_labels = [f'Lat: {vertex.Lat}<br>Lon: {vertex.Lon}'
                   for vertex in sorted(cphd_meta.SceneCoordinates.ImageAreaCornerPoints, key=lambda x: x.index)]
    for label, ptx, pty, yshift in zip(iacp_labels, im_rect['x'], im_rect['y'], [-20, 20, 20, -20]):
        fig.add_annotation(x=ptx, y=pty, text=label, showarrow=False, xshift=0, yshift=yshift)

    fig.add_trace(im_rect)
    if im_poly:
        fig.add_trace(im_poly)

    if cphd_meta.SceneCoordinates.ExtendedArea is not None:
        ext_rect, ext_poly = _make_image_area(cphd_meta.SceneCoordinates.ExtendedArea,
                                              name='Extended', colors=next(color_set))
        fig.add_trace(ext_rect)
        if ext_poly is not None:
            fig.add_trace(ext_poly)

    channel_colors = {}
    for chan_params in cphd_meta.Channel.Parameters:
        chan_id = chan_params.Identifier
        channel_colors[chan_id] = next(color_set)

    for chan_params in cphd_meta.Channel.Parameters:
        chan_id = chan_params.Identifier
        if chan_params.ImageArea is not None:
            fig.add_traces([t for t in _make_image_area(chan_params.ImageArea, name=f'Channel: {chan_id}',
                                                        colors=channel_colors[chan_id]) if t])

    antenna_aiming = _antenna_aiming_in_image_area(reader)
    for channel, aiming in antenna_aiming.items():
        for txrcv, symbol in zip(['Tx', 'Rcv'], ('triangle-down-open', 'triangle-up-open')):
            boresights = aiming[txrcv]['boresights']
            apcid = aiming[txrcv]['APCId']

            def add_boresight_trace(points, name, color):
                fig.add_trace(go.Scatter(x=points[:, 0],
                                         y=points[:, 1],
                                         name=name,
                                         legendgroup=name,
                                         mode='markers',
                                         marker=dict(symbol=symbol, color=color)))
                first_point = points[np.isfinite(points[:, 0])][0]
                fig.add_trace(go.Scatter(x=[first_point[0]],
                                         y=[first_point[1]],
                                         name=name,
                                         legendgroup=name,
                                         showlegend=False,
                                         mode='markers',
                                         marker=dict(symbol=symbol, size=15, color=color)))

            add_boresight_trace(boresights['mechanical'],
                                name=f"Channel: {channel} {txrcv} MB ({apcid})",
                                color=channel_colors[channel][0])
            if 'electrical' in boresights:
                add_boresight_trace(boresights['electrical'],
                                    name=f"Channel: {channel} {txrcv} EB ({apcid})",
                                    color=channel_colors[channel][-1])

    fig.update_layout(
        xaxis_title="IAX [m]", yaxis_title="IAY [m]",
        title_text='Image Area',
        meta='image_area')
    return fig


def _make_image_area(image_area, name=None, colors=None):
    x1, y1 = image_area.X1Y1
    x2, y2 = image_area.X2Y2
    rect = go.Scatter(x=[x1, x1, x2, x2, x1], y=[y1, y2, y2, y1, y1], fill="toself",
                      name=f"{name + ' ' if name is not None else ''}Rectangle")
    if colors:
        rect['line']['color'] = colors[0]
    if image_area.Polygon is not None:
        vertices = [vertex.get_array() for vertex in sorted(image_area.Polygon, key=lambda x: x.index)]
        vertices = np.array(vertices + [vertices[0]])
        poly = go.Scatter(x=vertices[:, 0], y=vertices[:, 1], fill="toself",
                          name=f"{name + ' ' if name is not None else ''}Polygon",
                          line={'color': rect['line']['color'], 'dash': 'dot', 'width': 1})
        if colors:
            poly['line']['color'] = colors[-1]
    else:
        poly = None
    return rect, poly


def _antenna_aiming_in_image_area(reader):
    cphd_meta = reader.cphd_meta
    results = {}

    if cphd_meta.Antenna is None:
        return results

    if cphd_meta.SceneCoordinates.ReferenceSurface.Planar is None:
        # Only Planar is handled
        return results

    apcs = {}
    for apc in cphd_meta.Antenna.AntPhaseCenter:
        apcs[apc.Identifier] = apc

    acfs = {}
    for acf in cphd_meta.Antenna.AntCoordFrame:
        acfs[acf.Identifier] = acf

    patterns = {}
    for antpat in cphd_meta.Antenna.AntPattern:
        patterns[antpat.Identifier] = antpat

    iarp = cphd_meta.SceneCoordinates.IARP.ECF.get_array()
    iax = cphd_meta.SceneCoordinates.ReferenceSurface.Planar.uIAX.get_array()
    iay = cphd_meta.SceneCoordinates.ReferenceSurface.Planar.uIAY.get_array()
    iaz = np.cross(iax, iay)

    def _compute_boresights(channel_id, apc_id, antpat_id, txrcv):
        times = reader.read_pvp_variable(f'{txrcv}Time', channel_id)
        uacx = reader.read_pvp_variable(f'{txrcv}ACX', channel_id)
        uacy = reader.read_pvp_variable(f'{txrcv}ACY', channel_id)
        if uacx is None or uacy is None:
            acf_id = apcs[apc_id].ACFId
            uacx = acfs[acf_id].XAxisPoly(times)
            uacy = acfs[acf_id].YAxisPoly(times)
        uacz = np.cross(uacx, uacy)

        apc_positions = reader.read_pvp_variable(f'{txrcv}Pos', channel_id)

        def _project_apc_into_image_area(along):
            distance = -_vdot(apc_positions - iarp, iaz) / _vdot(along, iaz)
            plane_points_ecf = apc_positions + distance[:, np.newaxis] * along
            plane_points_x = _vdot(plane_points_ecf - iarp, iax)
            plane_points_y = _vdot(plane_points_ecf - iarp, iay)
            return np.stack((plane_points_x, plane_points_y)).T

        boresights = {'mechanical': _project_apc_into_image_area(uacz)}

        ebpvp = reader.read_pvp_variable(f'{txrcv}EB', channel_id)
        if ebpvp is not None:
            eb_dcx = ebpvp[:, 0]
            eb_dcy = ebpvp[:, 1]
        else:
            eb_dcx = patterns[antpat_id].EB.DCXPoly(times)
            eb_dcy = patterns[antpat_id].EB.DCYPoly(times)

        if any(eb_dcx) or any(eb_dcy):
            eb_dcz = np.sqrt(1 - eb_dcx**2 - eb_dcy**2)
            eb = np.stack((eb_dcx, eb_dcy, eb_dcz)).T

            eb_boresight = np.zeros_like(uacz)
            eb_boresight += eb[:, 0, np.newaxis] * uacx
            eb_boresight += eb[:, 1, np.newaxis] * uacy
            eb_boresight += eb[:, 2, np.newaxis] * uacz

            boresights['electrical'] = _project_apc_into_image_area(eb_boresight)

        return boresights

    for chan_params in cphd_meta.Channel.Parameters:
        channel_id = chan_params.Identifier
        if not chan_params.Antenna:
            continue

        results[channel_id] = {}
        tx_apc_id = chan_params.Antenna.TxAPCId
        results[channel_id]['Tx'] = {
            'APCId': tx_apc_id,
            'boresights': _compute_boresights(channel_id,
                                              tx_apc_id,
                                              chan_params.Antenna.TxAPATId,
                                              'Tx')
        }

        rcv_apc_id = chan_params.Antenna.RcvAPCId
        results[channel_id]['Rcv'] = {
            'APCId': rcv_apc_id,
            'boresights': _compute_boresights(channel_id,
                                              rcv_apc_id,
                                              chan_params.Antenna.RcvAPATId,
                                              'Rcv')
        }
    return results


def _vdot(vec1, vec2, axis=-1, keepdims=False):
    """Vectorwise dot product of two bunches of vectors.

    Args
    ----
    vec1: array-like
        The first bunch of vectors
    vec2: array-like
        The second bunch of vectors
    axis: int, optional
        Which axis contains the vector components
    keepdims: bool, optional
        Keep the full broadcasted dimensionality of the arguments

    Returns
    -------
    array-like

    """
    return (np.asarray(vec1) * np.asarray(vec2)).sum(axis=axis, keepdims=keepdims)


class CphdPowerSpectralDensity:
    """
    Create a tool to visualize a CPHD's per-vector power spectral density
    """
    def __init__(self, root, cphd_reader):
        self.cphd_reader = cphd_reader
        ref_ch_id = cphd_reader.cphd_meta.Channel.RefChId
        self.channel_datas = {x.Identifier: x for x in cphd_reader.cphd_meta.Data.Channels}
        self.channel_parameters = {x.Identifier: x for x in cphd_reader.cphd_meta.Channel.Parameters}
        assert ref_ch_id in self.channel_datas
        self.has_signal = cphd_reader.cphd_meta.PVP.SIGNAL is not None
        self.pn_ref = None
        self.bn_ref = None
        self.sn_ref = None

        # prepare figure
        fig = mpl_fig.Figure(figsize=(5, 7), dpi=100)
        self.ax = fig.add_subplot()
        self.ax.set_xlabel("ΔTOA [s]" if cphd_reader.cphd_meta.Global.DomainType == 'FX' else "f_x [Hz]")
        self.ax.set_ylabel("Power Spectral Density")
        self.ax.set_yscale("log")
        self.ax.grid()
        self.vector_psd_line, = self.ax.plot(0, 0, label='Estimated Vector PSD')
        sn_ref_label = 'SNRef' if self.channel_parameters[ref_ch_id].NoiseLevel is not None else None
        self.sn_ref_line, = self.ax.plot(0, 0, label=sn_ref_label)
        self.sn_ref_line.set(visible=self.channel_parameters[ref_ch_id].NoiseLevel is not None)

        box = self.ax.get_position()
        self.ax.set_position([box.x0, box.y0 + box.height * 0.2, box.width, box.height * 0.8])
        self.ax.legend(loc='upper center', bbox_to_anchor=((0.5, -0.2)), ncol=2,
                       title=pathlib.Path(cphd_reader.file_name).name)

        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=tkinter.NSEW)
        root.columnconfigure(index=0, weight=1)
        root.rowconfigure(index=0, weight=1)
        root.wm_title("CPHD - Power Spectral Density")
        self.canvas = mpl_tk.FigureCanvasTkAgg(fig, master=mainframe)  # A tk.DrawingArea.
        self.canvas.draw()

        # pack_toolbar=False will make it easier to use a layout manager later on.
        toolbar = mpl_tk.NavigationToolbar2Tk(self.canvas, mainframe, pack_toolbar=False)
        toolbar.update()

        self.selected_channel = tkinter.StringVar(value=ref_ch_id)
        self.channel_select = ttk.Combobox(master=mainframe,
                                           textvariable=self.selected_channel,
                                           values=list(self.channel_datas),
                                           width=50,
                                           state='readonly')
        self.channel_select.bind('<<ComboboxSelected>>', self._update_channel)

        self.should_autoscale = tkinter.BooleanVar(value=True)
        autoscale_control = tkinter.Checkbutton(master=mainframe, text="Autoscale axes?",
                                                variable=self.should_autoscale,
                                                command=functools.partial(self._autoscale, draw=True))

        self.selected_vector = tkinter.IntVar(value=0)
        self.selected_vector.trace('w', self._update_plot)
        self.vector_slider = tkinter.Scale(mainframe, from_=0, to=self.channel_datas[ref_ch_id].NumVectors-1,
                                           orient=tkinter.HORIZONTAL,
                                           variable=self.selected_vector,
                                           length=256,
                                           showvalue=False)
        self.vector_entry = ttk.Spinbox(mainframe, textvariable=self.selected_vector,
                                        from_=0, to=self.channel_datas[ref_ch_id].NumVectors-1)

        toolbar.grid(column=0, row=0, columnspan=4, sticky=tkinter.NSEW)
        self.canvas.get_tk_widget().grid(column=0, row=1, columnspan=4, sticky=tkinter.NSEW)
        self.channel_select.grid(column=0, row=2, columnspan=3, sticky=tkinter.NSEW)
        autoscale_control.grid(column=3, row=2, sticky=tkinter.NSEW)
        label = tkinter.Label(master=mainframe, text='Vector Select:')
        label.grid(column=0, row=3, sticky=tkinter.NSEW)
        self.vector_slider.grid(column=1, row=3, columnspan=2, sticky=tkinter.NSEW)
        self.vector_entry.grid(column=3, row=3, sticky=tkinter.NSEW)

        for col in range(4):
            mainframe.columnconfigure(col, weight=1)
        mainframe.rowconfigure(1, weight=10)

        self._update_channel()

    def _update_sn_ref(self, vector_index):
        if self.sn_ref is not None:
            sn_ref_bw = self.bn_ref / self.scss[vector_index] * np.array([-1/2, 1/2])
            self.sn_ref_line.set_data(sn_ref_bw, self.sn_ref * np.ones_like(sn_ref_bw))

    def _update_channel(self, *args, **kwargs):
        channel_id = self.selected_channel.get()

        these_channel_parameters = self.channel_parameters[self.channel_select.get()]
        if these_channel_parameters.NoiseLevel is not None:
            self.pn_ref = these_channel_parameters.NoiseLevel.PNRef
            self.bn_ref = these_channel_parameters.NoiseLevel.BNRef
            if self.pn_ref is not None and self.bn_ref is not None:
                self.sn_ref = self.pn_ref / self.bn_ref

        self.scss = self.cphd_reader.read_pvp_variable('SCSS', index=channel_id)
        if self.has_signal:
            self.signal = self.cphd_reader.read_pvp_variable('SIGNAL', index=channel_id)

        self.selected_vector.set(0)
        self._update_slider(0)
        self.channel_select.selection_clear()

    def _update_slider(self, vector_index):
        self.vector_slider.configure(to=self.channel_datas[self.selected_channel.get()].NumVectors - 1)
        self.vector_slider.set(vector_index)

    def _autoscale(self, draw=False):
        if self.should_autoscale.get():
            self.ax.relim()
            self.ax.autoscale_view(True, True, True)
            if draw:
                self.canvas.draw()

    def _update_plot(self, *args):
        vector_index = self.selected_vector.get()
        vector = self.cphd_reader.read(slice(vector_index, vector_index + 1), None, index=self.selected_channel.get())
        scss = self.scss[vector_index]
        f, z = scipy.signal.welch(vector, fs=1/scss, window='boxcar',
                                  scaling='spectrum', return_onesided=False, detrend=False)
        self.vector_psd_line.set_data(np.fft.fftshift(f), np.fft.fftshift(z * len(z)))
        self._update_sn_ref(vector_index)
        self._autoscale()

        # update title
        title_parts = [self.selected_channel.get()]
        if self.sn_ref is not None:
            title_parts.extend([f'PNRef={self.pn_ref}', f'BNRef={self.bn_ref}'])
        if self.has_signal:
            title_parts.append(f'SIGNAL[{vector_index}]={self.signal[vector_index]}')
        self.ax.set_title('\n'.join(title_parts))

        # required to update canvas and attached toolbar!
        self.canvas.draw()
