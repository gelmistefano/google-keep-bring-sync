import gkeepapi
import requests
import logging
import os

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
    logging.info(f'Bring! Logging in as {self.email}')
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
      logging.info(f'Bring! Successfully logged in as {self.name}')
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
    logging.info(f'Bring! Finding list starts with {self.list_name}')
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
          logging.info(f'Bring! Found list {list["name"]} with UUID {self.list_uuid}')
          return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Load lists failed")
    
  def load_items(self) -> None:
    """
    Load items from the specified list UUID.

    Returns:
      dict: The loaded items as a dictionary.

    Raises:
      Exception: If loading items fails.
    """
    logging.info(f'Bring! Loading items from list {self.list_uuid}')
    url = f'{self.base_url}/bringlists/{self.list_uuid}'
    try:
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'GET', self.headers))
      response = requests.get(url, headers=self.headers)
      response.raise_for_status()
      logging.debug(f'Received response from {url}: {response.text}')
      data = response.json()
      logging.info(f'Bring! Loaded items from list {self.list_uuid}')
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
    logging.info(f'Bring! Loading locale {self.locale}')
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
          self.dictionary[item['name'].lower()] = item['itemId']
      logging.info(f'Bring! Loaded locale {self.locale}')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Load locale failed")
    
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
    logging.info(f'Bring! Adding item {item_name} to list {self.list_uuid}')
    url = f'{self.base_url}/bringlists/{self.list_uuid}'
    try:
      # Search for item_name in self.dictionary
      item_value = self.dictionary.get(item_name)
      purchase = item_value if item_value is not None else item_name
      payload = {"uuid": self.list_uuid, "purchase": purchase}
      logging.debug(f'Item {item_name} has value {item_value} and purchase {purchase}')
      
      logging.debug(f'Sending API call to {url}')
      logging.debug(debug_curl_output(url, 'PUT', self.putHeaders, payload))
      response = requests.put(url, headers=self.putHeaders, data=payload)
      response.raise_for_status()
      logging.debug(f'Received response from {url} (Status code: {response.status_code}): {response.text}')
      logging.info(f'Bring! Added item {item_name} to list {self.list_uuid}')
      return None
    except Exception as e:
      logging.error(e)
      raise Exception("Bring! Add item failed")
    

class GoogleKeep:
  def __init__(self, email: str, app_password: str, shopping_list_name: str) -> None:
    """
    Initializes a new instance of the class.

    Args:
      email (str): The email address of the user.
      app_password (str): The application password for authentication.
      shopping_list_name (str): The name of the shopping list.

    Returns:
      None
    """
    self.keep = gkeepapi.Keep()
    self.email = email
    self.password = app_password
    self.shopping_list_name = shopping_list_name
    self.shopping_list = []
    logging.debug(f'Initialized GoogleKeep with email {self.email} and shopping list name {self.shopping_list_name}')
    
  def login(self) -> None:
    """
    Logs into Google Keep using the provided email and password,
    and syncs the data.

    Raises:
      Exception: If the login fails.
    """
    try:
      logging.info(f'Google Keep Logging in as {self.email}')
      self.keep.login(self.email, self.password)
      self.keep.sync()
      logging.info(f'Google Keep Successfully logged in as {self.email}')
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
    logging.info(f'Google Loading shopping list {self.shopping_list_name}')
    try:
      for note in self.keep.all():
        logging.debug(f'Checking note {note.title}')
        if note.title == self.shopping_list_name:
          logging.debug(f'Found shopping list {self.shopping_list_name}')
          for item in note.items:
            logging.debug(f'Checking item {item.text} (Checked: {item.checked})')
            if not item.checked:
              logging.debug(f'Adding item {item.text} to shopping list')
              self.shopping_list.append(item.text)
      logging.debug(f'Shopping list: {self.shopping_list}')
      logging.info(f'Google Loaded shopping list {self.shopping_list_name}')
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
    logging.info(f'Google Checking items in shopping list {self.shopping_list_name}')
    try:
      for note in self.keep.all():
        logging.debug(f'Checking note {note.title}')
        if note.title == self.shopping_list_name:
          logging.debug(f'Found shopping list {self.shopping_list_name}')
          for item in note.items:
            logging.debug(f'Deleting item {item.text} (Checked: {item.checked})')
            if not item.checked:
              logging.debug(f'Deleting item {item.text}')
              item.delete()
              self.keep.sync()
      logging.info(f'Google Deleted items in shopping list {self.shopping_list_name}')
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
  BRING_LOCALE = os.environ.get('BRING_LOCALE')
  GOOGLE_EMAIL = os.environ.get('GOOGLE_EMAIL')
  GOOGLE_APP_PASSWORD = os.environ.get('GOOGLE_APP_PASSWORD')
  GOOGLE_SHOPPING_LIST_NAME = os.environ.get('GOOGLE_SHOPPING_LIST_NAME')
  
  bring = Bring(BRING_EMAIL, BRING_PASSWORD, BRING_LIST_NAME, BRING_LOCALE)
  keep = GoogleKeep(GOOGLE_EMAIL, GOOGLE_APP_PASSWORD, GOOGLE_SHOPPING_LIST_NAME)
  logging.info("Starting sync Google Shopping List to Bring!")
  try:
    keep.login()
    if not keep.load_shopping_list():
      logging.info(f'No items found in shopping list {keep.shopping_list_name}')
      return None
    bring.login()
    bring.find_list()
    bring.load_locale()
    for item in keep.shopping_list:
      bring.add_item(item)
    keep.delete_items()
  except Exception as e:
    logging.error(e)

main()