import os
import distro
import platform
import random
import time
import logging
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException,
    WebDriverException, NoSuchWindowException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# --- Global Settings ---
logging.basicConfig(level=logging.INFO,format='%(asctime)s UTC - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
DOTENV_PATH = '/app/config/.env'
# Define separate state files
CLAIM_SCHEDULE_STATE_FILE = '/app/config/claim_schedule_state.json'
EXTENSION_SCHEDULE_STATE_FILE = '/app/config/extension_schedule_state.json'
DEFAULT_WAIT_TIMEOUT = 20
CHECK_CLAIM_INTERVAL_MINUTES = 300 # 5 hours
CHECK_EXTENSION_INTERVAL_MINUTES = 5 # 5 minutes
MAIN_LOOP_SLEEP_SECONDS = 30 # Sleep between main loop iterations
RESTART_DELAY_SECONDS = 10 # Delay if restart container is needed
CONNECTING_WAIT_TIMEOUT_SECONDS = 45 # Wait for 'Connecting...' to resolve
SHORT_WAIT = 5 # Pause seconds for processing
MEDIUM_WAIT = 10 # Pause seconds for processing
LONG_WAIT = 20 # Pause seconds for processing

# --- Essential Helper Functions ---

def wait_for_element(driver, by, value, timeout=DEFAULT_WAIT_TIMEOUT):
    """Waits for an element to be present and returns it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logging.error(f"Timeout waiting for element: {by}={value} at URL {driver.current_url}")
        raise

def check_element_exists(driver, by, value, timeout=5):
    """Checks if an element exists without raising an error if not found."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except TimeoutException:
        return False

def get_os_info():
    """Gets basic OS information."""
    try:
        if platform.system() == 'Linux':
            return f"{distro.name(pretty=True)} {distro.version(pretty=True, best=True)}"
        else:
            return f"{platform.system()} {platform.version()}"
    except Exception as e:
        logging.warning(f"Could not get OS information: {e}")
        return "Unknown"

def click_claim_button(driver, claim_button_xpath):
    """Tries to find and click the 'Claim' button."""
    logging.info("Checking for the 'Claim' button existence...")
    if check_element_exists(driver, By.XPATH, claim_button_xpath, timeout=10):
        logging.info("'Claim' button found!")
        try:
            claim_button = wait_for_element(driver, By.XPATH, claim_button_xpath, timeout=15)
            logging.info("Centering the 'Claim' button on the screen...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", claim_button)
            time.sleep(random.uniform(0.5, 1.5))

            claim_button_clickable = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, claim_button_xpath))
            )
            logging.info("Clicking the 'Claim' button...")
            claim_button_clickable.click()
            logging.info("'Claim' button clicked successfully.")
            time.sleep(SHORT_WAIT)
            return True

        except ElementClickInterceptedException:
             logging.warning("'Claim' button intercepted. Trying to click via JavaScript...")
             try:
                 claim_button_js = driver.find_element(By.XPATH, claim_button_xpath)
                 driver.execute_script("arguments[0].click();", claim_button_js)
                 logging.info("'Claim' button clicked successfully via JavaScript.")
                 time.sleep(SHORT_WAIT)
                 return True
             except Exception as js_click_err:
                 logging.error(f"Failed to click 'Claim' button via JavaScript: {js_click_err}")
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error trying to find or click the 'Claim' button after finding it initially: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while trying to click the 'Claim' button: {e}", exc_info=True)
    else:
        logging.info("'Claim' button not found on the dashboard (normal if there's nothing to claim).")
    return False

# --- NEW Schedule State Loading Functions ---

def load_schedule_claim_state():
    """Loads the next claim check time from its state file."""
    try:
        with open(CLAIM_SCHEDULE_STATE_FILE, 'r') as f:
            state = json.load(f)
            claim_time = state.get('next_claim_check_time')
            # Basic validation: ensure it's a number
            if not isinstance(claim_time, (int, float)): claim_time = None
            return claim_time
    except FileNotFoundError:
        logging.info(f"Claim schedule state file ({CLAIM_SCHEDULE_STATE_FILE}) not found. Will use default time.")
        return None
    except (json.JSONDecodeError, TypeError) as e:
        logging.warning(f"Error reading or parsing claim schedule state file: {e}. Will use default time.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading claim schedule state: {e}", exc_info=True)
        return None

def load_schedule_extension_state():
    """Loads the next extension check time from its state file."""
    try:
        with open(EXTENSION_SCHEDULE_STATE_FILE, 'r') as f:
            state = json.load(f)
            ext_time = state.get('next_extension_check_time')
            # Basic validation: ensure it's a number
            if not isinstance(ext_time, (int, float)): ext_time = None
            return ext_time
    except FileNotFoundError:
        logging.info(f"Extension schedule state file ({EXTENSION_SCHEDULE_STATE_FILE}) not found. Will use default time.")
        return None
    except (json.JSONDecodeError, TypeError) as e:
        logging.warning(f"Error reading or parsing extension schedule state file: {e}. Will use default time.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading extension schedule state: {e}", exc_info=True)
        return None

# --- NEW Schedule State Saving Functions ---

def save_schedule_claim_state(claim_time):
    """Saves the next claim check time to its state file."""
    state = {'next_claim_check_time': claim_time}
    try:
        with open(CLAIM_SCHEDULE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        logging.debug(f"Claim schedule state saved to {CLAIM_SCHEDULE_STATE_FILE}")
    except IOError as e:
        logging.error(f"Failed to save claim schedule state to {CLAIM_SCHEDULE_STATE_FILE}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error saving claim schedule state: {e}", exc_info=True)

def save_schedule_extension_state(ext_time):
    """Saves the next extension check time to its state file."""
    state = {'next_extension_check_time': ext_time}
    try:
        with open(EXTENSION_SCHEDULE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        logging.debug(f"Extension schedule state saved to {EXTENSION_SCHEDULE_STATE_FILE}")
    except IOError as e:
        logging.error(f"Failed to save extension schedule state to {EXTENSION_SCHEDULE_STATE_FILE}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error saving extension schedule state: {e}", exc_info=True)


# --- Extension Specific Functions ---

def activate_extension_if_needed(driver):
    """Tries to activate the extension by clicking Login or Activate if not 'Activated'."""
    if check_element_exists(driver, By.XPATH, "//*[text()='Activated']"):
        logging.info("Extension is already 'Activated'.") # Less verbose log here
        return True

    logging.info("'Activated' not found, searching for activation buttons...")
    try:
        # Try clicking Login first
        if check_element_exists(driver, By.XPATH, "//*[text()='Login']", timeout=5):
            logging.info("'Login' button found, clicking...")
            login_button = wait_for_element(driver, By.XPATH, "//*[text()='Login']", timeout=5)
            login_button.click()
            wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=LONG_WAIT)
            logging.info("Extension activated after clicking 'Login'.")
            return True
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
        logging.warning(f"Could not click 'Login' or it didn't lead to activation: {e}")

    try:
        # Try clicking Activate as a fallback
        if check_element_exists(driver, By.XPATH, "//*[text()='Activate']", timeout=5):
            logging.info("'Activate' button found, clicking...")
            activate_button = wait_for_element(driver, By.XPATH, "//*[text()='Activate']", timeout=5)
            activate_button.click()
            wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=LONG_WAIT)
            logging.info("Extension activated after clicking 'Activate'.")
            return True
    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
        logging.error(f"Failed to click 'Activate': {e}")

    logging.error("Failed to activate the extension. 'Login' or 'Activate' buttons not found, didn't work, or didn't lead to 'Activated'.")
    return False # Critical activation failure

def verify_extension_connection(driver):
    """Verifies the connection status on the extension page (assumes already on the page). Returns True if connected."""
    logging.info("Verifying connection status on the extension page...") # Less verbose log here

    # 1. Ensure it's Activated first
    if not activate_extension_if_needed(driver):
         logging.error("Failed to ensure 'Activated' state during connection verification.")
         return False # Critical failure if cannot (re)activate

    # 2. Check connection states
    if check_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
        logging.info("Connection Status: Connected.")
        return True

    elif check_element_exists(driver, By.XPATH, "//*[text()='Disconnected']"):
        logging.warning("Connection Status: Disconnected!")
        return False # Failure

    elif check_element_exists(driver, By.XPATH, "//*[text()='Connecting...']"):
        logging.warning(f"Connection Status: Connecting... Waiting up to {CONNECTING_WAIT_TIMEOUT_SECONDS}s...")
        try:
            WebDriverWait(driver, CONNECTING_WAIT_TIMEOUT_SECONDS).until(
                 EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[text()='Connected']")),
                    EC.presence_of_element_located((By.XPATH, "//*[text()='Disconnected']"))
                 )
            )
            # Re-check after the wait
            if check_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
                 logging.info("Connection Status: Connected (after waiting).")
                 return True
            else:
                 logging.warning("Connection Status: Not 'Connected' after waiting for 'Connecting...'. Likely Disconnected.")
                 return False
        except TimeoutException:
            logging.error(f"Timeout waiting for 'Connected' or 'Disconnected' after 'Connecting...' status. Extension seems stuck.")
            return False
    else:
        # Add a short wait and retry if no status found immediately
        logging.warning("Connection Status: Initially unknown. Waiting a moment...")
        time.sleep(SHORT_WAIT)
        if check_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
             logging.info("Connection Status: Connected (after short wait).")
             return True
        elif check_element_exists(driver, By.XPATH, "//*[text()='Disconnected']"):
             logging.warning("Connection Status: Disconnected (after short wait).")
             return False
        else:
             logging.error("Connection Status: Still unknown after wait.")
             return False # Failure


# --- Main Logic ---

# Declare these globally so they are accessible in the finally block
next_claim_check_time = 0
next_extension_check_time = 0

def run_nodepay():
    global next_claim_check_time, next_extension_check_time # Need to modify global vars

    logging.info(f"Starting Nodepay Script - OS: {get_os_info()}")
    start_time = time.time()

    # 1. Load Configuration
    if not load_dotenv(dotenv_path=DOTENV_PATH):
        logging.error(f".env file not found or could not be loaded at {DOTENV_PATH}.")
        return False
    np_key = os.getenv('NP_KEY')
    extension_id = os.getenv('EXTENSION_ID')
    extension_url = os.getenv('EXTENSION_URL')
    if not np_key:
        logging.error("NP_KEY variable not found in .env.")
        return False
    if not extension_id or not extension_url:
        logging.error("EXTENSION_ID or EXTENSION_URL not defined.")
        return False
    extension_crx_path = f'/app/{extension_id}.crx'
    extension_internal_page = f'chrome-extension://{extension_id}/index.html'
    dashboard_url = f"{extension_url}dashboard"
    claim_button_xpath = "//div[contains(@class, 'cursor-pointer') and contains(@class, 'bg-[#58CC02]')][.//div[contains(text(), 'Claim')]]"
    if not os.path.exists(extension_crx_path):
        logging.error(f"Extension file not found at {extension_crx_path}.")
        return False
    logging.info(f"Configuration loaded. EXTENSION_ID: {extension_id}")


    # 2. Configure WebDriver
    driver = None
    main_window_handle = None
    extension_window_handle = None
    try:
        chrome_options = Options()
        chrome_options.add_extension(extension_crx_path)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new') # Use 'new' headless mode
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1024,768')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        logging.info("Initializing WebDriver...")
        driver = webdriver.Chrome(options=chrome_options)
        logging.info(f"WebDriver initialized. ChromeDriver Version: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'N/A')}")
        time.sleep(SHORT_WAIT)

        # Define the main working tab
        try:
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) >= 1)
            handles = driver.window_handles
            driver.switch_to.new_window('tab')
            driver.get("about:blank")
            main_window_handle = driver.current_window_handle
            logging.info(f"Main working window ('about:blank') defined: {main_window_handle}")
            if len(handles) > 0 and handles[0] != main_window_handle:
                 if handles[0] in driver.window_handles:
                      logging.info(f"Closing extra initial tab: {handles[0]}")
                      driver.switch_to.window(handles[0])
                      driver.close()
                      driver.switch_to.window(main_window_handle)
        except TimeoutException:
            logging.error("Timeout waiting for the initial WebDriver window.")
            return False
        except Exception as e:
             logging.error(f"Error setting up main window: {e}")
             return False

        # 3. Login to Nodepay Site (via Local Storage in the main tab)
        logging.info(f"Navigating to {extension_url} in main tab ({main_window_handle})...")
        driver.switch_to.window(main_window_handle)
        driver.get(extension_url)
        time.sleep(SHORT_WAIT)
        logging.info("Injecting token into Local Storage...")
        try:
            escaped_key = np_key.replace("'", "\\'")
            driver.execute_script(f"localStorage.setItem('np_trigger_1346947533587562496_x', 'checked');")
            driver.execute_script(f"localStorage.setItem('np_webapp_token', '{escaped_key}');")
            driver.execute_script(f"localStorage.setItem('np_token', '{escaped_key}');")
            stored_token = driver.execute_script("return localStorage.getItem('np_token');")
            if stored_token and stored_token.startswith(np_key[:5]):
                 logging.info("Token injected successfully into Local Storage.")
            else:
                 logging.warning("Failed to verify token in Local Storage after injection.")
                 return False
        except WebDriverException as e:
             logging.error(f"Error injecting token into Local Storage: {e}")
             return False

        # 4. Verify Dashboard Login (in a temporary tab)
        logging.info("Verifying initial login on dashboard (in temporary tab)...")
        driver.switch_to.new_window('tab')
        temp_dash_handle = driver.current_window_handle
        login_success = False
        try:
            driver.get(dashboard_url)
            wait_for_element(driver, By.XPATH, "//*[text()='Dashboard']", timeout=LONG_WAIT)
            logging.info("Initial site login successful.")
            login_success = True
        except TimeoutException:
            logging.error("Failed to log into site - 'Dashboard' not found. Check if NP_KEY is valid.")
        except Exception as e:
             logging.error(f"Unexpected error during initial login verification: {e}", exc_info=True)
        finally:
            logging.info(f"Closing initial temporary dashboard tab ({temp_dash_handle}).")
            try:
                if driver.current_window_handle != temp_dash_handle:
                     driver.switch_to.window(temp_dash_handle)
                driver.close()
            except NoSuchWindowException:
                 logging.warning(f"Tab {temp_dash_handle} was already closed.")
            except Exception as e_close:
                logging.warning(f"Error closing temporary dashboard tab: {e_close}")
            if main_window_handle in driver.window_handles:
                 driver.switch_to.window(main_window_handle)
            else:
                 logging.error("Main tab disappeared after closing initial dashboard. Exiting.")
                 return False

        if not login_success:
            logging.error("Initial dashboard login failed. Exiting.")
            return False

        # 5. Main Monitoring Loop - Load Schedule or Set Defaults
        logging.info(f"Setup complete ({time.time() - start_time:.2f}s). Loading schedule state...")

        # --- Use NEW loading functions ---
        loaded_claim_time = load_schedule_claim_state()
        loaded_ext_time = load_schedule_extension_state()
        current_time_init = time.time()

        # Initialize Claim Check Time
        if loaded_claim_time and loaded_claim_time > 0:
            next_claim_check_time = max(loaded_claim_time, current_time_init)
            logging.info(f"Loaded from storage. Next Claim check scheduled for: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_claim_check_time))}")
        else:
            next_claim_check_time = current_time_init
            logging.info(f"First Claim check scheduled for: NOW ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_claim_check_time))})")

        # Initialize Extension Check Time
        if loaded_ext_time and loaded_ext_time > 0:
            next_extension_check_time = max(loaded_ext_time, current_time_init)
            logging.info(f"Loaded from storage. Next Extension check scheduled for: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_extension_check_time))}")
        else:
            next_extension_check_time = current_time_init
            logging.info(f"First Extension check scheduled for: NOW ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_extension_check_time))})")

        # --- Reset persistent scheduled values
        save_schedule_claim_state(0)
        save_schedule_extension_state(0)

        logging.info("Entering main loop.")

        while True:
            current_time = time.time()
            active_handles = driver.window_handles

            # --- Main Tab Sanity Check ---
            if main_window_handle not in active_handles:
                logging.error("Main working tab not found! Attempting recovery...")
                if extension_window_handle and extension_window_handle in active_handles:
                     main_window_handle = extension_window_handle
                     driver.switch_to.window(main_window_handle)
                     logging.warning(f"Set extension tab ({main_window_handle}) as main.")
                elif active_handles:
                     main_window_handle = active_handles[0]
                     driver.switch_to.window(main_window_handle)
                     logging.warning(f"Set new main tab (first available): {main_window_handle}")
                else:
                     logging.error("No tabs found! Critical failure.")
                     return False

            # --- Check if the tracked extension tab still exists ---
            if extension_window_handle and extension_window_handle not in active_handles:
                 logging.warning(f"Tracked extension tab ({extension_window_handle}) not found. Will be recreated on next check.")
                 extension_window_handle = None

            # Ensure focus is on the main tab before checks
            if driver.current_window_handle != main_window_handle:
                 try:
                     driver.switch_to.window(main_window_handle)
                 except NoSuchWindowException:
                      logging.error("Failed to switch back to main tab (no longer exists?). Restarting.")
                      return False

            # --- Periodic Claim Check ---
            if current_time >= next_claim_check_time:
                logging.info("-" * 30)
                logging.info(f"Starting periodic Claim check...")
                claim_dashboard_handle = None
                original_handle = driver.current_window_handle # Save current tab (should be main)
                try:
                    # Open the dashboard in a NEW temporary tab
                    driver.switch_to.new_window('tab')
                    claim_dashboard_handle = driver.current_window_handle
                    logging.info(f"Opening {dashboard_url} in temporary tab ({claim_dashboard_handle}) for Claim check...")
                    driver.get(dashboard_url)
                    wait_for_element(driver, By.XPATH, "//*[text()='Dashboard']", timeout=LONG_WAIT)
                    click_claim_button(driver, claim_button_xpath)

                except TimeoutException:
                     logging.error("Timeout waiting for Dashboard during Claim check.")
                except WebDriverException as e:
                     logging.error(f"WebDriver error during Claim check: {e}")
                except Exception as e:
                     logging.error(f"Unexpected error during Claim check: {e}", exc_info=True)
                finally:
                    # --- Close ONLY the temporary claim tab ---
                    if claim_dashboard_handle and claim_dashboard_handle in driver.window_handles:
                        logging.info(f"Closing temporary Claim tab ({claim_dashboard_handle}).")
                        try:
                            current_handle_before_close = None
                            try: current_handle_before_close = driver.current_window_handle
                            except WebDriverException: pass

                            if current_handle_before_close != claim_dashboard_handle:
                                try: driver.switch_to.window(claim_dashboard_handle)
                                except NoSuchWindowException:
                                     logging.warning(f"Could not focus Claim tab ({claim_dashboard_handle}) before closing, might be closed already.")
                                     claim_dashboard_handle = None

                            if claim_dashboard_handle: driver.close()

                        except NoSuchWindowException:
                            logging.warning(f"Claim tab ({claim_dashboard_handle}) was already closed when trying to close explicitly.")
                        except WebDriverException as e_close:
                            logging.error(f"WebDriver error closing Claim tab: {e_close}")
                        except Exception as e_close:
                             logging.error(f"Unexpected error closing Claim tab: {e_close}")

                    # --- Reinforced and Direct Return Logic ---
                    try:
                        active_handles_after_close = driver.window_handles
                        if original_handle in active_handles_after_close:
                            driver.switch_to.window(original_handle)
                            logging.debug(f"Focus returned directly to original handle ({original_handle})")
                        elif main_window_handle in active_handles_after_close:
                            logging.warning("Original handle not found after claim, returning to main.")
                            driver.switch_to.window(main_window_handle)
                        elif active_handles_after_close:
                             fallback_handle = active_handles_after_close[0]
                             logging.error(f"Neither original nor main handle found! Attempting fallback to first remaining tab: {fallback_handle}")
                             driver.switch_to.window(fallback_handle)
                        else:
                            logging.error("No windows found after closing claim. Critical failure.")
                            next_claim_check_time = 0 # Reset to force a restart
                            return False # Definitely signals failure

                    except NoSuchWindowException:
                         logging.error("Critical failure attempting to switch back - Target window disappeared unexpectedly. Restarting.")
                         next_claim_check_time = 0 # Reset to force a restart
                         return False
                    except WebDriverException as e_switch:
                         logging.error(f"Critical WebDriver error attempting to return to original/main handle: {e_switch}. Restarting.")
                         next_claim_check_time = 0 # Reset to force a restart
                         return False

                    # Schedule next check
                    next_claim_check_time = time.time() + (CHECK_CLAIM_INTERVAL_MINUTES * 60) + random.uniform(-180, 180)
                    logging.info(f"Next Claim check scheduled for: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_claim_check_time))}")
                    logging.info("-" * 30)

            # --- Periodic Extension Check (with creation/recreation) ---
            if current_time >= next_extension_check_time:
                logging.info("-" * 30)
                logging.info(f"Starting periodic Extension check...")
                extension_status_ok = False
                original_handle = driver.current_window_handle
                temp_ext_handle = None

                try:
                    # Check if we have a valid handle and the tab still exists
                    if extension_window_handle and extension_window_handle in driver.window_handles:
                        logging.info(f"Checking existing extension tab: {extension_window_handle}")
                        driver.switch_to.window(extension_window_handle)
                        logging.info(f"Refreshing extension page ({extension_internal_page})...")
                        driver.refresh()
                        time.sleep(MEDIUM_WAIT)
                        extension_status_ok = verify_extension_connection(driver)
                    else:
                        if extension_window_handle:
                             logging.warning(f"Extension tab {extension_window_handle} not found. Recreating...")
                        else:
                             logging.info("Extension tab does not exist. Creating...")

                        driver.switch_to.new_window('tab')
                        temp_ext_handle = driver.current_window_handle
                        logging.info(f"Navigating to {extension_internal_page} in new tab {temp_ext_handle}")
                        driver.get(extension_internal_page)
                        time.sleep(MEDIUM_WAIT)
                        extension_status_ok = verify_extension_connection(driver)

                        if extension_status_ok:
                             extension_window_handle = temp_ext_handle
                             logging.info(f"New extension tab ({extension_window_handle}) created and verified successfully.")
                        else:
                             logging.error("Failed to verify connection after creating extension tab.")
                             if temp_ext_handle and temp_ext_handle in driver.window_handles:
                                  logging.info(f"Closing extension tab that failed creation: {temp_ext_handle}")
                                  try:
                                      if driver.current_window_handle != temp_ext_handle:
                                           driver.switch_to.window(temp_ext_handle)
                                      driver.close()
                                  except Exception as e_close:
                                       logging.warning(f"Error closing failed extension tab: {e_close}")
                             extension_window_handle = None

                except WebDriverException as e:
                    logging.error(f"WebDriver error during Extension check/creation: {e}")
                    extension_status_ok = False
                    if temp_ext_handle and temp_ext_handle == driver.current_window_handle:
                         extension_window_handle = None
                         try: driver.close()
                         except: pass
                except Exception as e:
                    logging.error(f"Unexpected error during Extension check/creation: {e}", exc_info=True)
                    extension_status_ok = False
                    if temp_ext_handle and temp_ext_handle == driver.current_window_handle:
                         extension_window_handle = None
                         try: driver.close()
                         except: pass
                finally:
                    if original_handle in driver.window_handles:
                        if driver.current_window_handle != original_handle:
                            try: driver.switch_to.window(original_handle)
                            except NoSuchWindowException:
                                logging.warning("Original handle disappeared while trying to switch back after extension check.")
                                if main_window_handle in driver.window_handles: driver.switch_to.window(main_window_handle)
                    elif main_window_handle in driver.window_handles:
                         logging.warning("Original handle not found after extension check, returning to main.")
                         driver.switch_to.window(main_window_handle)

                if not extension_status_ok:
                    logging.error("Periodic extension check failed. Restarting the container.")
                    next_extension_check_time = 0 # Reset to force a restart
                    return False # Signal failure

                # Schedule the next extension check
                next_extension_check_time = time.time() + (CHECK_EXTENSION_INTERVAL_MINUTES * 60) + random.uniform(-180, 180)
                logging.info(f"Next Extension check scheduled for: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_extension_check_time))}")
                logging.info("-" * 30)

            # Sleep
            try:
                time_to_next_claim = next_claim_check_time - current_time
                time_to_next_extension = next_extension_check_time - current_time
                sleep_duration = max(5, min(time_to_next_claim, time_to_next_extension, MAIN_LOOP_SLEEP_SECONDS))
                time.sleep(sleep_duration)
            except ValueError:
                time.sleep(5)

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Saving state before exiting...")
        # --- Use NEW saving functions ---
        save_schedule_claim_state(next_claim_check_time)
        save_schedule_extension_state(next_extension_check_time)
        return True # Indicate clean shutdown planned
    except WebDriverException as e:
         logging.error(f"Critical WebDriver error: {e}", exc_info=True)
         return False
    except Exception as e:
        logging.error(f"Critical unexpected error during execution: {e}", exc_info=True)
        return False
    finally:
        # --- Save state on any exit path (except maybe successful clean shutdown?) ---
        # Moved the save calls here to ensure state is saved even on unexpected error exit
        # Need to check if next_*_time variables have been initialized (they are global now)
        if 'next_claim_check_time' in globals() and next_claim_check_time > 0:
             save_schedule_claim_state(next_claim_check_time)
        if 'next_extension_check_time' in globals() and next_extension_check_time > 0:
             save_schedule_extension_state(next_extension_check_time)

        if driver:
            logging.info("Closing WebDriver...")
            try:
                driver.quit()
            except Exception as e_quit:
                logging.error(f"Error during WebDriver quit: {e_quit}")


# --- Entry Point ---
if __name__ == "__main__":
    #script_version = VERSION
    script_version = "1.2 (BETA)"
    #logging.info("-" * 50)
    logging.info( "=====================================================")
    logging.info(f"      🚀  NODE-PAY AUTOMATION - v{script_version} 🚀      ")
    logging.info( "      github.com/tonygabarron/Nodepay                ")
    logging.info( "      ----------------------------------------       ")
    logging.info(f"      Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logging.info( "=====================================================")

    success = run_nodepay()
    if not success:
        # State saving is now handled in the finally block of run_nodepay
        logging.info(f"Script encountered an error or failure. Container should restart. Waiting {RESTART_DELAY_SECONDS}s...")
        time.sleep(RESTART_DELAY_SECONDS)
        exit(1)
    else:
        logging.info("Script finished normally.")
        exit(0)