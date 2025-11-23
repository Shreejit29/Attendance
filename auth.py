# ============================================================
# auth.py — FINAL STORAGE API VERSION
# ============================================================

import streamlit as st
import hashlib

# Storage key
USERS_KEY = "users"


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _load_users():
    """Load users list from permanent storage."""
    users = st.storage.read(USERS_KEY)
    return users if users else []


def _save_users(users):
    st.storage.write(USERS_KEY, users)


def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


# ------------------------------------------------------------
# Create User
# ------------------------------------------------------------

def create_user(username, password, role, programme="", student_class=""):
    users = _load_users()

    # Check duplicate username
    for u in users:
        if u["username"] == username:
            return False, "Username already exists"

    new_user = {
        "username": username,
        "password": _hash_password(password),
        "role": role,
        "programme": programme,
        "class": student_class
    }

    users.append(new_user)
    _save_users(users)

    return True, "User created successfully"


# ------------------------------------------------------------
# Login User
# ------------------------------------------------------------

def login_user(username, password):
    users = _load_users()
    hashed = _hash_password(password)

    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u

    return None
