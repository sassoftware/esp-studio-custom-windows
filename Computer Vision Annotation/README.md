# Computer Vision Annotation Custom Window

This custom window enables you to annotate the results of an object detection model or a pose (keypoint) detection model. This enables you to visualize the results of the model. The custom window annotates the bounding boxes of object detections and adds circles for the keypoints. For object detections, the custom window also displays the detected class and probability. If object tracking information is available, the object ID is also displayed. Each object ID is displayed in a different color.

## Installation
Upload the `annotation.py` configuration file to SAS Event Stream Processing Studio. For more information, see [Upload a Configuration File](https://documentation.sas.com/?cdcId=espcdc&cdcVersion=default&docsetId=espstudio&docsetTarget=n1s1yakz9sl8upn1h9w2w7ba2mao.htm#p0a64jblkf46y4n1hofcs1ikonrz) in SAS Help Center. 

## Example Output

![](img/test_ot_keypoints_object_id.jpg)

## Usage

<!--start_of_usage-->
### Input Variables
Fields related to image and object detection are required. Fields related to keypoints are optional. Object ID (for object tracking) and attributes are also optional.

| Name                       | Description                                                              |Type          | Required or Optional   |
|:---------------------------|:-------------------------------------------------------------------------|:-----------  |:-----------------------|
| `image`                     | Input image                                                             |`blob`        | Required               |
| `label`                      | Delimited list containing the class of the detected objects            |`string`      | Required               |
| `x`                          | Top left X-coordinates of the bounding boxes                           |`array(dbl)`  | Required               |
| `y`                          | Top left Y-coordinates of the bounding boxes                           |`array(dbl)`  | Required               |
| `w`                          | Widths of the bounding boxes                                           |`array(dbl)`  | Required               |
| `h`                          | Heights of the bounding boxes                                          |`array(dbl)`  | Required               |
| `score`                      | Confidence scores array                                                |`array(dbl)`  | Required               |
| `object_id`                  | Tracked object ID, for example from the Object Tracker window          |`array(i32)`  | Optional               |
| `attribute`                  | Delimited list containing the attributes of the detected objects       |`string`      | Optional               |
| `object_track_count`         | Number of tracks per detected object                                   |`array(i32)`  | Optional               |
| `object_track_kpts_count`    | Number of keypoints per detected object for the track                  |`array(i32)`  | Optional               |
| `object_track_kpts_x`        | X-coordinates for the keypoints track                                  |`array(dbl)`  | Optional               |
| `object_track_kpts_y`        | Y-coordinates for the keypoints track                                  |`array(dbl)`  | Optional               |
| `object_track_kpts_score`    | Confidence scores for the keypoints track                              |`array(dbl)`  | Optional               |
| `object_track_kpts_label_id` | Label IDs for the keypoints track                                      |`array(i32)`  | Optional               |

### Output Variables
Add an output field, of type `blob`, to store the annotated image. If you use the same image as used in the input variables, the original image is overwritten with an annotated image.

| Name            | Description            | Type   |
|:----------------|:-----------------------|:-------|
| `annotated_image` | Annotated image      |`blob`  |

### Initialization
Set the options for the custom window. Note that either `png` or `jpg` is needed as the value for `output_image_encoding` to display images in Grafana.

| Name                   | Description                                                          | Default   |
|:-----------------------|:---------------------------------------------------------------------|:----------|
| `input_image_encoding`   | Input image encoding - must be one of the following: `wide`, `jpg`, `png`  | `wide`      |
| `output_image_encoding`  | Output image encoding - must be one of the following: `wide`, `jpg`, `png` | `jpg`       |
| `object_label_separator` | Object label separator                                               | `,`         |
| `kpts_labels`            | Keypoint labels                                                      |           |

<!--end_of_usage-->

An example value for `kpts_labels` is `nose,l_eye,r_eye,l_ear,r_ear,l_shoulder,r_shoulder,l_elbow,r_elbow,l_wrist,r_wrist,l_hip,r_hip,l_knee,r_knee,l_ankle,r_ankle` for YOLOv7 Pose.

## Development

### Real-life Test
This custom window has been tested using the [Pose Estimation Using an ONNX Model (YOLO Pose Version 7)](https://github.com/sassoftware/esp-studio-examples/tree/main/Advanced/onnx_pose_estimation) example. 

### Unit Tests

In the root directory, run

```
python -m unittest discover -v -b
```

The `test_output/` folder will contain the output of the tests.

### Docstrings

The docstrings are formatted with `pydocstringformatter`.

- Install: `pip install --upgrade pydocstringformatter`
- Usage: `pydocstringformatter -w --no-final-period --no-capitalize-first-letter *.py`


### Future Ideas
- Write outcomes to JPG or MP4 files, by using a subscriber connector
