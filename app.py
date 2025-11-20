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
from live_video_attendance import live_attendance_ui
from io import BytesIO
from datetime import datetime

st.title("📘 Smart Attendance System (InsightFace - Modular Version)")

mode = st.sidebar.selectbox("Menu", [
    "Register Student",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Live Video Attendance"
])


# --------------------------------------------
#         REGISTER STUDENT
# --------------------------------------------
if mode == "Register Student":
    st.header("Register Student")

    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")
    upload = st.file_uploader("Upload student photo", type=["jpg","png"])
    capture = st.camera_input("Or capture")

    if st.button("Register"):
        if not name or not sid:
            st.error("Enter name & student ID")
        else:
            src = capture or upload
            if not src:
                st.error("Upload or capture a photo")
            else:
                img = load_image_from_bytes(src.getvalue())
                emb = get_face_embedding(img)
                if emb:
                    add_student(sid, name, emb)
                    st.success(f"Registered {name} ({sid})")
                else:
                    st.error("No face detected in photo.")


# --------------------------------------------
#         TAKE ATTENDANCE (IMAGE)
# --------------------------------------------
if mode == "Take Attendance (Image)":
    st.header("Take Attendance from Image")

    details = class_subject_time_selector()

    upload = st.file_uploader("Upload class photo", type=["jpg","png"])
    capture = st.camera_input("Or capture class photo")

    if upload or capture:
        img = load_image_from_bytes((capture or upload).getvalue())

        detected = find_faces_in_image(img)
        students = load_students()
        present = {s["id"]: False for s in students}

        boxes = []
        labels = []

        for emb, box in detected:
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

        out_img = draw_boxes(img, boxes, labels)
        st.image(out_img, use_column_width=True, caption="Detected Faces")

        st.subheader("Session Details")
        st.write(f"**Class:** {details['class']}")
        st.write(f"**Subject:** {details['subject']}")
        st.write(f"**Time:** {details['time']}")

        auto_df = pd.DataFrame([{
            "Student ID": s["id"],
            "Name": s["name"],
            "Present": present[s["id"]],
        } for s in students])

        st.subheader("Automatic Attendance")
        st.dataframe(auto_df)

        st.write("### Manual Correction")
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

            file_name = (
                f"attendance_{details['class']}_{details['subject']}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )

            st.download_button("Download File", data=buf, file_name=file_name)


# --------------------------------------------
#         TAKE ATTENDANCE FROM VIDEO
# --------------------------------------------
if mode == "Take Attendance From Video":
    st.header("🎥 Attendance from Uploaded Video")

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

        st.subheader("Final Attendance Sheet")
        st.dataframe(final_df)

        if st.button("Download Video Excel"):
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


# --------------------------------------------
#         LIVE VIDEO ATTENDANCE
# --------------------------------------------
if mode == "Live Video Attendance":
    st.header("📡 Live Video Attendance")

    details = class_subject_time_selector()

    present, done = live_attendance_ui()

    if done:
        students = load_students()

        df = pd.DataFrame([
            {"Student ID": s["id"], "Name": s["name"], "Present": present[s["id"]]}
            for s in students
        ])

        st.subheader("Live Attendance Result")
        st.dataframe(df)

        st.subheader("Manual Correction")
        final_df = manual_attendance_ui(students, present)

        st.subheader("Final Attendance Sheet")
        st.dataframe(final_df)

        if st.button("Download Live Excel"):
            buf = BytesIO()
            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]
            final_df.to_excel(buf, index=False)
            buf.seek(0)

            st.download_button(
                "Download File",
                data=buf,
                file_name="live_attendance.xlsx"
            )
