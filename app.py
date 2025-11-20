# app.py  — Streamlit UI for Smart Attendance App

import streamlit as st
from PIL import Image
import pandas as pd
import numpy as np
import io
import os

# Import all helpers from utils.py
from utils import (
    enroll_student, list_students, set_mandatory,
    rebuild_embeddings_index, load_embeddings_index,
    extract_frames_from_video, process_frames_for_faces,
    match_embedding, deduplicate_matches,
    cluster_unknown_embeddings, generate_attendance,
    csv_to_qr_image
)

# ------------------------------------------------------------
# Streamlit Page Settings
# ------------------------------------------------------------

st.set_page_config(
    page_title="Smart Attendance (DeepFace)",
    layout="wide"
)

st.title("📚 Smart Classroom Attendance — DeepFace + Streamlit")

menu = st.sidebar.selectbox(
    "Navigation",
    ["Home", "Enrollment", "Manage Students", "Take Attendance (Photo/Video)", "Real-time Video Processing"]
)

st.markdown("""
<style>
.big-btn > button {padding: 14px 24px; font-size: 18px !important}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# Home Page
# ------------------------------------------------------------

if menu == "Home":
    st.header("Welcome 👋")
    st.write("""
    This application uses **DeepFace** for smart facial-recognition-based attendance.
    
    Features included:
    - Student enrollment with **upload or camera**
    - Attendance using **photo** or **video**
    - **Automatic frame sampling** from videos
    - **Precomputed embeddings** + **FAISS** for fast matching
    - **Unknown face clustering**
    - **QR Backup** of attendance
    - Mobile friendly interface
    """)

    st.info("Note: On first run, DeepFace will download pretrained model weights.")


# ------------------------------------------------------------
# Student Enrollment
# ------------------------------------------------------------

if menu == "Enrollment":
    st.header("👤 Enroll Student")

    sid = st.text_input("Student ID")
    name = st.text_input("Full Name")

    uploaded_img = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or Capture Using Camera")

    if st.button("Enroll Student", key="enroll-btn"):
        if not sid or not name or (uploaded_img is None and cam_img is None):
            st.warning("Please fill all fields and provide a photo.")
        else:
            src = uploaded_img if uploaded_img is not None else cam_img

            with open(f"tmp_{sid}.jpg", "wb") as f:
                f.write(src.getbuffer())

            enroll_student(sid, name, f"tmp_{sid}.jpg")
            os.remove(f"tmp_{sid}.jpg")

            st.success(f"Successfully enrolled {name} ({sid}). Updating embeddings...")

            with st.spinner("Rebuilding embedding index..."):
                rebuild_embeddings_index()

            st.success("Embeddings updated!")


# ------------------------------------------------------------
# Manage Students
# ------------------------------------------------------------

if menu == "Manage Students":
    st.header("🧾 Student Database")

    df = list_students()
    st.dataframe(df)

    st.subheader("Mark Mandatory Students")

    for _, row in df.iterrows():
        sid = row["student_id"]
        name = row["name"]
        flag = bool(row["mandatory"])

        updated = st.checkbox(f"{sid} — {name}", value=flag)

        if updated != flag:
            set_mandatory(sid, updated)
            st.experimental_rerun()


# ------------------------------------------------------------
# Take Attendance from Photo / Video
# ------------------------------------------------------------

if menu == "Take Attendance (Photo/Video)":
    st.header("📸 Take Attendance (Photo or Video)")

    uploaded_img = st.file_uploader("Upload Class Photo", type=["jpg", "jpeg", "png"])
    video_file = st.file_uploader("Or Upload Class Video", type=["mp4", "mov"])
    cam_img = st.camera_input("Or Capture Photo Using Camera")

    source_img_path = None

    # Priority: photo upload > camera > video frame
    if uploaded_img:
        with open("tmp_class.jpg", "wb") as f:
            f.write(uploaded_img.getbuffer())
        source_img_path = "tmp_class.jpg"
        st.image(uploaded_img, caption="Uploaded Class Photo", use_column_width=True)

    elif cam_img:
        with open("tmp_cam_class.jpg", "wb") as f:
            f.write(cam_img.getbuffer())
        source_img_path = "tmp_cam_class.jpg"
        st.image(cam_img, caption="Captured Image", use_column_width=True)

    elif video_file:
        with open("tmp_video.mp4", "wb") as f:
            f.write(video_file.getbuffer())

        st.info("Extracting frames from video...")
        frames = extract_frames_from_video("tmp_video.mp4", sample_rate=8)

        if len(frames) == 0:
            st.error("Could not extract frames from video.")
        else:
            mid_frame = frames[len(frames) // 2][:, :, ::-1]
            st.image(mid_frame, caption="Sampled Frame", use_column_width=True)

            with st.spinner("Detecting faces across frames..."):
                face_records = process_frames_for_faces(frames)

            st.success(f"Detected {len(face_records)} face crops from sampled frames.")

            # Load FAISS index
            index, embeddings, ids = load_embeddings_index()
            matched = []
            unknown_embs = []

            for rec in face_records:
                sid, dist = match_embedding(rec["embedding"], index, ids, threshold=0.8)
                if sid:
                    matched.append({"student_id": sid, "distance": dist})
                else:
                    unknown_embs.append(rec["embedding"])

            matched = deduplicate_matches(matched)
            clusters = cluster_unknown_embeddings(unknown_embs)

            meta = list_students()
            att_df = generate_attendance(meta, matched)

            st.subheader("Attendance Sheet")
            st.dataframe(att_df)

            # Download Excel
            buf = io.BytesIO()
            att_df.to_excel(buf, index=False)
            buf.seek(0)

            st.download_button("Download Attendance Excel", buf, file_name="attendance.xlsx")

            # QR Backup
            qr_buf = csv_to_qr_image(att_df)
            st.image(qr_buf, caption="QR Backup")

            st.download_button("Download QR Backup", qr_buf, file_name="attendance_qr.png")

    # PHOTO MODE: Recognize from a single image
    if source_img_path and st.button("Run Attendance"):
        index, embeddings, ids = load_embeddings_index()
        frames = [np.array(Image.open(source_img_path))[:, :, ::-1]]

        with st.spinner("Processing image..."):
            face_records = process_frames_for_faces(frames)

        matched = []
        unknown_embs = []

        for rec in face_records:
            sid, dist = match_embedding(rec["embedding"], index, ids, threshold=0.8)

            if sid:
                matched.append({"student_id": sid, "distance": dist})
            else:
                unknown_embs.append(rec["embedding"])

        matched = deduplicate_matches(matched)
        clusters = cluster_unknown_embeddings(unknown_embs)

        meta = list_students()
        att_df = generate_attendance(meta, matched)

        st.subheader("Attendance Sheet")
        st.dataframe(att_df)

        buffer = io.BytesIO()
        att_df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button("Download Excel", buffer, file_name="attendance.xlsx")

        qr_buf = csv_to_qr_image(att_df)
        st.image(qr_buf, caption="QR Backup")
        st.download_button("Download QR", qr_buf, file_name="attendance_qr.png")


# ------------------------------------------------------------
# Real-time-like Video Processing
# ------------------------------------------------------------

if menu == "Real-time Video Processing":
    st.header("🎥 Real-time Video Processing (Server-Side)")

    video_file = st.file_uploader("Upload Classroom Video", type=["mp4", "mov"])

    if video_file:
        with open("tmp_rt.mp4", "wb") as f:
            f.write(video_file.getbuffer())

        st.info("Sampling video frames...")
        frames = extract_frames_from_video("tmp_rt.mp4", sample_rate=5)

        st.write(f"Processing {len(frames)} frames...")

        index, embeddings, ids = load_embeddings_index()

        matched_all = []
        unknown_all = []

        progress = st.progress(0)

        for i, frame in enumerate(frames):
            recs = process_frames_for_faces([frame])

            for r in recs:
                sid, dist = match_embedding(r["embedding"], index, ids, threshold=0.8)
                if sid:
                    matched_all.append({"student_id": sid, "distance": dist})
                else:
                    unknown_all.append(r["embedding"])

            progress.progress(int((i + 1) / len(frames) * 100))

        matched_unique = deduplicate_matches(matched_all)
        clusters = cluster_unknown_embeddings(unknown_all)

        st.write(f"Matched Students: {len(matched_unique)}")
        st.write(f"Unknown Face Clusters: {len(clusters)}")

        att_df = generate_attendance(list_students(), matched_unique)
        st.dataframe(att_df)

        buf = io.BytesIO()
        att_df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Download Excel", buf, file_name="attendance.xlsx")

        qr_buf = csv_to_qr_image(att_df)
        st.image(qr_buf, caption="QR Backup")
        st.download_button("Download QR", qr_buf, file_name="attendance_qr.png")
