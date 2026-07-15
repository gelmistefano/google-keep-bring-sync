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
# Set the environment variables (or put them in .env and `set -a; . ./.env; set +a`)
export BRING_EMAIL=<bring_email>
export BRING_PASSWORD=<bring_password>
export BRING_LIST_NAME=<bring_list_name>
export BRING_LOCALE=<bring_locale>          # optional, defaults to it-IT
export GOOGLE_EMAIL=<google_email>
export GOOGLE_MASTER_TOKEN=<google_master_token>   # preferred, see Google authentication
export GOOGLE_APP_PASSWORD=<google_app_password>   # fallback only
export GOOGLE_SHOPPING_LIST_NAME=<google_shopping_list_name>
export GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED=<google_shopping_list_suffix_removed>
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
* * * * * cd /path/to/script && /path/to/script/.venv/bin/python main.py >> /var/log/shopping-sync.log 2>&1
```

### Docker

Docker is the recommended way to run the sync. **How the scheduling works:** the
image runs `cron` as its main process (`entrypoint.sh` → `cron -f`) with a job
that executes the script **every minute**. Combined with the Compose
`restart: unless-stopped` policy, the container stays running and re-syncs every
minute — it is "always active" without any host-side scheduler.

You do **not** need a host cron to keep it running. A host cron is only useful as
a watchdog or if you prefer to drive scheduling from the host (see
[Host cron](#host-cron-optional) below).

#### Docker Compose (recommended)

The Compose file reads all configuration from a local `.env` file (`env_file`),
so you never edit `docker-compose.yml` itself.

```bash
# 1. Create your .env from the template and fill in the values
cp .env.example .env
$EDITOR .env            # set GOOGLE_MASTER_TOKEN etc. (see Google authentication)

# 2. Build and start (detached, always-on)
docker compose build
docker compose up -d
```

Notes:
- Do not commit `.env` (it is git-ignored).
- Do not wrap values in quotes — Compose treats quotes as literal characters.

Common management commands:

```bash
docker compose logs -f          # follow sync output (one run per minute)
docker compose ps               # check it is running
docker compose restart          # restart after editing .env
docker compose pull && docker compose up -d --build   # update
docker compose down             # stop and remove the container
```

#### Plain docker run

If you prefer not to use Compose, pass the same `.env` with `--env-file`:

```bash
docker build -t google-keep-to-bring-sync:latest .
docker run -d --name google-bring-sync \
           --restart unless-stopped \
           --env-file .env \
           google-keep-to-bring-sync:latest
```

#### Host cron (optional)

The container already self-schedules every minute, so this is **not required**.
Use it only if you want the host to guarantee the container is always up (a
watchdog). Edit the host crontab with `crontab -e` and add:

```cron
# Watchdog: make sure the sync container is running (checked every minute).
# docker compose up -d is a no-op if it is already running.
* * * * * cd /path/to/google-keep-bring-sync && /usr/bin/docker compose up -d >> /var/log/bring-sync-watchdog.log 2>&1
```

If instead you want the **host** to drive the schedule (one sync per run, no
internal cron), build the one-shot image (`Dockerfile.nocron`, entrypoint
`python /app/script.py` — runs once and exits) and let host cron launch it every
minute. The `--rm` flag removes the finished container so they do not pile up,
and the `flock` guard skips a run if the previous one is still going:

```bash
# Build the one-shot image once
docker build -f Dockerfile.nocron -t google-keep-to-bring-sync:nocron .
```

```cron
* * * * * /usr/bin/flock -n /tmp/bring-sync.lock docker run --rm --env-file /path/to/.env google-keep-to-bring-sync:nocron >> /var/log/bring-sync.log 2>&1
```

> Do not point host cron at the default (main `Dockerfile`) image with `docker
> run`: that image starts its own internal cron and stays alive rather than
> exiting, so runs would accumulate. Use `Dockerfile.nocron` for the one-shot
> model, or just use the recommended Compose setup above, which is already
> always-on.

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
