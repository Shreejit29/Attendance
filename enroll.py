# enroll.py — Command-line student enrollment script

import argparse
import os
from utils import enroll_student

"""
Usage Example:
--------------
python enroll.py --id 101 --name "Rahul Patil" --image "rahul.jpg"

This will:
✓ Save the student's image inside student_db/
✓ Update metadata.csv
✓ Rebuild the embedding index
"""

def main():
    parser = argparse.ArgumentParser(description="Enroll a new student into the Smart Attendance System")

    parser.add_argument("--id", required=True, help="Student ID")
    parser.add_argument("--name", required=True, help="Full Name of the Student")
    parser.add_argument("--image", required=True, help="Path to face image (JPG/PNG)")

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Error: Image file '{args.image}' not found.")
        return

    print(f"Enrolling student: {args.name} (ID: {args.id}) ...")

    saved_path = enroll_student(args.id, args.name, args.image)

    print(f"Enrollment successful!")
    print(f"Photo saved at: {saved_path}")
    print(f"Embedding index updated.")


if __name__ == "__main__":
    main()
