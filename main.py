import gkeepapi
import requests
import logging
import os
import re
import unicodedata

def normalize(text: str) -> str:
  """
  Normalizes a string for catalog matching: strips accents, lowercases,
  trims and collapses inner whitespace.

  Args:
    text (str): The text to normalize.

  Returns:
    str: The normalized text.
  """
  text = unicodedata.normalize('NFKD', text)
  text = ''.join(c for c in text if not unicodedata.combining(c))
  return re.sub(r'\s+', ' ', text).strip().lower()

def debug_curl_output(uri: str, method: str, headers: dict, data: dict = {}) -> None:
  headers_str = " ".join([f'-H "{key}: {value}"' for key, value in headers.items()])
  msg = f'curl -X {method} {headers_str}'
  if data:
    msg += f' -d {data}'
  return f'{msg} {uri}'

class Bring:
  def __init__(self, email: str, password: str, list_name: str, locale="it-IT") -> None:
    """
    Initializes an instance of the class.

    Args:
      email (str): The email address of the user.
      password (str): The password of the user.
      list_name (str): The prefix name of the list.
      locale (str, optional): The locale to use. Defaults to "it-IT".
    """
    self.base_url = "https://api.getbring.com/rest/v2"
    self.email = email
    self.password = password
    self.list_name = list_name
    self.locale = locale
    self.dictionary = {}
    self.name = None
    self.uuid = None
    self.bearerToken = None
    self.refreshToken = None
    self.list_uuid = None
    self.headers = {
      "X-BRING-API-KEY": "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp",
      "X-BRING-CLIENT": "webApp",
      "X-BRING-CLIENT-SOURCE": "webApp",
      "X-BRING-COUNTRY": "IT"
    }
    self.putHeaders = {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    logging.debug(f'Initialized Bring! with email {self.email} and list name {self.list_name}')
    
  def login(self) -> None:
    """
    Logs in to the Bring! API using the provided email and password.
    
    Raises:
      Exception: If the login fails.
      
    Returns:
      None
    """
    logging.debug(f'Bring! Logging in as {self.email}')
    url = f'{self.base_url}/bringauth'
    payload = {"email": self.email, "password": self.password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'POST', headers, payload))
      response = requests.post(url, headers=headers, data=payload)
      response.raise_for_status()
      logging.debug(f'Received response from {url}: {response.text}')
      data = response.json()
      
      self.name = data['name']
      self.uuid = data['uuid']
      self.bearerToken = data['access_token']
      self.refreshToken = data['refresh_token']
      
      logging.debug(f'Name: {self.name} - UUID: {self.uuid} - BearerToken: {self.bearerToken} - RefreshToken: {self.refreshToken}')
      
      self.headers['X-BRING-USER-UUID'] = self.uuid
      self.headers['Authorization'] = f'Bearer {self.bearerToken}'
      self.putHeaders.update(self.headers)
      logging.debug(f'Bring! Successfully logged in as {self.name}')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Login failed")
    
  def find_list(self) -> None:
    """
    Finds the list with the specified name and sets the list_uuid attribute.

    Returns:
      None

    Raises:
      Exception: If loading the lists fails or if an error occurs during the request.
    """
    logging.debug(f'Bring! Finding list starts with {self.list_name}')
    url = f'{self.base_url}/bringusers/{self.uuid}/lists'
    try:
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'GET', self.headers))
      response = requests.get(url, headers=self.headers)
      response.raise_for_status()
      logging.debug(f'Received response from {url}: {response.text}')
      data = response.json()
      
      for list in data['lists']:
        logging.debug(f'Checking list {list["name"]} (UUID: {list["listUuid"]})')
        if self.list_name in list['name']:
          self.list_uuid = list['listUuid']
          logging.debug(f'Bring! Found list {list["name"]} with UUID {self.list_uuid}')
          return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Load lists failed")
    # No list matched the configured name: fail loudly instead of leaving
    # list_uuid as None and hitting .../bringlists/None later.
    raise Exception(f'Bring! No list found matching name "{self.list_name}"')
    
  def load_items(self) -> None:
    """
    Load items from the specified list UUID.

    Returns:
      dict: The loaded items as a dictionary.

    Raises:
      Exception: If loading items fails.
    """
    logging.debug(f'Bring! Loading items from list {self.list_uuid}')
    url = f'{self.base_url}/bringlists/{self.list_uuid}'
    try:
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'GET', self.headers))
      response = requests.get(url, headers=self.headers)
      response.raise_for_status()
      logging.debug(f'Received response from {url}: {response.text}')
      data = response.json()
      logging.debug(f'Bring! Loaded items from list {self.list_uuid}')
      return data
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Load items failed")
    
  def load_locale(self) -> None:
    """
    Loads the locale data from the Bring! API and populates the dictionary with item names.

    Returns:
      None

    Raises:
      Exception: If loading the locale fails.
    """
    logging.debug(f'Bring! Loading locale {self.locale}')
    url = f'https://web.getbring.com/locale/catalog.{self.locale}.json'
    try:
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'GET', self.headers))
      response = requests.get(url, headers=self.headers)
      response.raise_for_status()
      logging.debug(f'Received response from {url}: {response.text}')
      data = response.json()
      
      for section in data['catalog']['sections']:
        logging.debug(f'Loading section {section["name"]}')
        for item in section['items']:
          # Map normalized localized name -> language-independent itemId.
          # Sending the itemId as "purchase" makes Bring! recognize the
          # built-in catalog entry (icon + auto section) instead of creating
          # a custom item.
          self.dictionary[normalize(item['name'])] = item['itemId']
      logging.debug(f'Bring! Loaded locale {self.locale} with {len(self.dictionary)} catalog items')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Load locale failed")
    
  def match_item(self, item_name: str) -> tuple:
    """
    Matches a free-text item against the Bring! built-in catalog.

    Tries an exact normalized match first, then looks for the longest
    catalog name appearing as a contiguous run of words inside the text.
    Any leftover words (quantities, adjectives like "2", "intero") are
    returned as the Bring! specification so the built-in item is still used.

    Args:
      item_name (str): The raw item text from Google Keep.

    Returns:
      tuple: (purchase, specification). "purchase" is the catalog itemId when
        matched, otherwise the original text (custom item). "specification"
        holds the leftover text ("" when none).
    """
    normalized = normalize(item_name)

    # Exact catalog match.
    item_id = self.dictionary.get(normalized)
    if item_id is not None:
      return item_id, ""

    # Longest contiguous word-run match; keep original tokens for the spec.
    norm_words = normalized.split()
    orig_words = re.sub(r'\s+', ' ', item_name).strip().split()
    best = None  # (length, start, end, itemId)
    for start in range(len(norm_words)):
      for end in range(len(norm_words), start, -1):
        candidate = ' '.join(norm_words[start:end])
        found = self.dictionary.get(candidate)
        if found is not None:
          length = end - start
          if best is None or length > best[0]:
            best = (length, start, end, found)
          break
    if best is not None:
      _, start, end, item_id = best
      spec = ' '.join(orig_words[:start] + orig_words[end:])
      return item_id, spec

    # No catalog match: add as a custom item, preserving the original text.
    return item_name, ""

  def add_item(self, item_name: str) -> None:
    """
    Adds an item to the Bring! shopping list.

    Args:
      item_name (str): The name of the item to be added.

    Raises:
      Exception: If the item cannot be added to the shopping list.

    Returns:
      None
    """
    logging.debug(f'Bring! Adding item {item_name} to list {self.list_uuid}')
    url = f'{self.base_url}/bringlists/{self.list_uuid}'
    try:
      purchase, specification = self.match_item(item_name)
      matched = purchase != item_name or specification != ""
      payload = {"uuid": self.list_uuid, "purchase": purchase, "specification": specification}
      logging.debug(f'Item {item_name} -> purchase={purchase} specification={specification}')

      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'PUT', self.putHeaders, payload))
      response = requests.put(url, headers=self.putHeaders, data=payload)
      response.raise_for_status()
      logging.debug(f'Received response from {url} (Status code: {response.status_code}): {response.text}')
      # Only log an INFO line when an item is actually added (a change).
      if matched:
        spec_suffix = f' (spec: "{specification}")' if specification else ''
        logging.info(f'Bring! Added "{item_name}" as catalog item "{purchase}"{spec_suffix}')
      else:
        logging.info(f'Bring! Added "{item_name}" as custom item')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Add item failed")
    

class GoogleKeep:
  def __init__(self, email: str, app_password: str, shopping_list_name: str, suffix: str, master_token: str = None) -> None:
    """
    Initializes a new instance of the class.

    Args:
      email (str): The email address of the user.
      app_password (str): The application password for authentication.
      shopping_list_name (str): The name of the shopping list.
      suffix (str): Suffix to strip from item names (may be empty).
      master_token (str, optional): A Google master token. When set, it is
        used to authenticate via keep.resume(), which is the only login flow
        Google still accepts for gkeepapi (password/app-password login now
        returns BadAuthentication). Defaults to None.

    Returns:
      None
    """
    self.keep = gkeepapi.Keep()
    self.email = email
    self.password = app_password
    self.master_token = master_token or None
    self.shopping_list_name = shopping_list_name
    self.suffix = None if suffix == "" else suffix
    self.shopping_list = []
    logging.debug(f'Initialized GoogleKeep with email {self.email} and shopping list name {self.shopping_list_name}')

  def login(self) -> None:
    """
    Logs into Google Keep and syncs the data.

    Uses the master token (keep.resume) when available, otherwise falls back
    to password login. As of Google's auth changes, password/app-password
    login typically fails with BadAuthentication, so a master token is
    required. Obtain one once with gpsoauth and store it in
    GOOGLE_MASTER_TOKEN (see README).

    Raises:
      Exception: If the login fails.
    """
    try:
      if self.master_token:
        logging.debug(f'Google Keep Logging in as {self.email} with master token')
        # gkeepapi renamed resume() -> authenticate() (>=0.16); keep both so we
        # work on old (0.14.x) and new versions without a deprecation warning.
        authenticate = getattr(self.keep, 'authenticate', None) or self.keep.resume
        authenticate(self.email, self.master_token)
      else:
        logging.debug(f'Google Keep Logging in as {self.email} with password')
        self.keep.login(self.email, self.password)
      self.keep.sync()
      logging.debug(f'Google Keep Successfully logged in as {self.email}')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Google Login failed")
    
  def load_shopping_list(self) -> bool:
    """
    Loads the shopping list from Google Keep.

    Returns:
      bool: True if the shopping list is successfully loaded with items, False otherwise.
    
    Raises:
      Exception: If there is an error while loading the shopping list.
    """
    logging.debug(f'Google Loading shopping list {self.shopping_list_name}')
    try:
      for note in self.keep.all():
        logging.debug(f'Checking note {note.title}')
        if note.title == self.shopping_list_name:
          logging.debug(f'Found shopping list {self.shopping_list_name}')
          for item in note.items:
            logging.debug(f'Checking item {item.text} (Checked: {item.checked})')
            if not item.checked:
              logging.debug(f'item {item.text} found in shopping list - check for transformation')
              new_item = item.text
              if self.suffix and item.text.endswith(self.suffix):
                logging.debug(f'Removing suffix {self.suffix} from item {item.text}')
                new_item = item.text[:-len(self.suffix)]
              new_item = new_item.strip()
              logging.debug(f'Adding item {new_item} to shopping list')
              self.shopping_list.append(new_item)
      logging.debug(f'Shopping list: {self.shopping_list}')
      logging.debug(f'Google Loaded shopping list {self.shopping_list_name}')
      return len(self.shopping_list) > 0
    except Exception as e:
      logging.error(e)
      raise Exception("Google Load shopping list failed")
  
  def delete_items(self) -> None:
    """
    Delete items in the shopping list.

    Raises:
      Exception: If checking items fails.
    """
    logging.debug(f'Google Checking items in shopping list {self.shopping_list_name}')
    try:
      deleted = 0
      for note in self.keep.all():
        logging.debug(f'Checking note {note.title}')
        if note.title == self.shopping_list_name:
          logging.debug(f'Found shopping list {self.shopping_list_name}')
          for item in note.items:
            logging.debug(f'Deleting item {item.text} (Checked: {item.checked})')
            if not item.checked:
              logging.debug(f'Deleting item {item.text}')
              item.delete()
              deleted += 1
      # Single sync after all deletes instead of one network round-trip per item.
      if deleted:
        self.keep.sync()
        logging.info(f'Google Deleted {deleted} synced items from shopping list {self.shopping_list_name}')
      else:
        logging.debug(f'Google No items to delete in shopping list {self.shopping_list_name}')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Google Delete items failed")

def main() -> None:
  """
  Synchronizes a Google Shopping List with Bring shopping app.

  This function retrieves the necessary credentials from environment variables,
  initializes the Bring and GoogleKeep instances, and performs the synchronization
  by adding items from the Google Shopping List to the Bring shopping app.

  Raises:
    Exception: If any error occurs during the synchronization process.
  """
  format = "%(asctime)s\t[%(levelname)s] - %(funcName)s:\t %(message)s (%(filename)s:%(lineno)d)" if os.environ.get('DEBUG') == "TRUE" else "%(asctime)s\t%(funcName)s: %(message)s"
  log_level = logging.DEBUG if os.environ.get('DEBUG') == "TRUE" else logging.INFO
  logging.basicConfig(format=format, level=log_level, datefmt="%Y-%m-%d %H:%M:%S")
  
  BRING_EMAIL = os.environ.get('BRING_EMAIL')
  BRING_PASSWORD = os.environ.get('BRING_PASSWORD')
  BRING_LIST_NAME = os.environ.get('BRING_LIST_NAME')
  BRING_LOCALE = os.environ.get('BRING_LOCALE') or 'it-IT'
  GOOGLE_EMAIL = os.environ.get('GOOGLE_EMAIL')
  GOOGLE_APP_PASSWORD = os.environ.get('GOOGLE_APP_PASSWORD')
  GOOGLE_MASTER_TOKEN = os.environ.get('GOOGLE_MASTER_TOKEN')
  GOOGLE_SHOPPING_LIST_NAME = os.environ.get('GOOGLE_SHOPPING_LIST_NAME')
  GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED = os.environ.get('GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED')

  bring = Bring(BRING_EMAIL, BRING_PASSWORD, BRING_LIST_NAME, BRING_LOCALE)
  keep = GoogleKeep(GOOGLE_EMAIL, GOOGLE_APP_PASSWORD, GOOGLE_SHOPPING_LIST_NAME, GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED, GOOGLE_MASTER_TOKEN)
  logging.debug("Starting sync Google Shopping List to Bring!")
  try:
    keep.login()
    if not keep.load_shopping_list():
      logging.debug(f'No items found in shopping list {keep.shopping_list_name}')
      return None
    bring.login()
    bring.find_list()
    bring.load_locale()
    for item in keep.shopping_list:
      bring.add_item(item)
    keep.delete_items()
  except Exception as e:
    logging.error(e)

if __name__ == '__main__':
  main()