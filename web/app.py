import os
import re
import sys
import random
import string
import mariadb
import hashlib
import datetime
from cryptography.fernet import Fernet
from werkzeug.exceptions import BadRequest, Unauthorized
from flask import Flask, jsonify, session, request, redirect, render_template


encryption_key = Fernet.generate_key()
fernet = Fernet(encryption_key)

def encrypt_data(data):
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data

def decrypt_data(encrypted_data):
    decrypted_data = fernet.decrypt(encrypted_data).decode()
    return decrypted_data

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

def get_user_post_login(pconn, cur, email):
    cur.callproc("get_userid_by_email", (email,))
    id = cur.fetchall()
    # pconn.commit()
    cur.callproc("get_name_by_email", (email,))
    name = cur.fetchall()
    # pconn.commit()
    return str(id[0][0]), str(name[0][0])
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

@app.errorhandler(Unauthorized)
def handle_unauth_request(e):
    return jsonify({'code':'401', 'message':'Unauthorized'}), 401

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
    if 'id' in session:
        # session.pop('email', default=None)
        # session.pop('id', default=None)
        session.clear()
    return jsonify({'status':'logged out.'}), 200

@app.route('/auth/login', methods=['POST'])
def login():
    request_data = request.get_json()
    if 'email' not in request_data or 'password' not in request_data:
        raise BadRequest
    email = request_data["email"]
    pw = request_data["password"]
    pconn, cur = get_conn()
    cur.callproc("login", (email,create_digest(pw)))
    # pconn.commit()
    result = cur.fetchall()
    # app.logger.info('userid check: %s', cur.fetchall())
    if 'Login Successful' not in result[0]:
        return jsonify({'status':'invalid username or password'}), 200
    id, name = get_user_post_login(pconn, cur, email)
    session["name"] = name
    session["id"] = id
    # if 'verify' in session:
    #     return jsonify({'status':'unverified'}), 200
    # print(type(id))
    cur.callproc("check_if_user_verified", (id,))
    verified = cur.fetchone()
    app.logger.info('user_verified check: %s', verified)
    if not verified:
        session["e"] = email
        user = f"{name}-{id}"
        app.logger.info('user token %s', user)
        # token =  f"{id}{os.urandom(16).hex()}"
        # TODO: send email to user
        # session["verify"] = token
        token = create_digest(user)
        app.logger.info('verify token %s', token)
        return jsonify({'status':'unverified'}), 200
    cur.close()
    pconn.close()
    session["email"] = email
    return jsonify({'status':'login successful'}), 200

@app.route('/auth/register', methods=['POST'])
def register():
    request_data = request.get_json()
    if 'name' not in request_data or 'email' not in request_data or 'password' not in request_data:
        raise BadRequest
    email = request_data["email"]
    pw = request_data["password"]
    name = request_data["name"]
    pconn, cur = get_conn()
    cur.callproc("get_userid_by_email", (email,))
    result = cur.fetchall()
    # app.logger.info('userid check: %s', result)
    if result:
        return jsonify({'error':'user already exists'})
    try:
        cur.callproc("create_user", (name,email,create_digest(pw)))
        pconn.commit()
    except Exception:
        raise BadRequest
    finally:
        cur.close()
        pconn.close()
    # session['verify'] = token
    return jsonify({'status':'successfully registered'})

@app.route('/auth/forgot-password', methods=['POST'])
def forgot():
    request_data = request.get_json()
    if 'email' not in request_data:
        raise BadRequest
    token = os.urandom(16).hex()
    pconn, cur = get_conn()
    cur.callproc("get_userid_by_email", (request_data["email"],))
    id = cur.fetchone()
    # TODO: send email to user
    # print(f"reset token: {token}")
    token = create_digest(token)
    app.logger.info('reset token: %s', token)
    cur.callproc("set_reset_token", (str(id[0]),token))
    # session['reset'] = token
    pconn.close()
    return jsonify({'status':'reset code sent to email'})
    
@app.route('/auth/validate-reset', methods=['GET'])
def reset():
    token = request.args.get('token')
    if token == None:
        raise BadRequest
    pconn, cur = get_conn()
    cur.callproc("get_reset_token", (token[0],))
    result = cur.fetchall()
    cur.close()
    pconn.close()
    if token[1] != result[0]:
        return jsonify({'status':'invalid reset token'}), 200
    # if 'reset' not in session or create_digest(token) != session['reset']:
    #     raise BadRequest
    # session.pop('reset', default=None)
    return jsonify({'status':'password reset successful'})
    # pconn = pool.get_connection()
    # cur = pconn.cursor()
    # cur.callproc('reset_password', ())

@app.route('/auth/reset-password/', methods=['POST'])
def reset_pass():
    pconn, cur = get_conn()
    pass

@app.route('/auth/verify', methods=['GET'])
def verify():
    if 'id' not in session or 'e' not in session:
        raise Unauthorized
    token = request.args.get('token')
    if token == None:
        raise BadRequest
    hashed = create_digest(f"{session['name']}-{session['id']}")
    if hashed != token:
        return jsonify({'status':'invalid verification token'}), 200
    pconn, cur = get_conn()
    # id = cur.callproc('get_userid_by_email', (session['email']))
    cur.callproc("verify_user", (session["id"],))
    # if not result:
    #     return jsonify({'status':'failed to verify. please try again'})
    pconn.commit()
    cur.close()
    pconn.close()
    session['email'] = session['e']
    session.pop('e', default=None)
    return jsonify({'status':'successfully verified'})

@app.route('/user', methods=['GET', 'POST', 'DELETE'])
def update_email():
    if 'email' not in session:
        raise Unauthorized
    
    if request.method == 'GET':
        return jsonify({'status':'works, pretend for now'}), 200
    if request.method == 'POST':
        return jsonify({'status':'works, pretend for now'}), 200
    if request.method == 'DELETE':
        return jsonify({'status':'works, pretend for now'}), 200

@app.route('/shorturls', methods=['GET', 'POST'])
def shortcodes():
    if 'email' not in session:
        raise Unauthorized
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
        raise Unauthorized
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
        raise Unauthorized
    pconn, cur = get_conn()
    result = cur.callproc("get_user_urls", (session["id"]))
    pconn.commit()
    return jsonify(result)
    
@app.route('/shorturl/{short_code}/url', methods=['POST'])
def update_link_url(short_code):
    if 'email' not in session:
        raise Unauthorized
    pconn, cur = get_conn()
    result = cur.callproc("update_url_expiration", (session["id"]))
    pconn.commit()
    return jsonify(result)

if __name__ == "__main__":
    with app.app_context():
        app.run(host="0.0.0.0", port=5000, debug=True)