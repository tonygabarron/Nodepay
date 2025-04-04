# Nodepay Docker Automation ✨

[![Docker Build](https://img.shields.io/badge/Docker-Build-blue?logo=docker)](https://www.docker.com/)
[![Python Version](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a simple and efficient way to run the Nodepay Chrome extension 24/7 within a Docker container. It uses Selenium and a headless Chrome browser to automate the login process, activate the extension, click the "Claim" button when available, and keep it running reliably.

## Overview

Nodepay allows users to share their unused internet bandwidth. This project automates the process of running the Nodepay extension, eliminating the need to keep a browser window open manually on your desktop. It's designed to be deployed easily using Docker Compose.

## Features

*   **🐳 Dockerized:** Runs in an isolated Docker container. Easy setup and deployment.
*   **💻 Cross-Platform:** Works seamlessly on Windows, macOS, and Linux thanks to Docker.
*   **🕵️ Headless Operation:** Uses headless Chromium, so no graphical interface is needed on the host.
*   **⚙️ Optimized Resource Usage:** Runs efficiently using a headless browser, minimizing CPU and RAM consumption compared to a full desktop browser.
*   **🔑 Automatic Login:** Injects your `NP_KEY` into the Nodepay web app's local storage for seamless login.
*   **🖱️ Automatic Claim:** Checks the Nodepay dashboard periodically and automatically clicks the "Claim" button if it's available.
*   **🔄 Continuous Monitoring:** The script periodically checks if the extension is still active and connected.
*   **⚙️ Auto-Restart:** Configured with `restart: unless-stopped` in Docker Compose to automatically restart the container if the script exits unexpectedly.
*   **📄 Configuration via `.env`:** Keeps your sensitive `NP_KEY` separate from the codebase.
*   **🌐 Fixed IP Address:** Assigns a static internal IP address within the Docker network (optional, for advanced setups).

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Docker:** [Get Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose:** Usually included with Docker Desktop. For Linux, you might need to install it separately ([Install Docker Compose](https://docs.docker.com/compose/install/)).
*   **Git:** To clone this repository ([Get Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)).

*(Docker ensures this project runs consistently across Windows, macOS, and Linux environments.)*

## 🚀 Getting Started

Follow these steps to get the Nodepay container up and running:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/tonygabarron/Nodepay.git
    cd Nodepay
    ```

2.  **Configure Your Nodepay Key (`NP_KEY`):**

    *   **How to Obtain Your `NP_KEY`:**
        1.  Log in to your Nodepay account at [app.nodepay.ai/login](https://app.nodepay.ai/login).
        2.  Open your browser's Developer Tools (usually by pressing `F12`).
        3.  Go to the `Storage` tab (it might be under `Application` in Chrome/Edge, or `Storage` in Firefox).
        4.  In the side panel, expand `Local Storage` and select the entry for `https://app.nodepay.ai`.
        5.  Find the key named `np_token`.
        6.  Copy the **entire value** associated with `np_token`. This is your `NP_KEY`.

    *   **Create the `.env` file:**
        *   Navigate to the configuration directory:
            ```bash
            cd nodepay_config
            ```
        *   Create a file named `.env` (you can use `nano .env`, `vim .env`, or any text editor):
        *   Add your copied Nodepay Key to the file:
            ```dotenv
            # nodepay_config/.env
            NP_KEY=PASTE_YOUR_NODEPLAY_AUTH_KEY_HERE
            ```
            **Important:** Replace `PASTE_YOUR_NODEPLAY_AUTH_KEY_HERE` with the actual key you copied. **Do not commit this file with your key to version control.** The `.gitignore` file should prevent this.

3.  **Return to the Root Directory:**
    ```bash
    cd ..
    ```

4.  **Build and Run the Container:**
    Use Docker Compose to build the image and start the container in detached mode (`-d`):
    ```bash
    docker compose up -d --build
    ```
    *   `--build`: Forces Docker to build the image. Recommended for the first run or after code changes.
    *   `-d`: Runs the container in the background.

## Usage

*   **Check Logs:** To see the script's output and monitor its status:
    ```bash
    docker compose logs -f nodepay
    ```
    *(Press `Ctrl+C` to stop following the logs)*. You should see messages indicating successful login, activation, claim attempts, and periodic checks.

*   **Stop the Container:**
    ```bash
    docker compose down
    ```
    *(This stops and removes the container. Your `.env` file in `nodepay_config` will persist.)*

*   **Restart the Container:**
    ```bash
    docker compose restart nodepay
    ```
    *(Or simply run `docker compose up -d` again)*

## Important Notes

*   **⚠️ `NP_KEY` Expiration:**
    *   The `NP_KEY` obtained from Nodepay typically has a built-in expiration date (often set 14 days from issuance).
    *   However, Nodepay has recently been issuing keys with future start dates, which can result in a practical validity period closer to **90 days**.
    *   **When the key expires, the container will fail to log in.** You will need to repeat the steps in "How to Obtain Your `NP_KEY`" to get a fresh key and update the `nodepay_config/.env` file. Afterwards, restart the container (`docker compose restart nodepay` or `docker compose up -d --build`).
*   **Volume Mapping:** The `nodepay_config` directory on your host machine is mapped to `/app/config` inside the container. This ensures your `.env` file persists and allows the script to read your key.
*   **Claim Button Logic:** The script looks for a specific element structure for the "Claim" button. If Nodepay changes its website design, the claim functionality might need updating in `main.py`.
*   **Nodepay Updates:** Nodepay might update its extension or website, potentially breaking the automation. Updates to this repository may be needed.

## Contributing

Contributions are welcome! If you find a bug, have suggestions, or want to add features:

1.  Fork the repository (`https://github.com/tonygabarron/Nodepay/fork`).
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/YourFeature`).
6.  Open a Pull Request.

Please ensure your code follows the existing style and includes comments where necessary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Disclaimer: This project is independently developed and not affiliated with Nodepay. Use it responsibly and at your own risk.*