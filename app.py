# app.py — Ultra-fast Streamlit Attendance System (SFace + OpenCV only)
# - No TensorFlow
# - No RetinaFace/MTCNN downloads
# - Instant startup on Streamlit Cloud
# - Full features: enrollment, photo/video attendance, real-time-like, clustering

import streamlit as st
from PIL import Image
import numpy as np
import io
import os
import time

from utils import (
    enroll_student,
    list_students,
    set_mandatory,
    rebuild_embeddings_index,
    load_embeddings_index,
    extract_frames_from_video,
    process_frames_for_faces,
    match_embedding,
    deduplicate_matches,
    cluster_unknown_embeddings,
    generate_attendance
)

os.makedirs("student_db", exist_ok=True)

st.set_page_config(page_title="Smart Attendance (Fast)", layout="wide")
st.title("📘 Smart Attendance — Ultra-Fast (SFace + OpenCV Only)")


menu = st.sidebar.selectbox(
    "Menu",
    ["Home", "Enrollment", "Manage Students", "Take Attendance (Photo/Video)", "Real-time Video Processing"]
)


# -----------------------------------------------------------
# HOME
# -----------------------------------------------------------
if menu == "Home":
    st.header("Welcome")
    st.markdown("""
### ⚡ Optimized Smart Attendance System  
This version is tuned to deploy instantly on **Streamlit Cloud**:

- Uses **SFace (PyTorch)** for fast embeddings  
- Uses **OpenCV Haarcascade** for face detection  
- No TensorFlow  
- No RetinaFace  
- No large model downloads  
- Full features included  
    """)


# -----------------------------------------------------------
# ENROLLMENT
# -----------------------------------------------------------
if menu == "Enrollment":
    st.header("Enroll Student")

    sid = st.text_input("Student ID")
    name = st.text_input("Full Name")

    uploaded_img = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or capture a photo")

    if st.button("Enroll"):
        if not sid or not name or (uploaded_img is None and cam_img is None):
            st.warning("Please enter Student ID, Name and a photo.")
        else:
            src = uploaded_img if uploaded_img else cam_img
            tmp_path = f"tmp_en_{time.time()}.jpg"
            with open(tmp_path, "wb") as f:
                f.write(src.getbuffer())

            enroll_student(sid, name, tmp_path)
            os.remove(tmp_path)

            st.success(f"Enrolled {name}. Updating embeddings...")
            rebuild_embeddings_index()
            st.success("Embeddings updated.")


# -----------------------------------------------------------
# MANAGE STUDENTS
# -----------------------------------------------------------
if menu == "Manage Students":
    st.header("Manage Students")

    df = list_students()
    if df.empty:
        st.info("No students enrolled yet.")
    else:
        st.dataframe(df)
        st.subheader("Mandatory student selection")

        changed = False
        for _, row in df.iterrows():
            sid = row["student_id"]
            cur = bool(row["mandatory"])
            new_val = st.checkbox(f"{sid} — {row['name']}", value=cur)
            if new_val != cur:
                set_mandatory(sid, new_val)
                changed = True

        if changed:
            st.success("Mandatory list updated.")
            st.experimental_rerun()


# -----------------------------------------------------------
# ATTENDANCE (PHOTO / VIDEO)
# -----------------------------------------------------------
if menu == "Take Attendance (Photo/Video)":
    st.header("Take Attendance")

    uploaded_img = st.file_uploader("Upload class photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or capture class photo")
    video_file = st.file_uploader("Or upload class video", type=["mp4", "mov"])

    sample_rate = st.number_input("Video sampling rate (every N frames)", 1, 30, 8)

    source_path = None
    frames = None

    # photo input
    if uploaded_img:
        source_path = f"tmpclass_{time.time()}.jpg"
        with open(source_path, "wb") as f:
            f.write(uploaded_img.getbuffer())
        st.image(uploaded_img)

    elif cam_img:
        source_path = f"tmpclasscam_{time.time()}.jpg"
        with open(source_path, "wb") as f:
            f.write(cam_img.getbuffer())
        st.image(cam_img)

    # video input
    elif video_file:
        tmpvid = f"tmpvid_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(video_file.getbuffer())

        st.info("Extracting frames...")
        frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        st.success(f"Extracted {len(frames)} frames.")
        if frames:
            st.image(frames[len(frames)//2][:,:,::-1], caption="Sample frame")

    if (source_path or frames) and st.button("Run Attendance"):
        embeddings_db, ids_db = load_embeddings_index()
        meta = list_students()

        if meta.empty:
            st.warning("No students enrolled.")
        else:
            # process single image
            if source_path:
                img = Image.open(source_path).convert("RGB")
                arr = np.array(img)[:, :, ::-1]
                recs = process_frames_for_faces([arr])
                os.remove(source_path)
            else:
                recs = process_frames_for_faces(frames)

            matched = []
            unknown_embs = []

            for r in recs:
                emb = r["embedding"]
                sid, dist = match_embedding(emb, embeddings_db, ids_db, threshold=0.55)
                if sid:
                    matched.append({"student_id": sid, "distance": dist})
                else:
                    unknown_embs.append(emb)

            matched_unique = deduplicate_matches(matched)
            clusters = cluster_unknown_embeddings(unknown_embs)

            att_df = generate_attendance(meta, matched_unique)

            st.subheader("Attendance Result")
            st.dataframe(att_df)

            buf = io.BytesIO()
            att_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download Excel", buf, file_name="attendance.xlsx")

            st.info(f"Matched: {len(matched_unique)}")
            st.info(f"Unknown groups: {len(clusters)}")


# -----------------------------------------------------------
# REAL-TIME LIKE VIDEO PROCESSING
# -----------------------------------------------------------
if menu == "Real-time Video Processing":
    st.header("Real-time-like Video Processing")

    video_file = st.file_uploader("Upload classroom video", type=["mp4", "mov"])

    if video_file:
        tmpvid = f"tmp_rt_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(video_file.getbuffer())

        sample_rate = st.number_input("Sampling rate", 1, 30, 6)

        st.info("Sampling frames...")
        frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        embeddings_db, ids_db = load_embeddings_index()

        matched_all = []
        unknown_all = []

        progress = st.progress(0)
        total = len(frames)

        for idx, frame in enumerate(frames):
            recs = process_frames_for_faces([frame])
            for r in recs:
                emb = r["embedding"]
                sid, dist = match_embedding(emb, embeddings_db, ids_db, threshold=0.55)
                if sid:
                    matched_all.append({"student_id": sid, "distance": dist})
                else:
                    unknown_all.append(emb)

            progress.progress(int((idx + 1) / total * 100))

        matched_unique = deduplicate_matches(matched_all)
        clusters = cluster_unknown_embeddings(unknown_all)

        att_df = generate_attendance(list_students(), matched_unique)
        st.dataframe(att_df)

        buf = io.BytesIO()
        att_df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Download Excel", buf, file_name="attendance.xlsx")

        st.info(f"Matched unique: {len(matched_unique)}")
        st.info(f"Unknown clusters: {len(clusters)}")
