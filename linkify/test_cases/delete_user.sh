read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
echo "Deleting user..."
curl -X DELETE -b cookie-jar http://$host/user
echo "Checking if it worked..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
rm cookie-jar
