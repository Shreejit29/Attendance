# live_webrtc_attendance.py (basic)
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import cv2
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students

class SimpleProcessor(VideoProcessorBase):
    def __init__(self):
        self.students = load_students()
        self.present = {s["id"]: False for s in self.students}

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        detections = find_faces_in_image(rgb)
        for emb, _ in detections:
            for s in self.students:
                for st_emb in s.get("embeddings", []):
                    sim = cosine_similarity(emb, st_emb)
                    if sim > 0.55:
                        self.present[s["id"]] = True
        # draw little overlay
        return av.VideoFrame.from_ndarray(img, format="bgr24")

def live_webrtc_attendance_ui():
    st.subheader("📱 Live Mobile Camera Attendance")
    processor = SimpleProcessor()
    webrtc_streamer(key="webrtc-att", video_processor_factory=lambda: processor, media_stream_constraints={"video": True, "audio": False})
    if st.button("Finish Attendance"):
        return processor.present, True
    return None, False
