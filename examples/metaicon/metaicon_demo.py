import os
import tkinter
from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import widget_descriptors

from sarpy_apps.supporting_classes.metaicon.metaicon import MetaIcon
from sarpy_apps.supporting_classes.complex_image_reader import ComplexImageReader


class MetaIconDemo(WidgetPanel):
    _widget_list = ("metaicon", )

    metaicon = widget_descriptors.PanelDescriptor("metaicon", MetaIcon)  # type: MetaIcon

    def __init__(self, primary):
        self.primary = primary

        primary_frame = tkinter.Frame(primary)
        WidgetPanel.__init__(self, primary_frame)
        self.init_w_horizontal_layout()
        path_to_sicd = os.path.expanduser("~/sicd_example_1_PFA_RE32F_IM32F_HH.nitf")
        reader = ComplexImageReader(path_to_sicd)
        self.metaicon.create_from_reader(reader.base_reader, index=0)
        primary_frame.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.metaicon.canvas.set_canvas_size(800, 600)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = MetaIconDemo(root)
    root.after(1000, app.metaicon.update_everything())
    root.mainloop()

