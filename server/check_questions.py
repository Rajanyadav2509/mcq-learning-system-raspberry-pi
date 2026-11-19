import sqlite3

conn = sqlite3.connect("mcq.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM questions")
count = cursor.fetchone()[0]

print(f"Total Questions: {count}")

cursor.execute("""
SELECT
id,
question,
option_a,
option_b,
option_c,
option_d,
correct_answer
FROM questions
LIMIT 5
""")

rows = cursor.fetchall()

print("\nFirst 5 Questions:\n")

for row in rows:
    print(row)
    print("-"*80)

conn.close()