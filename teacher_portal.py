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
        "Take Attendance (Image)",     # Multi-shot attendance
        "Take Attendance (Video)",
        "Live Mobile Camera (WebRTC)",
        "Manage Students"
    ])

    # ============================================
    # MULTI-IMAGE ATTENDANCE (FINAL VERSION)
    # ============================================
    if choice == "Take Attendance (Image)":

        st.subheader("📸 Multi-Image Attendance Capture")

        # Step 1: Choose class, subject, time
        details = class_subject_time_selector()

        # Step 2: Upload / Capture multiple images
        uploads = st.file_uploader(
            "Upload one or more class photos",
            type=["jpg", "png"],
            accept_multiple_files=True
        )

        capture_more = st.camera_input("Or capture a photo")

        # Step 3: Combine all images
        images = []

        if uploads:
            for file in uploads:
                img = load_image_from_bytes(file.getvalue())
                images.append(img)

        if capture_more:
            img = load_image_from_bytes(capture_more.getvalue())
            images.append(img)

        # If at least one image provided
        if len(images) > 0:
            st.info(f"Processing {len(images)} class photos… Please wait.")

            students = load_students()
            present = {s["id"]: False for s in students}

            processed_count = 0

            # Step 4: Process each image
            for img in images:
                processed_count += 1
                st.write(f"### 🖼 Processing Image {processed_count}/{len(images)}")

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

                            # threshold for similarity
                            if sim > 0.55 and sim > best_sim:
                                best_sim = sim
                                best_name = s["name"]
                                best_id = s["id"]

                    labels.append(best_name)

                    # Mark present only once
                    if best_id:
                        present[best_id] = True

                # Show annotated preview
                out_img = draw_boxes(img, boxes, labels)
                st.image(out_img, use_column_width=True)

            st.success(f"Processed {len(images)} photos successfully!")

            # Step 5: Manual correction UI
            final_df = manual_attendance_ui(students, present)

            # Step 6: Add metadata
            final_df["Class"] = details["class"]
            final_df["Subject"] = details["subject"]
            final_df["Time"] = details["time"]

            st.dataframe(final_df)

            # Step 7: Download Excel
            if st.button("Download Excel"):
                buf = BytesIO()
                final_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button(
                    "Download File",
                    data=buf,
                    file_name="teacher_multi_image_attendance.xlsx"
                )

    # ============================================
    # VIDEO ATTENDANCE
    # ============================================
    if choice == "Take Attendance (Video)":
        st.subheader("🎥 Take Attendance From Uploaded Video")

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
    # LIVE WebRTC Mobile Camera Attendance
    # ============================================
    if choice == "Live Mobile Camera (WebRTC)":
        st.subheader("📱 Live Mobile Camera Attendance (WebRTC + Multi-Face Tracking)")

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

        st.dataframe(df[["id", "name", "programme", "student_class"]])

        sid = st.selectbox("Select Student to Delete", df["id"])

        if st.button("Delete Student"):
            delete_student_by_id(sid)
            st.success("Student Deleted Successfully!")
            st.experimental_rerun()
