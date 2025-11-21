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

# Global variables
global_present = {}
camera_mode = "environment"     # default: BACK CAMERA


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

    for emb, _ in detections:
        for s in students:
            for st_emb in s["embeddings"]:
                sim = cosine_similarity(emb, st_emb)
                if sim > 0.55:
                    global_present[s["id"]] = True

    return av.VideoFrame.from_ndarray(img, format="bgr24")


def mobile_webrtc_attendance_ui():
    global camera_mode

    st.subheader("📱 Mobile WebRTC Attendance (Front/Back Camera Toggle)")

    st.info("Open this Streamlit app on your mobile browser. Allow camera access.")

    reset_attendance()

    # -----------------------------------------
    # CAMERA FLIP BUTTON
    # -----------------------------------------
    if st.button("🔁 Flip Camera"):
        camera_mode = "user" if camera_mode == "environment" else "environment"
        st.success(f"Switched to: **{camera_mode.upper()}** camera")

    st.write(f"🎥 Using **{camera_mode.upper()}** camera")

    # -----------------------------------------
    # START WEBRTC STREAM WITH SELECTED CAMERA
    # -----------------------------------------
    webrtc_streamer(
        key=f"mobile-attendance-{camera_mode}",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIG,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={
            "video": {
                "facingMode": camera_mode
            },
            "audio": False
        },
    )

    if st.button("Finish Attendance"):
        return global_present, True

    return None, False
