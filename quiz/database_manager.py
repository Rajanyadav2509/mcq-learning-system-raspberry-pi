import os
import sqlite3
import re

# The admin panel (server/) and the quiz share ONE database file, so the
# quiz always shows exactly what is in the panel: a question uploaded in
# the panel appears in the quiz, and a question deleted in the panel is
# gone from the quiz. The quiz connects directly to the server's database
# (server/mcq.db, next to this quiz folder) — there is no separate local
# copy in between.
_QUIZ_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(
    os.path.dirname(_QUIZ_DIR), "server", "mcq.db")


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

    conn = sqlite3.connect(DATABASE)
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