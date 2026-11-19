import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from werkzeug.utils import secure_filename

from parser import parse_pdf, parse_docx
from config import *

app = Flask(__name__)
app.secret_key = "mcq_learning_system"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def init_db():
    """Ensures both tables exist. questions is also created inside
    parser.py, but uploads was never created anywhere until now — this
    makes a fresh mcq.db self-healing instead of crashing on first run."""

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM uploads
        ORDER BY id DESC
    """)
    files = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM questions
        ORDER BY id DESC
        LIMIT 20
    """)
    questions = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        files=files,
        questions=questions
    )


@app.route("/upload", methods=["POST"])
def upload():

    if "pdf" not in request.files:
        flash("No file selected.")
        return redirect(url_for("index"))

    file = request.files["pdf"]

    if file.filename == "":
        flash("Please choose a file.")
        return redirect(url_for("index"))

    if not (file and allowed_file(file.filename)):
        flash("Only PDF and DOCX files are allowed.")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    question_count = 0
    extension = filename.rsplit(".", 1)[1].lower()

    try:

        if extension == "pdf":
            question_count = parse_pdf(filepath)

        elif extension in ["doc", "docx"]:
            question_count = parse_docx(filepath)

        print("=" * 60)
        print("Questions imported:", question_count)

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM questions")
        total_questions = cursor.fetchone()[0]

        print("Total questions in database:", total_questions)
        print("=" * 60)

        cursor.execute("""
            INSERT INTO uploads
            (filename, filepath)
            VALUES (?, ?)
        """, (filename, filepath))

        conn.commit()
        conn.close()

        flash(f"{filename} uploaded successfully.")
        flash(f"{question_count} questions imported.")
        flash(f"Database now contains {total_questions} questions.")

    except Exception as e:
        flash(f"Parser Error: {e}")
        print("ERROR:", e)

    return redirect(url_for("index"))


@app.route("/clear_all", methods=["POST"])
def clear_all():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions")
    question_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM uploads")
    file_count = cursor.fetchone()[0]

    cursor.execute("SELECT filepath FROM uploads")
    filepaths = [row[0] for row in cursor.fetchall()]

    cursor.execute("DELETE FROM questions")
    cursor.execute("DELETE FROM uploads")
    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('questions', 'uploads')")

    conn.commit()
    conn.close()

    # Remove the uploaded files from disk as well.
    for filepath in filepaths:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass

    # Remove any stray files left in the uploads folder.
    upload_folder = app.config["UPLOAD_FOLDER"]
    if os.path.isdir(upload_folder):
        for name in os.listdir(upload_folder):
            path = os.path.join(upload_folder, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    flash(f"All cleared: {question_count} questions and "
          f"{file_count} files deleted.")

    return redirect(url_for("index"))


@app.route("/delete_question/<int:question_id>", methods=["POST"])
def delete_question(question_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questions WHERE id=?", (question_id,))
    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted:
        flash("Question deleted.")
    else:
        flash("Question not found.")

    return redirect(url_for("index"))


@app.route("/delete_file/<int:file_id>", methods=["POST"])
def delete_file(file_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT filepath FROM uploads WHERE id=?", (file_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash("File not found.")
        return redirect(url_for("index"))

    filepath = row[0]

    cursor.execute("DELETE FROM uploads WHERE id=?", (file_id,))
    conn.commit()
    conn.close()

    # Also remove the physical file from disk, if it still exists
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as e:
            flash(f"Removed from list, but couldn't delete file on disk: {e}")
            return redirect(url_for("index"))

    flash("File deleted.")
    return redirect(url_for("index"))


if __name__ == "__main__":

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )