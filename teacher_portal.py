# teacher_portal.py

import streamlit as st
import pandas as pd
from io import BytesIO

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
from live_webrtc_attendance import live_webrtc_attendance_ui


def teacher_portal(username):
    st.header(f"👨‍🏫 Teacher Portal — {username}")

    choice = st.selectbox("Select Task", [
        "Take Attendance (Image)",
        "Take Attendance (Video)",
        "Live Mobile Camera (WebRTC)",
        "Manage Students"
    ])

    # ============================================
    # MULTI-IMAGE ATTENDANCE — FINAL VERSION
    # ============================================
    if choice == "Take Attendance (Image)":

        st.subheader("📸 Multi-Image Attendance (Teacher)")

        details = class_subject_time_selector()

        # Session storage for captured images
        if "teacher_captures" not in st.session_state:
            st.session_state["teacher_captures"] = []

        # ---- Multiple Uploads ----
        uploads = st.file_uploader(
            "Upload one or more class photos",
            type=["jpg", "png"],
            accept_multiple_files=True,
            key="teacher_multi_upload"
        )

        # ---- Repeated Camera Capture ----
        if st.button("📸 Capture New Photo", key="teacher_capture_button"):
            cap = st.camera_input(
                "Take Photo",
                key=f"teacher_cap_{len(st.session_state['teacher_captures'])}"
            )
            if cap:
                st.session_state["teacher_captures"].append(cap)

        images = []

        # uploaded images
        if uploads:
            for f in uploads:
                images.append(load_image_from_bytes(f.getvalue()))

        # captured images
        for idx, cap in enumerate(st.session_state["teacher_captures"]):
            st.image(cap, width=150, caption=f"Captured {idx+1}")
            images.append(load_image_from_bytes(cap.getvalue()))

        if len(images) == 0:
            st.info("Upload or capture at least one image.")
            st.stop()

        # ---- Process Images ----
        if st.button("Process Attendance", key="teacher_process_button"):

            students = load_students()
            present = {s["id"]: False for s in students}

            st.write(f"### Processing {len(images)} images...")

            for i, img in enumerate(images, start=1):
                st.write(f"#### Image {i}/{len(images)}")

                detections = find_faces_in_image(img)

                boxes, labels = [], []

                for emb, box in detections:
                    boxes.append(box)

                    best_sim = 0
                    best_name = "Unknown"
                    best_id = None

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

                annotated = draw_boxes(img, boxes, labels)
                st.image(annotated, use_column_width=True)

            # ---- Manual correction ----
            final_df = manual_attendance_ui(students, present)

            # metadata
            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

            if st.button("Download Excel", key="teacher_download_button"):
                buf = BytesIO()
                final_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button(
                    "Download Attendance",
                    data=buf,
                    file_name="teacher_multi_image_attendance.xlsx"
                )

    # ============================================
    # VIDEO ATTENDANCE
    # ============================================
    if choice == "Take Attendance (Video)":

        st.subheader("🎥 Video Attendance")

        details = class_subject_time_selector()

        present, processed = video_attendance_ui()

        if processed:
            students = load_students()

            final_df = manual_attendance_ui(students, present)

            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

    # ============================================
    # LIVE WEBRTC MOBILE CAMERA
    # ============================================
    if choice == "Live Mobile Camera (WebRTC)":

        st.subheader("📱 Live Mobile Camera Attendance (WebRTC)")

        details = class_subject_time_selector()

        present, processed = live_webrtc_attendance_ui()

        if processed:
            students = load_students()

            final_df = manual_attendance_ui(students, present)

            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

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

    # ============================================
    # MANAGE STUDENTS
    # ============================================
    if choice == "Manage Students":

        st.subheader("Manage Students")

        students = load_students()
        df = pd.DataFrame(students)

        # FIX: correct column name for class: "class" NOT "student_class"
        st.dataframe(df[["id", "name", "programme", "class"]])

        sid = st.selectbox("Select Student to Delete", df["id"])

        if st.button("Delete Student"):
            delete_student_by_id(sid)
            st.success("Student Deleted Successfully!")
            st.experimental_rerun()
