# teacher_portal.py

import streamlit as st
import pandas as pd
from io import BytesIO

# Import your existing modules
from storage import load_students, delete_student_by_id
from class_selector import class_subject_time_selector
from video_attendance import video_attendance_ui
from manual_attendance import manual_attendance_ui
from face_utils import (
    load_image_from_bytes,
    find_faces_in_image,
    cosine_similarity,
    draw_boxes,
)

# NEW: WebRTC live attendance module
from live_webrtc_attendance import live_webrtc_attendance_ui



def teacher_portal(username):
    st.header(f"👨‍🏫 Teacher Portal — {username}")

    # Updated menu WITH WebRTC feature
    choice = st.selectbox("Select Task", [
        "Take Attendance (Image)",
        "Take Attendance (Video)",
        "Live Mobile Camera (WebRTC)",   # ← NEW
        "Manage Students"
    ])

    # ---------------------------------------
    # IMAGE ATTENDANCE
    # ---------------------------------------
    if choice == "Take Attendance (Image)":
        st.subheader("Take Attendance Using Image")

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
                best_sim, best_name = 0, "Unknown"

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

            final_df = manual_attendance_ui(students, present)
            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

            if st.button("Download Excel"):
                buf = BytesIO()
                final_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button("Download File", data=buf,
                                   file_name="teacher_image_attendance.xlsx")

    # ---------------------------------------
    # VIDEO ATTENDANCE
    # ---------------------------------------
    if choice == "Take Attendance (Video)":
        st.subheader("Take Attendance From Uploaded Video")

        details = class_subject_time_selector()

        present, processed = video_attendance_ui()

        if processed:
            students = load_students()

            df = pd.DataFrame([
                {
                    "Student ID": s["id"],
                    "Name": s["name"],
                    "Class": s["class"],
                    "Programme": s["programme"],
                    "Present": present[s["id"]]
                }
                for s in students
            ])

            df = manual_attendance_ui(students, present)
            st.dataframe(df)

    # ---------------------------------------
    # LIVE MOBILE CAMERA (WebRTC) — NEW FEATURE
    # ---------------------------------------
    if choice == "Live Mobile Camera (WebRTC)":
        st.subheader("📱 Live Mobile Camera Attendance (WebRTC + Multi-Face Tracking)")

        details = class_subject_time_selector()

        present, processed = live_webrtc_attendance_ui()

        if processed:
            students = load_students()

            final_df = pd.DataFrame([
                {
                    "Student ID": s["id"],
                    "Name": s["name"],
                    "Class": s.get("class", ""),
                    "Programme": s.get("programme", ""),
                    "Present": present[s["id"]],
                }
                for s in students
            ])

            final_df = manual_attendance_ui(students, present)
            st.dataframe(final_df)

            if st.button("Download Excel"):
                buf = BytesIO()
                final_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button(
                    "Download Attendance",
                    data=buf,
                    file_name="teacher_live_webrtc_attendance.xlsx"
                )

    # ---------------------------------------
    # MANAGE STUDENTS
    # ---------------------------------------
    if choice == "Manage Students":
        st.subheader("Manage Students")

        students = load_students()
        df = pd.DataFrame(students)

        st.dataframe(df[["id", "name", "programme", "class"]])

        sid = st.selectbox("Select Student to Delete", df["id"])

        if st.button("Delete Student"):
            delete_student_by_id(sid)
            st.success("Student Deleted Successfully!")
            st.experimental_rerun()
