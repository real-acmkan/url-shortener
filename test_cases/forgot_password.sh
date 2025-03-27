#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email (actual email for verification purposes): " username
echo "Sending password reset..."
curl -X POST -c cookie-jar -b cookie-jar http://$host/auth/forgot-password -H "Content-Type: application/json" -d '{"email":"'$username'"}'
read -r -p "token (from email): " token
echo "Testing reset token..."
curl -c cookie-jar http://$host/auth/validate-reset?token=$token
echo "Attempting t reset password from 12345 to password..."
curl -X POST -c cookie-jar -b cookie-jar http://127.0.0.1:8080/auth/reset-password -H "Content-Type: application/json" -d '{"password":"password"}'
echo "Logging in with new password..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$username'", "password":"password"}'
rm cookie-jar