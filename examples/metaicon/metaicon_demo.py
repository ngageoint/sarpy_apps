import os
import tkinter
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors

from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon


class MetaIconDemo(WidgetPanel):
    _widget_list = ("metaicon", )

    metaicon = widget_descriptors.PanelDescriptor("metaicon", MetaIcon)  # type: MetaIcon

    def __init__(self, primary):
        self.primary = primary

        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_horizontal_layout()
        self.metaicon.config(width=800, height=600)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = MetaIconDemo(root)
    root.after(200, app.filtered_panel.update_everything)
    root.after(200, app.frequency_vs_degree_panel.update_everything)
    root.mainloop()

