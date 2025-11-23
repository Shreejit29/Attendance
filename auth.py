# auth.py (JSON file storage)
import json
import os
import hashlib

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f, indent=4)


def _load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def _save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def create_user(username, password, role, programme="", student_class=""):
    users = _load_users()
    for u in users:
        if u["username"] == username:
            return False, "Username already exists"
    users.append({
        "username": username,
        "password": _hash_password(password),
        "role": role,
        "programme": programme,
        "class": student_class
    })
    _save_users(users)
    return True, "User created successfully"


def login_user(username, password):
    users = _load_users()
    hashed = _hash_password(password)
    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u
    return None
