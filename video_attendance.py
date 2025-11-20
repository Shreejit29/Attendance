# video_attendance.py
import cv2
import streamlit as st
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students

def process_video(video_bytes, frame_interval=30):
    """
    video_bytes: uploaded video file bytes
    frame_interval: extract 1 frame every X frames (default = 30)
    Returns: 
        detected_faces -> dict { student_id: True/False }
        frames_preview -> list of (frame_image_rgb, labels)
    """

    # Save the video temporarily
    temp_video_path = "temp_video.mp4"
    with open(temp_video_path, "wb") as f:
        f.write(video_bytes)

    cap = cv2.VideoCapture(temp_video_path)
    if not cap.isOpened():
        st.error("Could not open video.")
        return {}, []

    students = load_students()
    present = {s["id"]: False for s in students}

    frames_preview = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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

            frames_preview.append((frame_rgb, labels))

        frame_count += 1

    cap.release()

    return present, frames_preview


def video_attendance_ui():
    """
    Streamlit user interface for taking attendance from video.
    Returns attendance dict and preview frames.
    """
    st.subheader("🎥 Take Attendance From Video")

    video_file = st.file_uploader("Upload Video (mp4/mov/avi)", type=["mp4", "mov", "avi"])

    frame_interval = st.number_input(
        "Extract 1 frame every X frames:", 
        min_value=10, 
        max_value=200, 
        value=30
    )

    if video_file:
        if st.button("Process Video"):
            st.info("Processing video... please wait.")

            present, previews = process_video(video_file.getvalue(), frame_interval)

            st.success("Video processed successfully!")

            # Show preview frames
            st.subheader("Preview Detected Frames")
            for img, labels in previews[:10]:  # first 10 frames only
                st.image(img, caption=", ".join(labels), use_column_width=True)

            return present, True

    return None, False
