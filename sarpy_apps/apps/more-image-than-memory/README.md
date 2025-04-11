# More Image Than Memory (MITM) Viewer

## Overview

MITM (More Image Than Memory) is a specialized software tool designed for displaying and performing simple processing operations on complex Synthetic Aperture Radar (SAR) data using the NGA Sensor Independent Complex Data (SICD) format.

MITM allows technical users to efficiently work with SAR data that often exceeds available system memory through intelligent decimation strategies and memory management techniques.

## Key Features

- View and analyze SICD-formatted SAR data with an intuitive interface
- Efficient handling of datasets larger than available system memory
- Multiple visualization modes with customizable resampling and remapping options
- Multi-window support for comparing multiple SAR images

## System Requirements

- MITM functionality has been tested for Python 3.11
- Dependencies listed in requirements.txt

## Installation

### From Git Repository

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. (Optional) Create a Python virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```
   pip install -r requirements.txt
   ```

4. Run MITM:
   ```
   python main.py
   ```

### As a Standalone Application

MITM can be packaged as a standalone executable using PyInstaller:

1. Install python-mitm if not already installed:
   ```
   pip install python-mitm
   ```

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
MITM/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── PyMITM/
    ├── mitm_model.py          # Model components for MVC architecture
    ├── mitm_viewer.py         # View components for MVC architecture
    ├── mitm_controller.py     # Controller components for MVC architecture
    ├── mitm_subapplication.py # Abstract class for MITM environment subapplications
    ├── ui_*.py                # Compiled .ui files
    ├── utils/                 # Helper files
    ├── resources/             # Documentation
    ├── mitm_ui/               # Uncompiled .ui files
└── standalone/
    └── pyinstaller/
        └── mitm.spec          # Packaging scripts for distribution
```

## Architecture

MITM follows the Model-View-Controller (MVC) architectural pattern:

- **Model**: Manages data loading and application state
- **View**: Handles UI rendering and user interaction
- **Controller**: Coordinates between Model and View components

The application uses PySide (Qt for Python) for its graphical interface and PyQtGraph for specialized scientific image display, providing a responsive UI even with large datasets.

## Contributing

For contributions to MITM please follow the overall contribution guidence for SARPY_APPS.

## Contact

MITM was developed by NASIC. For issues, questions, or contributions, please submit issues in the 
SARPY_APPS repo and NGA will coordinate with NASIC when necessary.
