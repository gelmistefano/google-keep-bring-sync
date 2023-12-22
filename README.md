# Google Shopping List to Bring! Sync Script

This Python script synchronizes a Google Shopping List with the Bring shopping app. The synchronization process involves retrieving the necessary credentials from environment variables, initializing instances of the Bring and GoogleKeep classes, and performing the synchronization by adding items from the Google Shopping List to the Bring shopping app. You can run the script directly or run it in a Docker container.

The script uses the Bring API and Google Keep API to interact with the respective services.
The Bring class handles operations related to the Bring shopping app.
The GoogleKeep class handles operations related to Google Keep.
The main function orchestrates the synchronization process.

## Prerequisites

Before running the script, make sure you have the following environment variables set:

- `BRING_EMAIL`: The email address for Bring.
- `BRING_PASSWORD`: The password for Bring.
- `BRING_LIST_NAME`: The prefix name of the Bring shopping list.
- `BRING_LOCALE`: The locale for Bring. For example, "en-US".
- `GOOGLE_EMAIL`: The email address for Google.
- `GOOGLE_APP_PASSWORD`: The application password for Google authentication.
- `GOOGLE_SHOPPING_LIST_NAME`: The name of the Google Shopping List.
- `DEBUG`: (Optional) Set to "TRUE" for debug logs.

## Dependencies

Please ensure that you have the required Python libraries installed before running the script.
The script utilizes the following Python libraries:

- `gkeepapi`: For interacting with Google Keep.
- `requests`: For making HTTP requests.
- `logging`: For logging.

## Logging

The script logs information and debug messages during its execution. You can control the logging level by setting the DEBUG environment variable to "TRUE".

```bash
export DEBUG=TRUE
python main.py
```

## Usage

To run the synchronization script, you can either run it directly or run it in a Docker container. The following sections describe how to run the script in each of these ways.

### Virtualenv

To run the script directly, you can use the following commands:

```bash
# Set the environment variables
export BRING_EMAIL=<bring_email>
export BRING_PASSWORD=<bring_password>
export BRING_LIST_NAME=<bring_list_name>
export BRING_LOCALE=<bring_locale>
export GOOGLE_EMAIL=<google_email>
export GOOGLE_APP_PASSWORD=<google_app_password>
export GOOGLE_SHOPPING_LIST_NAME=<google_shopping_list_name>

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

This will run the script using the environment variables set in your shell. If you want you can also configure `cron` to run the script periodically.

```bash
# Edit the crontab
crontab -e
* * * * * /path/to/script/main.py > /var/log/shopping-sync.log 2>&1
```

### Docker

With docker you can run the script in a container. The Dockerfile is configured to run the script every minute.
To run the script in a Docker container, you can use the following commands:

```bash
# Build the Docker image
docker build -t google-keep-to-bring-sync:latest .
# Run the Docker container
docker run -e BRING_EMAIL=<YourBringEmail> \
           -e BRING_PASSWORD=<YourBringPassword> \
           -e BRING_LIST_NAME=<YourBringListName> \
           -e GOOGLE_EMAIL=<YourGoogleEmail> \
           -e GOOGLE_APP_PASSWORD=<YourGoogleAppPassword> \
           -e GOOGLE_SHOPPING_LIST_NAME=<YourGoogleShoppingListName> \
           -e DEBUG=FALSE \  # Optional, set to "TRUE" for debug logs
           google-keep-to-bring-sync:latest
```

Ensure you replace the placeholders `<YourBringEmail>`, `<YourBringPassword>`, `<YourBringListName>`, `<YourGoogleEmail>`, `<YourGoogleAppPassword>`, and `<YourGoogleShoppingListName>` with your actual credentials and data.

### Docker Compose

To run the script in a Docker container using Docker Compose, you can use the following commands:

```bash
# Build the Docker image
docker compose build
# Run the Docker container
docker compose up -d
```

Ensure you replace the environment variables with your actual credentials and data into `docker-compose.yml` file.

## Tested Environment

The script has been tested successfully on Python 3.9.2 and on Docker on a Raspberry Pi 4 running Debian GNU/Linux 11 (bullseye).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
