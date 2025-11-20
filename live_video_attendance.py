# live_video_attendance.py

import cv2
import streamlit as st
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students
from datetime import datetime
import time

def start_live_attendance(frame_skip=5):
    """
    Live webcam attendance.
    frame_skip -> detect face every X frames (to reduce CPU load)
    Returns: final present dictionary
    """

    stframe = st.empty()  # For live video display

    students = load_students()
    present = {s["id"]: False for s in students}

    cap = cv2.VideoCapture(0)  # Open webcam

    if not cap.isOpened():
        st.error("❌ Could not open webcam.")
        return present

    st.success("🎥 Webcam started! Detection running...")

    frame_count = 0

    start_time = time.time()
    session_duration = 20  # seconds of live attendance

    with st.spinner("Processing live attendance..."):
        while True:

            ret, frame = cap.read()
            if not ret:
                st.error("❌ Video frame capture failed.")
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Only detect every X frames
            if frame_count % frame_skip == 0:
                detections = find_faces_in_image(frame_rgb)

                labels = []

                for emb, box in detections:
                    best_name = "Unknown"
                    best_sim = 0

                    for s in students:
                        for st_emb in s["embeddings"]:
                            sim = cosine_similarity(emb, st_emb)
                            if sim > 0.55 and sim > best_sim:
                                best_sim = sim
                                best_name = s["name"]
                                present[s["id"]] = True

                    labels.append(best_name)

            # Display live frames
            stframe.image(frame_rgb, channels="RGB", use_column_width=True)

            frame_count += 1

            # stop session after 20 seconds
            if time.time() - start_time > session_duration:
                break

    cap.release()
    return present


def live_attendance_ui():
    """
    UI wrapper for Streamlit live attendance.
    """

    st.subheader("📡 Live Video Attendance (Webcam)")

    duration = st.slider("Select session duration (seconds)", 10, 60, 20)
    st.info("The webcam will run live and automatically mark present students.")

    if st.button("Start Live Attendance"):
        st.warning("📸 Webcam starting... allow browser permission.")

        present = start_live_attendance(frame_skip=4)

        return present, True

    return None, False
