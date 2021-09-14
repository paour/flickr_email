#! /bin/sh

echo "$CRONTAB root python /app/flickr_email.py" > /etc/cron.d/flickr_email
chmod 0644 /etc/cron.d/flickr_email
/usr/bin/crontab /etc/cron.d/flickr_email

cron -f
