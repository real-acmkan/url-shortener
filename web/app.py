import os
import sys
import random
import string
import mariadb
import hashlib
import datetime
from flask import Flask, jsonify, session, request, redirect, render_template


def create_connection_pool():
    pool = mariadb.ConnectionPool(
    host="mariadb",
    port=3306,
    user="root",
    password=os.getenv("DB_PASS"),
    database="linkify",
    pool_name="webapp",
    pool_size=50)
    return pool

def get_conn():
    pconn = pool.get_connection()
    return pconn

def create_digest(data):
    hash = hashlib.sha256()
    hash.update(bytes(data))
    return hash.digest().hex()

def create_short():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

try:
    pool = create_connection_pool()
except Exception as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/<short_id>', methods=['GET'])
def redirect_url(short_id):
    pconn = pool.get_connection()
    cur = pconn.cursor()
    url = cur.callproc("get_url", (short_id))
    if url:
        cur.callproc("log_click", (short_id))
        pconn.close()
        return redirect(url)
    pconn.close()
    return render_template('index.html')

@app.route('/api/v1/auth/logout', methods=['GET'])
def logout():
    if 'email' in session: 
        session.pop('email', default=None)
        session.pop('id', default=None)
    return jsonify({'status':'logged out.'})

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    email = request.form.get("email", default=None)
    pw = request.form.get("password", default=None)
    if email == None or pw == None:
        return jsonify({'status':'Please submit a valid username and password'})
    
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc("login", (email,create_digest(pw)))

    if not result:
        return jsonify({'status':'invalid username or password'})
    if 'verify' in session:
        return jsonify({'status':'unverified'})
    id = cur.callproc("get_userid_by_email", (email))
    session["email"] = email
    session["id"] = id
    return jsonify({'status':'login successful'})

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    email = request.form.get("email")
    pw = request.form.get("password")
    if email == None or pw == None:
        return jsonify({'status':'bad username or password'})
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc("get_userid_by_email", (email))
    if result:
        return jsonify({'error':'user already exists'}) 
    result = cur.callproc("create_user", (email,create_digest(pw)))
    token = os.urandom(16).hex()
    print(f"verify token: {token}")
    token = create_digest(token)
    session['verify'] = token
    return jsonify({'status':'successfully registered'})

@app.route('/api/v1/auth/forgot-password', methods=['POST'])
def forgot():
    token = os.urandom(16).hex()
    print(f"reset token: {token}")
    token = create_digest(token)
    session['reset'] = token
    return jsonify({'status':'reset code sent to email'})
    
@app.route('/api/v1/auth/reset-password/<token>', methods=['GET'])
def reset(token):
    if 'reset' not in session:
        return jsonify({'status':'missing reset token'})
    hashed = create_digest(token)
    if hashed != session['reset']:
        return jsonify({'status':'missing verification token'})
    session.pop('reset', default=None)
    return jsonify('status':'password reset successful')
    # pconn = pool.get_connection()
    # cur = pconn.cursor()
    # cur.callproc('reset_password', ())

@app.route('/api/v1/auth/update-email')
def update_email():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    

@app.route('/api/v1/auth/verify/<token>', methods=['GET'])
def verify(token):
    if 'verify' not in session:
        return jsonify({'status':'already verified'})
    if 'email' not in session:
        return jsonify({'status':'not logged in'})   
    hashed = create_digest(token)
    if hashed != session['verify']:
        return jsonify({'status':'invalid verification token'})
    pconn = pool.get_connection()
    cur = pconn.cursor()
    id = cur.callproc('get_userid_by_email', (session['email']))
    result = cur.callproc("verify_user", (id))
    if not result:
        return jsonify({'status':'failed to verify. please try again'})
    session.pop('verify', default=None)
    return jsonify({'status':'successfully verified'})
        

@app.route('/api/v1/user/create', methods=['POST'])
def create():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    url = request.form.get("url")
    if url is None:
        return jsonify({'status':'invalid url'})
    if not url.startswith("https://") or not url.startswith("http://"):
        return jsonify({'status':'url must specify protocol (https or http)'})
    
    short = create_short()
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc('create_url', (short, url, session['id'], "00:00:00"))
    return jsonify(result)

@app.route('/api/v1/user/remove', methods=['POST'])
def remove():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    url = request.form.get("url")
    if url is None:
        return jsonify({'status':'invalid url'})
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc("delete_url", (url, session['id']))
    return jsonify(result)
    

@app.route('/api/v1/user/list', methods=['GET'])
def list_of_links():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc("get_user_urls", (session["id"]))
    return jsonify(result)
    
@app.route('/api/v1/user/update', methods=['POST'])
def update():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    pconn = pool.get_connection()
    cur = pconn.cursor()
    result = cur.callproc("update_url_expiration", (session["id"]))
    return jsonify(result)

if __name__ == "__main__":
    with app.app_context():
        app.run(host="0.0.0.0", port=5000, debug=False)