import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import numpy as np
import cv2
from collections import deque
from scipy.spatial.distance import cdist

from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students


# ------------------------------
# Simple Multi-Face Tracker
# ------------------------------
class MultiFaceTracker:
    def __init__(self, max_lost=10):
        self.next_id = 0
        self.tracks = {}  # id -> track info
        self.max_lost = max_lost

    def register(self, box):
        self.tracks[self.next_id] = {
            "box": box,
            "lost": 0,
            "history": deque(maxlen=5),
        }
        self.next_id += 1

    def update(self, detected_boxes):
        if len(self.tracks) == 0:
            for box in detected_boxes:
                self.register(box)
            return self.tracks

        track_ids = list(self.tracks.keys())
        track_boxes = np.array([self.tracks[i]["box"] for i in track_ids])

        if len(detected_boxes) == 0:
            # increment lost counters
            for tid in track_ids:
                self.tracks[tid]["lost"] += 1
                if self.tracks[tid]["lost"] > self.max_lost:
                    del self.tracks[tid]
            return self.tracks

        detected_boxes_arr = np.array(detected_boxes)

        # compute distance matrix (centroid-based)
        def centroid(box):
            t, r, b, l = box
            return [(l + r) / 2, (t + b) / 2]

        track_centers = np.array([centroid(b) for b in track_boxes])
        detection_centers = np.array([centroid(b) for b in detected_boxes_arr])

        distances = cdist(track_centers, detection_centers)

        # greedy matching
        used_detects = set()
        for ti, tid in enumerate(track_ids):
            di = distances[ti].argmin()
            if di not in used_detects:
                self.tracks[tid]["box"] = tuple(detected_boxes_arr[di])
                self.tracks[tid]["lost"] = 0
                used_detects.add(di)
            else:
                self.tracks[tid]["lost"] += 1

        # remove lost tracks
        for tid in track_ids:
            if self.tracks[tid]["lost"] > self.max_lost:
                del self.tracks[tid]

        # register new detections
        for di, box in enumerate(detected_boxes):
            if di not in used_detects:
                self.register(box)

        return self.tracks


# ------------------------------
# Face Attendance Processor
# ------------------------------
class FaceAttendanceProcessor(VideoProcessorBase):
    def __init__(self):
        self.students = load_students()
        self.present = {s["id"]: False for s in self.students}

        self.tracker = MultiFaceTracker()
        self.face_assignments = {}  # track_id -> student_name

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        detections = find_faces_in_image(rgb)
        boxes = [d[1] for d in detections]

        # Track all face boxes
        tracked = self.tracker.update(boxes)

        # Recognize faces
        for (emb, detected_box) in detections:
            # find track ID for this face box
            for tid, track in tracked.items():
                if track["box"] == detected_box:

                    best_sim = 0
                    best_id = None
                    best_name = "Unknown"

                    for s in self.students:
                        for st_emb in s["embeddings"]:
                            sim = cosine_similarity(emb, st_emb)
                            if sim > 0.55 and sim > best_sim:
                                best_sim = sim
                                best_id = s["id"]
                                best_name = s["name"]

                    # store assignment for consistency across frames
                    self.face_assignments[tid] = best_name

                    if best_id:
                        self.present[best_id] = True

        # Draw boxes and labels
        for tid, track in tracked.items():
            (top, right, bottom, left) = track["box"]
            name = self.face_assignments.get(tid, "Unknown")

            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

            cv2.rectangle(img, (left, top), (right, bottom), color, 2)
            cv2.putText(img, f"{name} (ID:{tid})", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ------------------------------
# UI Wrapper
# ------------------------------
def live_webrtc_attendance_ui():
    st.subheader("📱 Live Mobile Camera Attendance (Multi-Face Tracking + WebRTC)")
    st.write("Use mobile browser → allow camera permissions → choose back/front camera.")

    # Camera selector
    cam_choice = st.selectbox(
        "Choose Camera",
        ["Front Camera", "Back Camera"],
        key="camera_choice"
    )

    # Apply facingMode
    constraints = {
        "video": {
            "facingMode": "user" if cam_choice == "Front Camera" else "environment"
        },
        "audio": False,
    }

    processor = FaceAttendanceProcessor()

    webrtc_streamer(
        key="live-attendance-webrtc-upgraded",
        video_processor_factory=lambda: processor,
        media_stream_constraints=constraints,
        async_processing=True,
    )

    # Finish button
    finish = st.button("Finish Attendance")

    if finish:
        return processor.present, True

    return None, False
