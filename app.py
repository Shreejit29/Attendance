# app.py (Final JSON-based master)
import os
import streamlit as st
from io import BytesIO

from auth import login_user, create_user
from storage import add_student, load_students, save_attendance
from face_utils import load_image_from_bytes, get_face_embedding, find_faces_in_image, cosine_similarity, draw_boxes
from manual_attendance import manual_attendance_ui
from class_selector import class_subject_time_selector
from video_attendance import video_attendance_ui
from admin_management import admin_panel_ui
from dashboard import dashboard_ui
from student_portal import student_portal
from teacher_portal import teacher_portal
from signup import signup_ui

if "user" not in st.session_state:
    st.session_state.user = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False
if "signup_captures" not in st.session_state:
    st.session_state.signup_captures = []
if "admin_register_caps" not in st.session_state:
    st.session_state.admin_register_caps = []
if "teacher_captures" not in st.session_state:
    st.session_state.teacher_captures = []

def top_bar():
    if st.session_state.user:
        col1, col2 = st.columns([6,1])
        with col1:
            st.write(f"### 👤 Logged in as: {st.session_state.user['username']} ({st.session_state.user.get('role','')})")
        with col2:
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.show_signup = False
                st.stop()

def login_ui():
    st.subheader("🔐 Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome {user['username']}!")
            return
        else:
            st.error("Invalid credentials.")
    if st.button("Create New Account"):
        st.session_state.show_signup = True

if st.session_state.user is None and st.session_state.show_signup:
    signup_ui()
    st.stop()
if st.session_state.user is None and not st.session_state.show_signup:
    login_ui()
    st.stop()
if st.session_state.user is None:
    st.stop()

top_bar()
role = st.session_state.user.get("role")
username = st.session_state.user.get("username")

if role == "student":
    student_portal(username)
    st.stop()
if role == "teacher":
    teacher_portal(username)
    st.stop()

mode = st.sidebar.selectbox("Choose Option", ["Register Student (Face)", "Take Attendance (Image)", "Take Attendance From Video", "Live Mobile Camera (WebRTC)", "Dashboard", "Admin Panel"])

if mode == "Register Student (Face)":
    st.header("Register Student (Admin)")
    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")
    programme = st.selectbox("Programme", ["BSc","BA","BCom","MSc","MA","Custom"])
    if programme == "Custom":
        programme = st.text_input("Enter Programme")
    student_class = st.text_input("Class (e.g., FYBSc A)")
    uploads = st.file_uploader("Upload 1 or more photos", type=["jpg","png"], accept_multiple_files=True)
    if "admin_register_caps" not in st.session_state:
        st.session_state["admin_register_caps"] = []
    if st.button("Capture New Photo (Admin)"):
        cap = st.camera_input("Capture Photo", key=f"admin_reg_cap_{len(st.session_state['admin_register_caps'])}")
        if cap:
            st.session_state["admin_register_caps"].append(cap)
    images = []
    if uploads:
        for f in uploads:
            images.append(load_image_from_bytes(f.getvalue()))
    for cap in st.session_state["admin_register_caps"]:
        images.append(load_image_from_bytes(cap.getvalue()))
    if st.button("Register Student"):
        if not all([name, sid, programme, student_class]):
            st.error("Fill all fields.")
        else:
            if len(images) == 0:
                st.error("Provide at least one photo.")
            else:
                embeddings = []
                for img in images:
                    emb = get_face_embedding(img)
                    if emb:
                        embeddings.append(emb)
                if len(embeddings) == 0:
                    st.error("No faces found.")
                else:
                    add_student(sid, name, programme, student_class, embeddings)
                    st.success(f"Registered {name} with {len(embeddings)} samples.")
                    st.session_state["admin_register_caps"] = []

elif mode == "Take Attendance (Image)":
    st.header("Image Attendance (Admin)")
    details = class_subject_time_selector()
    upload = st.file_uploader("Upload Class Photo", type=["jpg","png"])
    capture = st.camera_input("Or Capture")
    if upload or capture:
        img = load_image_from_bytes((capture or upload).getvalue())
        detections = find_faces_in_image(img)
        students = load_students()
        present = {s["id"]: False for s in students}
        boxes, labels = [], []
        for emb, box in detections:
            boxes.append(box)
            best_sim = 0
            best_id = None
            best_name = "Unknown"
            for s in students:
                for st_emb in s.get("embeddings", []):
                    sim = cosine_similarity(emb, st_emb)
                    if sim > 0.55 and sim > best_sim:
                        best_sim = sim
                        best_id = s["id"]
                        best_name = s["name"]
            labels.append(best_name)
            if best_id:
                present[best_id] = True
        st.image(draw_boxes(img, boxes, labels), use_column_width=True)
        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details.get("class","")
        final_df["Programme"] = [s.get("programme","") for s in students]
        final_df["Subject"] = details.get("subject","")
        final_df["Time"] = details.get("time","")
        admin_panel_ui(final_df, details.get("class",""), details.get("subject",""))
        if st.button("Save Attendance Permanently"):
            path = save_attendance(details.get("class",""), details.get("subject",""), final_df)
            st.success(f"Saved to {path}")
        if st.button("Download Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf, file_name="attendance_image.xlsx")

elif mode == "Take Attendance From Video":
    st.header("Video Attendance (Admin)")
    details = class_subject_time_selector()
    present, processed = video_attendance_ui()
    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details.get("class","")
        final_df["Subject"] = details.get("subject","")
        final_df["Time"] = details.get("time","")
        admin_panel_ui(final_df, details.get("class",""), details.get("subject",""))
        if st.button("Save Video Attendance Permanently"):
            path = save_attendance(details.get("class",""), details.get("subject",""), final_df)
            st.success(f"Saved to {path}")

elif mode == "Live Mobile Camera (WebRTC)":
    st.header("Live Mobile Camera (Admin)")
    from live_webrtc_attendance import live_webrtc_attendance_ui
    details = class_subject_time_selector()
    present, processed = live_webrtc_attendance_ui()
    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details.get("class","")
        final_df["Subject"] = details.get("subject","")
        final_df["Time"] = details.get("time","")
        admin_panel_ui(final_df, details.get("class",""), details.get("subject",""))
        if st.button("Save Live Attendance Permanently"):
            path = save_attendance(details.get("class",""), details.get("subject",""), final_df)
            st.success(f"Saved to {path}")

elif mode == "Dashboard":
    st.header("Dashboard")
    dashboard_ui()

elif mode == "Admin Panel":
    st.header("Admin Panel")
    admin_panel_ui()
