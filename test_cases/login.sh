#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email (same one you registered with): " username
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$username'", "password":"12345"}'
rm cookie-jar