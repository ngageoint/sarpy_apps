import tkinter
from tk_builder.panel_templates.widget_panel.widget_panel import AbstractWidgetPanel
from tk_builder.widgets import basic_widgets
from sarpy_apps.apps.annotation_tool.main_app_variables import AppVariables


class AnnotationFnamePopup(AbstractWidgetPanel):
    new_annotation = basic_widgets.Button        # type: basic_widgets.Button
    edit_existing_annotation = basic_widgets.Button       # type: basic_widgets.Button

    def __init__(self,
                 parent,
                 main_app_variables,    # type: AppVariables
                 ):
        self.main_app_variables = main_app_variables

        self.parent = parent
        self.master_frame = tkinter.Frame(parent)
        AbstractWidgetPanel.__init__(self, self.master_frame)
        widget_list = ["new_annotation", "edit_existing_annotation"]
        self.init_w_horizontal_layout(widget_list)

        self.master_frame.pack()
        self.pack()

        # set up callbacks
        self.new_annotation.on_left_mouse_click(self.callback_new)
        self.edit_existing_annotation.on_left_mouse_click(self.callback_existing)

    # noinspection PyUnusedLocal
    def callback_new(self, event):
        self.main_app_variables.new_annotation = True
        self.parent.destroy()

    # noinspection PyUnusedLocal
    def callback_existing(self, event):
        self.main_app_variables.new_annotation = False
        self.parent.destroy()
