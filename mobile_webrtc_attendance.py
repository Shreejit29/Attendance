# mobile_webrtc_attendance.py

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students

RTC_CONFIG = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

# Global attendance dictionary during session
global_present = {}

def reset_attendance():
    global global_present
    students = load_students()
    global_present = {s["id"]: False for s in students}


def video_frame_callback(frame):
    global global_present

    img = frame.to_ndarray(format="bgr24")
    rgb = img[:, :, ::-1]

    # Detect faces
    detections = find_faces_in_image(rgb)
    students = load_students()

    for emb, _ in detections:
        for s in students:
            for st_emb in s["embeddings"]:
                sim = cosine_similarity(emb, st_emb)
                if sim > 0.55:
                    global_present[s["id"]] = True

    return av.VideoFrame.from_ndarray(img, format="bgr24")


def mobile_webrtc_attendance_ui():
    st.subheader("📱 WebRTC Mobile Camera Attendance")

    reset_attendance()

    st.info("Open this Streamlit app on your MOBILE browser. Then allow camera access.")

    webrtc_streamer(
        key="mobile-attendance",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIG,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
    )

    if st.button("Finish Attendance"):
        return global_present, True

    return None, False
