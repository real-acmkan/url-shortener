#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
read -r -p "shortcode: " shortcode
read -r -p "new url: " url
echo "Getting current shortcode info..."
curl -X GET -b cookie-jar http://$host/shorturl/$shortcode
sleep 3
echo "Changing url destination..."
curl -X POST -b cookie-jar http://$host/shorturl/$shortcode/url -H "Content-Type: application/json" -d '{"url":"http://newpage.com"}'
echo "Updating expiry..."
curl -X POST -b cookie-jar http://$host/shorturl/$shortcode/expiry -H "Content-Type: application/json" -d '{"days":"3"}'
rm cookie-jar