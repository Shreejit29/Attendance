# mobile_webrtc_attendance.py

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import cv2
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students

RTC_CONFIG = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

# Global Attendance State
global_present = {}

# Global camera mode
if "camera_mode" not in st.session_state:
    st.session_state.camera_mode = "environment"   # default = back camera


def reset_attendance():
    global global_present
    students = load_students()
    global_present = {s["id"]: False for s in students}


def video_frame_callback(frame):
    global global_present

    img = frame.to_ndarray(format="bgr24")
    rgb = img[:, :, ::-1]

    detections = find_faces_in_image(rgb)
    students = load_students()

    # Draw boxes
    for emb, box in detections:
        x1, y1, x2, y2 = box

        # Mark present students
        for s in students:
            for st_emb in s["embeddings"]:
                sim = cosine_similarity(emb, st_emb)
                if sim > 0.55:
                    global_present[s["id"]] = True

        # Draw green square around face
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)

    return av.VideoFrame.from_ndarray(img, format="bgr24")


def mobile_webrtc_attendance_ui():
    st.subheader("📱 Mobile WebRTC Attendance (Front/Back Camera + Face Box)")

    # Camera flip button
    if st.button("🔄 Flip Camera (Front ↔ Back)"):
        st.session_state.camera_mode = (
            "user" if st.session_state.camera_mode == "environment" else "environment"
        )
        st.success(f"Camera switched to: **{st.session_state.camera_mode}** mode")

    st.info(f"📸 Current Camera: **{st.session_state.camera_mode}**")

    reset_attendance()

    webrtc_streamer(
        key="mobile-attendance",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIG,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={
            "video": {
                "facingMode": st.session_state.camera_mode   # front/back toggle
            },
            "audio": False
        },
    )

    # Finish Attendance
    if st.button("Finish Attendance"):
        return global_present, True

    return None, False
