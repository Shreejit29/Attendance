# signup.py (JSON-based multi-image signup)
import streamlit as st
from auth import create_user
from face_utils import load_image_from_bytes, extract_all_embeddings
from storage import add_student

def signup_ui():
    st.header("🆕 Create New Account")
    st.info("Students should upload/capture multiple face photos for accuracy.")

    username = st.text_input("Choose Username", key="signup_username")
    password = st.text_input("Choose Password", type="password", key="signup_password")
    role = st.selectbox("Select Role", ["student", "teacher", "admin"], key="signup_role")
    programme = st.text_input("Programme (Optional)", key="signup_programme")
    student_class = st.text_input("Class (Optional)", key="signup_class")

    images = []
    uploads = st.file_uploader("Upload photos (optional, multiple)", type=["jpg","png"], accept_multiple_files=True)
    if uploads:
        for f in uploads:
            try:
                images.append(load_image_from_bytes(f.getvalue()))
            except:
                pass

    if "signup_captures" not in st.session_state:
        st.session_state["signup_captures"] = []

    if st.button("Capture New Photo"):
        cap = st.camera_input("Take Photo", key=f"signup_cap_{len(st.session_state['signup_captures'])}")
        if cap:
            st.session_state["signup_captures"].append(cap)

    if st.session_state.get("signup_captures"):
        cols = st.columns(min(4, len(st.session_state["signup_captures"])))
        for idx, cap in enumerate(st.session_state["signup_captures"]):
            try:
                cols[idx % 4].image(cap, width=120)
                images.append(load_image_from_bytes(cap.getvalue()))
            except:
                pass

    if st.button("Create Account"):
        if not username or not password:
            st.error("Username and password required.")
            return
        if role == "student" and len(images) == 0:
            st.error("Students must upload/capture at least one photo.")
            return
        ok, msg = create_user(username, password, role, programme, student_class)
        if not ok:
            st.error(msg)
            return
        if role == "student":
            embeddings = []
            for img in images:
                embs = extract_all_embeddings(img)
                embeddings.extend(embs)
            if len(embeddings) == 0:
                st.error("No faces detected in provided images.")
                return
            add_student(username, username, programme, student_class, embeddings)
            st.success("Student registered and logged in.")
        else:
            st.success("Account created.")
        st.session_state.user = {"username": username, "role": role, "programme": programme, "class": student_class}
        st.session_state.show_signup = False
        st.session_state["signup_captures"] = []
        st.experimental_rerun()
