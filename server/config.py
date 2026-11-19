import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

DATABASE = os.path.join(BASE_DIR, "mcq.db")

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx"
}

MAX_CONTENT_LENGTH = 30 * 1024 * 1024