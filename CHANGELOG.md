# Change Log

## [1.1.21] - 2022-06-07
### Fixed
Broken import from sarpy

## [1.1.20] - 2022-06-06
### Changed
Updates for compliance with sarpy 1.3.0 changes

## [1.1.19] - 2022-04-15
### Fixed
Fixed a typo which caused the metaicon callback to open the metaviewer instead

## [1.1.18] - 2022-04-14
### Changed
Improved default shape drawing defaults in annotation

## [1.1.17] - 2022-04-13
### Changed
Addition of time profile plot in pulse explorer, and usage of clarified 
tk_builder constructs

## [1.1.16] - 2022-04-07
### Changed
Extended application of new tk_builder ImagePanelDetail object, and simplified 
the metaicon/viewer implementation

## [1.1.15] - 2022-04-06
### Changed
Refined the Image Viewer tool to separate the detail panel from basic view

## [1.1.14] - 2022-01-27
### Fixed
Correcting annotation type tool bug to allow resetting the image reader

## [1.1.13] - 2022-01-18
Correcting command-line argument bug

## [1.1.12] - 2022-01-14
Correcting metaicon shadow display bug and streamlining commandline args

## [1.1.11] - 2022-01-07
- Expanding use of remap functions to avoid failures
- Bug fix for rcs tool metadata menu

## [1.1.9] - 2021-11-23
Adding pulse explorer tool for CRSD file exploration

## [1.1.8] - 2021-11-15
- Creating simple method to visualize SICD ValidData polygon
- Correcting bug in annotation tools for setting json file

## [1.1.6] - 2021-11-03
Correcting SIDD metaicon North direction display and correcting SIDD metaviewer bug

## [1.1.5] - 2021-11-02
Adjustments for new image canvas tools on toolbar

## [1.1.4] - 2021-10-27
- Adding plain annotation tool and associated refactoring labeling and rcs tools
- General stability improvements for all apps

## [1.1.3] - 2021-10-04
Incorporating reader structure clarification from sarpy 1.2.25

## [1.1.2] - 2021-10-01
- Incorporate changes to remap functions and reader types from sarpy 1.2.24
- Adding canvas image readers specific to CPHD and CRSD usage

## [1.1.1] - 2021-09-29
- Bug fixes for metaicon and pyplot image panel
- Dropping of stated Python 2.7 support

## [1.1.0] - 2021-09-20
- Syncing for the base tk_builder 1.1 changes
- Using paned window for many apps, for simple resizing options
- Updating the metaicon for proper SIDD interpretation
- Introducing a method for CRSD metaicon production

# 1.1

## [1.0.15] - 2021-08-31
Adding a GFF file filter and bug fixes for file type handling

## [1.0.14] - 2021-07-13
- Introducing better command line usage for the apps
- RCSTool now reports results in expected units and format

## [1.0.13] - 2021-05-27
Compatibility with sarpy 1.2.0 reader change

## [1.0.12] - 2021-04-30
Including a schema check in the validation tool, where possible

## [1.0.11] - 2021-04-27
- Introduction of full image frequency analysis tool
- Simplification of RCS tool state
- Completion of missing elements of the validation tool

## [1.0.10] - 2021-04-20
Adding sicd validation and frequency support tools

## [1.0.9] - 2021-02-12
- Fix bug in rcs tool for using the primary feature, when set
- Complete refactoring of all tools and completion of labeling (formerly annotation) and rcs tools

## [1.0.7] - 2021-01-05
- Adjustments for tk_builder and sarpy updates
- Updates to tools:
    * Metaviewer updates
    * ImageViewer tool updates
    * Aperture tool updates
    * Metaicon updates
    * Creation of a labelling schema editor tool
- Incomplete updates to tools:
    * Annotation tool updates, refining to come
    * Preliminary RCS tool shell, completion and refining to come

## [1.0.6] - 2020-09-01
Animated gif capability added

## [1.0.5] - 2020-08-11
- Created new image panel object that contains axes, toolbar and allows for window resize
- Updates to metaicon to update graphic on window resize

## [1.0.3] - 2020-07-08 
Updates to aperture tool to update selection limits after window resize

## [1.0.2]
Updates to tools for more streamlined look

## [1.0.1] 
Updates to tools to incorporate updated tk_builder workflow
