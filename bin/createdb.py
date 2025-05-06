import sqlite3

con = sqlite3.connect('bank.db')
cur = con.cursor()

# Drop tables if they exist
cur.execute("DROP TABLE IF EXISTS users")
cur.execute("DROP TABLE IF EXISTS accounts")

# Recreate users table
cur.execute('''
    CREATE TABLE users (
        email TEXT PRIMARY KEY,
        name TEXT,
        password TEXT,
        username TEXT
    )
''')

# Recreate accounts table
cur.execute('''
    CREATE TABLE accounts (
        id TEXT PRIMARY KEY,
        owner TEXT,
        balance INTEGER,
        type TEXT,
        FOREIGN KEY(owner) REFERENCES users(email)
    )
''')

con.commit()
con.close()
