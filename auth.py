# auth.py  — Streamlit Storage API version (Permanent User Storage)

import streamlit as st
import hashlib


# -------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------

def hash_password(pwd: str) -> str:
    """Hash the password using SHA-256."""
    return hashlib.sha256(pwd.encode()).hexdigest()


def _load_users():
    """Load all users from Streamlit Storage."""
    users = st.storage.read("users")
    if users is None:
        return []   # return empty list initially
    return users


def _save_users(users):
    """Save all users permanently."""
    st.storage.write("users", users)


# -------------------------------------------------------
# PUBLIC FUNCTIONS
# -------------------------------------------------------

def create_user(username, password, role, programme="", student_class=""):
    """Create a new user and store permanently."""
    users = _load_users()

    # check duplicate username
    for u in users:
        if u["username"] == username:
            return False, "Username already exists"

    users.append({
        "username": username,
        "password": hash_password(password),
        "role": role,
        "programme": programme,
        "class": student_class
    })

    _save_users(users)
    return True, "User created successfully"


def login_user(username, password):
    """Login user using hashed password verification."""
    users = _load_users()
    hashed = hash_password(password)

    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u

    return None
