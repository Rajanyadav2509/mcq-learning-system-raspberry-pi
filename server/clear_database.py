import sqlite3

conn = sqlite3.connect("mcq.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM questions")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='questions'")

conn.commit()
conn.close()

print("All questions deleted successfully.")