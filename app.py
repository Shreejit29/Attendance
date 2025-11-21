import streamlit as st
import pandas as pd
from face_utils import (
    load_image_from_bytes,
    get_face_embedding,
    find_faces_in_image,
    cosine_similarity,
    draw_boxes,
)

from storage import add_student, load_students
from manual_attendance import manual_attendance_ui
from class_selector import class_subject_time_selector
from video_attendance import video_attendance_ui
from admin_management import admin_panel_ui
from dashboard import dashboard_ui

from io import BytesIO
from datetime import datetime


st.title("📘 Smart Attendance System")

mode = st.sidebar.selectbox("Menu", [
    "Register Student",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Dashboard",
    "Admin Panel"
])


# ---------------------------------------------------------
# REGISTER STUDENT
# ---------------------------------------------------------
if mode == "Register Student":
    st.header("Register Student")

    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")

    programme = st.selectbox("Programme", [
        "BSc", "BA", "BCom", "MSc", "MA", "Custom"
    ])

    if programme == "Custom":
        programme = st.text_input("Enter Programme")

    student_class = st.text_input("Class (e.g., FYBSc, SYBSc, Division A)")

    upload = st.file_uploader("Upload student photo", type=["jpg","png"])
    capture = st.camera_input("Or capture photo")

    if st.button("Register"):
        if not name or not sid or not programme or not student_class:
            st.error("Fill all fields.")
        else:
            src = capture or upload
            if not src:
                st.error("Upload or capture photo.")
            else:
                img = load_image_from_bytes(src.getvalue())
                emb = get_face_embedding(img)

                if emb:
                    add_student(
                        sid=sid,
                        name=name,
                        programme=programme,
                        student_class=student_class,
                        embedding=emb
                    )
                    st.success(f"Registered {name} ({sid})")
                else:
                    st.error("No face detected.")



# ---------------------------------------------------------
# TAKE ATTENDANCE (IMAGE)
# ---------------------------------------------------------
if mode == "Take Attendance (Image)":
    st.header("Take Attendance Using Image")

    details = class_subject_time_selector()

    upload = st.file_uploader("Upload class photo", type=["jpg","png"])
    capture = st.camera_input("Or capture")

    if upload or capture:
        img = load_image_from_bytes((upload or capture).getvalue())

        detections = find_faces_in_image(img)
        students = load_students()
        present = {s["id"]: False for s in students}

        boxes, labels = [], []

        for emb, box in detections:
            boxes.append(box)
            best_name, best_sim = "Unknown", 0

            for s in students:
                for st_emb in s["embeddings"]:
                    sim = cosine_similarity(emb, st_emb)
                    if sim > 0.55 and sim > best_sim:
                        best_sim = sim
                        best_name = s["name"]
                        present[s["id"]] = True

            labels.append(best_name)

        out_img = draw_boxes(img, boxes, labels)
        st.image(out_img, use_column_width=True)

        auto_df = pd.DataFrame([
            {
                "Student ID": s["id"],
                "Name": s["name"],
                "Class": s.get("class", ""),
                "Programme": s.get("programme", ""),
                "Present": present[s["id"]]
            }
            for s in students
        ])

        st.subheader("Automatic Attendance")
        st.dataframe(auto_df)

        st.subheader("Manual Correction")
        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details["class"]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        if st.button("Download Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)

            st.download_button("Download File", data=buf,
                               file_name="attendance_image.xlsx")



# ---------------------------------------------------------
# TAKE ATTENDANCE FROM VIDEO
# ---------------------------------------------------------
if mode == "Take Attendance From Video":
    st.header("🎥 Attendance From Video")

    details = class_subject_time_selector()

    present, processed = video_attendance_ui()

    if processed:
        students = load_students()

        df = pd.DataFrame([
            {
                "Student ID": s["id"],
                "Name": s["name"],
                "Class": s.get("class", ""),
                "Programme": s.get("programme", ""),
                "Present": present[s["id"]]
            }
            for s in students
        ])

        st.subheader("Automatic Attendance")
        st.dataframe(df)

        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details["class"]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        if st.button("Download Video Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf,
                               file_name="attendance_video.xlsx")



# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
if mode == "Dashboard":
    st.header("📊 Attendance Dashboard")
    dashboard_ui()



# ---------------------------------------------------------
# ADMIN PANEL
# ---------------------------------------------------------
if mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
