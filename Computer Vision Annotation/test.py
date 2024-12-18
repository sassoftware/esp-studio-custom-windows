"""This file can be used to test the computer vision annotation custom window.

It uses data collected from ESP via a File and Socket subscriber. It
uses data from w_postprocess and w_object_tracker from this example: https://github.com/sassoftware/esp-studio-examples/tree/main/Advanced/onnx_pose_estimation. This example uses a YOLOv7 Pose ONNX model.
"""

import inspect
import base64
import unittest
import numpy as np
import cv2
import pandas as pd
import annotation

annotation.SETTINGS = {
    "image_encoding": "jpg",
    "object_label_separator": ",",
    "kpts_labels": "nose,l_eye,r_eye,l_ear,r_ear,l_shoulder,r_shoulder,l_elbow,r_elbow,l_wrist,r_wrist,l_hip,r_hip,l_knee,r_knee,l_ankle,r_ankle",
}
espconfig = annotation._espconfig_  # pylint: disable=protected-access


class TestAnnotationCustomWindow(unittest.TestCase):
    """Parent class to test the custom window."""

    def process_and_validate_frame(self, df):
        """Helper function to process and validate frames."""
        for _, data in df.iterrows():  # Loop over all rows of the DataFrame
            frame = base64_string_to_opencv(
                data["image"]
            )  # base64 string of the DataFrame to an OpenCV frame
            expected_shape = frame.shape
            annotated_frame = annotation.annotate(
                data, frame
            )  # Annotate the frame with the data - this is what the custom window does
            write_frame(annotated_frame)  # Write the output to disk
            height, width = annotated_frame.shape[:2]
            self.assertGreater(height, 0, "Expected height > 0")
            self.assertGreater(width, 0, "Expected width > 0")
            self.assertEqual(
                annotated_frame.shape, expected_shape, "Expected shape not correct"
            )
            self.assertEqual(
                annotated_frame.dtype, np.uint8, "Output data type not uint8"
            )


class TestArrayRectObjectTracker(TestAnnotationCustomWindow):
    """Unit test class for testing annotation of object tracker data that has been written to a CSV file."""

    def setUp(self):
        """Sets up a data frame that is used for every test.

        The data frame is re-
        created before every test.

        The method works as follows:
        - Create a dataframe by reading from a CSV file. This CSV file has been created by subscribing to an Object Tracker window using a File and Socket subscriber.
        - Convert string representations of arrays into lists of appropriate types (integers or floats).
        - Rename columns to match the _espconfig_ inputs (variable mapping)
        - Drop unused columns
        - Check if all required fields have been set

        Attributes:
            df (pd.DataFrame): The DataFrame containing the object tracking data
                                with correct column names and data types.

        Raises:
            FileNotFoundError: If the specified CSV file does not exist at the provided path.
            ValueError: If there is an issue with the `set_and_check_mapping` function.
        """
        df = pd.read_csv(
            "test_files/array_rect_object_tracker_frame_id_180_pingpong.csv",
            converters={
                "Object_id": lambda x: csv_string_to_list(x, int),
                "Object_x": lambda x: csv_string_to_list(x, float),
                "Object_y": lambda x: csv_string_to_list(x, float),
                "Object_w": lambda x: csv_string_to_list(x, float),
                "Object_h": lambda x: csv_string_to_list(x, float),
                "Object_score": lambda x: csv_string_to_list(x, float),
                "Object_track_count": lambda x: csv_string_to_list(x, int),
                "Object_track_kpts_count": lambda x: csv_string_to_list(x, int),
                "Object_track_kpts_x": lambda x: csv_string_to_list(x, float),
                "Object_track_kpts_y": lambda x: csv_string_to_list(x, float),
                "Object_track_kpts_score": lambda x: csv_string_to_list(x, float),
                "Object_track_kpts_label_id": lambda x: csv_string_to_list(x, int),
            },
        )
        df = df.rename(
            columns={
                "image": "image",
                "Object_label": "label",
                "Object_x": "x",
                "Object_y": "y",
                "Object_w": "w",
                "Object_h": "h",
                "Object_score": "score",
                "Object_id": "object_id",
                "Object_track_count": "object_track_count",
                "Object_track_kpts_count": "object_track_kpts_count",
                "Object_track_kpts_x": "object_track_kpts_x",
                "Object_track_kpts_y": "object_track_kpts_y",
                "Object_track_kpts_score": "object_track_kpts_score",
                "Object_track_kpts_label_id": "object_track_kpts_label_id",
            }
        )

        df = drop_unused_columns(df)
        df = check_mapping(df)
        self.df = df

    def test_ot_keypoints_object_id(self):
        """Tests the annotation process for object keypoints and object ID."""
        df = self.df
        self.process_and_validate_frame(df)

    def test_ot_no_keypoints(self):
        """Tests the annotation process without object keypoints, but with an object ID."""
        df = self.df.drop(["object_track_kpts_x"], axis=1)
        self.process_and_validate_frame(df)

    def test_ot_no_keypoints_no_object_id(self):
        """Tests the annotation process without object keypoints and object ID."""
        df = self.df.drop(["object_track_kpts_x", "object_id"], axis=1)
        self.process_and_validate_frame(df)

    def test_no_detections(self):
        """Tests the annotation process without any detections."""
        df = self.df
        # Simulate not having any detections
        df["x"] = np.empty((len(df), 0)).tolist()  # Empty list
        df["y"] = np.empty((len(df), 0)).tolist()
        df["w"] = np.empty((len(df), 0)).tolist()
        df["h"] = np.empty((len(df), 0)).tolist()
        self.process_and_validate_frame(df)


class TestArrayRectPostprocessing(TestAnnotationCustomWindow):
    """Unit test class for testing annotation of postprocessed data that has been written to a CSV file."""

    def setUp(self):
        """See TestArrayRectObjectTracker.setUp()."""

        df = pd.read_csv(
            "test_files/array_rect_postprocessing_frame_id_180_pingpong.csv",
            converters={
                "Object_x": lambda x: csv_string_to_list(x, float),
                "Object_y": lambda x: csv_string_to_list(x, float),
                "Object_width": lambda x: csv_string_to_list(x, float),
                "Object_height": lambda x: csv_string_to_list(x, float),
                "Object_score": lambda x: csv_string_to_list(x, float),
                "Object_kpts_count": lambda x: csv_string_to_list(x, int),
                "Object_kpts_x": lambda x: csv_string_to_list(x, float),
                "Object_kpts_y": lambda x: csv_string_to_list(x, float),
                "Object_kpts_score": lambda x: csv_string_to_list(x, float),
                "Object_kpts_label_id": lambda x: csv_string_to_list(x, int),
            },
        )
        df = df.rename(
            columns={
                "image": "image",
                "Object_labels": "label",
                "Object_x": "x",
                "Object_y": "y",
                "Object_width": "w",
                "Object_height": "h",
                "Object_score": "score",
                "Object_kpts_count": "object_track_kpts_count",
                "Object_kpts_x": "object_track_kpts_x",
                "Object_kpts_y": "object_track_kpts_y",
                "Object_kpts_score": "object_track_kpts_score",
                "Object_kpts_label_id": "object_track_kpts_label_id",
            }
        )

        df = drop_unused_columns(df)
        df = check_mapping(df)
        self.df = df

    def test_pp_keypoints_attributes(self):
        """Tests the annotation process with keypoints and attributes."""
        df = self.df
        df["attribute"] = "playing,playing"
        self.process_and_validate_frame(df)

    def test_pp_keypoints(self):
        """Tests the annotation process with keypoints."""
        df = self.df
        self.process_and_validate_frame(df)

    def test_pp_no_keypoints(self):
        """Tests the annotation process without keypoints (just object detections)."""
        df = self.df.drop(["object_track_kpts_x"], axis=1)
        self.process_and_validate_frame(df)


# def show_frame(frame):
#     cv2.imshow(inspect.stack()[2][3], frame)
#     while cv2.waitKey(0) & 0xFF == ord("q"):
#         break


def write_frame(frame):
    """Write a frame to the test_output folder for manual testing."""
    cv2.imwrite(f"test_output/{inspect.stack()[2][3]}.jpg", frame)


def drop_unused_columns(df):
    """Drops unused columns from a DataFrame based on the _espconfig_ input variables.

    This function removes columns from the input DataFrame that are not listed in the
    `_espconfig_["inputVariables"]["fields"]` field of the custom window code.

    Args:
        df (pandas.DataFrame): The DataFrame from which unused columns will be dropped.

    Returns:
        pandas.DataFrame: A new DataFrame with only the columns specified in
        `_espconfig_["inputVariables"]["fields"]`.
    """
    input_field_names = [d["name"] for d in espconfig["inputVariables"]["fields"]]
    columns_to_drop = list(set(df.columns).difference(set(input_field_names)))
    print(f"Dropping {columns_to_drop} from CSV")
    return df.drop(columns_to_drop, axis=1)


def check_mapping(df):
    """Checks the mapping between DataFrame columns and expected input variables for the custom window.

    It identifies missing columns, both optional and required, and raises
    an error if any required columns are missing.

    Args:
        df (pandas.DataFrame): The DataFrame to check for column mappings.

    Returns:
        pandas.DataFrame: The input DataFrame if all required columns are present.

    Raises:
        ValueError: If any required columns are missing from the DataFrame.
    """
    required_input_fields = list(
        filter(lambda d: not d["optional"], espconfig["inputVariables"]["fields"])
    )
    input_field_names = [d["name"] for d in espconfig["inputVariables"]["fields"]]
    input_required_field_names = [d["name"] for d in required_input_fields]
    missing_columns = list(set(input_field_names).difference(set(df.columns)))
    print(f"Missing the following fields in the CSV: {missing_columns}")
    missing_required_columns = list(
        set(input_required_field_names).difference(set(df.columns))
    )
    print(
        f"Missing the following required fields in the CSV: {missing_required_columns}"
    )
    if len(missing_required_columns) > 0:
        raise ValueError("Missing required columns")
    return df


def csv_string_to_list(string, output_type=int):
    """Pandas converter to convert an array(i32) or array(dbl) in ESP that was written to a CSV file (e.g., '["1"; "2"; "3"]') into a Python list of integers or floats.

    Args:
        string (str): A string representation of a list of values, where the values are
                 separated by semicolons (e.g., '[1;2;3]' or '[1.1;2.2;3.3]').
                 The input may also be an empty string or '[]', in which case
                 the function returns an empty list.
        output_type (type, optional): The type to which each element in the list
                                       should be converted. This can either be `int`
                                       (default) or `float`.

    Returns:
        list[Union[int, float]]: A list of values (either integers or floats).
                                 If the input string is empty or '[]', an empty list
                                 is returned.
    """
    return (
        list(map(output_type, string.strip("[]").replace("'", "").split(";")))
        if string != "" and string != "[]"
        else []
    )


def base64_string_to_opencv(frame):
    """Converts a base64 encoded image (string) to an OpenCV frame.

    Args:
        frame (string): Base64 encoded image

    Returns:
        numpy.ndarray: OpenCV frame
    """
    frame = base64.b64decode(frame)
    frame = np.frombuffer(frame, dtype=np.uint8)
    return cv2.imdecode(frame, cv2.IMREAD_COLOR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
