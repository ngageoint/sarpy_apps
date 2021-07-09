"""
Command-line utility for opening the rcs tool.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from sarpy_apps.apps.rcs_tool.rcs_tool import main


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open the rcs tool with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None,
        help='The path to the optional image file for opening.')
    parser.add_argument(
        '-a', '--annotation', metavar='annotation', default=None,
        help='The path to the optional annotation file. '
             'If the image input is not specified, then this has no effect. '
             'If both are specified, then a check will be performed that the '
             'annotation actually applies to the provided image.')
    args = parser.parse_args()

    main(reader=args.input, annotation=args.annotation)
