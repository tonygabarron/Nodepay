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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv # <--- ADICIONADO: Importar a biblioteca

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ... (connection_status, check_active_element, wait_for_element_exists, wait_for_element) ...
# Nenhuma mudança necessária nessas funções auxiliares

def set_local_storage_item(driver, key, value):
    # Função para lidar com aspas na chave, se houver
    escaped_value = value.replace("'", "\\'")
    driver.execute_script(f"localStorage.setItem('{key}', '{escaped_value}');")
    result = driver.execute_script(f"return localStorage.getItem('{key}');")
    return result

def add_cookie_to_local_storage(driver, cookie_value):
    keys = ['np_webapp_token', 'np_token']
    logging.info(f"Attempting to add token to local storage...")
    for key in keys:
        result = set_local_storage_item(driver, key, cookie_value)
        # Log apenas uma parte para segurança, e verifique se não está vazio
        if result:
             logging.info(f"Added {key} starting with '{result[:5]}...' to local storage.")
        else:
             logging.warning(f"Failed to set or retrieve {key} in local storage.")
    logging.info("Token should now be in local storage.")
    #logging.info("!!!!! Your token can be used to login for 7 days !!!!!") # Talvez remover ou tornar opcional

# ... (get_chromedriver_version, get_os_info) ...
# Nenhuma mudança necessária nessas funções

def run():
    setup_logging()

    # --- MODIFICADO: Carregar variáveis do .env ---
    # Caminho para o arquivo .env DENTRO do container (mapeado pelo volume)
    dotenv_path = '/app/config/.env'
    # Tenta carregar o arquivo .env do caminho especificado
    loaded = load_dotenv(dotenv_path=dotenv_path)

    if loaded:
        logging.info(f"Successfully loaded environment variables from {dotenv_path}")
    else:
        # Se o arquivo não for encontrado, o script pode falhar depois ao tentar ler NP_KEY.
        # Você pode decidir parar aqui ou deixar a verificação posterior tratar disso.
        logging.warning(f"Could not find or load .env file at {dotenv_path}. Make sure the volume is mounted correctly and the file exists.")
        # Consider adding 'return' here if the key is absolutely required immediately.
    # --------------------------------------------

    branch = ''
    version = '1.0.9' + branch
    secUntilRestart = 60
    logging.info(f"Started the script {version}")

    try:
        os_info = get_os_info()
        logging.info(f'OS Info: {os_info}')

        # --- MODIFICADO: Ler NP_KEY e verificar ---
        # Ler a variável NP_KEY (que foi carregada do .env para o ambiente pelo load_dotenv)
        cookie = os.getenv('NP_KEY')
        # Ler outras variáveis que ainda vêm do Dockerfile ENV
        extension_id = os.getenv('EXTENSION_ID')
        extension_url = os.getenv('EXTENSION_URL')

        # Verificar se as variáveis essenciais foram carregadas/definidas
        if not cookie:
            # Mensagem de erro atualizada
            logging.error('No key found. Ensure NP_KEY is set in the .env file mounted at /app/config/.env')
            logging.info(f'Restarting in {secUntilRestart} seconds...')
            time.sleep(secUntilRestart)
            # Não use recursão direta para reiniciar, pode estourar a pilha.
            # O Docker/Compose cuidará do restart se configurado (restart: unless-stopped)
            # Apenas saia ou levante uma exceção para o Docker reiniciar.
            return # Ou raise SystemExit("Missing NP_KEY")

        if not extension_id or not extension_url:
            logging.error('EXTENSION_ID or EXTENSION_URL environment variables not set. Check Dockerfile.')
            return # Ou raise SystemExit("Missing extension config")
        # ------------------------------------------

        # --- MODIFICADO: Caminho absoluto para a extensão ---
        # Construir caminho absoluto baseado no WORKDIR e download do Dockerfile
        extension_path = f'/app/{extension_id}.crx'
        logging.info(f"Using extension file path: {extension_path}")

        # Verificar se o arquivo da extensão existe
        if not os.path.exists(extension_path):
            logging.error(f"Extension file not found at {extension_path}. Check Dockerfile download step and permissions.")
            return # Ou raise SystemExit("Extension file missing")
        # ---------------------------------------------

        chrome_options = Options()
        # Usar o caminho absoluto
        chrome_options.add_extension(extension_path)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new') # Use a nova versão do headless
        chrome_options.add_argument('--disable-dev-shm-usage')
        # Talvez adicionar:
        chrome_options.add_argument('--disable-gpu') # Útil em ambientes headless
        chrome_options.add_argument('--window-size=1024,768') # Definir tamanho inicial
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0") # User agent já estava ok

        # Inicializar o WebDriver
        chromedriver_version = get_chromedriver_version()
        logging.info(f'Using {chromedriver_version}')
        # Pode ser necessário especificar o caminho do chromedriver se não estiver no PATH padrão
        # driver = webdriver.Chrome(service=Service('/usr/bin/chromedriver'), options=chrome_options) # Exemplo se necessário
        driver = webdriver.Chrome(options=chrome_options) # Tenta usar o do PATH primeiro

    except Exception as e:
        logging.error(f'An error occurred during setup: {e}', exc_info=True) # Adiciona traceback
        logging.info(f'Restarting attempt in {secUntilRestart} seconds...')
        time.sleep(secUntilRestart)
        # Deixe o Docker/Compose reiniciar em vez de chamar run() recursivamente
        raise e # Levanta a exceção para sinalizar falha

    try:
        # NodePass checks for width less than 1024p - window size set in options now
        # driver.set_window_size(1024, driver.get_window_size()['height']) # Removido, setado nas options

        logging.info(f'Navigating to {extension_url} website...')
        driver.get(extension_url)
        # Esperar um pouco mais ou usar WebDriverWait para um elemento específico da página
        time.sleep(random.randint(5, 10)) # Aumentar um pouco

        add_cookie_to_local_storage(driver, cookie)
        # Esperar um pouco para o localStorage ser processado e a página talvez recarregar
        time.sleep(random.randint(3, 7))
        # Recarregar a página explicitamente para garantir que o token seja usado
        logging.info("Refreshing page after setting token...")
        driver.refresh()

        # Esperar pelo elemento 'Dashboard' aparecer após o refresh
        logging.info("Waiting for 'Dashboard' element to confirm login...")
        try:
            wait_for_element(driver, By.XPATH, "//*[text()='Dashboard']", timeout=30) # Aumentar timeout
            logging.info('Logged in successfully! Dashboard element found.')
        except TimeoutException:
            logging.error("'Dashboard' element not found after setting token and refreshing. Check token validity and website behavior.")
            # Você pode querer tirar um screenshot aqui para debug: driver.save_screenshot('login_fail.png')
            raise # Re-levanta a exceção para acionar o reinício

        # Esperar um pouco antes de ir para a extensão
        time.sleep(random.randint(5, 15))
        extension_page_url = f'chrome-extension://{extension_id}/index.html'
        logging.info(f'Accessing extension settings page: {extension_page_url}')
        driver.get(extension_page_url)
        time.sleep(random.randint(5, 10)) # Aumentar um pouco

        # --- Lógica de Login/Ativação da Extensão ---
        # A lógica original parece um pouco complexa e talvez propensa a race conditions.
        # Vamos simplificar e tornar mais robusto.

        # 1. Verificar se já está Ativado primeiro (caso ideal)
        try:
            wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=15)
            logging.info("Extension is already activated.")
            connection_status(driver) # Verificar status da conexão

        except TimeoutException:
            logging.info("'Activated' element not found initially. Checking for 'Login' or 'Activate' buttons.")

            # 2. Se não estiver Ativado, procurar por 'Login'
            try:
                login_button = wait_for_element(driver, By.XPATH, "//*[text()='Login']", timeout=10)
                logging.info("Found 'Login' button, clicking it...")
                login_button.click()
                # Esperar um pouco e verificar se 'Activated' aparece após o login
                try:
                    wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=20)
                    logging.info("Extension became 'Activated' after clicking Login.")
                    connection_status(driver)
                except TimeoutException:
                    logging.error("Clicked 'Login', but 'Activated' element did not appear. Check extension behavior.")
                    # Tentar recarregar e verificar novamente? Ou falhar?
                    driver.refresh()
                    time.sleep(5)
                    try:
                         wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=15)
                         logging.info("Extension became 'Activated' after refresh.")
                         connection_status(driver)
                    except TimeoutException:
                         logging.error("Still not 'Activated' after refresh. Activation failed.")
                         raise # Falhar para reiniciar

            except TimeoutException:
                logging.info("'Login' button not found. Checking for 'Activate' button.")

                # 3. Se não houver 'Login', procurar por 'Activate' (a lógica original estava comentada)
                try:
                    activate_button = wait_for_element(driver, By.XPATH, "//*[text()='Activate']", timeout=10)
                    logging.info("Found 'Activate' button, clicking it...")
                    activate_button.click()
                    # Esperar um pouco e verificar se 'Activated' aparece
                    try:
                        wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=20)
                        logging.info("Extension became 'Activated' after clicking Activate.")
                        connection_status(driver)
                    except TimeoutException:
                        logging.error("Clicked 'Activate', but 'Activated' element did not appear.")
                        # Tentar recarregar?
                        driver.refresh()
                        time.sleep(5)
                        try:
                            wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=15)
                            logging.info("Extension became 'Activated' after refresh.")
                            connection_status(driver)
                        except TimeoutException:
                            logging.error("Still not 'Activated' after refresh. Activation failed.")
                            raise # Falhar para reiniciar

                except TimeoutException:
                    logging.warning("'Activate' button also not found. Current state is unclear, assuming activation failed or element changed.")
                    # Se nem 'Activated', nem 'Login', nem 'Activate' foram encontrados, algo está errado.
                    raise NoSuchElementException("Could not find expected elements ('Activated', 'Login', 'Activate') on extension page.")


        # --- Limpeza de Janelas (Parece OK) ---
        all_windows = driver.window_handles
        if len(all_windows) > 1:
             logging.info(f"Found {len(all_windows)} windows/tabs. Closing extras...")
             active_window = driver.current_window_handle
             for window in all_windows:
                 if window != active_window:
                     try:
                         driver.switch_to.window(window)
                         driver.close()
                         logging.info(f"Closed window: {window}")
                     except Exception as close_err:
                         logging.warning(f"Could not close window {window}: {close_err}")
             driver.switch_to.window(active_window) # Voltar para a principal
             logging.info("Switched back to the main extension window.")
        else:
            logging.info("Only one window/tab open.")
        # ------------------------------------

        # Verificar status final
        connection_status(driver)

    except Exception as e:
        logging.error(f'An error occurred during main execution: {e}', exc_info=True) # Log com traceback
        logging.info(f'Attempting graceful shutdown and letting Docker handle restart...')
        if 'driver' in locals() and driver:
            driver.quit()
        # Não chamar run() aqui, deixar o Docker reiniciar
        raise e # Propagar a exceção para sinalizar falha ao Docker

    # --- Loop Principal (Parece OK, mas pode ser melhorado) ---
    logging.info("Setup complete. Entering main loop (refreshing connection status hourly).")
    while True:
        try:
            # Esperar por 1 hora (3600 segundos)
            time.sleep(3600)
            logging.info("Hourly check: Refreshing extension page and checking status...")
            driver.refresh()
            time.sleep(random.randint(5, 15)) # Esperar o refresh
            # Re-verificar se ainda está ativado e conectado
            try:
                wait_for_element(driver, By.XPATH, "//*[text()='Activated']", timeout=30)
                connection_status(driver)
            except TimeoutException:
                logging.error("Extension no longer shows 'Activated' after refresh. Attempting restart sequence.")
                # Aqui você pode tentar re-ativar ou simplesmente sair para o Docker reiniciar
                raise RuntimeError("Extension lost 'Activated' state.") # Sinaliza problema

        except KeyboardInterrupt:
            logging.info('KeyboardInterrupt received. Stopping the script...')
            if 'driver' in locals() and driver:
                driver.quit()
            break # Sai do loop while
        except Exception as loop_error:
            logging.error(f"Error during hourly check: {loop_error}", exc_info=True)
            logging.info("Attempting graceful shutdown and letting Docker handle restart...")
            if 'driver' in locals() and driver:
                driver.quit()
            # Levanta a exceção para que o Docker possa reiniciar o container
            raise loop_error # Sai do loop e sinaliza falha

# --- Ponto de Entrada ---
if __name__ == "__main__":
    try:
        run()
    except Exception as final_exception:
        logging.error(f"Script exited due to an unhandled exception in run(): {final_exception}", exc_info=True)
        # Sinaliza saída com erro para o Docker
        exit(1)
    logging.info("Script finished normally.")
    exit(0)