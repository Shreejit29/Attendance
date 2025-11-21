# app.py (Plan B: Signup also registers student with face embedding)

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# INTERNAL MODULES (must exist in repo)
from auth import login_user, create_user
from storage import add_student, load_students, delete_student_by_id
from face_utils import load_image_from_bytes, get_face_embedding, find_faces_in_image, cosine_similarity, draw_boxes
from manual_attendance import manual_attendance_ui
from class_selector import class_subject_time_selector
from video_attendance import video_attendance_ui
from admin_management import admin_panel_ui
from dashboard import dashboard_ui
from student_portal import student_portal
from teacher_portal import teacher_portal



# ---------------------------
# Session initialisation
# ---------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# ---------------------------
# Page title / header
# ---------------------------
st.set_page_config(page_title="Smart Attendance", layout="wide")
st.title("📘 Smart Attendance System (Plan B)")

# ---------------------------
# SIGNUP UI (Plan B: students provide photo)
# ---------------------------
def signup_ui():
    st.header("🆕 Create Account (Students: photo will be captured)")

    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        role = st.selectbox("Role", ["student", "teacher", "admin"])
        programme = st.text_input("Programme (optional)")
        student_class = st.text_input("Class (optional)")

    with col2:
        if st.button("Show logo (if available)"):
            if LOGO_PATH:
                st.image(LOGO_PATH, use_column_width=True)

    # For students: require a photo (upload or camera)
    photo = None
    if role == "student":
        st.write("Student registration requires a clear frontal photo for attendance matching.")
        photo_upload = st.file_uploader("Upload a clear face photo (jpg/png)", type=["jpg","png"], key="signup_photo_upload")
        photo_capture = st.camera_input("Or capture photo using camera", key="signup_photo_camera")

        # choose the available source
        photo = photo_capture or photo_upload

    if st.button("Create Account"):
        if not username or not password or not role:
            st.error("Username, password and role are required.")
            return

        # for students, photo mandatory
        if role == "student" and not photo:
            st.error("Please provide a photo for student registration.")
            return

        # create login user record
        ok, msg = create_user(username=username, password=password, role=role,
                              programme=programme, student_class=student_class)
        if not ok:
            st.error(msg)
            return

        # if student, create face embedding and save student record
        if role == "student":
            try:
                img = load_image_from_bytes(photo.getvalue())
            except Exception as e:
                st.error(f"Failed to read provided image: {e}")
                return

            emb = get_face_embedding(img)
            if emb is None:
                st.error("No face detected in the provided image. Please upload/capture a clearer frontal face photo.")
                return

            # Use username as student id (or you can prompt for a separate student id)
            sid = username
            name = username
            add_student(sid=sid, name=name, programme=programme, student_class=student_class, embedding=emb)
            st.success("Student account and face registration completed. You can now login.")

        else:
            st.success("Account created. You can now login.")

        # After successful signup, switch back to login view
        st.session_state.show_signup = False
        st.experimental_rerun()


# ---------------------------
# LOGIN UI
# ---------------------------
def login_ui():
    st.subheader("🔐 Login")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome, {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password. If you just signed up, try logging in after a second.")

    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Create New Account"):
            st.session_state.show_signup = True
            st.experimental_rerun()
    with col2:
        if st.button("Use Demo Admin"):
            # convenience: create demo admin if not exists and login
            demo_ok, _ = create_user("admin", "admin", "admin")
            # attempt login
            user = login_user("admin", "admin")
            if user:
                st.session_state.user = user
                st.experimental_rerun()

# ---------------------------
# Show signup or login
# ---------------------------
if st.session_state.user is None and st.session_state.show_signup:
    signup_ui()
    st.stop()

if st.session_state.user is None and not st.session_state.show_signup:
    login_ui()
    st.stop()

# --------------
# SAFETY GUARD
# --------------
if st.session_state.user is None:
    # ensure we never proceed without a logged-in user
    st.stop()

# --------------
# ROLE ROUTING
# --------------
role = st.session_state.user.get("role")
username = st.session_state.user.get("username")

if role == "student":
    # student portal should show only their attendance
    student_portal(username)
    st.stop()

if role == "teacher":
    teacher_portal(username)
    st.stop()

# Admin flow (default if not stopped earlier)
st.sidebar.title("Admin Menu")
mode = st.sidebar.selectbox("Choose Option", [
    "Register Student (Face)",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Dashboard",
    "Admin Panel"
])

# ---------------------------------------------------------
# REGISTER STUDENT (ADMIN FACE-BASED) - optional duplicate
# (admin may register a student with a different student id/photo)
# ---------------------------------------------------------
if mode == "Register Student (Face)":
    st.header("Register Student (Face Photo)")

    name = st.text_input("Student Name", key="reg_name")
    sid = st.text_input("Student ID (unique)", key="reg_sid")
    programme = st.text_input("Programme", key="reg_prog")
    student_class = st.text_input("Class (e.g., FYBSc A)", key="reg_class")

    upload = st.file_uploader("Upload student photo", type=["jpg","png"], key="reg_upload")
    capture = st.camera_input("Or capture photo", key="reg_camera")

    if st.button("Register Student (Save)"):
        src = capture or upload
        if not src:
            st.error("Upload or capture a photo.")
        elif not name or not sid:
            st.error("Provide student name and ID.")
        else:
            img = load_image_from_bytes(src.getvalue())
            emb = get_face_embedding(img)
            if emb is None:
                st.error("No face detected. Try a clearer frontal photo.")
            else:
                add_student(sid=sid, name=name, programme=programme, student_class=student_class, embedding=emb)
                st.success(f"Registered student {name} ({sid}) successfully.")

# ---------------------------------------------------------
# TAKE ATTENDANCE (IMAGE)
# ---------------------------------------------------------
elif mode == "Take Attendance (Image)":
    st.header("Take Attendance Using Image")

    details = class_subject_time_selector()

    upload = st.file_uploader("Upload class photo", type=["jpg","png"], key="att_img_upload")
    capture = st.camera_input("Or capture", key="att_img_cam")

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

        out_img = draw_boxes(img, boxes, labels)
        st.image(out_img, use_column_width=True)

        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details["class"]
        final_df["Programme"] = [s.get("programme", "") for s in students]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        # allow admin to save via admin panel
        admin_panel_ui(final_df, details["class"], details["subject"])

        if st.button("Download Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf, file_name="attendance_image.xlsx")

# ---------------------------------------------------------
# VIDEO ATTENDANCE
# ---------------------------------------------------------
elif mode == "Take Attendance From Video":
    st.header("🎥 Attendance From Uploaded Video")
    details = class_subject_time_selector()
    present, processed = video_attendance_ui()
    if processed:
        students = load_students()
        final_df = pd.DataFrame([
            {"Student ID": s["id"], "Name": s["name"], "Class": s.get("class",""),
             "Programme": s.get("programme",""), "Present": present[s["id"]]}
            for s in students
        ])
        final_df = manual_attendance_ui(students, present)
        final_df["Class"] = details["class"]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]
        admin_panel_ui(final_df, details["class"], details["subject"])
        if st.button("Download Video Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf, file_name="attendance_video.xlsx")

# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
elif mode == "Dashboard":
    st.header("📊 Attendance Dashboard")
    dashboard_ui()

# ---------------------------------------------------------
# ADMIN PANEL
# ---------------------------------------------------------
elif mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
