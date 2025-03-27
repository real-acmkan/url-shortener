#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
read -r -p "shortcode: " shortcode
echo "Fetching shortcode info"
curl -X GET -b cookie-jar http://$host/shorturl/$shortcode