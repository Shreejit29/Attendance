# app.py — Smart Attendance (TF-free) using DeepFace + Streamlit
# Features:
# - Enrollment (upload + camera)
# - Attendance: photo or video sampling
# - Real-time-like video processing
# - Unknown face clustering
# - No QR export, No TensorFlow usage
# - Detector backend: mtcnn/opencv/ssd (NO RetinaFace)
# - Embedding models: Facenet, ArcFace, VGG-Face, Facenet512

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

st.set_page_config(page_title="Smart Attendance (TF-free)", layout="wide")
st.title("Smart Attendance — DeepFace (TF-Free Deployment)")

menu = st.sidebar.selectbox(
    "Navigation",
    ["Home", "Enrollment", "Manage Students", "Take Attendance (Photo/Video)", "Real-time Video Processing"]
)

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
if menu == "Home":
    st.header("Welcome")
    st.markdown("""
### This is a TensorFlow-free Smart Attendance System

It supports:
- 📸 **Enrollment** (Upload or Camera)
- 🖼 **Attendance from PHOTO**
- 🎥 **Attendance from VIDEO** (sampled frames)
- ⚡ **Real-time-like server-side video processing**
- 🤨 **Unknown face grouping (clustering)**  
- 💡 **Fully TF-free — avoids all TensorFlow / Keras / RetinaFace errors**

You just need to:
1. Enroll students  
2. Upload a photo or video of classroom  
3. Download attendance Excel  
""")

# ---------------------------------------------------------
# ENROLLMENT
# ---------------------------------------------------------
if menu == "Enrollment":
    st.header("Enroll a Student")

    sid = st.text_input("Student ID")
    name = st.text_input("Full Name")
    uploaded_img = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or capture using camera")

    if st.button("Enroll Student"):
        if not sid or not name or (uploaded_img is None and cam_img is None):
            st.warning("Please enter Student ID, Name, and a Photo.")
        else:
            src = uploaded_img if uploaded_img is not None else cam_img
            tmp_path = f"tmp_en_{time.time()}.jpg"
            with open(tmp_path, "wb") as f:
                f.write(src.getbuffer())

            enroll_student(sid, name, tmp_path)
            os.remove(tmp_path)

            st.success(f"Enrolled {name} ({sid}). Rebuilding embeddings…")
            rebuild_embeddings_index()
            st.success("Embeddings updated successfully.")

# ---------------------------------------------------------
# MANAGE STUDENTS
# ---------------------------------------------------------
if menu == "Manage Students":
    st.header("Manage Students")

    df = list_students()
    if df.empty:
        st.info("No students enrolled yet.")
    else:
        st.dataframe(df)
        st.subheader("Mandatory Student Selection")

        updated = False
        for _, r in df.iterrows():
            sid = r["student_id"]
            cur = bool(r["mandatory"])
            new = st.checkbox(f"{sid} — {r['name']}", value=cur)
            if new != cur:
                set_mandatory(sid, new)
                updated = True

        if updated:
            st.success("Mandatory list updated.")
            st.experimental_rerun()

# ---------------------------------------------------------
# TAKE ATTENDANCE
# ---------------------------------------------------------
if menu == "Take Attendance (Photo/Video)":
    st.header("Take Attendance — Photo or Video")

    uploaded_img = st.file_uploader("Upload Class Photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or capture class photo")
    video_file = st.file_uploader("Or upload class video", type=["mp4", "mov"])

    detector_choice = st.selectbox("Face Detector", ["mtcnn", "opencv", "ssd"])
    model_choice = st.selectbox("Embedding Model", ["Facenet", "ArcFace", "VGG-Face", "Facenet512"])
    sample_rate = st.number_input("Video Sampling Rate (every N frames)", 1, 30, 8)

    source_path = None
    video_frames = None

    # PHOTO INPUT
    if uploaded_img:
        source_path = f"tmpclass_{time.time()}.jpg"
        with open(source_path, "wb") as f:
            f.write(uploaded_img.getbuffer())
        st.image(uploaded_img, caption="Uploaded Photo", use_column_width=True)

    elif cam_img:
        source_path = f"tmpcamclass_{time.time()}.jpg"
        with open(source_path, "wb") as f:
            f.write(cam_img.getbuffer())
        st.image(cam_img, caption="Captured Photo", use_column_width=True)

    # VIDEO INPUT
    elif video_file:
        tmpvid = f"tmpvideo_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(video_file.getbuffer())

        st.info("Extracting frames from video…")
        video_frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        if len(video_frames) == 0:
            st.error("No frames extracted — video may be corrupted.")
        else:
            st.success(f"Extracted {len(video_frames)} frames.")
            sample_img = video_frames[len(video_frames)//2][:,:,::-1]
            st.image(sample_img, caption="Example extracted frame")

    # RUN RECOGNITION
    if (source_path or video_frames) and st.button("Run Attendance"):
        index, embeddings, ids = load_embeddings_index()
        meta = list_students()

        if meta.empty:
            st.warning("No students enrolled.")
        else:
            # PROCESS SINGLE PHOTO
            if source_path:
                img = Image.open(source_path).convert("RGB")
                arr = np.array(img)[:, :, ::-1]
                recs = process_frames_for_faces([arr], model_choice, detector_choice)
                os.remove(source_path)
            else:
                recs = process_frames_for_faces(video_frames, model_choice, detector_choice)

            matched = []
            unknown_embs = []

            for r in recs:
                emb = r.get("embedding")
                if emb is None:
                    continue
                sid, dist = match_embedding(emb, index, ids, threshold=0.6)
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
            st.download_button("Download Attendance Excel", buf, file_name="attendance.xlsx")

            st.info(f"Matched students: {len(matched_unique)}")
            st.info(f"Unknown face clusters: {len(clusters)}")

# ---------------------------------------------------------
# REAL-TIME VIDEO PROCESSING
# ---------------------------------------------------------
if menu == "Real-time Video Processing":
    st.header("Real-time-like Video Processing")

    video_file = st.file_uploader("Upload classroom video", type=["mp4", "mov"])

    if video_file:
        tmpvid = f"tmp_rt_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(video_file.getbuffer())

        sample_rate = st.number_input("Sampling rate (1 = every frame)", 1, 30, 6)
        st.info("Sampling frames…")
        frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        index, embeddings, ids = load_embeddings_index()
        matched_all = []
        unknown_all = []

        progress = st.progress(0)
        total = len(frames)

        for i, frame in enumerate(frames):
            recs = process_frames_for_faces([frame])
            for r in recs:
                emb = r["embedding"]
                sid, dist = match_embedding(emb, index, ids, threshold=0.6)
                if sid:
                    matched_all.append({"student_id": sid, "distance": dist})
                else:
                    unknown_all.append(emb)
            progress.progress(int((i+1)/total*100))

        matched_unique = deduplicate_matches(matched_all)
        clusters = cluster_unknown_embeddings(unknown_all)
        att_df = generate_attendance(list_students(), matched_unique)

        st.subheader("Real-time Processing Result")
        st.dataframe(att_df)

        buf = io.BytesIO()
        att_df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Download Attendance Excel", buf, file_name="attendance.xlsx")

        st.info(f"Matched unique: {len(matched_unique)}")
        st.info(f"Unknown groups: {len(clusters)}")
