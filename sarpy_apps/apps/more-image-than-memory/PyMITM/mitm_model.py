from sarpy_apps.supporting_classes.metaicon.metaicon_data_container import MetaIconDataContainer
from sarpy.io.complex.converter import open_complex
from sarpy.geometry import point_projection
from PySide6.QtCore import QThread
import numpy as np
import psutil
import sys
import os

if sys.platform == 'win32':
    import win32api

from sarpy.visualization.remap import Density

class Model():

    def __init__(self, sys_arg0):
        """
        Initialize the data model component of the application.

        Creates the model that manages file reading and metadata extraction.
        Establishes a configuration handler based on the application path.

        Parameters
        ----------
        self : object
            The class instance.
        sys_arg0 : str
            The application executable path (sys.argv[0]).

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        self.openReaders = []
        self.config = Config(sys_arg0)

    def basic_file_read(self, fileName):
        """
        Read and process an image file.

        Opens a complex image file using the appropriate reader, records the
        reader in the list of open readers, and returns the reader along with
        the file size.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Path to the file to be read.

        Returns
        -------
        tuple
            (reader, size) where:
            - reader: The file reader object that provides access to the image data
            - size: The size of the file in bytes
        """

        reader = open_complex(fileName)

#        data = reader[:, :]

        self.openReaders.append((fileName.split('/')[-1], reader))

#        structure = reader.sicd_meta
#        return reader[:, :], structure
        size = os.path.getsize(fileName)
        
        return reader, size

    def get_metadata_from_open_reader(self, fileName):
        """
        Extract metadata from an open reader for display in the meta-icon.

        Finds the reader for the specified file and extracts relevant metadata
        fields for display, including image identification, geographic information,
        resolution, collection data parameters, and various angles.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Name of the file whose metadata should be extracted.

        Returns
        -------
        list
            A list of metadata values formatted for display in the meta-icon widget.
        """

        for file, reader in self.openReaders:
            if file == fileName:
                metaReader = reader
        
        sicd = metaReader.get_sicds_as_tuple()[0]
        dataContainer = MetaIconDataContainer.from_sicd(sicd)

        return [dataContainer.iid_line,
                dataContainer.geo_line,
                dataContainer.res_line,
                dataContainer.cdp_line,
                dataContainer.get_angle_line('azimuth'),
                dataContainer.get_angle_line('graze'),
                dataContainer.get_angle_line('layover'),
                dataContainer.get_angle_line('shadow'),
                dataContainer.get_angle_line('multipath'),
                dataContainer.north,
                dataContainer.layover,
                dataContainer.shadow,
                dataContainer.multipath,
                dataContainer.side_of_track]

    def get_aspect_ratio(self, fileName):
        """
        Calculate the correct aspect ratio for an image.

        Determines the proper aspect ratio for display based on the image's
        pixel spacing in row and column directions, adjusting for slant or
        ground plane imagery.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Name of the file whose aspect ratio should be calculated.

        Returns
        -------
        float
            The aspect ratio (width/height) to use for displaying the image.
        """

        for file, reader in self.openReaders:
            if file == fileName:
                metaReader = reader
        sicd = metaReader.get_sicds_as_tuple()[0]

        aspectRatioX = sicd.Grid.Col.SS
        aspectRatioY = sicd.Grid.Row.SS

        if sicd.Grid.ImagePlane   == 'Slant':
            aspectRatioY = aspectRatioY / np.cos(np.deg2rad(sicd.SCPCOA.GrazeAng))
        elif sicd.Grid.ImagePlane == 'Ground':
            aspectRatioY = aspectRatioY * np.cos(np.deg2rad(sicd.SCPCOA.GrazeAng))
        else:
            aspectRatio = 1

        aspectRatio = aspectRatioX / aspectRatioY

        return aspectRatio

    def get_avail_mem(self):
        """
        Get the amount of available system memory.

        Returns the current available memory in gigabytes using psutil.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        float
            Available memory in gigabytes.
        """
        return psutil.virtual_memory()[1] / 1000000000
    
    def setup_config(self, fileName):
        """
        Set up the application configuration.

        Reads the configuration file, validates network shortcuts,
        and ensures file format filters are properly configured.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Name of the configuration file to read.

        Returns
        -------
        None
            This method updates the configuration state.
        """

        self.config.read_config_file(fileName)
        self.config.check_network_shortcuts()
        self.config.check_file_formats()
    
class Config() :

    def __init__(self, sys_arg0):
        """
        Initialize the configuration manager.

        Sets up the configuration manager with default values and determines
        the appropriate file path for the configuration file based on the
        application path and platform.

        Parameters
        ----------
        self : object
            The class instance.
        sys_arg0 : str
            The application executable path (sys.argv[0]).

        Returns
        -------
        None
            This is the constructor and doesn't return a value.
        """

        # headers to search for in cfg file
        self.formatsKey = 'File Formats'
        self.dirsKey = 'Favorite Directories'

        # header contents
        self.fileFormats = []
        self.favoriteDirs = []
        
        self.headers = {
            self.formatsKey : self.fileFormats,
            self.dirsKey : self.favoriteDirs
        }

        self.fileName = ''
        self.makeFile = False
        self.default_file_formats = ['SICD Files (*.nitf *.ntf)']

        # if windows and running inside bundled EXE
        if(sys.platform == 'win32' and getattr(sys, '_MEIPASS', False)):
            # Ensure cfg file ends up in same directory as exe
            self.filepath = os.path.dirname(win32api.GetModuleFileName(0))
        else:
            self.filepath = os.path.dirname(sys_arg0)

    def read_config_file(self, fileName):
        """
        Read and parse the configuration file.

        Opens the specified configuration file and parses its contents,
        populating the headers dictionary with values for file formats
        and favorite directories.

        Parameters
        ----------
        self : object
            The class instance.
        fileName : str
            Name of the configuration file to read.

        Returns
        -------
        None
            This method updates the configuration state.
        """

        self.fileName = os.path.join(self.filepath, fileName)

        try:
            file = open(self.fileName, 'r')
        except:
            self.makeFile = True
            return
        
        currentHeader = ''

        # read through config file
        for line in file:
            line = line.strip()

            # found header
            if(line and line[0] == '[' and line[-1] == ']'):
                line = line[1:-1].strip()
                # validate header
                if(type(self.headers[line]) is list):
                    currentHeader = line

            elif(currentHeader):
                if(line and line[0] != '#'): # line is not a comment or empty
                    self.headers[currentHeader].append(line)
                    
        file.close()

    def check_network_shortcuts(self):
        """
        Add Windows network shortcuts to favorite directories.

        On Windows platforms, scans the Network Shortcuts directory and
        adds any shortcuts found there to the list of favorite directories.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the favorite directories list.
        """

        if sys.platform == 'win32':
            app_data_dir = os.getenv('APPDATA')
            shortcuts_dir = app_data_dir + '\\Microsoft\\Windows\\Network Shortcuts'
            for filepath in os.listdir(shortcuts_dir):
                f = os.path.join(shortcuts_dir, filepath)
                if(f not in self.favoriteDirs):
                    self.favoriteDirs.append(f)
    
    def check_file_formats(self):
        """
        Ensure file format filters are properly configured.

        If no file format filters were found in the configuration file,
        applies the default filters.

        Parameters
        ----------
        self : object
            The class instance.

        Returns
        -------
        None
            This method updates the file formats list.
        """

        if(not self.fileFormats):
            self.fileFormats.extend(self.default_file_formats)

    def write_config_file(self, dirs, filters):
        """
        Save the current configuration to the configuration file.

        Writes the current favorite directories and file format filters
        to the configuration file, either creating a new file or modifying
        an existing one.

        Parameters
        ----------
        self : object
            The class instance.
        dirs : list
            List of favorite directory paths to save.
        filters : list
            List of file format filter strings to save.

        Returns
        -------
        None
            This method writes to the configuration file.
        """

        outlines = []
        
        if(self.makeFile): # write new config file
            outlines.append('[' + self.dirsKey + ']\n')
            outlines.extend(dirs)
            outlines.append('\n')

            outlines.append('[' + self.formatsKey + ']\n')
            outlines.extend(filters)
            outlines.append('\n')

        else:  # modfiy existing config file
            file = open(self.fileName, 'r')
            currentHeader = ''
            lines = file.readlines()
            file.close()

            # read through config file
            underDirsHeader = False
            for line in lines:
                if not underDirsHeader:
                    outlines.append(line)
                line = line.strip()

                # found header
                if(line and line[0] == '[' and line[-1] == ']'):
                    if(underDirsHeader):
                        outlines.append('\n')
                        outlines.append(line+'\n')
                        underDirsHeader = False
                    line = line[1:-1].strip()
                    
                    # validate header
                    if(self.dirsKey == line):
                        outlines.extend(dirs)
                        underDirsHeader = True
        try:
            with open(self.fileName, 'w') as file:
                file.writelines(outlines)            
        except Exception as diag:
            print("Warning: could not save configuration.", diag)
    