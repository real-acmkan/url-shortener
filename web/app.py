import os
import re
import sys
import random
import string
import mariadb
import hashlib
import datetime
from werkzeug.exceptions import BadRequest
from flask import Flask, jsonify, session, request, redirect, render_template


def create_connection_pool():
    pool = mariadb.ConnectionPool(
    host="mariadb",
    port=3306,
    user="root",
    password=open(os.getenv("DB_PASS"), "r").read(),
    database="webapp",
    pool_name="app",
    pool_size=50)
    return pool

def get_conn():
    pconn = pool.get_connection()
    return pconn, pconn.cursor()

def create_digest(data):
    hash = hashlib.sha256()
    hash.update(str(data).encode())
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
app.config['SECRET_KEY'] = open(os.getenv("SECRET_KEY"), "r").read()
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({'code':'400', 'message':'Bad Request'}), 400

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/<short_id>', methods=['GET'])
def redirect_url(short_id):
    if not re.search("^[A-Za-z0-9]{6}$", short_id):
        return render_template('index.html')
    pconn, cur = get_conn()
    url = cur.callproc("get_url", (short_id,))
    if url:
        cur.callproc("log_click", (short_id,))
        pconn.close()
        return redirect(url)
    pconn.close()
    return render_template('index.html')

@app.route('/auth/logout', methods=['GET'])
def logout():
    if 'email' not in session:
        raise werkzeug.exceptions.Badrequest 
    session.pop('email', default=None)
    session.pop('id', default=None)
    return jsonify({'status':'logged out.'}), 200

@app.route('/auth/login', methods=['POST'])
def login():
    email = request.form.get("email", default=None)
    pw = request.form.get("password", default=None)
    if email == None or pw == None:
        raise werkzeug.exceptions.BadRequest
    pconn, cur = get_conn()
    result = cur.callproc("login", (email,create_digest(pw)))

    if not result:
        return jsonify({'status':'invalid username or password'})
    if 'verify' in session:
        return jsonify({'status':'unverified'})
    cur.callproc("get_userid_by_email", (email,))
    id = cur.fetchall()
    pconn.commit()
    cur.close()
    pconn.close()
    session["email"] = email
    session["id"] = id
    return jsonify({'status':'login successful'})

@app.route('/auth/register', methods=['POST'])
def register():
    email = request.form.get("email")
    pw = request.form.get("password")
    if email == None or pw == None:
        return jsonify({'status':'bad username or password'})
    pconn, cur = get_conn()
    cur.callproc("get_userid_by_email", (email,))
    result = cur.fetchall()
    # app.logger.info('userid check: %s', result)
    if result:
        return jsonify({'error':'user already exists'})
    try:
        cur.callproc("create_user", (email,create_digest(pw)))
        pconn.commit()

    except Exception:
        return jsonify({'error':'failed to create user. please try again'})
    finally:
        cur.close()
        pconn.close()
    token = os.urandom(16).hex()
    app.logger.info('verify token %s', token)
    token = create_digest(token)
    session['verify'] = token
    return jsonify({'status':'successfully registered'})

@app.route('/auth/forgot-password', methods=['POST'])
def forgot():
    token = os.urandom(16).hex()
    # app.logger.info('userid check: %s', result)
    print(f"reset token: {token}")
    token = create_digest(token)
    session['reset'] = token
    return jsonify({'status':'reset code sent to email'})
    
@app.route('/auth/validate-reset', methods=['GET'])
def reset(token):
    if 'reset' not in session or create_digest(token) != session['reset']:
        return jsonify({'status':'bad token'})
    session.pop('reset', default=None)
    return jsonify({'status':'password reset successful'})
    # pconn = pool.get_connection()
    # cur = pconn.cursor()
    # cur.callproc('reset_password', ())

@app.route('/auth/reset-password/', methods=['POST'])
def reset_pass():
    pconn, cur = get_conn()
    pass

@app.route('/auth/verify', methods=['GET'])
def verify(token):
    if 'verify' not in session:
        return jsonify({'status':'already verified'})
    if 'email' not in session:
        return jsonify({'status':'not logged in'})   
    hashed = create_digest(token)
    if hashed != session['verify']:
        return jsonify({'status':'invalid verification token'})
    pconn, cur = get_conn()
    id = cur.callproc('get_userid_by_email', (session['email']))
    result = cur.callproc("verify_user", (id,))
    if not result:
        return jsonify({'status':'failed to verify. please try again'})
    session.pop('verify', default=None)
    return jsonify({'status':'successfully verified'})

@app.route('/user', methods=['GET', 'POST', 'DELETE'])
def update_email():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})


@app.route('/shorturls', methods=['GET', 'POST'])
def shortcodes():
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    url = request.form.get("url")
    if url is None:
        return jsonify({'status':'invalid url'})
    if not url.startswith("https://") or not url.startswith("http://"):
        return jsonify({'status':'url must specify protocol (https or http)'})
    
    short = create_short()
    pconn, cur = get_conn()
    result = cur.callproc('create_url', (short, url, session['id'], "00:00:00"))
    pconn.commit()
    cur.close()
    pconn.close()
    return jsonify(result)

@app.route('/shorturl/{short_code}', methods=['GET', 'DELETE'])
def individual_shortcodes(short_code):
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    url = request.form.get("url")
    if url is None:
        return jsonify({'status':'invalid url'})
    pconn, cur = get_conn()
    result = cur.callproc("delete_url", (url, session['id']))
    pconn.commit()
    return jsonify(result)
    

@app.route('/shorturl/{short_code}/expiry', methods=['POST'])
def update_link_expiry(short_code):
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    pconn, cur = get_conn()
    result = cur.callproc("get_user_urls", (session["id"]))
    pconn.commit()
    return jsonify(result)
    
@app.route('/shorturl/{short_code}/url', methods=['POST'])
def update_link_url(short_code):
    if 'email' not in session:
        return jsonify({'status':'unauthorized'})
    pconn, cur = get_conn()
    result = cur.callproc("update_url_expiration", (session["id"]))
    pconn.commit()
    return jsonify(result)

if __name__ == "__main__":
    with app.app_context():
        app.run(host="0.0.0.0", port=5000, debug=True)