import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from signup import signup_ui
from auth import login_user

# AUTH & ROLE SYSTEM
from auth import login_user
from student_portal import student_portal
from teacher_portal import teacher_portal

# Internal modules
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
from video_attendance import video_attendance_ui
from admin_management import admin_panel_ui
from dashboard import dashboard_ui


# ------------------------------
# PAGE TITLE
# ------------------------------
st.title("📘 Smart Attendance System")


# ------------------------------
# LOGIN SYSTEM
# ------------------------------
# LOGIN SYSTEM
# LOGIN SYSTEM
if "user" not in st.session_state:
    st.session_state.user = None

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False


# -------------------
#  SHOW SIGNUP SCREEN
# -------------------
if st.session_state.show_signup:
    from signup import signup_ui
    signup_ui()

    if st.button("⬅ Back to Login"):
        st.session_state.show_signup = False
        st.rerun()

    st.stop()


# -------------------
#  NORMAL LOGIN SCREEN
# -------------------
if st.session_state.user is None and not st.session_state.show_signup:
    st.subheader("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        from auth import login_user
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome, {user['username']} ({user['role']})")
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Create New Account"):
        st.session_state.show_signup = True
        st.rerun()

    st.stop()

    st.stop()



# ------------------------------
# STUDENT DASHBOARD
# ------------------------------
if role == "student":
    student_portal(username)
    st.stop()


# ------------------------------
# TEACHER PORTAL
# ------------------------------
if role == "teacher":
    teacher_portal(username)
    st.stop()


# ------------------------------
# ADMIN MODE
# ------------------------------
st.sidebar.title("Admin Menu")
mode = st.sidebar.selectbox("Choose Option", [
    "Register Student",
    "Take Attendance (Image)",
    "Take Attendance From Video",
    "Dashboard",
    "Admin Panel"
])


# ---------------------------------------------------------
# REGISTER STUDENT
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

    upload = st.file_uploader("Upload student photo", type=["jpg", "png"])
    capture = st.camera_input("Or capture")

    if st.button("Register"):
        if not all([name, sid, programme, student_class]):
            st.error("Fill all fields.")
        else:
            src = capture or upload
            if not src:
                st.error("Upload or capture a photo.")
            else:
                img = load_image_from_bytes(src.getvalue())
                emb = get_face_embedding(img)

                if emb:
                    add_student(
                        sid=sid,
                        name=name,
                        programme=programme,
                        student_class=student_class,
                        embedding=emb
                    )
                    st.success(f"Registered {name} ({sid}) successfully.")
                else:
                    st.error("No face detected.")

# ---------------------------------------------------------
# TAKE ATTENDANCE (IMAGE)
# ---------------------------------------------------------
if mode == "Take Attendance (Image)":
    st.header("Take Attendance Using Image")

    details = class_subject_time_selector()

    upload = st.file_uploader("Upload class photo", type=["jpg","png"])
    capture = st.camera_input("Or capture")

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
        final_df["Programme"] = [s["programme"] for s in students]
        final_df["Subject"] = details["subject"]
        final_df["Time"] = details["time"]

        admin_panel_ui(final_df, details["class"], details["subject"])

        if st.button("Download Excel"):
            buf = BytesIO()
            final_df.to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("Download File", data=buf,
                               file_name="attendance_image.xlsx")

# ---------------------------------------------------------
# TAKE ATTENDANCE FROM VIDEO
# ---------------------------------------------------------
if mode == "Take Attendance From Video":
    st.header("🎥 Attendance From Uploaded Video")

    details = class_subject_time_selector()

    present, processed = video_attendance_ui()

    if processed:
        students = load_students()

        final_df = pd.DataFrame([
            {
                "Student ID": s["id"],
                "Name": s["name"],
                "Class": s["class"],
                "Programme": s["programme"],
                "Present": present[s["id"]]
            }
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
            st.download_button("Download File", data=buf,
                               file_name="attendance_video.xlsx")

# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
if mode == "Dashboard":
    st.header("📊 Attendance Dashboard")
    dashboard_ui()

# ---------------------------------------------------------
# ADMIN PANEL
# ---------------------------------------------------------
if mode == "Admin Panel":
    st.header("🛠 Admin Panel")
    admin_panel_ui()
