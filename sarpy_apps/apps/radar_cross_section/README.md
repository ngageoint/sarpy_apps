# RCS Tool
The RCS (Radar Cross Section) tool allows users to create complex geometry selections from SAR data shown as a image and calculate the RCS and other related parameters. This tool also provides features including importing/exporting, plotting, geometry visualization, and data tabulation to aid analysts. This tool is intended to be a sub-application to be used in conjunction with MITM(more image than memory) viewer(PyMITM). Users will select RCS tool from within the MITM application (see SUM for detailed guidance).

## Key Features

- Create complex geometries on SICD-fromatted SAR data
- Calculate RCS and related parameters, updating live
- Import/Export geometry collections as geojson format
- Export images and tabulated data to create reports
- Full resolution geometry previews for current selection
- Slow and fast time response plotting

## System Requirements

- PyRCS functionality has been tested for Python 3.11
- Dependencies listed in requirements.txt

## Download
### Gitlab
```console
git clone <link to rcs-tool repo>
```
## Installation

### Python
1. Navigate to the main rcs-tool directory
2. ```console
   pip install -r requirements.txt
   ```
3. ```console
   pip install src/.
   ```
4. Install PyMITM

### Standalone Application

PyRCS can be packaged as a standalone executable using PyInstaller:

1. Install PyMITM if not already installed:

2. Navigate to the PyInstaller directory:
   ```
   cd standalone/pyinstaller
   ```

3. Create the executable:
   ```
   pyinstaller mitm.spec
   ```

4. Run the executable:
   ```
   ./dist/mitm.exe
   ```

## Project Structure

```
RCS-Tool/
├── RCSApplication.py          # Application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── LICENSE                    # Software licenses for repo
├── docs                       # Documentation, generated docs and makefiles for generating docs
    ├── build                  # Built documentations
        ├── doctrees           # Built doctrees documentation
        ├── html               # Built html documentation
        ├── latex              # Built latex documentation
    ├── source                 # Source directory for sphinx  
├── src/                       # Source code directory
    ├── PyRCS                  # PyRCS module
        ├── rcs_controller.py  # Controller component for MVC architecture
        ├── rcs_model.py       # Model component for MVC architecture
        ├── rcs_viewer.py      # Viewer component for MVC architecture
        ├── ui_rcs_tool.py     # Compiled .ui file
        ├── rcs_ui/            # Uncompiled .ui files
            ├── rcs_tool.ui    # Uncompiled .ui file
└── standalone/
    └── pyinstaller/
        └── mitm.spec          # Packaging scripts for distribution
```

## Architecture

RCS Tool follows the Model-View-Controller (MVC) architectural pattern:

- **Model**: Manages data loading and application state
- **View**: Handles UI rendering and user interaction
- **Controller**: Coordinates between Model and View components

The application uses PySide (Qt for Python) for its graphical interface and PyQtGraph for specialized scientific image display, providing a responsive UI even with large datasets.

## Contributing

For contributions to MITM please follow the overall contribution guidence for SARPY_APPS.

## Contact

RCS was developed by NASIC. For issues, questions, or contributions, please submit issues in the 
SARPY_APPS repo and NGA will coordinate with NASIC when necessary.

## Project status
NASIC is no longer actively developing PyRCS.