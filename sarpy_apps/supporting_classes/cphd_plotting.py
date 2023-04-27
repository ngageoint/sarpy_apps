"""
Utilities for plotting CPHD metadata
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Valkyrie Systems Corporation"

import itertools

import numpy as np
import plotly.colors
import plotly.graph_objects as go


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
