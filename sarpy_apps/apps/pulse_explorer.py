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
        numpy.ndarray: Gets the times array for stft data for the current pulse.
        """

        return self._times

    @property
    def frequencies(self):
        """
        numpy.ndarray: Gets the frequencies array for stft data for the current pulse.
        """

        return self._frequencies

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


class PulseExplorer(WidgetPanel, WidgetWithMetadata):
    """
    The widget for selecting the Area of Interest for the aperture tool.
    """

    _widget_list = ("instructions", "image_panel")
    instructions = widget_descriptors.LabelDescriptor(
        "instructions",
        default_text='Maybe have a helpful description here?.',
        docstring='The basic instructions.')   # type: basic_widgets.Label
    image_panel = widget_descriptors.ImagePanelDescriptor(
        "image_panel", docstring='The image panel.')  # type: ImagePanel

    def __init__(self, parent):
        """

        Parameters
        ----------
        parent : tkinter.Tk|tkinter.Toplevel
        """

        # set the parent frame
        self.root = parent
        self.primary_frame = basic_widgets.Frame(parent)
        WidgetPanel.__init__(self, self.primary_frame)
        WidgetWithMetadata.__init__(self, parent)

        self.variables = AppVariables()

        self.init_w_vertical_layout()
        self.set_title()
        # todo: replace the instructions widget with a thing for selecting pulse

        # adjust packing so the image panel takes all the space
        self.instructions.master.pack(side='top', expand=tkinter.NO)
        self.image_panel.master.pack(side='bottom', fill=tkinter.BOTH, expand=tkinter.YES)
        # jazz up the instruction a little
        self.instructions.config(
            font=('Arial', '12'), anchor=tkinter.CENTER, relief=tkinter.RIDGE,
            justify=tkinter.CENTER, padding=5)
        # hide some extraneous image panel elements
        self.image_panel.hide_tools('shape_drawing')
        self.image_panel.hide_shapes()

        # define menus
        menubar = tkinter.Menu()
        # file menu
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Image", command=self.callback_select_files)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.exit)
        # menus for informational popups
        popups_menu = tkinter.Menu(menubar, tearoff=0)
        popups_menu.add_command(label="Metaicon", command=self.metaicon_popup)
        popups_menu.add_command(label="Metaviewer", command=self.metaviewer_popup)
        # ensure menus cascade
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Metadata", menu=popups_menu)

        # handle packing
        parent.config(menu=menubar)
        self.primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        # todo: handle if the pulse has changed...

    # callbacks
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
        self.root.destroy()

    def callback_select_files(self):
        fname = askopenfilename(initialdir=self.variables.browse_directory, filetypes=[crsd_files, all_files])
        if fname is None or fname in ['', ()]:
            return

        the_reader = STFTCanvasImageReader(fname)
        self.update_reader(the_reader, update_browse=os.path.split(fname)[0])

    # methods used in callbacks
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

        # change the tool to view
        self.image_panel.canvas.current_tool = 'VIEW'
        self.image_panel.canvas.current_tool = 'VIEW'
        # update the reader
        self.variables.image_reader = the_reader
        self.image_panel.set_image_reader(the_reader)
        self.set_title()
        # refresh appropriate GUI elements
        self.my_populate_metaicon()
        self.my_populate_metaviewer()

    def my_populate_metaicon(self):
        """
        Populate the metaicon.
        """
        if self.image_panel.canvas.variables.canvas_image_object is None or \
                self.image_panel.canvas.variables.canvas_image_object.image_reader is None:
            image_reader = None
            the_index = None
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
    root.geometry("1000x800")
    if reader is not None:
        app.update_reader(reader)

    root.mainloop()


if __name__ == '__main__':
    # import argparse
    # parser = argparse.ArgumentParser(
    #     description="Open the pulse explorer with optional input file.",
    #     formatter_class=argparse.RawTextHelpFormatter)
    #
    # parser.add_argument(
    #     '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    # args = parser.parse_args()
    #
    # main(reader=args.input)


    import os
    from matplotlib import pyplot
    crsd_file = r'R:\sar\Data_SomeDomestic\CRSD\AmazonRainforest\S1A_IW_RAW__0SDV_20161110T095516_20161110T095548_013878_01653D_8571_0_5000.crsd'

    # reader = open_received(crsd_file)
    # canvas_reader = STFTCanvasImageReader(reader)

    canvas_reader = STFTCanvasImageReader(crsd_file)
    data = canvas_reader[:, :]
    tims = canvas_reader.times
    freqs = canvas_reader.frequencies

    fig, ax = pyplot.subplots()
    ax.pcolormesh(tims, freqs, data, shading='auto')

    pyplot.show()
