"""
Command-line utility for opening the aperture tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from sarpy_apps.apps.aperture_tool.aperture_tool import main


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the aperture tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
