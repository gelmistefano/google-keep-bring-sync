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
- `GOOGLE_MASTER_TOKEN`: A Google master token. **This is the recommended (and now effectively required) way to authenticate** — see [Google authentication](#google-authentication).
- `GOOGLE_APP_PASSWORD`: The application password for Google authentication. Used only as a fallback when `GOOGLE_MASTER_TOKEN` is not set; Google generally rejects it now (`BadAuthentication`).
- `GOOGLE_SHOPPING_LIST_NAME`: The name of the Google Shopping List.
- `BRING_LOCALE`: The locale for Bring translate. For example, "en-US". Default is `it-IT`
- `GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED`: (Optional) The suffix removed from the Google Shopping List name. See [Suffix Removed](#suffix-removed) section for more details.
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
export GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED=<google_shopping_list_suffix_removed>
export BRING_LOCALE=<bring_locale>
export DEBUG=FALSE  # Optional, set to "TRUE" for debug logs

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
           -e GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED=<YourGoogleShoppingListSuffixRemoved> \
           -e BRING_LOCALE=<bring_locale> \
           -e DEBUG=FALSE \  # Optional, set to "TRUE" for debug logs
           google-keep-to-bring-sync:latest
```

Ensure you replace the placeholders `<YourBringEmail>`, `<YourBringPassword>`, `<YourBringListName>`, `<YourGoogleEmail>`, `<YourGoogleAppPassword>`, `<YourGoogleShoppingListName>`, `YourGoogleShoppingListSuffixRemoved` and `bring_locale` with your actual credentials and data.

### Docker Compose

The Compose file reads configuration from a local `.env` file (`env_file`), so
you do not edit `docker-compose.yml` itself.

```bash
# Create your .env from the template and fill in the values
cp .env.example .env
$EDITOR .env
# Build and run
docker compose build
docker compose up -d
```

Do not commit `.env` (it is git-ignored). Do not wrap values in quotes — Compose
treats quotes as literal characters.

### Google authentication

Google no longer accepts plain email + (app) password login for the
`gkeepapi`/`gpsoauth` flow — it returns `BadAuthentication` regardless of the
Python version. **This is why password login "stopped working"; it is not a
Python 3.9 vs newer issue.** The script has been verified end-to-end on Python
3.12 using a master token.

Authenticate with a **master token** instead. Obtain it once with `gpsoauth`:

```python
import gpsoauth
# oauth_token comes from the Google "embedded setup" browser flow; see the
# gpsoauth / gkeepapi docs for how to capture the oauth_token (aas_et/... value).
res = gpsoauth.exchange_token("your@gmail.com", oauth_token, "your-android-id")
print(res["Token"])  # starts with "aas_et/..." — this is the master token
```

Set the result as `GOOGLE_MASTER_TOKEN`. The script uses `keep.resume(email,
master_token)` when it is present and only falls back to password login
otherwise. The token is long-lived; store it securely (it grants broad account
access).

### Catalog Matching

To reuse Bring!'s built-in catalog items (with their icons and automatic
section sorting) instead of creating custom entries, item text from Google
Keep is matched against the localized Bring! catalog (`BRING_LOCALE`) before
insertion. Matching is case- and accent-insensitive.

When the item text contains more than a catalog name, the extra words are sent
as the Bring! **specification** and the built-in item is still used:

| Google Keep text   | Bring! item (built-in) | Specification |
|--------------------|------------------------|---------------|
| `Latte`            | Latte                  | –             |
| `latte intero`     | Latte                  | `intero`      |
| `2 Pomodori maturi`| Pomodori               | `2 maturi`    |
| `qualcosa di raro` | *(custom item)*        | –             |

Only text with no catalog match at all is added as a custom item.

### Suffix Removed

Sometimes happens that Google add a suffix to the item added in shopping list. For example, if you want to add item `Soap`, Google may will add `Soap on` in your list. In this case, you can set the `GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED` environment variable to `on` and the script will remove the suffix from the name of the item before import into Bring.

## Tested Environment

The script has been tested successfully on Python 3.9.2 and on Python 3.12
(end-to-end, master-token login) with the current pinned dependencies
(`gkeepapi 0.17.1`, `gpsoauth 2.0.0`, `requests 2.34.2`, `urllib3 2.7.0`). The
Docker image is based on `python:3.12-slim-bookworm`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
