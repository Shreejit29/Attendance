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
from admin_management import admin_panel_ui   # NEW ADMIN PANEL

from io import BytesIO
from datetime import datetime


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------
st.title("📘 FaceRoll-Smart Attendance App")


# ---------------------------------------------------------
# SIDEBAR MENU
# ---------------------------------------------------------
mode = st.sidebar.selectbox("Menu", [
    "Register Student",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Admin Panel"
])


# ---------------------------------------------------------
# REGISTER STUDENT
# ---------------------------------------------------------
if mode == "Register Student":
    st.header("Register Student")

    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")

    upload = st.file_uploader("Upload student photo", type=["jpg","png"])
    capture = st.camera_input("Or capture using camera")

    if st.button("Register"):
        if not name or not sid:
            st.error("Enter student name & ID")
        else:
            src = capture or upload
            if not src:
                st.error("Upload or capture a photo")
            else:
                img = load_image_from_bytes(src.getvalue())
                emb = get_face_embedding(img)

                if emb:
                    add_student(sid, name, emb)
                    st.success(f"Registered {name} ({sid}) successfully")
                else:
                    st.error("No face detected. Try clearer image.")



# ---------------------------------------------------------
# TAKE ATTENDANCE (IMAGE)
# ---------------------------------------------------------
if mode == "Take Attendance (Image)":
    st.header("Take Attendance Using Image")

    details = class_subject_time_selector()

    upload = st.file_uploader("Upload class photo", type=["jpg","png"])
    capture = st.camera_input("Or capture class photo")

    if upload or capture:
        img = load_image_from_bytes((capture or upload).getvalue())

        detections = find_faces_in_image(img)
        students = load_students()

        present = {s["id"]: False for s in students}
        boxes, labels = [], []

        # MATCHING
        for emb, box in detections:
            boxes.append(box)
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

        # DISPLAY RESULTS
        out = draw_boxes(img, boxes, labels)
        st.image(out, caption="Detected Students", use_column_width=True)

        st.subheader("Session Details")
        st.write(f"**Class:** {details['class']}")
        st.write(f"**Subject:** {details['subject']}")
        st.write(f"**Time:** {details['time']}")

        auto_df = pd.DataFrame([
            {"Student ID": s["id"], "Name": s["name"], "Present": present[s["id"]]}
            for s in students
        ])

        st.subheader("Automatic Attendance")
        st.dataframe(auto_df)

        st.subheader("Manual Correction")
        final_df = manual_attendance_ui(students, present)

        st.subheader("Final Attendance Sheet")
        st.dataframe(final_df)

        if st.button("Download Excel"):
            buf = BytesIO()

            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            final_df.to_excel(buf, index=False)
            buf.seek(0)

            st.download_button(
                "Download Attendance File",
                data=buf,
                file_name=f"attendance_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )



# ---------------------------------------------------------
# TAKE ATTENDANCE FROM VIDEO
# ---------------------------------------------------------
if mode == "Take Attendance From Video":
    st.header("🎥 Attendance From Uploaded Video")

    details = class_subject_time_selector()

    present, processed = video_attendance_ui()

    if processed:
        students = load_students()

        df = pd.DataFrame([
            {"Student ID": s["id"], "Name": s["name"], "Present": present[s["id"]]}
            for s in students
        ])

        st.subheader("Automatic Attendance From Video")
        st.dataframe(df)

        st.subheader("Manual Correction")
        final_df = manual_attendance_ui(students, present)

        if st.button("Download Video Attendance"):
            buf = BytesIO()

            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            final_df.to_excel(buf, index=False)
            buf.seek(0)

            st.download_button(
                "Download File",
                data=buf,
                file_name="video_attendance.xlsx"
            )



# ---------------------------------------------------------
# ADMIN PANEL (STUDENT + TEACHER + TIMETABLE + HISTORY)
# ---------------------------------------------------------
if mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
