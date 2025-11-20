import streamlit as st
import pandas as pd
from face_utils import load_image_from_bytes, get_face_embedding, find_faces_in_image, compare_embeddings, draw_boxes
from storage import add_student, load_students
from io import BytesIO
from datetime import datetime

st.title("📘 Smart Attendance System (DeepFace)")

mode = st.sidebar.selectbox("Menu", ["Register Student", "Take Attendance"])

# -------------------- REGISTER STUDENT ----------------------
if mode == "Register Student":
    st.header("Register Student")

    name = st.text_input("Student Name")
    sid  = st.text_input("Student ID")
    upload = st.file_uploader("Upload student photo", type=["jpg","png"])
    capture = st.camera_input("Or capture photo")

    if st.button("Register"):
        if not sid or not name:
            st.error("Enter name & student ID")
        else:
            src = capture or upload
            if not src:
                st.error("Upload/capture photo")
            else:
                img = load_image_from_bytes(src.getvalue())
                emb = get_face_embedding(img)
                if emb:
                    add_student(sid, name, emb)
                    st.success("Student registered successfully!")
                else:
                    st.error("No face detected. Try another photo.")

# --------------------- TAKE ATTENDANCE ----------------------
if mode == "Take Attendance":
    st.header("Upload classroom photo")

    upload = st.file_uploader("Upload class photo", type=["jpg","png"])
    capture = st.camera_input("Or capture class photo")

    if upload or capture:
        img_bytes = (capture or upload).getvalue()
        img = load_image_from_bytes(img_bytes)

        faces = find_faces_in_image(img)

        students = load_students()
        present = {s["id"]: False for s in students}

        boxes = []
        labels = []

        for emb, box in faces:
            boxes.append((box["x"], box["y"], box["w"], box["h"]))

            matched = "Unknown"

            for s in students:
                for st_emb in s["embeddings"]:
                    ok, dist = compare_embeddings(emb, st_emb)
                    if ok:
                        matched = s["name"]
                        present[s["id"]] = True
                        break

            labels.append(matched)

        out_img = draw_boxes(img, boxes, labels)
        st.image(out_img, caption="Detected Faces", use_column_width=True)

        # CREATE ATTENDANCE TABLE
        df = pd.DataFrame([{
            "Student ID": s["id"],
            "Name": s["name"],
            "Present": present[s["id"]]
        } for s in students])

        st.subheader("Attendance Sheet")
        st.dataframe(df)

        if st.button("Download Excel"):
            buf = BytesIO()
            df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download", data=buf, file_name="attendance.xlsx")

