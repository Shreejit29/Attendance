# auth.py

import streamlit as st
import json
import os
import hashlib

USERS_FILE = "users.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login_user(username, password):
    users = load_users()
    hashed = hash_pass(password)

    for user in users:
        if user["username"] == username and user["password"] == hashed:
            return user

    return None


def create_user(username, password, role):
    users = load_users()

    # prevent duplicate usernames
    for u in users:
        if u["username"] == username:
            return False, "Username already exists"

    users.append({
        "username": username,
        "password": hash_pass(password),
        "role": role
    })
    save_users(users)
    return True, "User created"
