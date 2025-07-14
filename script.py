import sqlite3

conn = sqlite3.connect("crime_2024.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
conn.close()

print([t[0] for t in tables])