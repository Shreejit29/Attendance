# ===========================================================
# Smart Attendance System - FINAL CLEAN VERSION (Plan B)
# With Signup + Login + Role Routing + Logout + User Display
# Added: Security Level (low/medium/high) with password rules and login-attempt limits.
# ===========================================================

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# INTERNAL MODULES (must exist in repo)
from auth import login_user, create_user
from storage import add_student, load_students
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

# Optional logo
LOGO_PATH = "/mnt/data/c5faf612-92da-468e-9e38-a88bf4e9e287.png"

# -----------------------------------------------------------
# INITIALIZE SESSION
# -----------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# prepare signup captures storage
if "signup_captures" not in st.session_state:
    st.session_state["signup_captures"] = []

# prepare temporary teacher capture storage
if "teacher_captures" not in st.session_state:
    st.session_state["teacher_captures"] = []

# prepare admin register captures
if "admin_register_caps" not in st.session_state:
    st.session_state["admin_register_caps"] = []

# -----------------------------------------------------------
# Helper: Security configuration (stored permanently)
# -----------------------------------------------------------
def get_security_level():
    lvl = st.storage.read("security_level")
    return lvl if lvl in ("low", "medium", "high") else "low"

def set_security_level(level):
    st.storage.write("security_level", level)

def max_login_attempts_for_level(level):
    return {"low": 10, "medium": 5, "high": 3}.get(level, 10)

# -----------------------------------------------------------
# Logout / Top bar
# -----------------------------------------------------------
def top_bar():
    if st.session_state.user:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"### 👤 Logged in as: {st.session_state.user['username']} ({st.session_state.user.get('role','')})")
        with col2:
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.show_signup = False
                st.stop()

# -----------------------------------------------------------
# SIGNUP UI (multi-image support for students + password policy)
# -----------------------------------------------------------
def signup_ui():
    st.header("🆕 Create Account (Students: upload/capture face photos)")

    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input("Choose Username", key="signup_username")
        password = st.text_input("Choose Password", type="password", key="signup_password")
        role = st.selectbox("Role", ["student", "teacher", "admin"], key="signup_role")
        programme = st.text_input("Programme (Optional)", key="signup_programme")
        student_class = st.text_input("Class (Optional)", key="signup_class")
    with col2:
        if LOGO_PATH and st.button("Show Logo", key="signup_show_logo"):
            st.image(LOGO_PATH, use_column_width=True)

    # show current security level info
    sec_level = get_security_level()
    st.info(f"Security level: **{sec_level}** — affects password rules and login limits.")

    # -----------------------------
    # MULTI-IMAGE SUPPORT FOR STUDENTS
    # -----------------------------
    images = []

    if role == "student":
        st.write("### 📸 Upload or Capture MULTIPLE Photos")

        # Upload multiple files (optional)
        uploads = st.file_uploader(
            "Upload photos",
            type=["jpg", "png"],
            accept_multiple_files=True,
            key="signup_multi_upload"
        )
        if uploads:
            for f in uploads:
                try:
                    images.append(load_image_from_bytes(f.getvalue()))
                except:
                    continue

        # Unlimited capture flow via session_state
        st.write("### OR Capture Photos (use camera multiple times)")
        if st.button("Capture New Photo", key="signup_capture_new"):
            cap_key = f"signup_cap_{len(st.session_state['signup_captures'])}"
            cap = st.camera_input("Take Photo", key=cap_key)
            if cap:
                st.session_state["signup_captures"].append(cap)

        # show previews of captured images and add them to images list
        if st.session_state["signup_captures"]:
            cols = st.columns(min(4, len(st.session_state["signup_captures"])))
            for idx, cap in enumerate(st.session_state["signup_captures"]):
                try:
                    cols[idx % len(cols)].image(cap, width=150, caption=f"Captured {idx+1}")
                    images.append(load_image_from_bytes(cap.getvalue()))
                except:
                    continue

        if st.button("Clear Captured Photos", key="signup_clear_caps"):
            st.session_state["signup_captures"] = []

    # -----------------------------
    # CREATE ACCOUNT BUTTON
    # -----------------------------
    if st.button("Create Account", key="signup_create"):
        # Basic validation
        if not username or not password:
            st.error("Username and password are required.")
            return

        # Enforce password policy according to security level
        level = get_security_level()
        if level == "high":
            if len(password) < 10 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
                st.error("High security requires: min length 10, at least one uppercase letter, and one digit.")
                return
        elif level == "medium":
            if len(password) < 8:
                st.error("Medium security requires password of at least 8 characters.")
                return
        else:  # low
            if len(password) < 6:
                st.error("Low security requires password of at least 6 characters.")
                return

        # If student, must provide at least one image
        if role == "student" and len(images) == 0:
            st.error("Students must upload or capture at least one face photo.")
            return

        ok, msg = create_user(username, password, role, programme, student_class)
        if not ok:
            st.error(msg)
            return

        # process student images and save embeddings
        if role == "student":
            embeddings = []
            for img in images:
                try:
                    emb = get_face_embedding(img)
                    if emb:
                        embeddings.append(emb)
                except:
                    continue

            if len(embeddings) == 0:
                st.error("No valid face detected in any uploaded images.")
                return

            add_student(
                sid=username,
                name=username,
                programme=programme,
                student_class=student_class,
                embeddings=embeddings
            )

            st.success(f"Student registered with {len(embeddings)} face samples!")

        else:
            st.success("Account created successfully!")

        # auto-login
        st.session_state.user = {
            "username": username,
            "role": role,
            "programme": programme,
            "class": student_class
        }
        st.session_state.show_signup = False
        # clear signup captures to avoid reuse
        st.session_state["signup_captures"] = []
        return

# -----------------------------------------------------------
# LOGIN UI (with login-attempt limits based on security level)
# -----------------------------------------------------------
def login_ui():
    st.subheader("🔐 Login")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    # read security level and attempt counts
    sec_level = get_security_level()
    max_attempts = max_login_attempts_for_level(sec_level)

    # load attempt dict from storage (persistent)
    attempts = st.storage.read("login_attempts") or {}

    # check lockout
    user_attempts = attempts.get(username, 0)
    if user_attempts >= max_attempts:
        st.error(f"Account locked due to {user_attempts} failed attempts (security level: {sec_level}). Contact admin.")
        return

    if st.button("Login", key="login_button"):
        user = login_user(username, password)
        if user:
            # reset attempts
            attempts[username] = 0
            st.storage.write("login_attempts", attempts)
            st.session_state.user = user
            st.success(f"Welcome {user['username']}!")
            return
        else:
            # increment attempts and persist
            attempts[username] = attempts.get(username, 0) + 1
            st.storage.write("login_attempts", attempts)
            remaining = max_attempts - attempts[username]
            if remaining <= 0:
                st.error("Invalid credentials. Account locked due to repeated failures.")
            else:
                st.error(f"Invalid username or password. Attempts left: {remaining}")

    st.markdown("---")
    if st.button("Create New Account", key="goto_signup"):
        st.session_state.show_signup = True
        return

# -----------------------------------------------------------
# SHOW LOGIN OR SIGNUP FIRST
# -----------------------------------------------------------
if st.session_state.user is None and st.session_state.show_signup:
    signup_ui()
    st.stop()

if st.session_state.user is None and not st.session_state.show_signup:
    login_ui()
    st.stop()

# -----------------------------------------------------------
# SAFETY GUARD BEFORE ROLE ROUTING
# -----------------------------------------------------------
if st.session_state.user is None:
    st.stop()

# Show top bar (user & logout)
top_bar()

role = st.session_state.user["role"]
username = st.session_state.user["username"]

# -----------------------------------------------------------
# ADMIN: quick security controls (only visible to admin)
# -----------------------------------------------------------
if role == "admin":
    with st.sidebar.expander("🔒 Security Settings (Admin only)", expanded=False):
        current = get_security_level()
        new = st.selectbox("Security Level", ["low", "medium", "high"], index=["low","medium","high"].index(current))
        if st.button("Save Security Level"):
            set_security_level(new)
            st.success(f"Security level set to: {new}")
            # also reset login attempts when raising security, to avoid accidental lockouts
            if new in ("medium","high"):
                st.storage.write("login_attempts", {})

# -----------------------------------------------------------
# STUDENT PORTAL
# -----------------------------------------------------------
if role == "student":
    student_portal(username)
    st.stop()

# -----------------------------------------------------------
# TEACHER PORTAL
# -----------------------------------------------------------
if role == "teacher":
    teacher_portal(username)
    st.stop()

# -----------------------------------------------------------
# ADMIN PORTAL
# -----------------------------------------------------------
mode = st.sidebar.selectbox("Choose Option", [
    "Register Student (Face)",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Live Mobile Camera (WebRTC)",
    "Dashboard",
    "Admin Panel"
])

# ---------------------------------------------------------
# REGISTER STUDENT (ADMIN) — MULTI-IMAGE SUPPORT
# ---------------------------------------------------------
if mode == "Register Student (Face)":
    st.header("Register Student (Admin)")

    name = st.text_input("Student Name")
    sid = st.text_input("Student ID")

    programme = st.selectbox("Programme", [
        "BSc", "BA", "BCom", "MSc", "MA", "Custom"
    ])
    if programme == "Custom":
        programme = st.text_input("Enter Programme")

    student_class = st.text_input("Class (e.g., FYBSc A, SYBCom B)")

    st.write("### Upload Multiple Photos for Better Accuracy")
    uploads = st.file_uploader(
        "Upload 1 or more student photos",
        type=["jpg", "png"],
        accept_multiple_files=True,
        key="admin_register_uploads"
    )

    st.write("### OR Capture Multiple Photos")
    if "admin_register_caps" not in st.session_state:
        st.session_state["admin_register_caps"] = []

    if st.button("Capture New Photo (Admin)", key="admin_register_capture"):
        cap_key = f"admin_reg_cap_{len(st.session_state['admin_register_caps'])}"
        cap = st.camera_input("Capture Photo", key=cap_key)
        if cap:
            st.session_state["admin_register_caps"].append(cap)

    # collect images
    images = []
    # from uploads
    if uploads:
        for f in uploads:
            try:
                images.append(load_image_from_bytes(f.getvalue()))
            except:
                continue
    # from admin captures
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
                    st.error("No valid faces detected.")
                else:
                    add_student(
                        sid=sid,
                        name=name,
                        programme=programme,
                        student_class=student_class,
                        embeddings=embeddings
                    )
                    st.success(f"Registered {name} with {len(embeddings)} samples!")

# ------ ADMIN: IMAGE ATTENDANCE (single-image kept for admin by default) ------
elif mode == "Take Attendance (Image)":
    st.header("🖼 Image Attendance (Admin)")
    details = class_subject_time_selector()

    upload = st.file_uploader("Upload Class Photo", type=["jpg","png"], key="admin_single_image")
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
        final_df["Class"] = details.get("class", "")
        final_df["Programme"] = [s.get("programme", "") for s in students]
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

# ------ ADMIN: VIDEO ATTENDANCE ------
elif mode == "Take Attendance From Video":
    st.header("📹 Video Attendance")
    details = class_subject_time_selector()
    present, processed = video_attendance_ui()

    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details.get("class", "")
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

# ---------------------------------------------------------
# LIVE MOBILE CAMERA ATTENDANCE (WebRTC)
# ---------------------------------------------------------
elif mode == "Live Mobile Camera (WebRTC)":
    st.header("📱 Live Mobile Camera Attendance (WebRTC)")

    from live_webrtc_attendance import live_webrtc_attendance_ui

    details = class_subject_time_selector()

    present, processed = live_webrtc_attendance_ui()

    if processed:
        students = load_students()
        final_df = manual_attendance_ui(students, present)

        final_df["Class"] = details.get("class", "")
        final_df["Subject"] = details.get("subject", "")
        final_df["Time"] = details.get("time", "")

        admin_panel_ui(final_df, details.get("class", ""), details.get("subject", ""))

# ------ ADMIN: DASHBOARD ------
elif mode == "Dashboard":
    st.header("📊 Dashboard")
    dashboard_ui()

# ------ ADMIN: ADMIN PANEL ------
elif mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
