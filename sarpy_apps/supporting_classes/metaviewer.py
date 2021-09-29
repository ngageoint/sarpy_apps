"""
A viewer for the meta-data associated with the file readers.
"""

__classification__ = "UNCLASSIFIED"
__author__ = ("Jason Casey", "Thomas McCullough")

import tkinter

from tk_builder.widgets import basic_widgets

from sarpy.compliance import integer_types, string_types
from sarpy.io.general.base import BaseReader
from sarpy.io.general.nitf import NITFDetails, NITFReader


def _primitive_list(the_list):
    primitive = True
    for entry in the_list:
        primitive &= (isinstance(entry, float) or
                      isinstance(entry, integer_types) or
                      isinstance(entry, string_types) or
                      isinstance(entry, list))
    return primitive


class Metaviewer(basic_widgets.Treeview):
    """
    For viewing a rendering of a json compatible object.
    """

    def __init__(self, master):
        """

        Parameters
        ----------
        master : tkinter.Tk|tkinter.Toplevel
            The GUI element which is the parent or master of this node.
        """
        basic_widgets.Treeview.__init__(self, master)
        self.parent = master
        self.parent.geometry("800x600")
        self.pack(expand=tkinter.YES, fill=tkinter.BOTH)

    def hide_on_close(self):
        """
        Sets the condition so that the close button does not destroy the tool.
        """

        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def empty_entries(self):
        """
        Empty all entries - for the purpose of reinitializing.

        Returns
        -------
        None
        """

        self.delete(*self.get_children())

    def close_window(self):
        self.parent.withdraw()

    def add_node(self, the_parent, the_key, the_value):
        """
        For the given key and value, this creates the node for the given value,
        and recursively adds children, as appropriate.

        Parameters
        ----------
        the_parent : str
            The parent key for this entry.
        the_key : str
            The key for this entry - should be unique amongst children of this parent.
        the_value : dict|list|str|int|float
            The value for this entry.

        Returns
        -------
        None
        """

        real_key = '{}_{}'.format(the_parent, the_key)
        if isinstance(the_value, list):
            if _primitive_list(the_value):
                self.insert(the_parent, "end", real_key, text="{}: {}".format(the_key, the_value))
            else:
                # add a parent node for this list
                self.insert(the_parent, "end", real_key, text=the_key)
                for i, value in enumerate(the_value):
                    # add a node for each list element
                    element_key = '{}[{}]'.format(the_key, i)
                    self.add_node(real_key, element_key, value)
        elif isinstance(the_value, dict):
            self.insert(the_parent, "end", real_key, text=the_key)
            for key in the_value:
                val = the_value[key]
                self.add_node(real_key, key, val)
        elif isinstance(the_value, float):
            self.insert(the_parent, "end", real_key, text="{0:s}: {1:0.16G}".format(the_key, the_value))
        else:
            self.insert(the_parent, "end", real_key, text="{}: {}".format(the_key, the_value))

    def populate_from_reader(self, reader):
        """
        Populate the entries from a reader implementation.

        Parameters
        ----------
        reader : BaseReader

        Returns
        -------
        None
        """

        def do_sicds():
            try:
                sicds = reader.get_sicds_as_tuple()
                if sicds is None:
                    return
                elif len(sicds) == 1:
                    self.add_node("", "SICD", sicds[0].to_dict())
                else:
                    for i, entry in enumerate(sicds):
                        self.add_node("", "SICD_{}".format(i), entry.to_dict())
            except AttributeError:
                pass

        def do_sidds():
            try:
                sidds = reader.sidd_meta
                if sidds is None:
                    pass
                elif isinstance(sidds, (list, tuple)):
                    for i, entry in enumerate(sidds):
                        self.add_node("", "SIDD_{}".format(i), entry.to_dict())
                else:
                    self.add_node("", "SIDD", sidds.to_dict())
            except AttributeError:
                pass

        def do_cphd():
            try:
                cphd = reader.cphd_meta
                if cphd is None:
                    pass
                else:
                    self.add_node("", "CPHD", cphd.to_dict())
            except AttributeError:
                pass

        def do_nitf():
            if isinstance(reader, NITFReader):
                nitf_details = reader.nitf_details  # type: NITFDetails
                self.add_node("", "NITF", nitf_details.get_headers_json())

        # empty any present entries
        self.empty_entries()
        # populate relevant meta-data structures
        if reader.reader_type == "SICD":
            do_sicds()
        elif reader.reader_type == "SIDD":
            do_sidds()
            do_sicds()
        elif reader.reader_type == "CPHD":
            do_cphd()
        do_nitf()
