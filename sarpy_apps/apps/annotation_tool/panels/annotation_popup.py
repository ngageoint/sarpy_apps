from tk_builder.panel_builder import WidgetPanel
from tk_builder.widgets import basic_widgets
from tk_builder.base_elements import StringDescriptor
from tk_builder.widgets import widget_descriptors
from sarpy_apps.apps.annotation_tool.main_app_variables import AppVariables as MainAppVariables
from sarpy.annotation.annotate import AnnotationMetadata
from sarpy.annotation.annotate import Annotation
from sarpy.annotation.annotate import FileAnnotationCollection
import tkinter


class AppVariables(object):
    parent_types_main_text = StringDescriptor(
        'parent_types_main_text', default_value='',
        docstring='The parent types main text.')  # type: str


class AnnotationPopup(WidgetPanel):
    _widget_list = (("parent_types",),
                    ("thing_type_label", "thing_type"),
                    ("comment_label", "comment"),
                    ("confidence_label", "confidence"),
                    ("reset", "submit")
                    )
    parent_types = widget_descriptors.LabelDescriptor("parent_types")      # type: basic_widgets.Label
    thing_type = widget_descriptors.ComboboxDescriptor("thing_type")  # type: basic_widgets.Combobox
    reset = widget_descriptors.ButtonDescriptor("reset")        # type: basic_widgets.Button
    submit = widget_descriptors.ButtonDescriptor("submit")       # type: basic_widgets.Button
    comment = widget_descriptors.EntryDescriptor("comment")       # type: basic_widgets.Entry
    confidence = widget_descriptors.ComboboxDescriptor("confidence")     # type: basic_widgets.Combobox

    thing_type_label = widget_descriptors.LabelDescriptor("thing_type_label")      # type: basic_widgets.Label
    comment_label = widget_descriptors.LabelDescriptor("comment_label")         # type: basic_widgets.Label
    confidence_label = widget_descriptors.LabelDescriptor("confidence_label")            # type: basic_widgets.Label

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
        self.variables = AppVariables

        self.parent = parent
        self.primary_frame = tkinter.Frame(parent)
        WidgetPanel.__init__(self, self.primary_frame)

        self.init_w_rows()

        self.set_text("annotate")

        # set up base types for initial dropdown menu
        self.setup_main_parent_selections()
        self.setup_confidence_selections()

        # set label text
        self.thing_type_label.set_text("object type")
        self.comment_label.set_text("comment")
        self.confidence_label.set_text("confidence")

        self.primary_frame.pack()

        self.parent_types.set_text(self.variables.parent_types_main_text)

        # set up callbacks
        self.thing_type.on_selection(self.callback_update_selection)
        self.reset.config(command=self.callback_reset)
        self.submit.config(command=self.callback_submit)

        # populate existing fields if editing an existing geometry
        previous_annotation = self.main_app_variables.canvas_geom_ids_to_annotations_id_dict[str(self.main_app_variables.current_canvas_geom_id)]
        if previous_annotation.properties:
            object_type = previous_annotation.properties.elements[0].label_id
            comment = previous_annotation.properties.elements[0].comment
            confidence = previous_annotation.properties.elements[0].confidence

            self.thing_type.set(object_type)
            self.thing_type.configure(state="disabled")
            self.comment.set_text(comment)
            self.confidence.set(confidence)
        else:
            self.thing_type.set("")
            self.comment.set_text("")
            self.confidence.set("")

    # noinspection PyUnusedLocal
    def callback_update_selection(self, event):
        selection_id = [key for key, val in self.label_schema.labels.items() if val == self.thing_type.get()][0]
        children_ids = []
        for key, val in self.label_schema.parent_types.items():
            if selection_id in val:
                child_index = val.index(selection_id) - 1
                if child_index >= 0:
                    children_ids.append(val[child_index])
        children_ids = set(children_ids)
        child_labels = []
        current_parent_text = self.parent_types.get_text()
        if current_parent_text == self.variables.parent_types_main_text:
            new_parent_text = self.label_schema.labels[selection_id]
        else:
            new_parent_text = current_parent_text + " -> " + self.label_schema.labels[selection_id]
        if children_ids:
            for child_id in children_ids:
                child_labels.append(self.label_schema.labels[child_id])
            self.thing_type.update_combobox_values(child_labels)
            self.parent_types.set_text(new_parent_text)
        else:
            self.thing_type.configure(state="disabled")

    # noinspection PyUnusedLocal
    def callback_reset(self):
        self.thing_type.configure(state="normal")
        self.setup_main_parent_selections()

    # noinspection PyUnusedLocal
    def callback_submit(self):
        if not 'disabled' in self.thing_type.state():
            print("please select a valid type.")
        elif self.confidence.get() not in self.main_app_variables.label_schema.confidence_values:
            print("select a confidence value")
        else:
            comment_text = self.comment.get()
            thing_type = self.thing_type.get()
            confidence_val = self.confidence.get()

            current_canvas_geom_id = self.main_app_variables.current_canvas_geom_id
            annotation = self.main_app_variables.canvas_geom_ids_to_annotations_id_dict[str(current_canvas_geom_id)]     # type: Annotation
            annotation_metadata = AnnotationMetadata(comment=comment_text,
                                                     label_id=thing_type,
                                                     confidence=confidence_val)
            annotation.add_annotation_metadata(annotation_metadata)
            new_file_annotation_collection = FileAnnotationCollection(self.main_app_variables.label_schema,
                                                                      image_file_name=self.main_app_variables.file_annotation_collection.image_file_name)
            self.main_app_variables.file_annotation_collection = new_file_annotation_collection
            for key, val in self.main_app_variables.canvas_geom_ids_to_annotations_id_dict.items():
                self.main_app_variables.file_annotation_collection.add_annotation(val)
            self.main_app_variables.file_annotation_collection.to_file(self.main_app_variables.file_annotation_fname)
            self.parent.destroy()

    def setup_main_parent_selections(self):
        base_type_ids = []
        for type_id, parents in self.label_schema.parent_types.items():
            main_parent = parents[-1]
            base_type_ids.append(main_parent)
        base_type_ids = set(base_type_ids)
        base_labels = []
        for type_id in base_type_ids:
            base_labels.append(self.label_schema.labels[type_id])
        self.thing_type.update_combobox_values(base_labels)
        self.parent_types.set_text("")

    def setup_confidence_selections(self):
        self.confidence.update_combobox_values(self.main_app_variables.label_schema.confidence_values)
