import os
import re
import sys
import random
import string
import pymysql
import hashlib
import datetime
import settings
from email_helper import send_mail
from cryptography.fernet import Fernet
from werkzeug.exceptions import BadRequest, Unauthorized
from flask import Flask, jsonify, session, request, redirect, render_template


encryption_key = Fernet.generate_key()
fernet = Fernet(encryption_key)

def encrypt_data(data):
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_data(encrypted_data):
    decrypted_data = fernet.decrypt(encrypted_data).decode()
    return decrypted_data

def get_conn():
    pconn = pymysql.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            database=settings.DB_NAME)
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
    cur.callproc("get_name_by_email", (email,))
    name = cur.fetchall()
    return str(id[0][0]), str(name[0][0])

def get_short_info(short_code, id):
    pconn, cur = get_conn()
    cur.callproc("get_user_urls", (id,))
    results = cur.fetchall()
    hit = None
    for li in results:
        if short_code in li:
            hit = li
            break
    cur.close()
    pconn.close()
    return hit


try:
    pconn, cur = get_conn()
    cur.close()
    pconn.close()
except Exception as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)


app = Flask(__name__)
app.config['SECRET_KEY'] = settings.APP_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=15)

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({'code':'400', 'message':'Bad Request'}), 400

@app.errorhandler(Unauthorized)
def handle_unauth_request(e):
    return jsonify({'code':'401', 'message':'Unauthorized'}), 401


@app.route('/<short_id>', methods=['GET'])
def redirect_url(short_id):
    if not re.search("^[A-Za-z0-9]{6}$", short_id):
        return jsonify({'status':'resource not found'}), 404
    pconn, cur = get_conn()
    cur.callproc("get_url", (short_id,))
    url = cur.fetchone()
    if url:
        cur.callproc("log_click", (short_id,))
        pconn.commit()
        cur.close()
        pconn.close()
        return redirect(url)
    pconn.close()
    return jsonify({'status':'shortcode not found'}), 404

@app.route('/auth/logout', methods=['GET'])
def logout():
    if 'id' in session:
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
    result = cur.fetchall()
    if 'Login Successful' not in result[0]:
        return jsonify({'status':'invalid username or password'}), 200
    id, name = get_user_post_login(pconn, cur, email)
    session["name"] = name
    cur.callproc("check_if_user_verified", (id,))
    verified = cur.fetchone()
    app.logger.info('user_verified check: %s', verified)
    if not verified:
        session["e"] = email
        user = f"{name}-{id}"
        app.logger.info('user token %s', user)
        token = create_digest(user)
        res = send_mail(token, request_data["email"], "verify", app.logger)
        if res == False:
            raise BadRequest
        app.logger.info('verify token %s', token)
        return jsonify({'status':'unverified'}), 200
    cur.close()
    pconn.close()
    session["email"] = email
    session["id"] = id
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
    return jsonify({'status':'successfully registered'})

@app.route('/auth/forgot-password', methods=['POST'])
def forgot():
    request_data = request.get_json()
    if 'email' not in request_data:
        raise BadRequest
    pconn, cur = get_conn()
    cur.callproc("get_userid_by_email", (request_data["email"],))
    id = str(cur.fetchone()[0])
    if not id:
        return jsonify({'status':'if an account is associated with that email a reset link will be sent'}), 200
    token = os.urandom(16).hex()
    reset_token = encrypt_data(f"{id}#{request_data['email']}#{token}")
    res = send_mail(reset_token, request_data["email"], "reset", app.logger)
    if res == False:
        raise BadRequest
    app.logger.info('reset token: %s', reset_token)
    token = create_digest(reset_token)
    app.logger.info('hashed reset token: %s', token)
    cur.callproc("set_reset_token", (id,token,))
    cur.close()
    pconn.commit()
    pconn.close()
    return jsonify({'status':'if an account is associated with that email a reset link will be sent'}), 200

@app.route('/auth/validate-reset', methods=['GET'])
def reset():
    token = request.args.get('token')
    if token == None:
        raise BadRequest
    try:
        pconn, cur = get_conn()
        reset_token = decrypt_data(token)
        id = reset_token.split("#")[0]
        cur.callproc("get_reset_token", (id,))
        result = cur.fetchall()
        hashed = create_digest(token)
        if not result or hashed != result[0][0]:
            app.logger.info("user: %s", hashed)
            app.logger.info("db: %s", result[0][0])
            raise BadRequest
        session["email"] = reset_token.split("#")[1]
        session["reset"] = hashed
    except Exception as e:
        app.logger.info(e)
        raise BadRequest
    finally:
        cur.close()
        pconn.close()
    return jsonify({'status':'valid reset token'}), 200

@app.route('/auth/reset-password', methods=['POST'])
def reset_pass():
    if 'email' not in session or 'reset' not in session:
        raise Unauthorized
    request_data = request.get_json()
    if 'password' not in request_data:
        raise BadRequest
    pconn, cur = get_conn()
    app.logger.info(f"email: {session['email']}")
    cur.callproc('reset_password', (session['email'], session['reset'], create_digest(request_data['password']),))
    result = cur.fetchall()
    if 'Password reset successful' not in result[0][0]:
        raise BadRequest
    session.pop('reset', default=None)
    cur.close()
    pconn.commit()
    pconn.close()
    return jsonify({'status':'Password successfully reset'})

@app.route('/auth/verify', methods=['GET'])
def verify():
    if 'e' not in session:
        raise Unauthorized
    token = request.args.get('token')
    if token == None:
        raise BadRequest
    pconn, cur = get_conn()
    cur.callproc('get_userid_by_email', (session['e'],))
    id = str(cur.fetchone()[0])
    hashed = create_digest(f"{session['name']}-{id}")
    if hashed != token:
        return jsonify({'status':'invalid verification token'}), 200
    cur.callproc("verify_user", (id,))
    pconn.commit()
    cur.close()
    pconn.close()
    session['email'] = session['e']
    session['id'] = id
    session.pop('e', default=None)
    return jsonify({'status':'successfully verified'}), 200

@app.route('/user', methods=['GET', 'POST', 'DELETE'])
def update_email():
    if 'id' not in session:
        raise Unauthorized

    if request.method == 'GET':
        info = {"id":session["id"], "name":session["name"], "email":session["email"]}
        return jsonify(info), 200
    if request.method == 'POST':
        request_data = request.get_json()
        if "email" in request_data:
            pconn, cur = get_conn()
            cur.callproc("update_user_email", (session["id"], request_data["email"]))
            cur.close()
            pconn.commit()
            pconn.close()
            session["email"] = request_data["email"]
            return jsonify({'status':'success'}), 200
        if "name" in request_data:
            pconn, cur = get_conn()
            cur.callproc("update_user_name", (session["id"], request_data["name"]))
            cur.close()
            pconn.commit()
            pconn.close()
            session["name"] = request_data["name"]
            return jsonify({'status':'success'}), 200
        raise BadRequest
    if request.method == 'DELETE':
        pconn, cur = get_conn()
        cur.callproc("delete_user_account", (session["id"],))
        cur.close()
        pconn.commit()
        pconn.close()
        session.clear()
        return jsonify({'status':'success'}), 200

@app.route('/shorturls', methods=['GET', 'POST'])
def shortcodes():
    if 'id' not in session:
        raise Unauthorized
    if request.method == "GET":
        pconn, cur = get_conn()
        cur.callproc("get_user_urls", (session["id"],))
        result = cur.fetchall()
        response = []
        for row in result:
            response.append({'expires':row[3],'url':row[2],'shortcode':row[1],'clicks':row[4]})
        return response, 200
    if request.method == "POST":
        request_data = request.get_json()
        if "url" not in request_data:
            raise BadRequest
        if not request_data["url"].startswith("https://") and not request_data["url"].startswith("http://"):
            raise BadRequest
        short = create_short()
        ts = datetime.datetime.now()
        expiry = ts + datetime.timedelta(days=15)
        timestamp = expiry.strftime('%Y-%m-%d %H:%M:%S')
        pconn, cur = get_conn()
        cur.callproc('create_url', (short, request_data['url'], session['id'], timestamp))
        pconn.commit()
        cur.close()
        pconn.close()
        return jsonify({'created':ts.strftime('%Y-%m-%d %H:%M:%S'),'expires':expiry,'url':request_data["url"],'shortcode':short,'clicks':0}), 200

@app.route('/shorturl/<short_code>', methods=['GET', 'DELETE'])
def individual_shortcodes(short_code):
    if 'id' not in session:
        raise Unauthorized
    if request.method == "GET":
        data = get_short_info(short_code, session["id"])
        if data is None:
            raise BadRequest
        return jsonify({'expires':data[3], 'url':data[2], 'short_code':data[1],'clicks':data[4]}), 200
    if request.method == "DELETE":
        pconn, cur = get_conn()
        cur.callproc("delete_url", (short_code, session['id']))
        pconn.commit()
        cur.close()
        pconn.close()
        return jsonify({'status':'success'}), 200

@app.route('/shorturl/<short_code>/expiry', methods=['POST'])
def update_link_expiry(short_code):
    if 'id' not in session:
        raise Unauthorized
    request_data = request.get_json()
    if "days" not in request_data:
        raise BadRequest
    try:
        if int(request_data["days"]) > 30:
            raise BadRequest
    except ValueError as err:
        raise BadRequest
    data = get_short_info(short_code, session["id"])
    if data is None:
        raise BadRequest
    pconn, cur = get_conn()
    expiry = data[3] + datetime.timedelta(days=int(request_data["days"]))
    timestamp = expiry.strftime('%Y-%m-%d %H:%M:%S')
    cur.callproc("update_url_expiration", (short_code, timestamp,))
    cur.close()
    pconn.commit()
    pconn.close()
    return jsonify({'status':'success'}), 200

@app.route('/shorturl/<short_code>/url', methods=['POST'])
def update_link_url(short_code):
    if 'id' not in session:
        raise Unauthorized
    request_data = request.get_json()
    if "url" not in request_data:
        raise BadRequest
    data = get_short_info(short_code, session["id"])
    if data is None:
        raise BadRequest
    pconn, cur = get_conn()
    cur.callproc("edit_url", (session["id"], short_code, request_data["url"],))
    result = cur.fetchall()
    cur.close()
    pconn.commit()
    pconn.close()
    if 'URL updated successfully' not in result[0][0]:
        return BadRequest
    return jsonify({'status':result[0][0]}), 200

if __name__ == "__main__":
    with app.app_context():
        app.run(host=settings.APP_HOST, port=settings.APP_PORT, debug=True)