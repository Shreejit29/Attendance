import json
import os
import hashlib

# permanent storage location
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)

# ensure file exists
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f)


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


def create_user(username, password, role, programme="", student_class=""):
    users = load_users()

    # check if exists
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
    return True, "User created successfully"


def login_user(username, password):
    users = load_users()
    hashed = hash_password(password)

    for u in users:
        if u["username"] == username and u["password"] == hashed:
            return u

    return None
