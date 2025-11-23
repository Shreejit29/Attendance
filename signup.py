# signup.py — FULL Multi-Image Signup (Streamlit Storage API)

import streamlit as st
from auth import create_user
from face_utils import load_image_from_bytes, extract_all_embeddings
from storage import add_student


def signup_ui():
    st.header("🆕 Create New Account")
    st.info("Students can upload or capture MULTIPLE images for accurate face registration.")

    # ---------------------------------------------------------
    # BASIC CREDENTIALS
    # ---------------------------------------------------------
    username = st.text_input("Choose Username", key="signup_username")
    password = st.text_input("Choose Password", type="password", key="signup_password")

    role = st.selectbox("Select Role", ["student", "teacher", "admin"], key="signup_role")

    # ---------------------------------------------------------
    # ROLE-SPECIFIC FIELDS
    # ---------------------------------------------------------
    programme = st.text_input("Programme (Optional)", key="signup_programme")
    student_class = st.text_input("Class (Optional)", key="signup_class")

    st.write("---")

    # ---------------------------------------------------------
    # MULTI-IMAGE SUPPORT FOR STUDENTS
    # ---------------------------------------------------------
    images = []

    if role == "student":
        st.subheader("📸 Upload or Capture MULTIPLE Face Photos")

        # File Upload
        uploads = st.file_uploader(
            "Upload Photos (Supports MULTIPLE)",
            type=["jpg", "png"],
            accept_multiple_files=True,
            key="signup_uploads"
        )

        if uploads:
            for f in uploads:
                try:
                    images.append(load_image_from_bytes(f.getvalue()))
                except:
                    pass

        # Camera Capture (UNLIMITED using session_state)
        if "signup_captures" not in st.session_state:
            st.session_state["signup_captures"] = []

        st.write("### Or Capture Photos")

        if st.button("📷 Capture New Photo", key="signup_capture_btn"):
            cap_key = f"signup_cap_{len(st.session_state['signup_captures'])}"
            cap = st.camera_input("Take Photo", key=cap_key)
            if cap:
                st.session_state["signup_captures"].append(cap)

        # Add captured photos to list
        if st.session_state["signup_captures"]:
            st.write("### Captured Photos")
            cols = st.columns(4)
            for idx, cap in enumerate(st.session_state["signup_captures"]):
                try:
                    cols[idx % 4].image(cap, width=130, caption=f"Shot {idx+1}")
                    images.append(load_image_from_bytes(cap.getvalue()))
                except:
                    pass

        if st.button("🗑 Clear Captured Photos", key="signup_clear"):
            st.session_state["signup_captures"] = []

    # ---------------------------------------------------------
    # CREATE ACCOUNT
    # ---------------------------------------------------------
    if st.button("Create Account", key="signup_create"):
        # Basic validation
        if not username or not password:
            st.error("Username and password are required.")
            return

        # Student must provide face photos
        if role == "student" and len(images) == 0:
            st.error("Students must provide at least one face photo.")
            return

        # Create user in permanent storage
        ok, msg = create_user(username, password, role, programme, student_class)
        if not ok:
            st.error(msg)
            return

        # Student Face Embeddings
        if role == "student":
            embeddings = []

            for img in images:
                try:
                    embs = extract_all_embeddings(img)
                    embeddings.extend(embs)
                except:
                    pass

            if len(embeddings) == 0:
                st.error("No valid faces detected. Try again with clearer photos.")
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

        # Auto-login after signup
        st.session_state.user = {
            "username": username,
            "role": role,
            "programme": programme,
            "class": student_class,
        }

        st.session_state.show_signup = False
        st.session_state["signup_captures"] = []  # clear stored photos
        st.experimental_rerun()
