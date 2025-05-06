import sqlite3

con = sqlite3.connect("bank.db")
cur = con.cursor()

cur.execute("ALTER TABLE users ADD COLUMN login_otp TEXT")

con.commit()
con.close()

print("✅ login_otp column added to users table.")
