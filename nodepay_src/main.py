# nodepay_src/main.py (Version with Claim Button)

import os
import distro
import platform
import subprocess
import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# --- Global Settings ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Path to the .env file INSIDE the container
DOTENV_PATH = '/app/config/.env'
# Default wait timeout for Selenium elements
DEFAULT_WAIT_TIMEOUT = 20
# Interval between checks in the main loop (1 hour)
CHECK_INTERVAL_SECONDS = 3600
# Delay before exiting to allow restart by Docker
RESTART_DELAY_SECONDS = 60

# --- Essential Helper Functions ---

def wait_for_element(driver, by, value, timeout=DEFAULT_WAIT_TIMEOUT):
    """Waits for an element to be present and returns it."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        logging.error(f"Timeout waiting for element: {by}={value}")
        raise # Re-raise the exception to be handled upstream

def check_element_exists(driver, by, value, timeout=5):
    """Checks if an element exists without throwing an error if not found."""
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
        logging.warning(f"Could not get OS info: {e}")
        return "Unknown"

# --- Main Logic ---

def run_nodepay():
    logging.info(f"Starting Nodepay Script - OS: {get_os_info()}")

    # 1. Load Configuration
    if not load_dotenv(dotenv_path=DOTENV_PATH):
        logging.error(f".env file not found or could not be loaded at {DOTENV_PATH}. Check the volume.")
        return False # Indicates initialization failure

    np_key = os.getenv('NP_KEY')
    extension_id = os.getenv('EXTENSION_ID') # Comes from Dockerfile ENV
    extension_url = os.getenv('EXTENSION_URL') # Comes from Dockerfile ENV

    if not np_key:
        logging.error("NP_KEY variable not found in .env. Please ensure it exists.")
        return False
    if not extension_id or not extension_url:
        logging.error("EXTENSION_ID or EXTENSION_URL not defined. Check the Dockerfile.")
        return False

    extension_crx_path = f'/app/{extension_id}.crx' # Path defined in Dockerfile
    extension_internal_page = f'chrome-extension://{extension_id}/index.html'

    if not os.path.exists(extension_crx_path):
        logging.error(f"Extension file not found at {extension_crx_path}. Check the download step in the Dockerfile.")
        return False

    logging.info(f"Configuration loaded. EXTENSION_ID: {extension_id}")

    # 2. Configure WebDriver
    driver = None # Initialize as None so finally knows if cleanup is needed
    try:
        chrome_options = Options()
        chrome_options.add_extension(extension_crx_path)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1024,768')
        # User agent might help avoid detection
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

        logging.info("Initializing WebDriver...")
        # Try using chromedriver from the default PATH
        driver = webdriver.Chrome(options=chrome_options)
        logging.info(f"WebDriver initialized. ChromeDriver Version: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'N/A')}")

        # 3. Login to Nodepay Website (via Local Storage)
        logging.info(f"Navigating to {extension_url}...")
        driver.get(extension_url)
        time.sleep(random.randint(3, 6)) # Short pause for the page to load

        logging.info("Injecting token into Local Storage...")
        escaped_key = np_key.replace("'", "\\'") # Escape single quotes if any
        driver.execute_script(f"localStorage.setItem('np_trigger_1346947533587562496_x', 'checked');")
        driver.execute_script(f"localStorage.setItem('np_webapp_token', '{escaped_key}');")
        driver.execute_script(f"localStorage.setItem('np_token', '{escaped_key}');")

        # Check if the token was set (optional, but good for debugging)
        stored_token = driver.execute_script("return localStorage.getItem('np_token');")
        if stored_token and stored_token.startswith(np_key[:5]):
             logging.info("Token successfully injected into Local Storage.")
        else:
             logging.warning("Failed to verify token in Local Storage after injection.")

        logging.info(f"Opening page {extension_url}dashboard to apply the token and verify login...")
        driver.get(f"{extension_url}dashboard")

        # Verify login by waiting for a dashboard element
        try:
            wait_for_element(driver, By.XPATH, "//*[text()='Dashboard']", timeout=30)
            logging.info("Website login successful ('Dashboard' element found).")
        except TimeoutException:
            logging.error("Failed to log in to the website - 'Dashboard' not found after refresh. Check the validity of NP_KEY.")
            # driver.save_screenshot('/app/config/login_failure.png') # Uncomment for debugging
            return False # Critical failure

        # <<< START: Logic to click the 'Claim' button >>>
        claim_button_xpath = "//div[contains(@class, 'cursor-pointer') and contains(@class, 'bg-[#58CC02]')][.//div[contains(text(), 'Claim')]]"
        logging.info("Checking for the existence of the 'Claim' button on the dashboard...")

        if check_element_exists(driver, By.XPATH, claim_button_xpath, timeout=10):
            logging.info("'Claim' button found!")
            try:
                # Wait a bit longer to ensure the button is ready for click
                claim_button = wait_for_element(driver, By.XPATH, claim_button_xpath, timeout=15)

                # Scroll to the button
                logging.info("Centering the 'Claim' button on the screen...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", claim_button)
                time.sleep(random.uniform(0.5, 1.5)) # Short pause after scroll

                # Wait until the button is clickable
                claim_button_clickable = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, claim_button_xpath))
                )

                logging.info("Clicking the 'Claim' button...")
                claim_button_clickable.click()
                logging.info("'Claim' button clicked successfully.")
                # Short pause for the 'Claim' action to process
                time.sleep(random.randint(3, 6))

            except ElementClickInterceptedException:
                 logging.warning("'Claim' button intercepted. Trying to click via JavaScript...")
                 try:
                     # Find the element again before attempting JS click
                     claim_button_js = driver.find_element(By.XPATH, claim_button_xpath)
                     driver.execute_script("arguments[0].click();", claim_button_js)
                     logging.info("'Claim' button clicked successfully via JavaScript.")
                     time.sleep(random.randint(3, 6))
                 except Exception as js_click_err:
                     logging.error(f"Failed to click 'Claim' button via JavaScript: {js_click_err}")
                     # driver.save_screenshot('/app/config/claim_js_click_failure.png') # Uncomment for debugging
            except (TimeoutException, NoSuchElementException) as e:
                logging.error(f"Error trying to find or click the 'Claim' button after initially finding it: {e}")
                # driver.save_screenshot('/app/config/claim_click_failure.png') # Uncomment for debugging
            except Exception as e:
                logging.error(f"Unexpected error trying to click the 'Claim' button: {e}", exc_info=True)
                # driver.save_screenshot('/app/config/claim_unexpected_failure.png') # Uncomment for debugging
        else:
            logging.info("'Claim' button not found on the dashboard (this is normal if there's nothing to claim).")
        # <<< END: Logic to click the 'Claim' button >>>

        # 4. Extension Activation
        logging.info(f"Accessing the extension's internal page: {extension_internal_page}")
        driver.get(extension_internal_page)
        time.sleep(random.randint(5, 10)) # Wait for the extension page to load

        activated = False
        # First, check if it's already activated
        if check_element_exists(driver, By.XPATH, "//*[text()='Activated']"):
            logging.info("Extension is already activated.")
            activated = True
        else:
            # If not, try clicking Login
            logging.info("'Activated' not found, looking for 'Login' button...")
            try:
                login_button = wait_for_element(driver, By.XPATH, "//*[text()='Login']", timeout=10)
                logging.info("'Login' button found, clicking...")
                login_button.click()
                # Wait a bit for activation to occur after the click
                wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=25)
                logging.info("Extension activated after clicking 'Login'.")
                activated = True
            except (TimeoutException, NoSuchElementException):
                logging.warning("'Login' button not found or did not lead to activation. Looking for 'Activate' button...")
                # If Login failed or didn't exist, try clicking Activate
                try:
                    activate_button = wait_for_element(driver, By.XPATH, "//*[text()='Activate']", timeout=10)
                    logging.info("'Activate' button found, clicking...")
                    activate_button.click()
                    wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=25)
                    logging.info("Extension activated after clicking 'Activate'.")
                    activated = True
                except (TimeoutException, NoSuchElementException):
                    logging.error("Failed to activate the extension. 'Login' or 'Activate' buttons not found or did not work.")
                    # driver.save_screenshot('/app/config/activation_failure.png') # Uncomment for debugging
                    return False # Critical failure

        if not activated:
             logging.error("Could not confirm extension activation.")
             return False

        # 5. Check Initial Connection Status
        if check_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
            logging.info("Initial connection status: Connected!")
        elif check_element_exists(driver, By.XPATH, "//*[text()='Disconnected']"):
            logging.warning("Initial connection status: Disconnected!")
        else:
            logging.warning("Initial connection status: Unknown (elements not found).")


        # 6. Clean Up Extra Windows (if any)
        all_windows = driver.window_handles
        if len(all_windows) > 1:
            logging.info(f"Closing {len(all_windows) - 1} extra windows/tabs...")
            main_window = driver.current_window_handle
            for window in all_windows:
                if window != main_window:
                    try:
                        driver.switch_to.window(window)
                        driver.close()
                    except Exception as e:
                        logging.warning(f"Could not close window {window}: {e}")
            driver.switch_to.window(main_window)


        # 7. Main Monitoring Loop
        logging.info("Setup complete. Entering monitoring loop (checking every hour).")
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)

            logging.info("Periodic check: Reloading extension page and checking status...")
            try:
                # Stay on the extension page to check the status
                current_url = driver.current_url
                if extension_internal_page not in current_url:
                    logging.warning(f"WebDriver was not on the extension page ({extension_internal_page}). Navigating back.")
                    driver.get(extension_internal_page)
                    time.sleep(random.randint(5,10)) # Wait for load
                else:
                    driver.refresh()
                    time.sleep(random.randint(10, 20)) # Longer wait after refresh

                # Re-verify if still 'Activated'
                wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=30)

                # Check connection status
                if check_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
                    logging.info("Connection status: Connected.")
                elif check_element_exists(driver, By.XPATH, "//*[text()='Disconnected']"):
                    logging.warning("Connection status: Disconnected!")
                else:
                    logging.warning("Connection status: Unknown.")

            except TimeoutException:
                 logging.error("'Activated' element not found after periodic refresh. The extension might have stopped.")
                 # driver.save_screenshot('/app/config/loop_timeout_failure.png') # Uncomment for debugging
                 return False # Signals failure for restart
            except Exception as loop_err:
                 logging.error(f"Unexpected error in verification loop: {loop_err}", exc_info=True)
                 return False # Signals failure for restart

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down...")
        return True # Normal shutdown requested by user
    except Exception as e:
        logging.error(f"Critical error during execution: {e}", exc_info=True)
        # Try to take screenshot if driver still exists
        # if driver:
        #     try:
        #         driver.save_screenshot('/app/config/critical_error.png')
        #     except Exception:
        #         pass
        return False # Signals critical failure
    finally:
        if driver:
            logging.info("Closing WebDriver...")
            driver.quit()


# --- Entry Point ---
if __name__ == "__main__":
    success = run_nodepay()
    if not success:
        logging.info(f"Script encountered an error or failure. Container should restart (if configured). Waiting {RESTART_DELAY_SECONDS}s...")
        time.sleep(RESTART_DELAY_SECONDS) # Give time for logs to be read before restart
        exit(1) # Signal exit with error
    else:
        logging.info("Script finished normally.")
        exit(0) # Signal normal exit