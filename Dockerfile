FROM python:3.9
RUN apt-get update && apt-get -y install cron vim
RUN pip install --no-cache-dir Jinja2 flickr_api
WORKDIR /app
RUN echo "${crontab:-1 1 * * *} python /app/flick_email.py" > /etc/cron.d/crontab
COPY flickr_email.py /app/flickr_email.py
COPY email.jinja2 /app/email.jinja2
RUN chmod +x /app/flickr_email.py
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab
VOLUME /app/config

# run crond as main process of container
CMD ["cron", "-f"]
#CMD ["python", "/app/flickr_email.py", "-v"]
