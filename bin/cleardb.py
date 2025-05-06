import sqlite3

con = sqlite3.connect('bank.db')
cur = con.cursor()

# Drop existing tables
cur.execute("DROP TABLE IF EXISTS users")
cur.execute("DROP TABLE IF EXISTS accounts")

con.commit()
con.close()
