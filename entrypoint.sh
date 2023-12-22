#!/bin/sh
set -e

echo "Google Keep Shopping list to Bring Shopping list Script"

printenv | grep -v "no_proxy" >> /etc/environment
cron -f