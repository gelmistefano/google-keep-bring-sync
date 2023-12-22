# Use Python image as the base
FROM python:3.9-slim-bullseye

ARG BRING_EMAIL
ARG BRING_PASSWORD
ARG BRING_LIST_NAME
ARG GOOGLE_EMAIL
ARG GOOGLE_APP_PASSWORD
ARG GOOGLE_SHOPPING_LIST_NAME

ENV BRING_LOCALE="it-IT"
ENV DEBUG=FALSE

# Install cron
RUN apt-get update && apt-get -y install cron
# Clean the apt-get cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
# Clean temporary files
RUN rm -rf /tmp/*

# Copy the requirements file to the image's working directory
COPY requirements.txt /app/requirements.txt
# Set the working directory to /app
WORKDIR /app
# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy the Python script to the image's working directory
COPY main.py /app/script.py
# Make the script executable
RUN chmod +x /app/script.py

# Add a cronjob to run the script every minute
RUN echo "* * * * * /usr/local/bin/python /app/script.py > /proc/1/fd/1 2>&1" > /etc/cron.d/mycron
RUN crontab /etc/cron.d/mycron

# Copy Entry point script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Start cron in the background when the container starts
ENTRYPOINT ["/app/entrypoint.sh"]