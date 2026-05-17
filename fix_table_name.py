import sqlite3

conn = sqlite3.connect('foodbank.db')
cursor = conn.cursor()
cursor.execute("ALTER TABLE foodbank RENAME TO foods")
conn.commit()
conn.close()
print("Table foodbank renamed to foods")
