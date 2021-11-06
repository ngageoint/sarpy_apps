"""
CRSD pulse explorer
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Thomas Rackers", "Thomas McCullough")

import logging
import os
from enum import Enum, auto

import numpy
from scipy.signal import spectrogram, resample

import tkinter
from tkinter import ttk, messagebox

from tkinter.filedialog import askopenfilename

from tk_builder.base_elements import TypedDescriptor, StringDescriptor
from tk_builder.panels.pyplot_image_panel import PyplotImagePanel
from tk_builder.widgets import basic_widgets

from sarpy_apps.supporting_classes.file_filters import crsd_files, all_files
from sarpy_apps.supporting_classes.widget_with_metadata import \
    WidgetWithMetadata

from sarpy.io.general.base import SarpyIOError, FlatReader
from sarpy.io.received.converter import open_received
from sarpy.io.received.base import CRSDTypeReader
from sarpy.processing.windows import kaiser
from sarpy.processing.fft_base import fftshift

from sarpy_apps.supporting_classes.image_reader import CRSDTypeCanvasImageReader

logger = logging.getLogger(__name__)

_PULSE_DISPLAY_VALUES = ('RFSignal',)


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
    deramp_bandwidth = abs(rcv_window_length * deramp_rate)
    upsample_factor = (deramp_bandwidth + sampling_rate) / sampling_rate

    sample_size = round(upsample_factor * pulse_data.size)
    oversample_factor = sample_size / (upsample_factor * pulse_data.size)
    use_data = resample(pulse_data - numpy.mean(pulse_data), sample_size)
    time_interval = 1 / (sampling_rate * upsample_factor * oversample_factor)
    times = time_interval * numpy.arange(sample_size) - 0.5 * rcv_window_length
    return use_data * numpy.exp(
        1j * numpy.pi * deramp_rate * times * times), 1. / time_interval


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

    nfft = 2 ** int(numpy.ceil(numpy.log2(numpy.sqrt(data.shape[0]))) + 2)
    nperseg = int(0.97 * nfft)
    window = kaiser(nperseg, 5)
    noverlap = int(0.9 * nfft)
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
        frequencies += params.F0Ref + dfic0 - 0.5 * sampling_rate
    else:
        reramped, reramped_sampling_rate = _reramp(pulse_data, sampling_rate,
                                                   fic_rate)
        times, frequencies, stft_data = _stft(reramped, reramped_sampling_rate)
        frequencies += \
            params.F0Ref + dfic0 + \
            0.5 * fic_rate * pulse_data.size / reramped_sampling_rate - \
            0.5 * reramped_sampling_rate
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
                'and got argument {}. Setting to 0.'.format(
                    len(signal_data_sizes), value))
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
                raise SarpyIOError(
                    'Could not open file {} as a CRSD reader'.format(value))
            value = reader

        if not isinstance(value, CRSDTypeReader):
            raise TypeError(
                'base_reader must be a CRSDReader, got type {}'.format(
                    type(value)))
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
            times, frequencies, data = _rf_signal(self.base_reader, self.index,
                                                  self.pulse)
        else:
            raise ValueError('Got unhandled pulse display value `{}`'.format(
                self.pulse_display))

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

class Operation(Enum):
    REV = auto()
    PREV = auto()
    STOP = auto()
    NEXT = auto()
    FWD = auto()


class SliderWidget(basic_widgets.Frame):
    """
    Widget panel with slider for forward/reverse and manual scan.
    """

    @staticmethod
    def _only_numeric_input(p):
        if p.isdigit() or p == "":
            return True
        return False

    def __init__(self, parent, reader):
        """

        Parameters
        ----------
        parent: basic_widgets.Frame
        reader: STFTCanvasImageReader
        """

        super().__init__(parent)

        self['padding'] = 5

        self.reader = reader

        self.label_1 = basic_widgets.Label(self, text='1')

        self.combobox_style = ttk.Style()
        self.combobox_style.configure('Channel.TCombobox')
        self.popdown_style = ttk.Style()
        self.label_channel = basic_widgets.Label(self, text='Channel')
        self.cbx_channel = basic_widgets.Combobox(self, state='readonly')
        self.var_cbx_channel = tkinter.StringVar()
        self.cbx_channel.configure(font=('TkFixedFont', 10), justify='left',
                                   textvariable=self.var_cbx_channel, width=30,
                                   values=[], style='Channel.TCombobox',
                                   state='disabled')

        self.label_pulse = basic_widgets.Label(self, text='Pulse')
        self.entry_pulse = basic_widgets.Entry(self)
        self.var_pulse_number = tkinter.StringVar(value='1')
        self.entry_pulse.configure(font=('TkFixedFont', 10), justify='right',
                                   textvariable=self.var_pulse_number, width=6)
        self.entry_callback = self.register(self._only_numeric_input)
        self.entry_pulse.configure(validate="key",
                                   validatecommand=(self.entry_callback, "%P"))

        self.fullscale = basic_widgets.Label(self, text='TBD')

        self.label_1.grid(row=0, column=0, padx=5, sticky='w')
        self.label_channel.grid(row=0, column=1, padx=5, sticky='e')
        self.cbx_channel.grid(row=0, column=2, padx=5)
        self.label_pulse.grid(row=0, column=3, padx=5)
        self.entry_pulse.grid(row=0, column=4, padx=5, sticky='w')
        self.fullscale.grid(row=0, column=5, padx=5, sticky='e')
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)
        self.columnconfigure(4, weight=1)
        self.columnconfigure(5, weight=0)

        self.scale = basic_widgets.Scale(self, from_=1, to=100, length=600,
                                         orient='horizontal',
                                         command=lambda s: \
                                             self.var_pulse_number.set(
                                                 f"{int(float(s))}")
                                         )
        self.scale.configure(variable=self.var_pulse_number)
        self.scale.grid(row=1, column=0, columnspan=6, padx=5, pady=8,
                        sticky='esw')


class DirectionWidget(basic_widgets.Frame):
    """
    Button pair to select forward/reverse/stopped direction.
    """

    def __init__(self, parent, reader):
        """

        Parameters
        ----------
        parent: basic_widgets.Frame
        reader: STFTCanvasImageReader
        """

        super().__init__(parent)
        self.parent = parent

        self.button_style = ttk.Style()
        self.button_style.configure('ToggleOff.TButton', font=('Arial', 24),
                                    foreground="gray50",
                                    background="PaleTurquoise3",
                                    width=3, sticky='CENTER')
        self.button_style.configure('ToggleOn.TButton', font=('Arial', 24),
                                    foreground="black",
                                    background="PaleTurquoise1",
                                    width=3, sticky='CENTER')

        self.button_rev = \
            basic_widgets.Button(self.parent, text="\u25C0",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.REV))
        self.button_prev = \
            basic_widgets.Button(self.parent, text="-1",
                                 style='ToggleOff.TButton')
        self.button_next = \
            basic_widgets.Button(self.parent, text="+1",
                                 style='ToggleOff.TButton')
        self.button_fwd = \
            basic_widgets.Button(self.parent, text="\u25B6",
                                 style='ToggleOff.TButton',
                                 command=lambda: self.action(Operation.FWD))

        self.mode = Operation.STOP

        # Remove these eventually.
        self.button_rev.state(['disabled'])
        self.button_fwd.state(['disabled'])

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
            self.set_button(self.button_rev, True)
            self.set_button(self.button_fwd, False)
        elif self.mode == Operation.FWD:
            self.set_button(self.button_rev, False)
            self.set_button(self.button_fwd, True)
        else:
            self.set_button(self.button_rev, False)
            self.set_button(self.button_fwd, False)


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


class PulseExplorer(basic_widgets.Frame, WidgetWithMetadata):
    def __init__(self, primary, reader=None, **kwargs):
        """

        Parameters
        ----------
        primary : tkinter.Toplevel|tkinter.Tk
        reader : None|str|CRSDTypeReader|CRSDTypeCanvasImageReader
        kwargs
            Keyword arguments passed through to the Frame
        """

        basic_widgets.Frame.__init__(self, primary, **kwargs)
        WidgetWithMetadata.__init__(self, primary)

        self.root = primary

        self.variables = AppVariables()

        self.style_pyplot_panel = ttk.Style()
        self.style_pyplot_panel.configure('TLabelframe', labelmargins=10)
        self.pyplot_panel = PyplotImagePanel(self)  # type: PyplotImagePanel

        self.pyplot_panel.cmap_name = 'turbo'
        self.pyplot_panel.set_ylabel('Freq (GHz)')
        self.pyplot_panel.set_xlabel('Time (\u03BCsec)')
        self.pyplot_panel.set_title('[this space available]')

        self.scanner_panel = basic_widgets.Frame(self, padding=10)  # type: basic_widgets.Frame
        self.scanner_panel.columnconfigure(0, weight=0)
        self.scanner_panel.columnconfigure(1, weight=0)
        self.scanner_panel.columnconfigure(2, weight=1)
        self.scanner_panel.columnconfigure(3, weight=0)
        self.scanner_panel.columnconfigure(4, weight=0)

        self.dir_buttons = DirectionWidget(self.scanner_panel, reader)  # type: DirectionWidget
        self.slider = SliderWidget(self.scanner_panel, reader)  # type: SliderWidget

        self.dir_buttons.button_rev.grid(row=0, column=0, sticky='w')
        self.dir_buttons.button_prev.grid(row=0, column=1, sticky='w')
        self.slider.grid(row=0, column=2, sticky='ew')
        self.dir_buttons.button_next.grid(row=0, column=3, sticky='e')
        self.dir_buttons.button_fwd.grid(row=0, column=4, sticky='e')

        self.pyplot_panel.pack(side="top", expand=True, fill='both')
        self.scanner_panel.pack(side="bottom", expand=False, fill='x')

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.pack(expand=True, fill='both')
        self.set_frame_title()

        self.current_pulse = 0

        # define menus
        menubar = tkinter.Menu()
        # file menu
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image",
                             command=self.callback_select_files)
        filemenu.add_command(label="Settings...",
                             command=self.callback_settings_popup)
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

        self.update_reader(reader)

        # self.image_panel.canvas.bind('<<RemapChanged>>', self.handle_remap_change)
        self.slider.cbx_channel.bind('<<ComboboxSelected>>', self.handle_image_index_changed)
        self.slider.scale.bind('<ButtonRelease-1>', self.handle_pulse_changed)
        self.slider.entry_pulse.bind('<FocusOut>', self.handle_pulse_changed)
        self.slider.entry_pulse.bind('<Return>', self.handle_pulse_changed)
        self.dir_buttons.button_prev.bind('<Button-1>', self.pulse_step_prev)
        self.dir_buttons.button_next.bind('<Button-1>', self.pulse_step_next)

    def set_frame_title(self):
        """
        Sets the LabelFrame title.
        """

        file_name = None if self.variables.image_reader is None \
            else self.variables.image_reader.file_name
        if file_name is None:
            the_title = " . . . "
        else:
            the_title = " {} ".format(os.path.split(file_name)[1])
        self.pyplot_panel.config(style='Pyplot.TLabelframe', text=the_title)

    def set_title(self):
        """
        Sets the window title.
        """

        file_name = None if self.variables.image_reader is None \
            else self.variables.image_reader.file_name
        if file_name is None:
            the_title = "Pulse Explorer"
        else:
            the_title = "Pulse Explorer for {}".format(
                os.path.split(file_name)[1])
        self.winfo_toplevel().title(the_title)

    def set_pulse_count(self):
        """
        Sets the pulse count.
        """
        pass

    def exit(self):
        self.root.destroy()

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

        self.variables.image_reader.index = self.slider.cbx_channel.current()
        self.display_in_pyplot_frame()
        self.my_populate_metaicon()
        self.slider.cbx_channel.selection_clear()
        # Update number of pulses.
        pulse_count = self.variables.image_reader.pulse_count
        self.slider.fullscale.configure(text=str(pulse_count))
        self.slider.scale.configure(to=pulse_count)

    def handle_pulse_changed(self, event):
        new_pulse = int(self.slider.var_pulse_number.get())
        try:
            if (new_pulse - 1) != self.variables.image_reader.pulse:
                self.variables.image_reader.pulse = new_pulse - 1
            self.display_in_pyplot_frame()
        except AttributeError:
            messagebox.showwarning(message="Image must be opened first.")
            self.slider.var_pulse_number.set(1)

    def pulse_step(self, direction):
        new_pulse = int(self.slider.var_pulse_number.get()) + direction
        try:
            if 0 < new_pulse <= self.variables.image_reader.pulse_count:
                self.slider.var_pulse_number.set(new_pulse)
                self.variables.image_reader.pulse = new_pulse - 1
                self.display_in_pyplot_frame()
        except AttributeError:
            messagebox.showwarning(message="Image must be opened first.")
            self.slider.var_pulse_number.set(1)

    def pulse_step_prev(self, event):
        self.pulse_step(-1)

    def pulse_step_next(self, event):
        self.pulse_step(+1)

    def update_reader(self, the_reader, update_browse=None):
        """
        Update the reader.

        Parameters
        ----------
        the_reader : None|str|CRSDTypeReader|STFTCanvasImageReader
        update_browse : None|str
        """

        if the_reader is None:
            return

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
        self.display_in_pyplot_frame()
        self.set_frame_title()
        # refresh appropriate GUI elements
        # self.pyplot_panel.make_blank()
        identifiers = [entry.Identifier for entry
                       in the_reader.base_reader.crsd_meta.Channel.Parameters]
        self.my_populate_metaicon()
        self.my_populate_metaviewer()
        self.update_combobox(identifiers)
        self.slider.fullscale.configure(text=str(self.variables.image_reader.pulse_count))

    def callback_select_files(self):
        fname = askopenfilename(initialdir=self.variables.browse_directory,
                                filetypes=[crsd_files, all_files])
        if fname is None or fname in ['', ()]:
            return

        the_reader = STFTCanvasImageReader(fname)
        self.update_reader(the_reader, update_browse=os.path.split(fname)[0])

    def callback_settings_popup(self):
        pass

    def display_in_pyplot_frame(self):
        times = 1.0e6 * self.variables.image_reader.times
        frequencies = 1.0e-9 * self.variables.image_reader.frequencies
        image_data = self.variables.image_reader.pulse_data[:, :]
        self.pyplot_panel.update_pcolormesh(times, frequencies, image_data,
                                            shading='gouraud', snap=True)

    def update_combobox(self, identifiers):
        # Update channels combobox.
        # Get channel identifiers from metadata.
        self.slider.cbx_channel['values'] = identifiers
        self.slider.cbx_channel.set(identifiers[0])
        self.slider.cbx_channel.configure(state='readonly')

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """

        self.populate_metaicon(self.variables.image_reader)

    def my_populate_metaviewer(self):
        """
        Populate the metaviewer.
        """

        self.populate_metaviewer(self.variables.image_reader)


def main(reader=None):
    """
    Main method for initializing the pulse explorer

    Parameters
    ----------
    reader : None|str|CRSDTypeReader|STFTCanvasImageReader
    """

    root = tkinter.Tk()

    the_style = ttk.Style()
    the_style.theme_use('default')

    app = PulseExplorer(root, reader)

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
