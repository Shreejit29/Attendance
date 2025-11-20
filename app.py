"""
app.py
Main Streamlit app for the Smart Attendance App.
"""
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import uuid

from face_utils import load_image_from_bytes, face_encodings_from_image, find_faces_in_class_image, match_encoding, draw_bounding_boxes
from storage import add_student, get_student_list

st.set_page_config(page_title="Smart Attendance", layout="wide")

st.title("📚 Smart Attendance (Streamlit)")

# Sidebar: mode
mode = st.sidebar.selectbox("Mode", ["Register Student", "Take Attendance", "View / Export"])

if mode == "Register Student":
    st.header("Register new student")
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("Full name")
        student_id = st.text_input("Student ID (unique)")
        photo_upload = st.file_uploader("Upload a photo (jpg/png)", type=["jpg","jpeg","png"])
        capture = st.camera_input("Or capture from camera (browser)")
    with col2:
        st.write("Tips for better recognition:")
        st.write("- Provide clear, front-facing photo(s).")
        st.write("- Prefer 2-3 photos per student (different angles).")
        add_btn = st.button("Register / Add encoding")
    if add_btn:
        if not student_name or not student_id:
            st.error("Provide name and student ID.")
        else:
            added = False
            encs = []
            image_bytes = None
            for src in [capture, photo_upload]:
                if src:
                    # src is BytesIO-like in Streamlit
                    image_bytes = src.getvalue()
                    try:
                        img = load_image_from_bytes(image_bytes)
                        e = face_encodings_from_image(img)
                        if e:
                            encs.extend(e)
                            added = True
                        else:
                            st.warning("No face found in one of the provided images.")
                    except Exception as e:
                        st.error(f"Image processing error: {e}")
            if added and encs:
                add_student(student_id, student_name, encodings=encs, image_bytes=image_bytes)
                st.success(f"Registered {student_name} ({student_id}) with {len(encs)} encodings.")
            else:
                st.error("No face encodings captured. Try clearer photos or more images.")

elif mode == "Take Attendance":
    st.header("Take attendance (auto from photos)")
    st.write("Upload one or more class photos or capture realtime with camera.")
    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload class photo(s)", type=["jpg","jpeg","png"], accept_multiple_files=True)
        cam = st.camera_input("Or capture a photo")
        clear_button = st.button("Clear previous session data")
    with col2:
        tolerance = st.slider("Matching tolerance (lower = stricter)", 0.3, 0.7, 0.5)
        show_boxes = st.checkbox("Show bounding boxes & labels", True)

    # load known students
    students = get_student_list()
    known_encodings = []
    known_meta = []
    for s in students:
        for enc in s["encodings"]:
            known_encodings.append(enc)
            known_meta.append({"id": s["id"], "name": s["name"]})
    # Prepare attendance table
    attendance = {}
    for s in students:
        attendance[s["id"]] = {"name": s["name"], "id": s["id"], "present": False}

    # gather images
    images = []
    if uploaded:
        for f in uploaded:
            try:
                images.append((f.name, f.getvalue()))
            except Exception:
                st.warning(f"Could not read {f.name}")
    if cam:
        images.append(("camera_capture", cam.getvalue()))

    if images:
        faces_found = []
        for fname, blob in images:
            img_rgb = load_image_from_bytes(blob)
            faces = find_faces_in_class_image(img_rgb)
            locations = [loc for loc,enc in faces]
            encs = [enc for loc,enc in faces]
            labels = []
            for enc in encs:
                idx = match_encoding(known_encodings, enc, tolerance=tolerance)
                if idx is not None:
                    meta = known_meta[idx]
                    labels.append(meta["name"])
                    # Mark that student present (set True)
                    attendance[meta["id"]]["present"] = True
                else:
                    labels.append("Unknown")
            faces_found.append((img_rgb, locations, labels))
            # show image with boxes
            if show_boxes:
                boxed = draw_bounding_boxes(img_rgb, locations, labels)
                st.image(boxed, caption=f"Detected faces in {fname}", use_column_width=True)
            else:
                st.image(img_rgb, caption=f"{fname}", use_column_width=True)

        # Show automatic attendance summary
        st.subheader("Automatic attendance (detected)")
        df = pd.DataFrame([{"Student ID": v["id"], "Name": v["name"], "Present": v["present"]} for v in attendance.values()])
        edited = st.dataframe(df)

        # Manual corrections
        st.subheader("Manual corrections")
        # create editable table via session state
        if "attendance_df" not in st.session_state:
            st.session_state["attendance_df"] = df
        edited_df = st.experimental_data_editor(st.session_state["attendance_df"], num_rows="dynamic")
        st.session_state["attendance_df"] = edited_df

        # Export to excel
        if st.button("Export attendance to Excel"):
            out = BytesIO()
            today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            # use the current edited df
            final_df = st.session_state["attendance_df"]
            final_df.to_excel(out, index=False, sheet_name=f"Attendance_{today}")
            out.seek(0)
            st.download_button("Download Excel", data=out, file_name=f"attendance_{today}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No class photos yet. Upload or capture a photo.")

elif mode == "View / Export":
    st.header("Registered students")
    students = get_student_list()
    if not students:
        st.info("No students registered yet.")
    else:
        df = pd.DataFrame([{"Student ID": s["id"], "Name": s["name"], "Num encodings": len(s["encodings"])} for s in students])
        st.dataframe(df)
        if st.button("Export students to CSV"):
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download students CSV", data=csv, file_name="students.csv", mime="text/csv")
