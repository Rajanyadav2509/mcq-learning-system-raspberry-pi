import sqlite3
import re

import fitz
import pdfplumber
from docx import Document

DATABASE = "mcq.db"


def create_database():

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
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

    conn.commit()
    conn.close()


def insert_question(question, a, b, c, d, answer):

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM questions WHERE question=?",
        (question,)
    )

    if cur.fetchone():
        conn.close()
        return False

    cur.execute("""
    INSERT INTO questions(
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer
    )
    VALUES(?,?,?,?,?,?)
    """, (question, a, b, c, d, answer))

    conn.commit()
    conn.close()

    return True


def clean(x):

    if x is None:
        return ""

    x = str(x)
    x = x.replace("\r", " ")
    x = x.replace("\n", " ")
    x = re.sub(r"\s+", " ", x)

    return x.strip()


# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------

def extract_text(pdf):
    """Flat text extraction, used only by the regex fallback parser."""

    doc = fitz.open(pdf)

    txt = ""

    for page in doc:
        txt += page.get_text()

    doc.close()

    return txt


def _parse_pdf_tables(pdf_path):
    """
    Handles table-formatted question banks, e.g.:

        ID | Question | A | B | C | D | Ans
        102 | The value of an ideal voltage source has: | Zero internal
        resistance | Infinite internal resistance | ... | A

    Returns (imported_count, duplicate_count, total_rows_found).
    """

    imported = 0
    duplicate = 0
    total = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if not row or len(row) < 7:
                        continue

                    row_id, question, a, b, c, d, ans = row[:7]

                    # Skip header rows ("ID", "Question", "A", "B", "C", "D", "Ans")
                    if clean(row_id).upper() in ("", "ID"):
                        continue

                    question = clean(question)
                    a = clean(a)
                    b = clean(b)
                    c = clean(c)
                    d = clean(d)
                    ans = clean(ans).upper()

                    if not question or not ans:
                        continue

                    total += 1

                    if insert_question(question, a, b, c, d, ans):
                        imported += 1
                        print("Imported:", question[:80])
                    else:
                        duplicate += 1

    return imported, duplicate, total


def _parse_pdf_words(pdf_path):
    """
    Fallback for borderless table PDFs (e.g. ece_questions.pdf) where
    pdfplumber cannot see the table rows: rebuild each question from the
    words' positions instead. The header row (ID | Question | A | B | C |
    D | Ans) gives the left edge of each column; a line whose ID column
    holds a number starts a new question, and the lines below it (empty
    ID column) are its continuation lines, so wrapped question text is
    joined back together.

    Returns (imported_count, duplicate_count, total_rows_found).
    """

    header = ["ID", "Question", "A", "B", "C", "D", "Ans"]
    fields = ["q", "a", "b", "c", "d", "ans"]

    imported = 0
    duplicate = 0
    total = 0

    edges = None
    cur = None

    def flush():
        nonlocal imported, duplicate, total, cur
        if not cur:
            return
        if (cur["q"] and cur["a"] and cur["b"] and cur["c"]
                and cur["d"] and cur["ans"] in ("A", "B", "C", "D")):
            total += 1
            if insert_question(cur["q"], cur["a"], cur["b"],
                               cur["c"], cur["d"], cur["ans"]):
                imported += 1
                print("Imported:", cur["q"][:80])
            else:
                duplicate += 1
        cur = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue

            # Find the header baseline on this page; reuse the previous
            # page's column edges if this page has no header.
            by_top = {}
            for w in words:
                by_top.setdefault(round(w["top"]), []).append(w)
            for top, ws in sorted(by_top.items()):
                texts = [w["text"] for w in ws]
                if all(h in texts for h in header):
                    edges = sorted(
                        w["x0"] for w in ws if w["text"] in header)
                    break
            if edges is None:
                continue

            def col_of(w):
                cx = (w["x0"] + w["x1"]) / 2
                col = 0
                for i, e in enumerate(edges):
                    if cx >= e:
                        col = i
                return col

            lines = {}
            for w in words:
                lines.setdefault(round(w["top"]), []).append(w)

            for top in sorted(lines):
                ws = sorted(lines[top], key=lambda w: w["x0"])
                cells = {i: [] for i in range(7)}
                for w in ws:
                    cells[col_of(w)].append(w["text"])

                id_txt = clean(" ".join(cells[0]))

                if id_txt.isdigit():
                    flush()
                    cur = {
                        "q": clean(" ".join(cells[1])),
                        "a": clean(" ".join(cells[2])),
                        "b": clean(" ".join(cells[3])),
                        "c": clean(" ".join(cells[4])),
                        "d": clean(" ".join(cells[5])),
                        "ans": clean(" ".join(cells[6])).upper(),
                    }
                elif id_txt == "" and cur is not None:
                    # Continuation line: append each column's words.
                    for i in range(1, 7):
                        t = clean(" ".join(cells[i]))
                        if t:
                            cur[fields[i - 1]] = clean(
                                cur[fields[i - 1]] + " " + t)
                # Any other line (header, title, junk) is skipped.

    flush()

    return imported, duplicate, total


def _parse_pdf_regex(pdf_path):
    """
    Fallback for prose-style question banks, e.g.:

        1. What is X?
        A. option
        B. option
        C. option
        D. option
        Answer: B
    """

    text = extract_text(pdf_path)

    pattern = re.compile(
        r'\d+\.\s*(.*?)'
        r'\s*A\.\s*(.*?)'
        r'\s*B\.\s*(.*?)'
        r'\s*C\.\s*(.*?)'
        r'\s*D\.\s*(.*?)'
        r'\s*Answer:\s*([ABCD])',
        re.S
    )

    matches = pattern.findall(text)

    imported = 0
    duplicate = 0

    for q, a, b, c, d, ans in matches:

        q = clean(q)
        a = clean(a)
        b = clean(b)
        c = clean(c)
        d = clean(d)

        if insert_question(q, a, b, c, d, ans):
            imported += 1
            print("Imported:", q[:80])
        else:
            duplicate += 1

    return imported, duplicate, len(matches)


def parse_pdf(pdf_path):

    create_database()

    imported, duplicate, total = _parse_pdf_tables(pdf_path)

    # If the table parser found nothing (e.g. a borderless table whose
    # rows pdfplumber cannot see), rebuild the questions from the words'
    # positions instead.
    if total == 0:
        imported, duplicate, total = _parse_pdf_words(pdf_path)

    # If still nothing (e.g. a prose-style question bank), try the
    # regex-based fallback instead.
    if total == 0:
        imported, duplicate, total = _parse_pdf_regex(pdf_path)

    print("-" * 40)
    print("Imported :", imported)
    print("Duplicate :", duplicate)
    print("Total :", total)

    return imported


# ---------------------------------------------------------------------------
# DOCX parsing
# ---------------------------------------------------------------------------

def _parse_docx_tables(docx_path):
    """Handles Word docs where questions are laid out in a table, same
    columns as the PDF version: ID | Question | A | B | C | D | Ans."""

    doc = Document(docx_path)

    imported = 0
    duplicate = 0
    total = 0

    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells]

            if len(cells) < 7:
                continue

            row_id, question, a, b, c, d, ans = cells[:7]

            if clean(row_id).upper() in ("", "ID"):
                continue

            question = clean(question)
            a = clean(a)
            b = clean(b)
            c = clean(c)
            d = clean(d)
            ans = clean(ans).upper()

            if not question or not ans:
                continue

            total += 1

            if insert_question(question, a, b, c, d, ans):
                imported += 1
                print("Imported:", question[:80])
            else:
                duplicate += 1

    return imported, duplicate, total


def _parse_docx_regex(docx_path):
    """Fallback for prose-style Word docs (paragraphs, not tables)."""

    doc = Document(docx_path)
    text = "\n".join(p.text for p in doc.paragraphs)

    pattern = re.compile(
        r'\d+\.\s*(.*?)'
        r'\s*A\.\s*(.*?)'
        r'\s*B\.\s*(.*?)'
        r'\s*C\.\s*(.*?)'
        r'\s*D\.\s*(.*?)'
        r'\s*Answer:\s*([ABCD])',
        re.S
    )

    matches = pattern.findall(text)

    imported = 0
    duplicate = 0

    for q, a, b, c, d, ans in matches:

        q = clean(q)
        a = clean(a)
        b = clean(b)
        c = clean(c)
        d = clean(d)

        if insert_question(q, a, b, c, d, ans):
            imported += 1
            print("Imported:", q[:80])
        else:
            duplicate += 1

    return imported, duplicate, len(matches)


def parse_docx(docx_path):

    create_database()

    imported, duplicate, total = _parse_docx_tables(docx_path)

    if total == 0:
        imported, duplicate, total = _parse_docx_regex(docx_path)

    print("-" * 40)
    print("Imported :", imported)
    print("Duplicate :", duplicate)
    print("Total :", total)

    return imported


if __name__ == "__main__":

    path = input("Enter PDF or DOCX path : ").strip()

    if path.lower().endswith(".pdf"):
        count = parse_pdf(path)
    else:
        count = parse_docx(path)

    print(f"\n{count} questions imported. Database ready.")