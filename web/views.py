from flask import render_template, url_for, session, redirect
from werkzeug.exceptions import Unauthorized

def index():
    return render_template('index.html')

def dashboard():
    if 'id' not in session: 
        raise Unauthorized
    return render_template('dashboard.html')

def login_page():
    return render_template('login.html')

def register_page():
    return render_template('sign-up.html')

def profile():
    return render_template('profile.html')