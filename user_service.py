import os 
import sqlite3
from datetime import datetime, timedelta
from passlib.hash import pbkdf2_sha256
from flask import request, g, redirect, flash
import jwt
import hmac
from functools import wraps

SECRET = 'bfg28y7efg238re7r6t32gfo23vfy7237yibdyo238do2v3'

def get_user_with_credentials(email, password):
    try:
        con = sqlite3.connect('bank.db')
        cur = con.cursor()
        cur.execute('SELECT email, name, password, mfa_secret FROM users WHERE email=?', (email,))
        row = cur.fetchone()
        if row is None:
            return None
        email, name, hashed_password, mfa_secret = row

        if not pbkdf2_sha256.verify(password, hashed_password):
            return None

        return {
            "email": email,
            "name": name,
            "token": create_token(email),
            "mfa_secret": mfa_secret
        }
    finally:
        con.close()



def logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get("auth_token")
        if not token:
            return redirect("/")
        try:
            data = jwt.decode(token, SECRET, algorithms=["HS256"])
            g.user = data["sub"]
        except jwt.InvalidTokenError:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def create_token(email):
    now = datetime.utcnow()
    payload = {'sub': email, 'iat': now, 'exp': now + timedelta(minutes=60)}
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    return token

def is_logged_in():
    token = request.cookies.get('auth_token')
    try:
        jwt.decode(token, SECRET, algorithms=['HS256'])
        return True
    except jwt.InvalidTokenError:
        return False