# Url Shortener
Project for CS3103 by Matthew Toms-Zuberec (3714677) and Sebastien Fournet (3717029)
-------------------
# NOTE: A version of this is already running on port 8028 for evaluation

## Directory structure
```
 - README.md
 - linkify
    |- web (flask app)
        |- app.py
        |- email_helper.py
        |- settings.py
    |- docs (api documentation)
        |- api_schema.yaml
    |- db (DDL to setup database)
        |- db.sql
```

## Setup
- First, import the db.sql file using the following command (you need a database you can write to):
```shell 
mysql -u "username" -p "database_name" < db/db.sql
```
- Second, edit settings.py and update the variables to match DB.
```python
#/usr/bin/env python

DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "FIXME"
DB_USER = "FIXME"
DB_PASS = "FIXME"

APP_HOST = "cs3103.cs.unb.ca"
APP_PORT = 8028
APP_KEY = "SUPERSECRETKEY"
```
- Third step is to start app.py (located in web/):
```shell
nohup python app.py > log.txt 2>&1 &
```
- Finally, run the test cases. API documentation is provided in docs/
```
Required order to run:

1. register.sh (register the test account)
2. verify.sh (demo verification process)
3. login.sh (demo logging in)
4. logout.sh (demo logging in and then immediately logout)
5. forgot_password.sh (sends email and walks you through reset)
6. create_shorturl.sh
7. visit_shorturl.sh
8. get_shorturl.sh
9. get_user_shorturls.sh
10. update_shorturl.sh
11. delete_shorturl.sh
12. get_user_info.sh
13. update_user_info.sh
14. delete_user.sh
```
