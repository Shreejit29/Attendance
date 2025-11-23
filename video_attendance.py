# video_attendance.py (uses temp file on disk; stable)
import cv2
import streamlit as st
import numpy as np
from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students
import tempfile
import os

def process_video(video_bytes, frame_interval=30):
    fd, temp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    with open(temp_path, "wb") as f:
        f.write(video_bytes)

    cap = cv2.VideoCapture(temp_path)
    if not cap.isOpened():
        return {}, []

    students = load_students()
    present = {s["id"]: False for s in students}
    previews = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detections = find_faces_in_image(rgb)
            labels = []
            for emb, box in detections:
                best_name = "Unknown"
                best_id = None
                best_sim = 0
                for s in students:
                    for st_emb in s.get("embeddings", []):
                        sim = cosine_similarity(emb, st_emb)
                        if sim > 0.55 and sim > best_sim:
                            best_sim = sim
                            best_name = s["name"]
                            best_id = s["id"]
                if best_id:
                    present[best_id] = True
                labels.append(best_name)
            previews.append((rgb, labels))
        frame_count += 1

    cap.release()
    try:
        os.remove(temp_path)
    except:
        pass
    return present, previews


def video_attendance_ui():
    st.subheader("🎥 Take Attendance From Video")
    video_file = st.file_uploader("Upload Video (mp4/mov/avi)", type=["mp4", "mov", "avi"])
    frame_interval = st.number_input("Extract 1 frame every X frames:", min_value=10, max_value=200, value=30)
    if video_file and st.button("Process Video"):
        st.info("Processing video — this may take a while.")
        present, previews = process_video(video_file.getvalue(), frame_interval)
        st.success("Video processed.")
        st.subheader("Preview Detected Frames")
        for img, labels in previews[:10]:
            st.image(img, caption=", ".join(labels), use_column_width=True)
        return present, True
    return None, False
