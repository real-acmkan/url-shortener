read -r -p "host (ip:port): " host
read -r -p "email: " email
echo "Logging in..."
curl -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$email'", "password":"password"}'
echo "Current user info:"
curl -b cookie-jar http://$host/user
echo "Updating user name from tester to bob..."
curl -X POST -b cookie-jar -c cookie-jar http://$host/user -H "Content-Type: application/json" -d '{"name":"bob"}'
echo "Checking for change"
curl -b cookie-jar http://$host/user
echo "Changing user email..."
read -r -p "New email (you will have to verify it again): " new_email
curl -X POST -b cookie-jar -c cookie-jar http://$host/user -H "Content-Type: application/json" -d '{"email":"'$new_email'"}'
echo "Checking for change..."
curl -b cookie-jar http://$host/user
rm cookie-jar
echo "Finishing verification..."
curl -q -X POST -c cookie-jar http://$host/auth/login -H "Content-Type: application/json" -d '{"email":"'$new_email'", "password":"password"}'
read -r -p "token (from email link, take value from ?token=): " token
curl -X GET -c cookie-jar -b cookie-jar http://$host/auth/verify?token=$token
rm cookie-jar
