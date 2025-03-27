#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -q -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
echo "Shortening http://example.com..."
curl -X POST -b cookie-jar http://$host/shorturls -H "Content-Type: application/json" -d '{"url":"http://example.com"}'
rm cookie-jar