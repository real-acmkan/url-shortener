#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email (sanity check to match registration): " email
curl -q -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"12345"}' 

read -r -p "token (from email link): " token
curl -X GET -c cookie-jar -b cookie-jar http://$host/auth/verify?token=$token
rm cookie-jar