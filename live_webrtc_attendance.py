import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import numpy as np
import cv2
from collections import deque
from scipy.spatial.distance import cdist

from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students


# ============================================================
# MULTI-FACE TRACKER (Improved)
# ============================================================
class MultiFaceTracker:
    def __init__(self, max_lost=10):
        self.next_id = 0
        self.tracks = {}  # track_id → data
        self.max_lost = max_lost

    def _centroid(self, box):
        # box = [x1, y1, x2, y2]
        x1, y1, x2, y2 = box
        return [(x1 + x2) / 2, (y1 + y2) / 2]

    def register(self, box):
        self.tracks[self.next_id] = {
            "box": box,
            "lost": 0,
            "history": deque(maxlen=5),
        }
        self.next_id += 1

    def update(self, detected_boxes):
        if len(self.tracks) == 0:
            for b in detected_boxes:
                self.register(b)
            return self.tracks

        track_ids = list(self.tracks.keys())
        track_boxes = np.array([self.tracks[i]["box"] for i in track_ids])

        # If no detections: increment lost counters
        if len(detected_boxes) == 0:
            for tid in track_ids:
                self.tracks[tid]["lost"] += 1
                if self.tracks[tid]["lost"] > self.max_lost:
                    del self.tracks[tid]
            return self.tracks

        # Convert for distance computation
        detected_boxes_arr = np.array(detected_boxes)

        # Centroids
        track_centers = np.array([self._centroid(b) for b in track_boxes])
        detect_centers = np.array([self._centroid(b) for b in detected_boxes_arr])

        # Distances
        distances = cdist(track_centers, detect_centers)

        used_detects = set()

        # Greedy matching
        for ti, tid in enumerate(track_ids):
            di = distances[ti].argmin()

            if di not in used_detects:
                self.tracks[tid]["box"] = tuple(detected_boxes_arr[di])
                self.tracks[tid]["lost"] = 0
                used_detects.add(di)
            else:
                self.tracks[tid]["lost"] += 1

        # Remove lost tracks
        for tid in track_ids:
            if self.tracks[tid]["lost"] > self.max_lost:
                del self.tracks[tid]

        # Register new detections
        for di, b in enumerate(detected_boxes):
            if di not in used_detects:
                self.register(b)

        return self.tracks


# ============================================================
# VIDEO PROCESSOR
# ============================================================
class FaceAttendanceProcessor(VideoProcessorBase):
    def __init__(self):
        self.students = load_students()  # STREAMLIT STORAGE
        self.present = {s["id"]: False for s in self.students}

        self.tracker = MultiFaceTracker(max_lost=15)
        self.face_assignments = {}  # track_id → student_name

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # detect: (embedding, bbox)
        detections = find_faces_in_image(rgb)
        detected_boxes = [d[1] for d in detections]

        # Track faces
        tracked = self.tracker.update(detected_boxes)

        # Recognize faces
        for emb, box in detections:
            # match detection to correct track_id
            for tid, tr in tracked.items():
                if tr["box"] == tuple(box):

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

                    self.face_assignments[tid] = best_name

                    if best_id:
                        self.present[best_id] = True

        # Draw
        for tid, tr in tracked.items():
            x1, y1, x2, y2 = tr["box"]
            name = self.face_assignments.get(tid, "Unknown")

            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, f"{name}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, color, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ============================================================
# UI WRAPPER
# ============================================================
def live_webrtc_attendance_ui():
    st.subheader("📱 Live Mobile Camera Attendance (WebRTC + Multi-Face Tracking)")
    st.write("Open on mobile browser → Allow camera → Use back/front camera.")

    cam_choice = st.selectbox(
        "Choose Camera",
        ["Front Camera", "Back Camera"],
        key="camera_select"
    )

    constraints = {
        "video": {
            "facingMode": "user" if cam_choice == "Front Camera" else "environment"
        },
        "audio": False,
    }

    processor = FaceAttendanceProcessor()

    webrtc_streamer(
        key="webrtc-attendance",
        video_processor_factory=lambda: processor,
        media_stream_constraints=constraints,
        async_processing=True
    )

    if st.button("Finish Attendance"):
        return processor.present, True

    return None, False
