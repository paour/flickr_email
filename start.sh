#! /bin/sh

echo "$CRON_SCHEDULE root /usr/local/bin/python /app/flickr_email.py $CRON_POSTFIX" > /etc/cron.d/flickr_email
chmod 0644 /etc/cron.d/flickr_email
/usr/bin/crontab /etc/cron.d/flickr_email

cron -f
