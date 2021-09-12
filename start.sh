#! /bin/sh

echo "$CRONTAB python /app/flickr_email.py" > /etc/cron.d/crontab
chmod 0644 /etc/cron.d/crontab
/usr/bin/crontab /etc/cron.d/crontab

cron -f
