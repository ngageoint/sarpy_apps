"""
Command-line utility for opening the image viewer.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from sarpy_apps.apps.image_viewer.image_viewer import main


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the image viewer with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
