import tkinter as tk
from tkinter import ttk
from sarpy.io.complex.sicd import SICDType

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class Metaviewer(ttk.Treeview):
    # TODO:
    #  1.) how do you reinitialize this thing?
    #  2.) Where all is this used? Why not a treeview - should be a treeview.

    def __init__(self, master):
        """

        Parameters
        ----------
        master : tk.Tk
            The GUI element which is the parent or master of this node.
        """

        super(Metaviewer, self).__init__(master)
        self.parent = master
        self.parent.geometry("800x600")
        self.pack(expand=True, fill='both')
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.parent.withdraw()

    def add_node(self, k, v):
        """
        Given a name and dictionary of values, recursively add elements.

        Parameters
        ----------
        k : str
        v : dict

        Returns
        -------
        None
        """

        # TODO: make this more robust to types - list, at least

        for key, val in v.items():
            new_key = "{}_{}".format(k, key)
            if isinstance(val, dict):
                self.insert(k, 1, new_key, text=key)
                self.add_node(new_key, val)
            else:
                self.insert(k, 1, new_key, text="{}: {}".format(key, val))

    def create_w_sicd(self, sicd_meta):
        """
        Initialize from a SICD structure.

        Parameters
        ----------
        sicd_meta : SICDType

        Returns
        -------
        None
        """

        # TODO: this should be replaced with something more multi-purpose

        for k, v in sicd_meta.to_dict().items():
            self.insert("", 1, k, text=k)
            self.add_node(k, v)
