#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email: " email
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"12345"}'
curl -X GET -b cookie-jar -c cookie-jar http://$host/auth/logout
rm cookie-jar
