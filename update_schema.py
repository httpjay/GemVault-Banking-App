import sqlite3

con = sqlite3.connect('bank.db')
cur = con.cursor()
cur.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")
con.commit()
con.close()

print("✅ mfa_secret column added to users table.")
