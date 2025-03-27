#!/bin/bash
read -r -p "host (ip:port): " host
read -r -p "shortcode: " shortcode
curl -vv http://$host/$shortcode
