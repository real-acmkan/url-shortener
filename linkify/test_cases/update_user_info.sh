read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
echo "Updating user name from tester to bob..."
curl -X POST -b cookie-jar http://$host/user -H "Content-Type: application/json" -d '{"name":"bob"}'
echo "Checking for change"
curl -b cookie-jar http://$host/user
rm cookie-jar