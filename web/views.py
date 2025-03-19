from flask import render_template, url_for

def index():
    return render_template('index.html')

def dashboard():
    return render_template('dashboard.html')

def login_page():
    return render_template('login.html')

def register_page():
    return render_template('sign-up.html')

def profile():
    return render_template('profile.html')