import os
import sqlite3
import re

# The admin panel (server/) and the quiz share ONE database file, so the
# quiz always shows exactly what is in the panel: a question uploaded in
# the panel appears in the quiz, and a question deleted in the panel is
# gone from the quiz. The quiz connects directly to the server's database
# (server/mcq.db, next to this quiz folder) — there is no separate local
# copy in between.
# The database lives in different places depending on the folder layout:
#   - repo layout: quiz/ and server/ side by side  -> ../server/mcq.db
#   - flat layout: everything in one folder (the original zip, e.g. on a
#     Windows PC or the Pi)  -> mcq.db next to this file
# Use the one that actually exists. If BOTH exist (two copies of the
# project on the same machine), use the most recently changed one: the
# admin panel writes to its database whenever a question is uploaded,
# deleted or cleared, so the newest file is the panel's current database
# and the quiz always matches the panel, whichever folder it is in.
_QUIZ_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(os.path.dirname(_QUIZ_DIR), "server", "mcq.db"),
    os.path.join(_QUIZ_DIR, "mcq.db"),
]
_EXISTING = [path for path in _CANDIDATES if os.path.exists(path)]
if _EXISTING:
    DATABASE = max(_EXISTING, key=os.path.getmtime)
else:
    DATABASE = _CANDIDATES[0]


def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_option(option):
    option = clean_text(option)

    # Remove prefixes like "A.", "B)", etc.
    option = re.sub(r"^[A-Da-d][.)]\s*", "", option)

    return option


def get_answer_index(answer):
    """
    Converts database answer to option index.

    Supported formats:
        A
        B
        C
        D

        a
        b
        c
        d

        Answer: B
        Correct Answer: C

        1
        2
        3
        4
    """

    if answer is None:
        return 0

    answer = clean_text(answer).upper()

    # Exact match
    if answer == "A":
        return 0

    if answer == "B":
        return 1

    if answer == "C":
        return 2

    if answer == "D":
        return 3

    # Number format
    if answer == "1":
        return 0

    if answer == "2":
        return 1

    if answer == "3":
        return 2

    if answer == "4":
        return 3

    # Formats like "Answer: B"
    match = re.search(r"\b([ABCD])\b", answer)

    if match:
        mapping = {
            "A": 0,
            "B": 1,
            "C": 2,
            "D": 3
        }

        return mapping[match.group(1)]

    return 0


def get_all_questions():

    # Clear error (instead of sqlite's cryptic "unable to open database
    # file") when the database is in neither of the known places.
    if not os.path.exists(DATABASE):
        raise FileNotFoundError(
            "Quiz database not found. Looked for: "
            + ", ".join(_CANDIDATES)
        )

    # timeout=10: wait briefly if the admin panel is writing (uploading)
    # instead of failing with "database is locked".
    conn = sqlite3.connect(DATABASE, timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer
        FROM questions
        ORDER BY id
    """)

    rows = cursor.fetchall()

    conn.close()

    questions = []

    for row in rows:

        question = clean_text(row[0])

        options = [
            clean_option(row[1]),
            clean_option(row[2]),
            clean_option(row[3]),
            clean_option(row[4])
        ]

        answer_index = get_answer_index(row[5])

        questions.append({

            "question": question,

            "options": options,

            "answer": answer_index

        })

    return questions


if __name__ == "__main__":

    questions = get_all_questions()

    print(f"\nLoaded {len(questions)} Questions\n")

    for i, q in enumerate(questions[:5], start=1):

        print("-" * 70)

        print(f"Question {i}")

        print("Question :", q["question"])

        print("A :", q["options"][0])
        print("B :", q["options"][1])
        print("C :", q["options"][2])
        print("D :", q["options"][3])

        print("Answer Index :", q["answer"])