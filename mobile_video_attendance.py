# mobile_video_attendance.py

import cv2
import streamlit as st
import numpy as np
import time
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students


def start_mobile_ip_attendance(ip_url, frame_skip=5, duration=20):
    """
    ip_url: http://<IP>:<PORT>/video
    frame_skip: process every X frames
    duration: total seconds to scan
    """

    stframe = st.empty()  # Live display

    cap = cv2.VideoCapture(ip_url)

    if not cap.isOpened():
        st.error("❌ Could not connect to mobile camera stream.")
        return None

    students = load_students()
    present = {s["id"]: False for s in students}

    start_time = time.time()
    frame_count = 0

    st.success("📱 Mobile camera connected! Detecting attendance...")

    while True:
        ret, frame = cap.read()
        if not ret:
            st.error("❌ Lost connection to mobile camera.")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if frame_count % frame_skip == 0:
            detections = find_faces_in_image(frame_rgb)

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

        stframe.image(frame_rgb, use_column_width=True)

        frame_count += 1

        if time.time() - start_time > duration:
            break

    cap.release()
    return present


def mobile_attendance_ui():
    st.subheader("📱 Mobile Camera Attendance (IP Webcam)")

    st.info("Use any Mobile IP Webcam app and paste the video URL below.")

    ip_url = st.text_input(
        "Enter Mobile Camera Stream URL",
        placeholder="e.g., http://192.168.1.5:8080/video"
    )

    duration = st.slider("Scan Duration (seconds)", 10, 60, 20)

    if st.button("Start Mobile Attendance"):
        if not ip_url:
            st.error("Enter your mobile IP webcam link.")
            return None, False

        present = start_mobile_ip_attendance(ip_url, frame_skip=3, duration=duration)
        if present is None:
            return None, False

        return present, True

    return None, False
