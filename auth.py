import streamlit as st
import hashlib

# Use Streamlit persistent storage
USERS = st.storage("users")

# -------------------------------------------------------
# Utility: Hash password
# -------------------------------------------------------
def _hash(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------------------------------------
# Create a new user
# -------------------------------------------------------
def create_user(username, password, role, programme="", student_class=""):
    users = USERS.read() or []

    # check if username exists
    for u in users:
        if u["username"] == username:
            return False, "Username already exists"

    users.append({
        "username": username,
        "password": _hash(password),
        "role": role,
        "programme": programme,
        "class": student_class,
    })

    USERS.write(users)
    return True, "User created successfully"

# -------------------------------------------------------
# Login user
# -------------------------------------------------------
def login_user(username, password):
    users = USERS.read() or []
    hashed = _hash(password)

    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u

    return None
