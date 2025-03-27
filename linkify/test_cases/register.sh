#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "email (you need to be able receive email): " email
echo "Creating test user with name: tester, email:'$email', password: 12345"
curl -X POST -c cookie-jar http://$host/auth/register -H "Content-Type: application/json" -d '{"name":"tester", "email":"'$email'", "password":"12345"}'