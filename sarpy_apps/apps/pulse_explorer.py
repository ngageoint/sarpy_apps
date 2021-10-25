"""
CRSD pulse explorer
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Thomas Rackers", "Thomas McCullough")

import logging
import os

import numpy
from scipy.signal import spectrogram, resample

import tkinter
from tkinter import ttk

from tkinter.filedialog import askopenfilename

from tk_builder.base_elements import TypedDescriptor, StringDescriptor
from tk_builder.panel_builder import WidgetPanel
from tk_builder.panels.image_panel import ImagePanel
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.widgets import widget_descriptors, basic_widgets

from sarpy_apps.supporting_classes.file_filters import crsd_files, all_files
from sarpy_apps.supporting_classes.widget_with_metadata import WidgetWithMetadata

from sarpy.io.general.base import SarpyIOError, FlatReader
from sarpy.io.received.converter import open_received
from sarpy.io.received.base import CRSDTypeReader
from sarpy.processing.windows import kaiser
from sarpy.processing.fft_base import fftshift

from sarpy_apps.supporting_classes.image_reader import CRSDTypeCanvasImageReader


logger = logging.getLogger(__name__)

_PULSE_DISPLAY_VALUES = ('RFSignal', )


def _reramp(pulse_data, sampling_rate, deramp_rate):
    """

    Parameters
    ----------
    pulse_data : numpy.ndarray
    sampling_rate : float
    deramp_rate : float

    Returns
    -------
    (numpy.ndarray, float)
        The reramped_data and new sampling rate.
    """

    rcv_window_length = pulse_data.size / sampling_rate
    deramp_bandwidth = abs(rcv_window_length*deramp_rate)
    upsample_factor = (deramp_bandwidth + sampling_rate) / sampling_rate

    sample_size = round(upsample_factor * pulse_data.size)
    oversample_factor = sample_size / (upsample_factor * pulse_data.size)
    use_data = resample(pulse_data - numpy.mean(pulse_data), sample_size)
    time_interval = 1 / (sampling_rate * upsample_factor * oversample_factor)
    times = time_interval * numpy.arange(sample_size) - 0.5 * rcv_window_length
    return use_data*numpy.exp(1j*numpy.pi*deramp_rate*times*times), 1./time_interval


def _stft(data, sampling_rate):
    """
    Take the specified short time fourier transform of the provided data.

    Parameters
    ----------
    data : numpy.ndarray
        Must be one-dimensional
    sampling_rate : float
        The sampling rate.

    Returns
    -------
    numpy.ndarray
    """

    if not (isinstance(data, numpy.ndarray) and data.ndim == 1):
        raise ValueError(
            'This short time fourier transform function only applies to a '
            'one-dimensional numpy array')

    nfft = 2**int(numpy.ceil(numpy.log2(numpy.sqrt(data.shape[0]))) + 2)
    nperseg = int(0.97*nfft)
    window = kaiser(nperseg, 5)
    noverlap = int(0.9*nfft)
    frequencies, times, trans_data = spectrogram(
        data, sampling_rate, window=window, nperseg=nperseg, noverlap=noverlap,
        nfft=nfft, return_onesided=False)
    return times, fftshift(frequencies, axes=0), fftshift(trans_data, axes=0)


def _rf_signal(reader, index, pulse):
    """
    Gets the RF Signal data for the given index (channel) and pulse.

    Parameters
    ----------
    reader : CRSDTypeReader
    index : int
    pulse : int

    Returns
    -------
    (numpy.ndarray, numpy.ndarray, numpy.ndarray)
        The times, frequencies, and stft data array
    """

    crsd = reader.crsd_meta
    params = crsd.Channel.Parameters[index]
    sampling_rate = params.Fs
    pulse_data = reader[pulse, :, index].flatten()
    fic_rate = float(reader.read_pvp_variable('FICRate', index, pulse)[0])
    dfic0 = float(reader.read_pvp_variable('DFIC0', index, pulse)[0])

    if fic_rate == 0:
        times, frequencies, stft_data = _stft(pulse_data, sampling_rate)
        frequencies += params.F0Ref + dfic0 - 0.5*sampling_rate
    else:
        reramped, reramped_sampling_rate = _reramp(pulse_data, sampling_rate, fic_rate)
        times, frequencies, stft_data = _stft(reramped, reramped_sampling_rate)
        frequencies += \
            params.F0Ref + dfic0 + \
            0.5*fic_rate*pulse_data.size/reramped_sampling_rate - \
            0.5*reramped_sampling_rate
    return times, frequencies, stft_data


class STFTCanvasImageReader(CRSDTypeCanvasImageReader):
    __slots__ = (
        '_base_reader', '_chippers', '_index', '_data_size', '_remap_function',
        '_signal_data_size', '_pulse', '_pulse_display', '_pulse_data',
        '_times', '_frequencies')

    def __init__(self, reader):
        """

        Parameters
        ----------
        reader : str|CRSDTypeReader
            The crsd type reader, or path to appropriate data file.
        """

        self._signal_data_size = None
        self._pulse = None
        self._pulse_display = None
        self._pulse_data = None
        self._times = None
        self._frequencies = None
        self.pulse_display = _PULSE_DISPLAY_VALUES[0]
        CRSDTypeCanvasImageReader.__init__(self, reader)

    @property
    def pulse_display(self):
        """
        str: The pulse display string determining methodology
        """

        return self._pulse_display

    @pulse_display.setter
    def pulse_display(self, value):
        if value not in _PULSE_DISPLAY_VALUES:
            raise ValueError(
                'pulse display (`{}`) not one of the allowed values\n\t`{}`'.format(
                    value, _PULSE_DISPLAY_VALUES))
        self._pulse_display = value
        self._set_pulse_data()

    @property
    def pulse_count(self):
        """
        None|int: The pulse count.
        """

        if self._signal_data_size is None:
            return None
        return self._signal_data_size[0]

    @property
    def index(self):
        """
        int: The reader index.
        """

        return self._index

    @index.setter
    def index(self, value):
        value = int(value)
        signal_data_sizes = self.base_reader.get_data_size_as_tuple()
        if not (0 <= value < len(signal_data_sizes)):
            logging.error(
                'The index property must be 0 <= index < {}, '
                'and got argument {}. Setting to 0.'.format(len(signal_data_sizes), value))
            value = 0
        self._index = value
        self._signal_data_size = signal_data_sizes[value]
        self.pulse = 0

    @property
    def base_reader(self):
        # type: () -> CRSDTypeReader
        """
        CRSDTypeReader: The crsd reader object
        """

        return self._base_reader

    @base_reader.setter
    def base_reader(self, value):
        if isinstance(value, str):
            reader = None
            try:
                reader = open_received(value)
            except SarpyIOError:
                pass

            if reader is None:
                raise SarpyIOError('Could not open file {} as a CRSD reader'.format(value))
            value = reader

        if not isinstance(value, CRSDTypeReader):
            raise TypeError('base_reader must be a CRSDReader, got type {}'.format(type(value)))
        self._base_reader = value
        # noinspection PyProtectedMember
        self._chippers = value._get_chippers_as_tuple()
        self.index = 0

    @property
    def pulse(self):
        """
        int: The pulse currently being considered.
        """

        return self._pulse

    @pulse.setter
    def pulse(self, value):
        if self.pulse_count is None:
            self._pulse = None
            self._pulse_data = None

        value = int(value)
        if not (0 <= value < self.pulse_count):
            raise ValueError('Got invalid pulse number `{}`'.format(value))
        self._pulse = value
        self._set_pulse_data()

    @property
    def times(self):
        """
        numpy.ndarray: Gets the times array for stft/spectrogram data for the current pulse.
        """

        return self._times

    @property
    def frequencies(self):
        """
        numpy.ndarray: Gets the frequencies array for stft/spectrogram data for the current pulse.
        """

        return self._frequencies

    @property
    def pulse_data(self):
        """
        numpy.ndarray: The spectrogram of the currently selected pulse
        """
        return self._pulse_data

    def _set_pulse_data(self):
        if self.pulse is None:
            self._pulse_data = None
            return

        if self._pulse_display == 'RFSignal':
            times, frequencies, data = _rf_signal(self.base_reader, self.index, self.pulse)
        else:
            raise ValueError('Got unhandled pulse display value `{}`'.format(self.pulse_display))

        self._times = times
        self._frequencies = frequencies
        self._data_size = data.shape
        self._pulse_data = FlatReader(data)

    def __getitem__(self, item):
        if self._pulse_data is None:
            return None
        if self.remap_function is None:
            return self._pulse_data.__getitem__(item)
        return self.remap_complex_data(self._pulse_data.__getitem__(item))

###########
# The main app

class AppVariables(object):
    """
    App variables for the aperture tool.
    """

    browse_directory = StringDescriptor(
        'browse_directory', default_value=os.path.expanduser('~'),
        docstring='The directory for browsing for file selection.')  # type: str
    image_reader = TypedDescriptor(
        'image_reader', STFTCanvasImageReader,
        docstring='The crsd type canvas image reader object.')  # type: STFTCanvasImageReader


from enum import Enum

class Operation(Enum):
    REV = -2
    PREV = -1
    STOP = 0
    NEXT = 1
    FWD = 2


class SliderWidget(basic_widgets.Frame):
    """
    Widget panel with slider for forward/reverse and manual scan.
    """

    def __init__(self, parent):
        """

        Parameters
        ----------
        parent: basic_widgets.Frame
        """

        super().__init__(parent)

        self.label_1 = basic_widgets.Label(self, text='1')
        self.label_2 = basic_widgets.Label(self, text='Pulse')

        self.entry = basic_widgets.Entry(self)
        self.var_entry = tkinter.IntVar(value=1)
        self.entry.configure(font=('TkFixedFont', 12), justify='right',
                             textvariable=self.var_entry, width=6)

        self.fullscale = basic_widgets.Label(self, text='100')

        self.label_1.grid(row=0, column=0, sticky='w', padx=5)
        self.label_2.grid(row=0, column=1, sticky='e', padx=5)
        self.entry.grid(row=0, column=2, sticky='w', padx=5)
        self.fullscale.grid(row=0, column=3, sticky='e', padx=5)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=0)

        self.scale = basic_widgets.Scale(self)
        self.var_scale = tkinter.IntVar(value=1)
        self.scale.configure(from_=1, to=100, length=600, orient='horizontal',
                             variable=self.var_scale)
        self.scale.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky='esw')


class DirectionWidget(basic_widgets.Frame):
    """
    Button pair to select forward/reverse/stopped direction.
    """

    def __init__(self, parent):
        """

        Parameters
        ----------
        parent: basic_widgets.Frame
        """

        super().__init__(parent)
        self.parent = parent

        self.button_style = ttk.Style()
        self.button_style.configure('ToggleOff.TButton', font=('Arial', 24),
                                    foreground="gray50", background="PaleTurquoise3",
                                    sticky='CENTER')
        self.button_style.configure('ToggleOn.TButton', font=('Arial', 24),
                                    foreground="black", background="PaleTurquoise1",
                                    sticky='CENTER')

        self.button_rev = \
            basic_widgets.Button(self.parent, text="\u23EA",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.REV))
        self.button_prev = \
            basic_widgets.Button(self.parent, text="\u25C0",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.PREV))
        self.button_next = \
            basic_widgets.Button(self.parent, text="\u25B6",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.NEXT))
        self.button_fwd = \
            basic_widgets.Button(self.parent, text="\u23E9",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.FWD))

        self.mode = Operation.STOP

    @staticmethod
    def set_button(button, mode):
        """

        Parameters
        ----------
        button: ttk.Button
            Button to be reconfigured
        mode: bool|int
            New button state, True = on/pressed or False = off/released
        """
        if mode:
            button.state(['pressed'])
            button.configure(style='ToggleOn.TButton')
        else:
            button.state(['!pressed'])
            button.configure(style='ToggleOff.TButton')

    def action(self, new_mode):
        """
        Set direction based on buttons' states and new button press.

        Parameters
        ----------
        new_mode: Enum.Operation
            Button that was pressed, Operation.Rev = left arrow, Operation.Fwd = right arrow
        """
        self.mode = Operation.STOP if self.mode == new_mode else new_mode
        if self.mode == Operation.REV:
            self.set_button(self.button_rev,True)
            self.set_button(self.button_fwd,False)
        elif self.mode == Operation.PREV:
            pass
        elif self.mode == Operation.FWD:
            self.set_button(self.button_rev,False)
            self.set_button(self.button_fwd,True)
        elif self.mode == Operation.NEXT:
            pass
        else:
            self.set_button(self.button_rev,False)
            self.set_button(self.button_fwd,False)


class PulseExplorer(basic_widgets.Frame, WidgetWithMetadata):
    def __init__(self, primary):
        """

        Parameters
        ----------
        primary : tkinter.Toplevel|tkinter.Tk
        """

        super().__init__(primary)

        self.root = primary
        self.primary = basic_widgets.Frame(primary)  # type: basic_widgets.Frame

        basic_widgets.Frame.__init__(self, primary)
        WidgetWithMetadata.__init__(self, primary)

        self.variables = AppVariables()

        self.style_pyplot_panel = ttk.Style()
        self.style_pyplot_panel.configure('TLabelframe', labelmargins=10)
        self.pyplot_panel = PyplotImagePanel(self.primary)  # type: PyplotImagePanel

        self.pyplot_panel.cmap_name = 'viridis'
        self.pyplot_panel.set_ylabel('Freq (GHz)')
        self.pyplot_panel.set_xlabel('Time (\u03BCsec)')

        self.scanner_panel = basic_widgets.Frame(primary)  # type: basic_widgets.Frame
        self.scanner_panel.columnconfigure(0, weight=0)
        self.scanner_panel.columnconfigure(1, weight=0)
        self.scanner_panel.columnconfigure(2, weight=1)
        self.scanner_panel.columnconfigure(3, weight=0)
        self.scanner_panel.columnconfigure(4, weight=0)

        self.dir_buttons = DirectionWidget(self.scanner_panel)
        self.slider = SliderWidget(self.scanner_panel)

        self.dir_buttons.button_rev.grid(row=0, column=0, sticky='w')
        self.dir_buttons.button_prev.grid(row=0, column=1, sticky='w')
        self.slider.grid(row=0, column=2, sticky='ew')
        self.dir_buttons.button_next.grid(row=0, column=3, sticky='e')
        self.dir_buttons.button_fwd.grid(row=0, column=4, sticky='e')

        self.pyplot_panel.pack(side="top", expand=True, fill='both')
        self.scanner_panel.pack(side="bottom", expand=False, fill='x')

        self.primary.rowconfigure(0, weight=1)
        self.primary.rowconfigure(1, weight=0)
        # self.primary.grid(row=0, column=0, sticky="NSEW", expand=True, fill='both')
        self.primary.pack(expand=True, fill='both')
        self.set_frame_title()

        # define menus
        menubar = tkinter.Menu()
        # file menu
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.callback_select_files)
        filemenu.add_command(label="Settings...", command=self.callback_settings_popup)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Metadata", menu=popups_menu)

        primary.config(menu=menubar)

        # # hide extraneous tool elements
        # self.image_panel.hide_tools('shape_drawing')
        # self.image_panel.hide_shapes()

        # # bind canvas events for proper functionality
        # # this makes for bad performance on a larger image - do not activate
        # # self.image_panel.canvas.bind('<<SelectionChanged>>', self.handle_selection_change)
        # self.image_panel.canvas.bind('<<SelectionFinalized>>', self.handle_selection_change)
        # self.image_panel.canvas.bind('<<RemapChanged>>', self.handle_remap_change)
        # self.image_panel.canvas.bind('<<ImageIndexChanged>>', self.handle_image_index_changed)

    def set_frame_title(self):
        """
        Sets the LabelFrame title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = " . . . "
        else:
            the_title = " {} ".format(os.path.split(file_name)[1])
        self.pyplot_panel.config(style='Pyplot.TLabelframe', text=the_title)

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Pulse Explorer"
        else:
            the_title = "Pulse Explorer for {}".format(os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def exit(self):
        self.primary.destroy()
        self.root.destroy()

    # # noinspection PyUnusedLocal
    # def handle_selection_change(self, event):
    #     """
    #     Handle a change in the selection area.
    #
    #     Parameters
    #     ----------
    #     event
    #     """
    #
    #     if self.variables.image_reader is None:
    #         return
    #
    #     # full_image_width = self.image_panel.canvas.variables.state.canvas_width
    #     # fill_image_height = self.image_panel.canvas.variables.state.canvas_height
    #     # self.image_panel.canvas.zoom_to_canvas_selection((0, 0, full_image_width, fill_image_height))
    #     self.display_canvas_rect_selection_in_pyplot_frame()

    # noinspection PyUnusedLocal
    def handle_remap_change(self, event):
        """
        Handle that the remap for the image canvas has changed.

        Parameters
        ----------
        event
        """

        pass

    # noinspection PyUnusedLocal
    def handle_image_index_changed(self, event):
        """
        Handle that the image index has changed.

        Parameters
        ----------
        event
        """

        self.my_populate_metaicon()

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : str|CRSDTypeReader|STFTCanvasImageReader
        update_browse : None|str
        """

        if update_browse is not None:
            self.variables.browse_directory = update_browse
        elif isinstance(the_reader, str):
            self.variables.browse_directory = os.path.split(the_reader)[0]

        if isinstance(the_reader, str):
            the_reader = STFTCanvasImageReader(the_reader)

        if isinstance(the_reader, CRSDTypeReader):
            the_reader = STFTCanvasImageReader(the_reader)

        if not isinstance(the_reader, STFTCanvasImageReader):
            raise TypeError('Got unexpected input for the reader')

        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_frame_title()
        # refresh appropriate GUI elements
        # self.pyplot_panel.make_blank()
        self.my_populate_metaicon()
        self.my_populate_metaviewer()

    def callback_select_files(self):
        fname = askopenfilename(initialdir=self.variables.browse_directory,
                                filetypes=[crsd_files, all_files])
        if fname is None or fname in ['', ()]:
            return

        the_reader = STFTCanvasImageReader(fname)
        self.update_reader(the_reader, update_browse=os.path.split(fname)[0])

    # def display_canvas_rect_selection_in_pyplot_frame(self):
    #     def get_extent(coords):
    #         row_min = int(numpy.floor(min(coords[0::2])))
    #         row_max = int(numpy.ceil(max(coords[0::2])))
    #         col_min = int(numpy.floor(min(coords[1::2])))
    #         col_max = int(numpy.ceil(max(coords[1::2])))
    #         return row_min, row_max, col_min, col_max
    #
        # threshold = self.image_panel.canvas.variables.config.select_size_threshold
        #
        # select_id = self.image_panel.canvas.variables.select_rect.uid
        # rect_coords = self.image_panel.canvas.get_shape_image_coords(select_id)
        # extent = get_extent(rect_coords)

        # if abs(extent[1] - extent[0]) < threshold or abs(extent[3] - extent[2]) < threshold:
        #     self.pyplot_panel.make_blank()
        # else:
        #     times = 1e6*self.variables.image_reader.times[extent[2]:extent[3]]
        #     frequencies = 1e-9*self.variables.image_reader.frequencies[extent[0]:extent[1]]
        #     image_data = self.variables.image_reader.pulse_data[extent[0]: extent[1], extent[2]:extent[3]]
        #     self.pyplot_panel.update_pcolormesh(times, frequencies, image_data, shading='gouraud', snap=True)

    def callback_settings_popup(self):
        pass
    
    def display_in_pyplot_frame(self):
        times = 1.0e6 * self.variables.image_reader.times
        frequencies = 1.0e-9 * self.variables.image_reader.frequencies
        pulse_data = self.variables.image_reader.pulse_data
        self.pyplot_panel.update_pcolormesh(times, frequencies, pulse_data, shading='gouraud', snap=True)

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        if self.image_panel.canvas.variables.canvas_image_object is None or \
                self.image_panel.canvas.variables.canvas_image_object.image_reader is None:
            image_reader = None
            the_index = 0
        else:
            image_reader = self.image_panel.canvas.variables.canvas_image_object.image_reader
            the_index = self.image_panel.canvas.get_image_index()
        self.populate_metaicon(image_reader, the_index)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        if self.image_panel.canvas.variables.canvas_image_object is None:
            image_reader = None
        else:
            image_reader = self.image_panel.canvas.variables.canvas_image_object.image_reader
        self.populate_metaviewer(image_reader)


def main(reader=None):
    """
    Main method for initializing the pulse explorer

    Parameters
    ----------
    reader : None|str|CRSDTypeReader|STFTCanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('classic')

    app = PulseExplorer(root)

    if reader is not None:
        app.update_reader(reader)

    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the pulse explorer with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None,
        help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)


    # import os
    # from matplotlib import pyplot
    # # crsd_file = (r'R:\sar\Data_SomeDomestic\CRSD\AmazonRainforest'\
    # #              r'\S1A_IW_RAW__0SDV_20161110T095516_20161110T095548'\
    # #              r'_013878_01653D_8571_0_5000.crsd')
    # crsd_file = (r'C:\Users\609798\PycharmProjects\SarPy\sarpy_apps'
    #              r'\..\..\Sarpy\S1A_IW_RAW__0SDV_20161110T095516'
    #              r'_20161110T095548_013878_01653D_8571_0_5000.crsd')
    #
    # # reader = open_received(crsd_file)
    # # canvas_reader = STFTCanvasImageReader(reader)
    #
    # canvas_reader = STFTCanvasImageReader(crsd_file)
    # data = canvas_reader[:, :]
    # tims = canvas_reader.times
    # freqs = canvas_reader.frequencies
    #
    # fig, ax = pyplot.subplots()
    # ax.pcolormesh(tims, freqs, data, shading='auto')
    #
    # pyplot.show()
