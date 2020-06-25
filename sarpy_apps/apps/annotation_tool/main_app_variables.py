from sarpy.annotation.annotate import FileAnnotationCollection
from sarpy.annotation.schema_processing import LabelSchema
from tk_builder.panel_templates.image_canvas_panel.image_canvas_panel import ImageCanvasPanel
from tk_builder.base_elements import StringDescriptor, TypedDescriptor, BooleanDescriptor

class AppVariables(object):
    """
    The main application variables for the annotation panel.
    """
    image_fname = StringDescriptor(
        'image_fname',
        docstring='The filename for the annotation tool.')  # type: str
    label_schema = TypedDescriptor(
        'label_schema', LabelSchema,
        docstring='The label schema object.')  # type: LabelSchema
    file_annotation_collection = TypedDescriptor(
        'file_annotation_collection', FileAnnotationCollection,
        docstring='The file annotation collection.')  # type: FileAnnotationCollection
    file_annotation_fname = StringDescriptor(
        'file_annotation_fname',
        docstring='The path for the annotation results file.')  # type: str
    annotate_canvas = TypedDescriptor(
        'annotate_canvas', ImageCanvasPanel,
        docstring='The image canvas panel for the annotation.')  # type: ImageCanvasPanel
    context_canvas = TypedDescriptor(
        'context_canvas', ImageCanvasPanel,
        docstring='The image canvas panel for the context.')  # type: ImageCanvasPanel
    new_annotation = BooleanDescriptor(
        'new_annotation', default_value=False,
        docstring='The state variable for whether a new annotation has been '
                  'created.')  # type: bool

    def __init__(self):
        # TODO: how would this work for complex geometry (multiline/polygon/geometry?)
        self.canvas_geom_ids_to_annotations_id_dict = {}
        """
        The dictionary which provides a mapping of canvas geometry id to the file 
        annotation id.
        """

        # TODO: I have no idea about type here...probably should be a descriptor above.
        self.current_canvas_geom_id = ''
        """
        The current canvas geometry id.
        """
