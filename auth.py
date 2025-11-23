import json
import os
import hashlib

USERS_FILE = "data/users.json"
os.makedirs("data", exist_ok=True)

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def create_user(username, password, role, programme="", student_class=""):
    users = load_users()

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

    save_users(users)
    return True, "User created"

def login_user(username, password):
    users = load_users()
    hashed = hash_password(password)

    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u
    return None
