# app.py — Final master app (Storage API everywhere)
# Smart Attendance System — Clean Final Version (Option A)
# Uses Streamlit Storage API for permanent data (no JSON files)

import os
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# Internal modules (must be in repository)
from auth import login_user, create_user
from storage import add_student, load_students, save_attendance
from face_utils import (
    load_image_from_bytes,
    get_face_embedding,
    find_faces_in_image,
    cosine_similarity,
    draw_boxes,
)
from manual_attendance import manual_attendance_ui
from class_selector import class_subject_time_selector
from video_attendance import video_attendance_ui
from admin_management import admin_panel_ui
from dashboard import dashboard_ui
from student_portal import student_portal
from teacher_portal import teacher_portal
from signup import signup_ui

# Optional logo (showing is optional)
LOGO_PATH = "/mnt/data/c5faf612-92da-468e-9e38-a88bf4e9e287.png"

# ---------------------------------------------------------------------
# SESSION-STATE INITIALIZATION
# ---------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# prepare multi-photo capture storages
if "signup_captures" not in st.session_state:
    st.session_state["signup_captures"] = []

if "admin_register_caps" not in st.session_state:
    st.session_state["admin_register_caps"] = []

if "teacher_captures" not in st.session_state:
    st.session_state["teacher_captures"] = []

# ---------------------------------------------------------------------
# TOP BAR (user display + logout)
# ---------------------------------------------------------------------
def top_bar():
    if st.session_state.user:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"### 👤 Logged in as: {st.session_state.user['username']} ({st.session_state.user.get('role','')})")
        with col2:
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.show_signup = False
                # clear temporary captures to be safe
                st.session_state["signup_captures"] = []
                st.session_state["admin_register_caps"] = []
                st.session_state["teacher_captures"] = []
                st.stop()

# ---------------------------------------------------------------------
# LOGIN UI (uses auth.login_user)
# ---------------------------------------------------------------------
def login_ui():
    st.subheader("🔐 Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_button"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome {user['username']}!")
            return
        else:
            st.error("Invalid username or password.")

    st.markdown("---")
    if st.button("Create New Account", key="goto_signup"):
        st.session_state.show_signup = True
        return

# ---------------------------------------------------------------------
# SHOW LOGIN OR SIGNUP
# ---------------------------------------------------------------------
if st.session_state.user is None and st.session_state.show_signup:
    signup_ui()
    st.stop()

if st.session_state.user is None and not st.session_state.show_signup:
    login_ui()
    st.stop()

# Safety guard
if st.session_state.user is None:
    st.stop()

# Show top bar
top_bar()

role = st.session_state.user.get("role")
username = st.session_state.user.get("username")

# ROUTE to role-specific portals
if role == "student":
    student_portal(username)
    st.stop()

if role == "teacher":
    teacher_portal(username)
    st.stop()

# Admin (default) UI
mode = st.sidebar.selectbox("Choose Option", [
    "Register Student (Face)",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Live Mobile Camera (WebRTC)",
    "Dashboard",
    "Admin Panel"
])

# ---------------------------------------------------------------------
# REGISTER STUDENT (ADMIN) — MULTI-IMAGE SUPPORT
# ---------------------------------------------------------------------
if mode == "Register Student (Face)":
    st.header("Register Student (Admin)")

    name = st.text_input("Student Name", key="admin_reg_name")
    sid = st.text_input("Student ID", key="admin_reg_id")

    programme = st.selectbox("Programme", [
        "BSc", "BA", "BCom", "MSc", "MA", "Custom"
    ], key="admin_reg_programme")
    if programme == "Custom":
        programme = st.text_input("Enter Programme", key="admin_reg_programme_custom")

    student_class = st.text_input("Class (e.g., FYBSc A)", key="admin_reg_class")

    st.write("### Upload Multiple Photos (optional)")
    uploads = st.file_uploader(
        "Upload 1 or more student photos",
        type=["jpg", "png"],
        accept_multiple_files=True,
        key="admin_register_uploads"
    )

    st.write("### Or Capture Multiple Photos")
    if "admin_register_caps" not in st.session_state:
        st.session_state["admin_register_caps"] = []

    if st.button("Capture New Photo (Admin)", key="admin_register_capture"):
        cap_key = f"admin_reg_cap_{len(st.session_state['admin_register_caps'])}"
        cap = st.camera_input("Capture Photo", key=cap_key)
        if cap:
            st.session_state["admin_register_caps"].append(cap)

    # Collect images
    images = []
    if uploads:
        for f in uploads:
            try:
                images.append(load_image_from_bytes(f.getvalue()))
            except:
                continue

    for cap in st.session_state["admin_register_caps"]:
        try:
            images.append(load_image_from_bytes(cap.getvalue()))
        except:
            continue

    if st.button("Register Student (Admin)", key="admin_register_button"):
        if not all([name, sid, programme, student_class]):
            st.error("Please fill all fields.")
        else:
            if len(images) == 0:
                st.error("Please upload or capture at least one photo.")
            else:
                embeddings = []
                for img in images:
                    try:
                        emb = get_face_embedding(img)
                        if emb:
                            embeddings.append(emb)
                    except:
                        continue

                if len(embeddings) == 0:
                    st.error("No valid faces detected in provided images.")
                else:
                    add_student(
                        sid=sid,
                        name=name,
                        programme=programme,
                        student_class=student_class,
                        embeddings=embeddings
                    )
                    st.success(f"Registered {name} with {len(embeddings)} face samples!")
                    # clear admin captures so new registration starts fresh
                    st.session_state["admin_register_caps"] = []

# ---------------------------------------------------------------------
# ADMIN: IMAGE ATTENDANCE (single image default)
# ---------------------------------------------------------------------
elif mode == "Take Attendance (Image)":
    st.header("🖼 Image Attendance (Admin)")
    details = class_subject_time_selector()

    upload = st.file_uploader("Upload Class Photo", type=["jpg", "png"], key="admin_single_image")
    capture = st.camera_input("Or Capture", key="admin_single_capture")

    if upload or capture:
        img = load_image_from_bytes((capture or upload).getvalue())
        detections = find_faces_in_image(img)

        students = load_students()
        present = {s["id"]: False for s in students}
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

        st.image(draw_boxes(img, boxes, labels), use_column_width=True)

        final_df = manual_attendance_ui(students, present)
        # Ensure required metadata columns
        final_df["Class"] = details.get("class", "")
        final_df["Programme"] = [s.get("programme", "") for s in students]
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        # Admin panel UI (view/save etc.)
        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

        # Save attendance permanently
        if st.button("Save Attendance Permanently"):
            key = save_attendance(details.get("class", ""), details.get("subject", ""), final_df)
            st.success(f"Saved attendance under key: {key}")

        # Download option
        if st.button("Download Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf, file_name="attendance_image.xlsx")

# ---------------------------------------------------------------------
# ADMIN: VIDEO ATTENDANCE
# ---------------------------------------------------------------------
elif mode == "Take Attendance From Video":
    st.header("📹 Video Attendance (Admin)")
    details = class_subject_time_selector()
    present, processed = video_attendance_ui()

    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details.get("class", "")
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

        if st.button("Save Video Attendance Permanently"):
            key = save_attendance(details.get("class", ""), details.get("subject", ""), final_df)
            st.success(f"Saved attendance under key: {key}")

# ---------------------------------------------------------------------
# LIVE MOBILE CAMERA (WebRTC) — ADMIN
# ---------------------------------------------------------------------
elif mode == "Live Mobile Camera (WebRTC)":
    st.header("📱 Live Mobile Camera Attendance (WebRTC) — Admin")
    from live_webrtc_attendance import live_webrtc_attendance_ui  # local import

    details = class_subject_time_selector()
    present, processed = live_webrtc_attendance_ui()

    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details.get("class", "")
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

        if st.button("Save Live Attendance Permanently"):
            key = save_attendance(details.get("class", ""), details.get("subject", ""), final_df)
            st.success(f"Saved attendance under key: {key}")

# ---------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------
elif mode == "Dashboard":
    st.header("📊 Dashboard")
    dashboard_ui()

# ---------------------------------------------------------------------
# ADMIN PANEL
# ---------------------------------------------------------------------
elif mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()

# ---------------------------------------------------------------------
# END OF FILE
# ---------------------------------------------------------------------
