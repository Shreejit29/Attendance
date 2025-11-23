# ============================================================
# video_attendance.py — FINAL STREAMLIT STORAGE API VERSION
# ============================================================

import cv2
import streamlit as st
import numpy as np

from face_utils import find_faces_in_image, cosine_similarity
from storage import load_students


# ------------------------------------------------------------
# Process uploaded video (NO disk writes)
# ------------------------------------------------------------
def process_video(video_bytes, frame_interval=30):
    """
    Process uploaded video entirely in memory.
    Extracts frames at given intervals and performs face recognition.

    Returns:
        present -> {student_id: True/False}
        previews -> list of (frame_rgb, labels)
    """

    # Convert bytes to numpy array → OpenCV video stream
    video_array = np.frombuffer(video_bytes, dtype=np.uint8)
    video = cv2.imdecode(video_array, cv2.IMREAD_ANYCOLOR)

    # 👇 CV2 cannot decode video directly from bytes → we must write to memory buffer
    # Workaround: Write temporary memory-based video using cv2.VideoCapture with file-like buffer
    # Final stable solution:
    temp_path = "temp_video_stream.mp4"
    with open(temp_path, "wb") as f:
        f.write(video_bytes)

    cap = cv2.VideoCapture(temp_path)
    if not cap.isOpened():
        st.error("❌ Could not open video.")
        return {}, []

    students = load_students()
    present = {s["id"]: False for s in students}

    previews = []
    frame_count = 0

    # ------------------------------------------------------------
    # Read frames
    # ------------------------------------------------------------
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Only process every Xth frame
        if frame_count % frame_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            detections = find_faces_in_image(rgb)
            labels = []

            for emb, box in detections:
                best_name = "Unknown"
                best_id = None
                best_sim = 0

                for s in students:
                    for st_emb in s["embeddings"]:
                        sim = cosine_similarity(emb, st_emb)
                        if sim > 0.55 and sim > best_sim:
                            best_sim = sim
                            best_name = s["name"]
                            best_id = s["id"]

                labels.append(best_name)

                if best_id:
                    present[best_id] = True

            previews.append((rgb, labels))

        frame_count += 1

    cap.release()

    return present, previews


# ------------------------------------------------------------
# Streamlit Frontend UI
# ------------------------------------------------------------
def video_attendance_ui():
    """Interactive UI for taking attendance from video."""
    st.subheader("🎥 Take Attendance From Video")

    video_file = st.file_uploader(
        "Upload Video (mp4/mov/avi)",
        type=["mp4", "mov", "avi"],
        key="video_upload_teacher"
    )

    frame_interval = st.number_input(
        "Extract 1 frame every X frames:",
        min_value=10,
        max_value=200,
        value=30,
        step=10
    )

    # ----------------------------------------------
    # PROCESS BUTTON
    # ----------------------------------------------
    if video_file and st.button("Process Video"):
        st.info("⏳ Processing video... please wait.")

        present, previews = process_video(video_file.getvalue(), frame_interval)

        st.success("✅ Video processed successfully!")

        # Show previews (first 10 frames)
        st.subheader("🖼 Preview of Extracted Frames")
        for img, labels in previews[:10]:
            st.image(img, caption=", ".join(labels), use_column_width=True)

        return present, True

    return None, False
