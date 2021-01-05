import tkinter
from tkinter.messagebox import showinfo, askyesno


from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.widgets import widget_descriptors

from sarpy_apps.apps.annotation_tool.main_app_variables import AppVariables as MainAppVariables
from sarpy_apps.apps.annotation_tool.schema_editor import select_schema_entry

from sarpy.annotation.annotate import AnnotationMetadata
from sarpy.annotation.annotate import Annotation
from sarpy.annotation.annotate import FileAnnotationCollection

__classification__ = "UNCLASSIFIED"
__author__ = "Jason Casey"


class AnnotationPopup(WidgetPanel):
    _widget_list = (("object_type_label", "object_type"),
                    ("comment_label", "comment"),
                    ("confidence_label", "confidence"),
                    ("reset", "submit")
                    )
    object_type = widget_descriptors.EntryDescriptor(
        "object_type", default_text='')  # type: basic_widgets.Entry
    reset = widget_descriptors.ButtonDescriptor(
        "reset", default_text='Reset')  # type: basic_widgets.Button
    submit = widget_descriptors.ButtonDescriptor(
        "submit", default_text='Submit')  # type: basic_widgets.Button
    comment = widget_descriptors.EntryDescriptor(
        "comment", default_text='')  # type: basic_widgets.Entry
    confidence = widget_descriptors.ComboboxDescriptor(
        "confidence", default_text='')  # type: basic_widgets.Combobox

    object_type_label = widget_descriptors.LabelDescriptor(
        "object_type_label", default_text='Object Type:')  # type: basic_widgets.Label
    comment_label = widget_descriptors.LabelDescriptor(
        "comment_label", default_text='Comment:')  # type: basic_widgets.Label
    confidence_label = widget_descriptors.LabelDescriptor(
        "confidence_label", default_text='Confidence:')  # type: basic_widgets.Label

    def __init__(self, parent, main_app_variables):
        """

        Parameters
        ----------
        parent
            The app parent.
        main_app_variables : MainAppVariables
        """

        self.label_schema = main_app_variables.label_schema
        self.main_app_variables = main_app_variables

        self.parent = parent
        self.primary_frame = tkinter.Frame(parent)
        WidgetPanel.__init__(self, self.primary_frame)

        self.init_w_rows()

        self.set_text("Annotate")

        # set up base types for initial dropdown menu
        self.setup_confidence_selections()

        self.primary_frame.pack()

        # set up callbacks
        self.object_type.config(validate='focusin', validatecommand=self.select_object_type)
        self.reset.config(command=self.callback_reset)
        self.submit.config(command=self.callback_submit)

        # populate existing fields if editing an existing geometry
        previous_annotation = self.main_app_variables.canvas_geom_ids_to_annotations_id_dict[str(self.main_app_variables.current_canvas_geom_id)]
        if previous_annotation.properties:
            object_type = previous_annotation.properties.elements[0].label_id
            comment = previous_annotation.properties.elements[0].comment
            confidence = previous_annotation.properties.elements[0].confidence

            self.object_type.set_text(object_type)
            self.object_type.configure(state="disabled")
            self.comment.set_text(comment)
            self.confidence.set(confidence)
        else:
            self.object_type.set_text("")
            self.comment.set_text("")
            self.confidence.set("")

    def select_object_type(self):
        current_value = self.object_type.get()
        value = select_schema_entry(self.label_schema, start_id=current_value)
        self.object_type.set_text(value)

    def callback_reset(self):
        self.object_type.configure(state="normal")

    def callback_submit(self):
        if self.object_type.get() == '':
            showinfo("Select Object Type", message="Select the object type")
            return

        if self.confidence.get() not in self.main_app_variables.label_schema.confidence_values:
            result = askyesno("Confidence Selection?", message="The confidence selected in not one of the permitted values. Continue?")
            if not (result is True):
                return

        comment_text = self.comment.get()
        the_object_type = self.object_type.get()
        confidence_val = self.confidence.get()

        current_canvas_geom_id = self.main_app_variables.current_canvas_geom_id
        annotation = self.main_app_variables.canvas_geom_ids_to_annotations_id_dict[str(current_canvas_geom_id)]     # type: Annotation
        annotation_metadata = AnnotationMetadata(comment=comment_text,
                                                 label_id=the_object_type,
                                                 confidence=confidence_val)
        annotation.add_annotation_metadata(annotation_metadata)
        # TODO: why is this not editing in place? We also need some kind of error catching here
        new_file_annotation_collection = FileAnnotationCollection(self.main_app_variables.label_schema,
                                                                  image_file_name=self.main_app_variables.file_annotation_collection.image_file_name)
        self.main_app_variables.file_annotation_collection = new_file_annotation_collection
        for key, val in self.main_app_variables.canvas_geom_ids_to_annotations_id_dict.items():
            self.main_app_variables.file_annotation_collection.add_annotation(val)
        self.main_app_variables.file_annotation_collection.to_file(self.main_app_variables.file_annotation_fname)
        self.parent.destroy()

    def setup_confidence_selections(self):
        self.confidence.update_combobox_values(self.main_app_variables.label_schema.confidence_values)
