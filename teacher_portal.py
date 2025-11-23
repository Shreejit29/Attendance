# ============================================================
# teacher_portal.py — Streamlit Storage API Version (FINAL)
# ============================================================

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

    # ======================================================
    # 1️⃣ MULTI-IMAGE TEACHER ATTENDANCE
    # ======================================================
    if choice == "Take Attendance (Image)":

        st.subheader("📸 Multi-Image Attendance (Teacher)")
        details = class_subject_time_selector()

        # Storage for captures
        if "teacher_captures" not in st.session_state:
            st.session_state["teacher_captures"] = []

        # Multiple uploads
        uploads = st.file_uploader(
            "Upload one or more class photos",
            type=["jpg", "png"],
            accept_multiple_files=True,
            key="teacher_multi_upload"
        )

        # Multi-camera capture
        if st.button("📸 Capture New Photo", key="teacher_capture_new"):
            cap = st.camera_input("Take Photo", 
                                  key=f"teacher_cap_{len(st.session_state['teacher_captures'])}")
            if cap:
                st.session_state["teacher_captures"].append(cap)

        images = []

        # Process uploaded images
        if uploads:
            for f in uploads:
                images.append(load_image_from_bytes(f.getvalue()))

        # Show & add captured images
        if st.session_state["teacher_captures"]:
            cols = st.columns(4)
            for idx, cap in enumerate(st.session_state["teacher_captures"]):
                cols[idx % 4].image(cap, width=150)
                images.append(load_image_from_bytes(cap.getvalue()))

        if len(images) == 0:
            st.info("Upload or capture at least one image.")
            return

        # Process Attendance
        if st.button("Process Attendance", key="teacher_process"):

            students = load_students()
            present = {s["id"]: False for s in students}

            st.write(f"### Processing {len(images)} images...\n")

            # Loop through images
            for i, img in enumerate(images, start=1):
                st.write(f"#### Image {i}/{len(images)}")

                detections = find_faces_in_image(img)
                boxes, labels = [], []

                # Face recognition
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

                result_img = draw_boxes(img, boxes, labels)
                st.image(result_img, use_column_width=True)

            # Manual correction
            final_df = manual_attendance_ui(students, present)

            # metadata
            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

            # Optional Excel download
            if st.button("Download Excel", key="teacher_download"):
                buf = BytesIO()
                final_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button("Download Attendance File", buf, 
                                   file_name="teacher_attendance.xlsx")

            # Permanent save (Teacher version)
            if st.button("Save Attendance Permanently", key="teacher_save_storage"):
                key = f"attendance/{details['class']}_{details['subject']}_{details['time']}"
                st.storage.write(key, final_df.to_dict(orient="records"))
                st.success(f"Saved to permanent storage: {key}")

    # ======================================================
    # 2️⃣ VIDEO ATTENDANCE
    # ======================================================
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

            # Permanent save
            if st.button("Save Video Attendance"):
                key = f"attendance/{details['class']}_{details['subject']}_{details['time']}"
                st.storage.write(key, final_df.to_dict(orient="records"))
                st.success(f"Saved under: {key}")

    # ======================================================
    # 3️⃣ LIVE WEBRTC MOBILE CAMERA
    # ======================================================
    if choice == "Live Mobile Camera (WebRTC)":

        st.subheader("📱 Live Mobile Camera Attendance")

        details = class_subject_time_selector()
        present, processed = live_webrtc_attendance_ui()

        if processed:
            students = load_students()
            final_df = manual_attendance_ui(students, present)

            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

            if st.button("Save Live Attendance"):
                key = f"attendance/{details['class']}_{details['subject']}_{details['time']}"
                st.storage.write(key, final_df.to_dict(orient="records"))
                st.success(f"Stored at: {key}")

    # ======================================================
    # 4️⃣ MANAGE STUDENTS
    # ======================================================
    if choice == "Manage Students":

        st.subheader("🧑‍🎓 Manage Students")

        students = load_students()
        df = pd.DataFrame(students)

        st.dataframe(df[["id", "name", "programme", "class"]])

        sid = st.selectbox("Select Student to Delete", df["id"])

        if st.button("Delete Student"):
            delete_student_by_id(sid)
            st.success("Student removed.")
            st.experimental_rerun()
