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
from io import BytesIO
from datetime import datetime

st.title("📘 Smart Attendance System (InsightFace - TensorFlow Free)")

mode = st.sidebar.selectbox("Menu", ["Register Student", "Take Attendance"])


# ==================================================
#                 REGISTER STUDENT
# ==================================================
if mode == "Register Student":
    st.header("Register Student")

    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")
    upload = st.file_uploader("Upload student photo", type=["jpg", "png"])
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


# ==================================================
#                 TAKE ATTENDANCE
# ==================================================
if mode == "Take Attendance":
    st.header("Take Attendance")

    # --------------------------------------------
    # Select Class, Subject, Time
    # --------------------------------------------
    details = class_subject_time_selector()

    st.write("---")

    upload = st.file_uploader("Upload class photo", type=["jpg", "png"])
    capture = st.camera_input("Or capture class photo")

    if upload or capture:
        img = load_image_from_bytes((capture or upload).getvalue())

        detected = find_faces_in_image(img)  # faces + embeddings
        students = load_students()
        present = {s["id"]: False for s in students}

        boxes = []
        labels = []

        # --------------------------------------------
        # Automatic attendance matching
        # --------------------------------------------
        for emb, box in detected:
            boxes.append(box)
            best_name = "Unknown"
            best_sim = 0.0

            for s in students:
                for st_emb in s["embeddings"]:
                    sim = cosine_similarity(emb, st_emb)
                    if sim > 0.55 and sim > best_sim:
                        best_sim = sim
                        best_name = s["name"]
                        present[s["id"]] = True

            labels.append(best_name)

        # --------------------------------------------
        # Display detection with rectangles
        # --------------------------------------------
        out_img = draw_boxes(img, boxes, labels)
        st.image(out_img, use_column_width=True, caption="Detected Faces")

        # --------------------------------------------
        # Automatic attendance table
        # --------------------------------------------
        st.subheader("Automatic Attendance Result")

        auto_df = pd.DataFrame([{
            "Student ID": s["id"],
            "Name": s["name"],
            "Present": present[s["id"]],
        } for s in students])

        st.dataframe(auto_df)

        st.write("### Manual Attendance Correction (If someone was missed)")

        # --------------------------------------------
        # Manual attendance editor
        # --------------------------------------------
        final_df = manual_attendance_ui(students, present)

        # --------------------------------------------
        # Add CLASS / SUBJECT / TIME columns
        # --------------------------------------------
        final_df["Class"] = details["class"]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        st.subheader("Final Attendance Sheet")
        st.dataframe(final_df)

        # --------------------------------------------
        # Excel Export
        # --------------------------------------------
        if st.button("Download Excel"):
            buffer = BytesIO()
            final_df.to_excel(buffer, index=False)
            buffer.seek(0)

            file_name = (
                f"{details['class'].replace(' ', '_')}_"
                f"{details['subject'].replace(' ', '_')}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )

            st.download_button(
                "Download File",
                data=buffer,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
