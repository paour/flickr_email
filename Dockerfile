FROM python:3.9
RUN apt-get update && apt-get -y install cron vim
RUN pip install --no-cache-dir Jinja2 flickr_api

WORKDIR /app

COPY flickr_email.py email.jinja2 start.sh /app/
RUN chmod +x /app/flickr_email.py /app/start.sh

VOLUME /app/config
ENV CRONTAB="1 1 * * *"

# run crond as main process of container
ENTRYPOINT ["/app/start.sh"]
#CMD ["python", "/app/flickr_email.py", "-v"]
