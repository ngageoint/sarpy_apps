"""
Command-line utility for opening the sicd validation tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from sarpy_apps.apps.validation_tool.validation_tool import main


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the validation tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    args = parser.parse_args()

    main(reader=args.input)
