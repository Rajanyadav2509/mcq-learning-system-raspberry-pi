import sqlite3

DATABASE = "mcq.db"


class QuestionDatabase:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.cursor = self.conn.cursor()
        self.create_table()

    # -----------------------------
    # Create table
    # -----------------------------
    def create_table(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            question TEXT UNIQUE NOT NULL,

            option_a TEXT NOT NULL,

            option_b TEXT NOT NULL,

            option_c TEXT NOT NULL,

            option_d TEXT NOT NULL,

            correct_answer TEXT NOT NULL
        )
        """)

        self.conn.commit()

    # -----------------------------
    # Insert Question
    # -----------------------------
    def insert_question(self,
                        question,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        answer):

        self.cursor.execute(
            """
            SELECT id
            FROM questions
            WHERE question=?
            """,
            (question,)
        )

        if self.cursor.fetchone():
            return False

        self.cursor.execute(
            """
            INSERT INTO questions(

            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer

            )

            VALUES(?,?,?,?,?,?)
            """,

            (
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                answer
            )
        )

        self.conn.commit()

        return True

    # -----------------------------
    # Total Questions
    # -----------------------------
    def total_questions(self):

        self.cursor.execute(
            "SELECT COUNT(*) FROM questions"
        )

        return self.cursor.fetchone()[0]

    # -----------------------------
    # Load All Questions
    # -----------------------------
    def load_questions(self):

        self.cursor.execute("""

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

        rows = self.cursor.fetchall()

        answer_map = {

            "A":0,
            "B":1,
            "C":2,
            "D":3

        }

        questions=[]

        for row in rows:

            questions.append({

                "question":row[0],

                "options":[

                    row[1],
                    row[2],
                    row[3],
                    row[4]

                ],

                "correct":answer_map[row[5].upper()]

            })

        return questions

    # -----------------------------
    # Get One Question
    # -----------------------------
    def get_question(self,index):

        data=self.load_questions()

        if len(data)==0:
            return None

        if index>=len(data):
            index=0

        return data[index]

    # -----------------------------
    # Delete All Questions
    # -----------------------------
    def clear_database(self):

        self.cursor.execute(
            "DELETE FROM questions"
        )

        self.conn.commit()

    # -----------------------------
    # Close
    # -----------------------------
    def close(self):

        self.conn.close()


# -----------------------------
# Test
# -----------------------------
if __name__=="__main__":

    db=QuestionDatabase()

    print("Total Questions :",db.total_questions())

    questions=db.load_questions()

    for q in questions:

        print()

        print(q["question"])

        print(q["options"])

        print("Correct :",q["correct"])

    db.close()