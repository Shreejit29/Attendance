import streamlit as st
import os
import numpy as np
import pandas as pd
from PIL import Image
import io
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

st.set_page_config(page_title="Smart Attendance (Face Recognition)", layout="wide")
st.title("📘 Smart Attendance System — Face Recognition (No DeepFace)")


# Sidebar
menu = st.sidebar.selectbox(
    "Menu",
    ["Home", "Enrollment", "Manage Students", "Take Attendance (Photo/Video)", "Real-time Processing"]
)


# -------------------------------------------------------------
# HOME
# -------------------------------------------------------------
if menu == "Home":
    st.header("Welcome to the Smart Attendance System")
    st.markdown("""
### Key Features
- Face Recognition using **dlib** (safe for Streamlit Cloud)
- Photo / Video attendance
- Real-time-like processing
- Enrollment from upload or camera
- Mandatory attendance marking
- Excel export  
- Zero heavy dependencies  
- No TensorFlow, No DeepFace, No SciPy  
    """)


# -------------------------------------------------------------
# ENROLLMENT
# -------------------------------------------------------------
if menu == "Enrollment":
    st.header("Enroll a Student")

    sid = st.text_input("Student ID")
    name = st.text_input("Full Name")

    uploaded_img = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])
    cam_img = st.camera_input("Or capture a photo")

    if st.button("Enroll Student"):
        if not sid or not name:
            st.warning("Student ID and name required.")
        elif not uploaded_img and not cam_img:
            st.warning("Please upload or capture a photo.")
        else:
            src = uploaded_img if uploaded_img else cam_img
            tmp_path = f"tmp_enroll_{time.time()}.jpg"
            with open(tmp_path, "wb") as f:
                f.write(src.getbuffer())

            enroll_student(sid, name, tmp_path)
            os.remove(tmp_path)

            st.success(f"{name} enrolled successfully.")
            st.info("Rebuilding embedding index...")
            rebuild_embeddings_index()
            st.success("Embedding index updated.")


# -------------------------------------------------------------
# MANAGE STUDENTS
# -------------------------------------------------------------
if menu == "Manage Students":
    st.header("Manage Student Records")

    df = list_students()
    if df.empty:
        st.info("No students enrolled yet.")
    else:
        st.dataframe(df)

        st.subheader("Set Mandatory Students")

        changed = False
        for _, row in df.iterrows():
            sid = row["student_id"]
            current = bool(row["mandatory"])
            new = st.checkbox(f"{sid} – {row['name']}", value=current)
            if new != current:
                set_mandatory(sid, new)
                changed = True

        if changed:
            st.success("Mandatory list updated.")
            st.experimental_rerun()


# -------------------------------------------------------------
# TAKE ATTENDANCE (PHOTO / VIDEO)
# -------------------------------------------------------------
if menu == "Take Attendance (Photo/Video)":
    st.header("Take Attendance")

    uploaded_photo = st.file_uploader("Upload class photo", type=["jpg", "jpeg", "png"])
    cam_photo = st.camera_input("Capture class photo")
    uploaded_video = st.file_uploader("Upload class video", type=["mp4", "mov"])

    sample_rate = st.number_input("Video sampling rate (every N frames)", 1, 30, 8)

    frames = None
    image_arr = None

    # Handle Photo
    if uploaded_photo:
        image_arr = np.array(Image.open(uploaded_photo).convert("RGB"))
        st.image(uploaded_photo)

    elif cam_photo:
        image_arr = np.array(Image.open(cam_photo).convert("RGB"))
        st.image(cam_photo)

    # Handle Video
    elif uploaded_video:
        tmpvid = f"tmpvid_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(uploaded_video.getbuffer())

        st.info("Extracting frames...")
        frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        st.success(f"Extracted {len(frames)} frames")

        if frames:
            st.image(frames[len(frames)//2][:,:,::-1], caption="Sample frame")

    # Run attendance
    if (image_arr is not None or frames is not None) and st.button("Run Attendance"):
        embeddings_db, ids_db = load_embeddings_index()
        meta = list_students()

        if meta.empty:
            st.warning("No students enrolled yet.")
        else:
            if image_arr is not None:
                processed = process_frames_for_faces([image_arr[:, :, ::-1]])
            else:
                processed = process_frames_for_faces(frames)

            matched = []
            unknown = []

            for r in processed:
                emb = r["embedding"]
                sid, dist = match_embedding(emb, embeddings_db, ids_db)

                if sid:
                    matched.append({"student_id": sid, "distance": dist})
                else:
                    unknown.append(emb)

            matched = deduplicate_matches(matched)
            clusters = cluster_unknown_embeddings(unknown)

            att_df = generate_attendance(meta, matched)

            st.subheader("Attendance Result")
            st.dataframe(att_df)

            # Download Excel
            buf = io.BytesIO()
            att_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download Excel", buf, "attendance.xlsx")

            st.info(f"Recognized Students: {len(matched)}")
            st.info(f"Unknown Face Clusters: {len(clusters)}")


# -------------------------------------------------------------
# REAL-TIME-LIKE VIDEO PROCESSING
# -------------------------------------------------------------
if menu == "Real-time Processing":
    st.header("Real-Time-like Processing (Video Upload)")

    uploaded_video = st.file_uploader("Upload a video", type=["mp4", "mov"])

    if uploaded_video:
        tmpvid = f"tmp_rt_{time.time()}.mp4"
        with open(tmpvid, "wb") as f:
            f.write(uploaded_video.getbuffer())

        sample_rate = st.number_input("Sample every N frames", 1, 30, 5)

        st.info("Sampling frames...")
        frames = extract_frames_from_video(tmpvid, sample_rate)
        os.remove(tmpvid)

        total = len(frames)
        st.success(f"Frames extracted: {total}")

        embeddings_db, ids_db = load_embeddings_index()

        matched_all = []
        unknown = []

        progress = st.progress(0)

        for idx, frame in enumerate(frames):
            processed = process_frames_for_faces([frame])

            for r in processed:
                emb = r["embedding"]
                sid, dist = match_embedding(emb, embeddings_db, ids_db)

                if sid:
                    matched_all.append({"student_id": sid, "distance": dist})
                else:
                    unknown.append(emb)

            progress.progress(int((idx+1)/total*100))

        matched = deduplicate_matches(matched_all)
        clusters = cluster_unknown_embeddings(unknown)

        att_df = generate_attendance(list_students(), matched)
        st.dataframe(att_df)

        buf = io.BytesIO()
        att_df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Download Excel", buf, "attendance.xlsx")

        st.info(f"Recognized: {len(matched)}")
        st.info(f"Unknown clusters: {len(clusters)}")
