"""ESP Custom window code to annotate the output of Computer Vision models."""

import cv2

# Import ESP specific packages, when available. This allows to test the Python code outside of ESP
try:
    import esp  # type: ignore
    import esp_utils  # type: ignore
except ModuleNotFoundError:
    print("Running without ESP packages")

# Constants for creating the annotated image
FONT_FACE = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.3
THICKNESS = 1
SAS_BLUE = (5, 74, 153)[::-1]  # SAS Blue (b,g,r)
MARGIN = 2

# Logging context name
LOGGING_CONTEXT = "DF.ESP.CUSTOM.CV_ANNOTATION"

# Supported values
SUPPORTED_PSEUDONYMIZATION = ["none", "black_bbox"]
SUPPORTED_IMAGE_ENCODING = ["wide", "jpg", "png"]

# Keep track of errors
error = False  # pylint: disable=invalid-name

SETTINGS = {}

# Colors are in RGB format, note that OpenCV uses BGR
# Colors taken from https://brand.sas.com/en/home/brand-assets/design-elements/color.html
COLORS = [
    [7, 102, 209],  # SAS Blue
    [217, 163, 11],  # Deep Yellow
    [204, 45, 45],  # Deep Red
    [6, 193, 204],  # Deep Teal
    [41, 184, 105],  # Deep Green
    [219, 18, 125],  # Viya Pink
    [0, 0, 0],  # Black
    [126, 136, 154],  # Slate
    [255, 255, 255],  # White
    [3, 41, 84],  # Midnight Blue
]


def init(settings):
    """Initializes the global SETTINGS configuration and validates the provided settings.

    Args:
        settings (dict): A dictionary containing configuration options.
            - `pseudonymization` (str): Pseudonymization setting. Must be one of `none` or `black_bbox`.
            - `input_image_encoding` (str): Specifies the input image encoding format. Must be in `SUPPORTED_IMAGE_ENCODING`.
            - `output_image_encoding` (str): Specifies the output image encoding format. Must be in `SUPPORTED_IMAGE_ENCODING`.
            - `object_label_separator` (str): Separator used for object labels. Cannot be an empty string.
            - `skeleton` (str, optional): Skeleton definition for keypoints. Only required when using keypoints.
            - `kpts_labels` (str, optional): Keypoint labels. Only required when using keypoints.
            - `show_keypoint_labels` (str, optional): Whether to show keypoint labels or not. Only required when using keypoints.
    """
    global SETTINGS
    global error

    if settings["pseudonymization"] not in SUPPORTED_PSEUDONYMIZATION:
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message=f"Pseudonymization setting `{settings['pseudonymization']}` is not supported. Must be either {','.join(SUPPORTED_PSEUDONYMIZATION)}",
            level="fatal",
        )
        error = True

    if settings["input_image_encoding"] not in SUPPORTED_IMAGE_ENCODING:
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message=f"Input image encoding `{settings['input_image_encoding']}` is not supported. Must be either {','.join(SUPPORTED_IMAGE_ENCODING)}",
            level="fatal",
        )
        error = True

    if settings["output_image_encoding"] not in SUPPORTED_IMAGE_ENCODING:
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message=f"Output image encoding `{settings['output_image_encoding']}` is not supported. Must be either {','.join(SUPPORTED_IMAGE_ENCODING)}",
            level="fatal",
        )
        error = True

    if settings["object_label_separator"] == "":
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message="Object label separator not set",
            level="fatal",
        )
        error = True

    if settings["kpts_labels"] == "":
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message="Keypoint labels are not set",
            level="info",
        )

    if not error:
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message=f"Using `{settings['pseudonymization']}` pseudonymization setting",
            level="info",
        )
        esp.logMessage(
            logcontext=LOGGING_CONTEXT,
            message=f"Using `{settings['input_image_encoding']}` (input) and `{settings['output_image_encoding']}` (output) image encoding",
            level="info",
        )
        if settings["kpts_labels"] != "":
            esp.logMessage(
                logcontext=LOGGING_CONTEXT,
                message=f"Using `{settings['kpts_labels']}` as keypoint labels",
                level="info",
            )
        SETTINGS = settings


def create(data, _):
    """Processes image data and generates an event with the annotated image.

    This function is called for every event.

    This function processes an input image based on the global `SETTINGS` configuration
    and annotates it using the `annotate` function. It converts the image to and from
    OpenCV format as needed and returns an event containing the annotated image.

    Args:
        data (dict): A dictionary containing the input data.
        context (any): Not used in this function.

    Returns:
        dict: A dictionary representing the event containing the annotated image.
            - `annotated_image`: The annotated image in blob format.
        None: If a fatal error is detected (`error` is set globally).
    """
    if error:
        return None

    if SETTINGS["input_image_encoding"] == "wide":
        image = esp_utils.image_conversion.sas_wide_image_to_opencv_image(data["image"])
    else:
        image = esp_utils.image_conversion.blob_image_to_opencv_image(data["image"])

    image = annotate(data, image)

    if SETTINGS["output_image_encoding"] == "wide":
        image = esp_utils.image_conversion.opencv_image_to_sas_wide_image(image)
    elif SETTINGS["output_image_encoding"] == "png":
        image = esp_utils.image_conversion.opencv_image_to_blob_image(
            image, type=".png"
        )
    else:
        image = esp_utils.image_conversion.opencv_image_to_blob_image(
            image, type=".jpeg"
        )

    event = {}
    event["annotated_image"] = image
    return event


def annotate(data, opencv_image):
    """Applies annotations to an OpenCV image for object detection and keypoint detection.

    This function annotates the given OpenCV image with bounding boxes, labels,
    and optionally, keypoints. When object tracking information is provided, this is shown as well and a different color is used for every object ID. The type and extent of annotations
    depend on the data provided.

    Args:
        data (dict): A dictionary containing the annotation data. Expected keys include:
            - `label` (str): Labels for detected objects.
            - `x`, `y`, `w`, `h` (list[float]): Top-left coordinates and dimensions of bounding boxes.
            - `score` (list[float]): Confidence scores for the detected objects.
            - `object_id` (list[int], optional): Unique IDs for the detected objects.
            - `object_track_kpts_x`, `object_track_kpts_y` (list[float], optional):
              Coordinates of keypoints for tracked objects.
            - `object_track_kpts_score` (list[float], optional): Confidence scores for keypoints.
            - `object_track_kpts_label_id` (list[int], optional): Label IDs for keypoints.
            - `object_track_count` (list[int], optional): Number of tracked objects.
            - `object_track_kpts_count` (list[int], optional): Number of keypoints per tracked object.
        opencv_image (numpy.ndarray): The input image in OpenCV format.

    Returns:
        numpy.ndarray: The annotated OpenCV image.

    Details:
        - Calls `annotate_object_detection` to apply object detection annotations.
        - Optionally calls `annotate_keypoints` to add keypoint annotations if keypoint data is provided.
    """

    if SETTINGS["pseudonymization"] == "black_bbox":
        if data["x"] is not None:
            for i in range(len(data["x"])):
                start_point = (int(data["x"][i]), int(data["y"][i]))
                end_point = (
                    int(data["x"][i] + data["w"][i]),
                    int(data["y"][i] + data["h"][i]),
                )
                cv2.rectangle(
                    opencv_image, start_point, end_point, (0, 0, 0), -1, cv2.LINE_AA
                )

    opencv_image = annotate_object_detection(
        opencv_image,
        data["label"],
        data["x"],
        data["y"],
        data["w"],
        data["h"],
        data["score"],
        None if "object_id" not in data else data["object_id"],
        None if "attribute" not in data else data["attribute"],
    )

    if "object_track_kpts_x" in data and data["x"] is not None:
        opencv_image = annotate_keypoints(
            opencv_image,
            len(data["x"]),
            None if "object_id" not in data else data["object_id"],
            None if "object_track_count" not in data else data["object_track_count"],
            data["object_track_kpts_count"],
            data["object_track_kpts_x"],
            data["object_track_kpts_y"],
            data["object_track_kpts_score"],
            data["object_track_kpts_label_id"],
        )
    return opencv_image


def pseudonymize_black_bbox(data, opencv_image):
    """Pseudonymizes the given OpenCV image by drawing black bounding boxes over specified regions."""
    for i in range(len(data["x"])):
        start_point = (int(data["x"][i]), int(data["y"][i]))
        end_point = (
            int(data["x"][i] + data["w"][i]),
            int(data["y"][i] + data["h"][i]),
        )
        cv2.rectangle(opencv_image, start_point, end_point, (0, 0, 0), -1, cv2.LINE_AA)
    return opencv_image


def annotate_object_detection(
    opencv_image, label, x, y, w, h, score, object_id=None, attrs=None
):
    """Annotates an OpenCV image with bounding boxes, labels, and confidence scores for object detection.

    This function draws bounding boxes around detected objects, with optional object IDs and
    confidence scores, and overlays the corresponding label for each object.

    Args:
        opencv_image (numpy.ndarray): The input image in OpenCV format to be annotated.
        label (str): A string containing object labels separated by the configured separator.
        x (list[float]): List of x-coordinates for the top-left corners of bounding boxes.
        y (list[float]): List of y-coordinates for the top-left corners of bounding boxes.
        w (list[float]): List of widths for the bounding boxes.
        h (list[float]): List of heights for the bounding boxes.
        score (list[float]): List of confidence scores for each detected object.
        object_id (list[int], optional): List of unique object IDs. If provided, IDs are included in the annotation. A different color is used for each object ID.
        attrs (str): A string containing attributes separated by the configured separator.

    Returns:
        numpy.ndarray: The annotated OpenCV image.
    """
    if x is None:  # return if no objects have been detected
        return opencv_image

    for i in range(len(x)):  # pylint: disable=consider-using-enumerate
        start_point = (int(x[i]), int(y[i]))
        end_point = (
            int(x[i] + w[i]),
            int(y[i] + h[i]),
        )

        text = ""
        if object_id is not None:
            text += f"#{object_id[i]} "

        text += f"{label.split(SETTINGS['object_label_separator'])[i]} ({score[i]*100:.0f}%)"
        if attrs is not None:
            text = text + f" > {attrs.split(SETTINGS['object_label_separator'])[i]}"
        if object_id is not None:
            color = get_color(int(object_id[i]) - 1)
        else:
            color = get_color(0)
        opencv_image = draw_bbox(opencv_image, start_point, end_point, text, color)
    return opencv_image


def draw_bbox(opencv_image, start_point, end_point, text, color):
    """Draws a bounding box with a label on an image.

    This function draws a rectangle around the specified region of an image and overlays
    a label with text above the bounding box.

    Args:
        opencv_image (numpy.ndarray): The input image in OpenCV format.
        start_point (tuple[int, int]): Coordinates (x, y) of the top-left corner of the bounding box.
        end_point (tuple[int, int]): Coordinates (x, y) of the bottom-right corner of the bounding box.
        text (str): The label text to be displayed above the bounding box.
        color (tuple[int, int, int]): The color of the bounding box in BGR format.

    Returns:
        numpy.ndarray: The image with the bounding box and label text drawn.

    Details:
        - If the average brightness of the box color is low, the text is drawn in white.
          Otherwise, it is drawn in black for better contrast.
        - A filled rectangle is drawn behind the text for readability.
    """

    cv2.rectangle(
        opencv_image, start_point, end_point, color, 1, cv2.LINE_AA
    )  # Draw bounding box

    # Use white text if the background is dark, and vice versa
    if sum(color) / 3 < 150:
        text_color = (255, 255, 255)  # (b,g,r)
    else:
        text_color = (0, 0, 0)  # (b,g,r)

    text_size = cv2.getTextSize(text, FONT_FACE, FONT_SCALE, THICKNESS)
    text_width = int(text_size[0][0])
    text_height = int(text_size[0][1])
    line_height = text_size[1]

    x_min, y_min = start_point
    text_x = x_min + MARGIN
    text_y = y_min - line_height - MARGIN

    # Draw a filled rectangle to place the text in
    cv2.rectangle(
        opencv_image,
        (text_x - MARGIN, text_y + line_height + MARGIN),
        (text_x + text_width + MARGIN, text_y - text_height - MARGIN),
        color,
        -1,
        cv2.LINE_AA,
    )

    # Add the text
    cv2.putText(
        opencv_image,
        text,
        (text_x, text_y),
        FONT_FACE,
        FONT_SCALE,
        text_color,
        THICKNESS,
        cv2.LINE_AA,
    )
    return opencv_image


def annotate_keypoints(
    opencv_image,
    n_objects,
    object_ids,
    object_track_count,
    object_track_kpts_count,
    object_track_kpts_x,
    object_track_kpts_y,
    object_track_kpts_score,
    object_track_kpts_label_id,
):
    """Annotates keypoints on an image.

    Each keypoint is marked with a circle with a
    text label. Only the last position of the keypoint track is drawn.

    Args:
        opencv_image (np.ndarray): The input image in OpenCV format to be annotated.
        n_objects (int): The number of objects to annotate.
        object_ids (list[int] | None): List of unique object IDs. If `None`, no object IDs are used.
        object_track_count (list[int] | None): List of the number of tracks per object.
            If `None`, assumes one track per object.
        object_track_kpts_count (list[int]): List of keypoint counts per track.
        object_track_kpts_x (list[float]): List of x-coordinates for all keypoints across tracks.
        object_track_kpts_y (list[float]): List of y-coordinates for all keypoints across tracks.
        object_track_kpts_score (list[float]): List of confidence scores for keypoints.
        object_track_kpts_label_id (list[int]): List of label IDs for keypoints.

    Returns:
        np.ndarray: The annotated OpenCV image.
    """
    kpts_count_pointer = 0
    # Get keypoints as list of lists for object
    offset = 0
    for o in range(n_objects):
        if object_ids is not None:
            object_id = int(object_ids[o])
        else:
            object_id = 1
        kpts_x = []
        kpts_y = []
        score = []
        label_id = []
        if object_track_count is None:
            number_of_tracks_object = 1
        else:
            number_of_tracks_object = object_track_count[o]
        for t in range(number_of_tracks_object):
            kpts_count = object_track_kpts_count[kpts_count_pointer]
            kpts_count_pointer += 1
            kpts_x.append(object_track_kpts_x[offset : offset + kpts_count])
            kpts_y.append(object_track_kpts_y[offset : offset + kpts_count])
            score.append(object_track_kpts_score[offset : offset + kpts_count])
            label_id.append(object_track_kpts_label_id[offset : offset + kpts_count])
            offset += kpts_count

        # Plot keypoints per object

        # Plot all keypoints in track
        # for t in range(number_of_tracks_object):
        # Plot last keypoints in track
        for t in [number_of_tracks_object - 1]:

            # Lines
            if SETTINGS["skeleton"] != "":
                for skeleton_pair in SETTINGS["skeleton"].split(","):
                    try:
                        sk_from = skeleton_pair.split("-")[0]
                        sk_to = skeleton_pair.split("-")[1]
                        sk_from_id = SETTINGS["kpts_labels"].split(",").index(sk_from)
                        sk_to_id = SETTINGS["kpts_labels"].split(",").index(sk_to)

                        pos_a = label_id[t].index(sk_from_id)
                        pos_b = label_id[t].index(sk_to_id)

                        start_point = (int(kpts_x[t][pos_a]), int(kpts_y[t][pos_a]))
                        end_point = (int(kpts_x[t][pos_b]), int(kpts_y[t][pos_b]))
                        opencv_image = cv2.line(
                            opencv_image,
                            start_point,
                            end_point,
                            get_color(object_id - 1),
                            1,
                            cv2.LINE_AA,
                        )
                    except ValueError:
                        pass

            for k in range(len(kpts_x[t])):
                if SETTINGS["kpts_labels"] != "":
                    label_name = SETTINGS["kpts_labels"].split(",")[label_id[t][k]]
                else:
                    label_name = ""

                # Use rectangle for right body parts and circle for left body parts
                if label_name.startswith("r_") or label_name.startswith("right_"):
                    cv2.rectangle(
                        opencv_image,
                        (int(kpts_x[t][k]) - 4, int(kpts_y[t][k]) - 4),
                        (int(kpts_x[t][k]) + 4, int(kpts_y[t][k]) + 4),
                        get_color(object_id - 1),
                        -1,
                        cv2.LINE_AA,
                    )
                else:
                    cv2.circle(
                        opencv_image,
                        (int(kpts_x[t][k]), int(kpts_y[t][k])),
                        4,
                        get_color(object_id - 1),
                        -1,
                        cv2.LINE_AA,
                    )

                if SETTINGS["show_keypoint_labels"] == "yes":
                    cv2.putText(
                        opencv_image,
                        label_name,
                        (int(kpts_x[t][k]), int(kpts_y[t][k])),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
    return opencv_image


def get_color(object_id):
    """Helper function to get a BGR color from a list of RGB colors."""
    return COLORS[object_id % len(COLORS)][
        ::-1
    ]  # Reverse the list to use BGR instead of RGB


_espconfig_ = {
    "inputVariables": {
        "desc": "Fields for image and object detection are required. Keypoints, object tracking, and attributes are optional.",
        "fields": [
            {
                "name": "image",
                "desc": "Input image (blob)",
                "esp_type": "blob",
                "optional": False,
            },
            {
                "name": "label",
                "desc": "Delimited list containing the class of the detected objects (string or rstring)",
                "esp_type": "any",
                "optional": False,
            },
            {
                "name": "x",
                "desc": "Top left X-coordinates of the bounding boxes (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": False,
            },
            {
                "name": "y",
                "desc": "Top left Y-coordinates of the bounding boxes (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": False,
            },
            {
                "name": "w",
                "desc": "Widths of the bounding boxes (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": False,
            },
            {
                "name": "h",
                "desc": "Heights of the bounding boxes (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": False,
            },
            {
                "name": "score",
                "desc": "Confidence scores array (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": False,
            },
            {
                "name": "object_id",
                "desc": "Unique object IDs from tracking, e.g., Object Tracker window (array(i32))",
                "esp_type": "array(i64)",
                "optional": True,
            },
            {
                "name": "attribute",
                "desc": "Delimited list of object attributes (string or rstring)",
                "esp_type": "any",
                "optional": True,
            },
            {
                "name": "object_track_count",
                "desc": "Number of tracks per detected object (array(i32))",
                "esp_type": "array(i32)",
                "optional": True,
            },
            {
                "name": "object_track_kpts_count",
                "desc": "Number of keypoints per detected object for the track (array(i32))",
                "esp_type": "array(i32)",
                "optional": True,
            },
            {
                "name": "object_track_kpts_x",
                "desc": "X-coordinates for the keypoints track (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": True,
            },
            {
                "name": "object_track_kpts_y",
                "desc": "Y-coordinates for the keypoints track (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": True,
            },
            {
                "name": "object_track_kpts_score",
                "desc": "Confidence scores for the keypoints track (array(dbl))",
                "esp_type": "array(dbl)",
                "optional": True,
            },
            {
                "name": "object_track_kpts_label_id",
                "desc": "Label IDs for the keypoints track (array(i32))",
                "esp_type": "array(i32)",
                "optional": True,
            },
            # {
            #     "name": "camera_id",
            #     "desc": "Camera ID",
            #     "esp_type": "string",
            #     "optional": True,
            # },
        ],
    },
    "outputVariables": {
        "desc": "Define an output field of type `blob` to store the annotated image. **Note:** If you use the same field name as your input image, the original will be overwritten.",
        "fields": [
            {
                "name": "annotated_image",
                "desc": "Annotated image (blob)",
                "esp_type": "blob",
            }
        ],
    },
    "settings": {
        "desc": "",
        "expand_parms": False,
        "process_blocks": False,
        "encode_binary": False,
    },
    "initialization": {
        "desc": "Configure the custom window options. **Important:** Use `png` or `jpg` for `output_image_encoding` to display images in Grafana. Use `wide` for optimal performance when staying within ESP.",
        "fields": [
            {
                "name": "input_image_encoding",
                "desc": "Input image encoding - must be one of the following: `wide`, `jpg`, `png`",
                "default": "wide",
                "input_type": "dropdown",
                "values": ["wide", "jpg", "png"],
            },
            {
                "name": "output_image_encoding",
                "desc": "Output image encoding - must be one of the following: `wide`, `jpg`, `png`",
                "default": "jpg",
                "input_type": "dropdown",
                "values": ["wide", "jpg", "png"],
            },
            {
                "name": "pseudonymization",
                "desc": "Pseudonymization setting - must be one of the following: `none`, `black_bbox`",
                "default": "none",
                "input_type": "dropdown",
                "values": ["none", "black_bbox"],
            },
            {
                "name": "object_label_separator",
                "desc": "Object label separator",
                "default": ",",
            },
            {
                "name": "kpts_labels",
                "desc": "Keypoint labels, comma separated, in the order of the label IDs. For example: `nose,l_eye,...`",
                "default": "",
            },
            {
                "name": "skeleton",
                "desc": "Skeleton definition for keypoints. For example: `nose-l_eye,nose-r_eye,...`",
                "default": "",
            },
            {
                "name": "show_keypoint_labels",
                "desc": "Whether to show keypoint labels or not",
                "default": "no",
                "input_type": "dropdown",
                "values": ["yes", "no"],
            },
        ],
    },
}
"""metadata start

{
    "name": "Computer Vision Annotation",
    "description": "Annotate the results of an object detection and/or a keypoint detection model.",
    "tags": [
        "computer_vision",
        "python"
    ],
    "versionNotes": "Initial version"
}
metadata end
"""
