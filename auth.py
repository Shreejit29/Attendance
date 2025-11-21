# auth.py
import json
import os
import hashlib
import random
import string
from typing import Optional

USERS_FILE = "users.json"
OTP_STORE_FILE = "otps.json"  # temporary OTP store

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def load_otps():
    if not os.path.exists(OTP_STORE_FILE):
        return {}
    with open(OTP_STORE_FILE, "r") as f:
        return json.load(f)

def save_otps(d):
    with open(OTP_STORE_FILE, "w") as f:
        json.dump(d, f, indent=2)

def login_user(username: str, password: str) -> Optional[dict]:
    users = load_users()
    hashed = hash_pass(password)
    for user in users:
        if user["username"] == username and user["password"] == hashed:
            if user.get("verified", False):
                return user
            else:
                # Not verified yet
                return None
    return None

def create_user(username: str, password: str, role: str,
                email: str="", programme: str="", student_class: str="") -> (bool, str):
    users = load_users()
    for user in users:
        if user["username"] == username:
            return False, "Username already exists."

    new = {
        "username": username,
        "password": hash_pass(password),
        "role": role,
        "email": email,
        "programme": programme,
        "class": student_class,
        "verified": False  # will be set True after OTP verification
    }
    users.append(new)
    save_users(users)
    return True, "User created (unverified)."

def set_user_verified(username: str):
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["verified"] = True
            save_users(users)
            return True
    return False

def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))

def store_otp_for_user(username: str, otp: str):
    d = load_otps()
    d[username] = {"otp": otp}
    save_otps(d)

def verify_otp_for_user(username: str, otp: str) -> bool:
    d = load_otps()
    rec = d.get(username)
    if not rec:
        return False
    if rec.get("otp") == otp:
        # remove otp after successful verification
        d.pop(username, None)
        save_otps(d)
        return True
    return False
