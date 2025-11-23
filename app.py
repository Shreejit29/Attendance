# ===========================================================
# Smart Attendance System - FINAL CLEAN VERSION (Plan B)
# With Signup + Login + Role Routing + Logout + User Display
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


# -----------------------------------------------------------
# LOGOUT BUTTON + USER DISPLAY
# -----------------------------------------------------------
def top_bar():
    if st.session_state.user:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"### 👤 Logged in as: {st.session_state.user['username']} ({st.session_state.user['role']})")
        with col2:
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.show_signup = False
                # NO experimental_rerun here
                st.stop()   # stop execution → Streamlit safely reruns
# -----------------------------------------------------------
# SIGNUP UI (Plan B: Students upload or capture a photo)
# -----------------------------------------------------------
def signup_ui():
    st.header("🆕 Create Account (Students require face photo)")

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

    # Student photo requirement
    photo = None
    if role == "student":
        st.write("📸 Please upload/capture a clear frontal face photo.")
        upload = st.file_uploader("Upload Photo", type=["jpg","png"], key="signup_upload")
        capture = st.camera_input("Or Capture Photo", key="signup_capture")
        photo = capture or upload

    if st.button("Create Account", key="signup_create"):
        if not username or not password:
            st.error("Username and password are required.")
            return

        if role == "student" and not photo:
            st.error("Students must provide a face photo.")
            return

        ok, msg = create_user(username, password, role, programme, student_class)
        if not ok:
            st.error(msg)
            return

        # For students → register face
        if role == "student":
            try:
                img = load_image_from_bytes(photo.getvalue())
            except:
                st.error("Invalid image file.")
                return

            emb = get_face_embedding(img)
            if emb is None:
                st.error("No face detected—use a clear frontal photo.")
                return

            add_student(
                sid=username,
                name=username,
                programme=programme,
                student_class=student_class,
                embedding=emb
            )

            st.success("Student account + Face registration completed!")

        else:
            st.success("Account created successfully!")

        # Auto-login
        st.session_state.user = {
            "username": username,
            "role": role,
            "programme": programme,
            "class": student_class
        }

        st.session_state.show_signup = False
        return


# -----------------------------------------------------------
# LOGIN UI
# -----------------------------------------------------------
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
    "Live Mobile Camera (WebRTC)",   # <-- NEW
    "Dashboard",
    "Admin Panel"
])
# ---------------------------------------------------------
# REGISTER STUDENT (MULTI-IMAGE SUPPORT)
# ---------------------------------------------------------
if mode == "Register Student":
    st.header("Register Student")

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
        accept_multiple_files=True
    )

    st.write("### OR Capture Multiple Photos")
    capture = st.camera_input("Capture Photo")
    more_caps = st.checkbox("Add another capture")

    captured_images = []
    if capture:
        captured_images.append(capture)

    # Allow second capture
    if more_caps:
        capture2 = st.camera_input("Capture Another Photo")
        if capture2:
            captured_images.append(capture2)

    if st.button("Register"):
        if not all([name, sid, programme, student_class]):
            st.error("Please fill all fields.")
        else:
            images = []

            # Add uploaded images
            if uploads:
                for file in uploads:
                    images.append(load_image_from_bytes(file.getvalue()))

            # Add captured images
            for cap in captured_images:
                images.append(load_image_from_bytes(cap.getvalue()))

            if len(images) == 0:
                st.error("Please upload or capture at least one photo.")
            else:
                embeddings = []
                valid_faces = 0

                for img in images:
                    emb = get_face_embedding(img)
                    if emb:
                        embeddings.append(emb)
                        valid_faces += 1

                if valid_faces == 0:
                    st.error("No valid faces detected in any image. Try again.")
                return

                add_student(
                    sid=sid,
                    name=name,
                    programme=programme,
                    student_class=student_class,
                    embedding=embeddings   # store ALL embeddings
                )

                st.success(f"Successfully registered {name} with {valid_faces} face samples.")


# ------ ADMIN: IMAGE ATTENDANCE ------
elif mode == "Take Attendance (Image)":
    st.header("🖼 Image Attendance")
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
            best_name = "Unknown"
            for s in students:
                for st_emb in s["embeddings"]:
                    sim = cosine_similarity(emb, st_emb)
                    if sim > 0.55 and sim > best_sim:
                        best_sim = sim
                        best_name = s["name"]
                        present[s["id"]] = True
            labels.append(best_name)

        st.image(draw_boxes(img, boxes, labels), use_column_width=True)

        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details["class"]
        final_df["Programme"] = [s.get("programme","") for s in students]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        admin_panel_ui(final_df, details["class"], details["subject"])

# ------ ADMIN: VIDEO ATTENDANCE ------
elif mode == "Take Attendance From Video":
    st.header("📹 Video Attendance")
    details = class_subject_time_selector()
    present, processed = video_attendance_ui()

    if processed:
        students = load_students()
        final_df = pd.DataFrame([
            {
                "Student ID": s["id"],
                "Name": s["name"],
                "Class": s.get("class",""),
                "Programme": s.get("programme",""),
                "Present": present[s["id"]],
            }
            for s in students
        ])
        final_df = manual_attendance_ui(students, present)

        admin_panel_ui(final_df, details["class"], details["subject"])
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

        final_df = pd.DataFrame([
            {
                "Student ID": s["id"],
                "Name": s["name"],
                "Class": s.get("class", ""),
                "Programme": s.get("programme", ""),
                "Present": present[s["id"]],
            }
            for s in students
        ])

        # Manual correction UI
        final_df = manual_attendance_ui(students, present)

        # Save to admin history
        admin_panel_ui(final_df, details["class"], details["subject"])

# ------ ADMIN: DASHBOARD ------
elif mode == "Dashboard":
    st.header("📊 Dashboard")
    dashboard_ui()

# ------ ADMIN: ADMIN PANEL ------
elif mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
