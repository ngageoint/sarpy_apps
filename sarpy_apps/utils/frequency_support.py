"""
Command-line utility for opening the frequency support analysis tools.
"""

__classification__ = "UNCLASSIFIED"
__author__ = "Thomas McCullough"

from sarpy_apps.apps.frequency_support_tool.full_support_tool import main as full_main
from sarpy_apps.apps.frequency_support_tool.local_support_tool import main as local_main


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Open one of the frequency support tools with optional input file.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-i', '--input', metavar='input', default=None, help='The path to the optional image file for opening.')
    parser.add_argument(
        '-t', '--type', default='local', choices=['local', 'full'],
        help="What type of analysis is being performed?")
    args = parser.parse_args()

    if args.type == 'local':
        local_main(reader=args.input)
    elif args.type == 'full':
        full_main(reader=args.input)
    else:
        raise ValueError('Got unexpected type {}'.format(args.type))
