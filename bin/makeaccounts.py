import sqlite3
from passlib.hash import pbkdf2_sha256

con = sqlite3.connect('bank.db')
cur = con.cursor()

# 🔥 Drop old tables
cur.execute("DROP TABLE IF EXISTS accounts")
cur.execute("DROP TABLE IF EXISTS users")

# 👤 Create users table
cur.execute('''
    CREATE TABLE users (
        email TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        password TEXT,
        username TEXT
    )
''')

# 💰 Create accounts table
cur.execute('''
    CREATE TABLE accounts (
        id TEXT PRIMARY KEY,
        owner TEXT,
        balance INTEGER,
        type TEXT,
        FOREIGN KEY(owner) REFERENCES users(email)
    )
''')

# ➕ Insert sample user 1 - Alice
cur.execute(
    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
    ('alice@example.com', 'Alice', 'Xu', pbkdf2_sha256.hash("123456"), 'alice_001')
)
cur.execute(
    "INSERT INTO accounts VALUES (?, ?, ?, ?)",
    ('alice_001_SAV', 'alice@example.com', 300, 'savings')
)
cur.execute(
    "INSERT INTO accounts VALUES (?, ?, ?, ?)",
    ('alice_001_CHK', 'alice@example.com', 500, 'checking')
)

# ➕ Insert sample user 2 - Bob
cur.execute(
    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
    ('bob@example.com', 'Bobby', 'Tables', pbkdf2_sha256.hash("123456"), 'bob_001')
)
cur.execute(
    "INSERT INTO accounts VALUES (?, ?, ?, ?)",
    ('bob_001_SAV', 'bob@example.com', 300, 'savings')
)
cur.execute(
    "INSERT INTO accounts VALUES (?, ?, ?, ?)",
    ('bob_001_CHK', 'bob@example.com', 500, 'checking')
)

con.commit()
con.close()
print("✅ Fresh users and accounts created.")
