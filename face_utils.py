
---

# `face_utils.py`
```python
"""
face_utils.py
Helpers for loading images, encoding faces, and matching.
"""

import numpy as np
import face_recognition
import cv2
from typing import List, Tuple

def load_image_from_bytes(image_bytes: bytes):
    """Return RGB np.array from image bytes (Streamlit uploads)."""
    arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return img_rgb

def face_encodings_from_image(image_rgb) -> List[np.ndarray]:
    """Return list of face encodings from an RGB image."""
    # face_recognition works with RGB numpy arrays
    locations = face_recognition.face_locations(image_rgb, model="hog")
    encs = face_recognition.face_encodings(image_rgb, locations)
    return encs

def find_faces_in_class_image(image_rgb) -> List[Tuple[Tuple[int,int,int,int], np.ndarray]]:
    """Return list of tuples: (location, encoding) for each face in image."""
    locations = face_recognition.face_locations(image_rgb, model="hog")
    encs = face_recognition.face_encodings(image_rgb, locations)
    return list(zip(locations, encs))

def match_encoding(known_encodings: List[np.ndarray], target_encoding: np.ndarray, tolerance=0.5):
    """
    Compare a single target encoding to known encodings.
    Returns index of best match or None.
    """
    if not known_encodings:
        return None
    distances = face_recognition.face_distance(known_encodings, target_encoding)
    best_idx = np.argmin(distances)
    if distances[best_idx] <= tolerance:
        return int(best_idx)
    return None

def draw_bounding_boxes(image_rgb, face_locations, labels=None):
    """Draw boxes & labels on image (RGB numpy array). Returns BGR encoded bytes suitable for Streamlit image display."""
    img = cv2.cvtColor(image_rgb.copy(), cv2.COLOR_RGB2BGR)
    for i, loc in enumerate(face_locations):
        top, right, bottom, left = loc
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
        if labels and i < len(labels):
            cv2.putText(img, labels[i], (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    # convert back to RGB for streamlit
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
