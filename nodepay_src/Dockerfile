# Use a specific Debian version for reproducible builds
FROM debian:11-slim

# Define the main working directory
WORKDIR /app

# Define environment variables (not related to the NP_KEY credential)
ENV CHROME_WEBSTORE=https://chromewebstore.google.com/detail/nodepay-extension/
ENV EXTENSION_ID=lgmpfmgeabnnlemejacfljbmonaomfmm
ENV EXTENSION_URL='https://app.nodepay.ai/'
ENV GIT_USERNAME=sryze
ENV GIT_REPO=crx-dl
# Add the scripts directory to PATH for crx-dl.py
ENV PATH="/app/crx-dl:${PATH}"

# Install necessary packages and clean up apt cache
RUN apt update && \
    apt upgrade -y && \
    apt install -qqy --no-install-recommends \
    curl \
    wget \
    git \
    chromium \
    chromium-driver \
    python3 \
    python3-pip \
    coreutils \
    bash && \
    # Install required Python packages
    pip3 install --no-cache-dir distro python-dotenv selenium requests && \
    # Cleanup
    apt autoremove --purge -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Clone the crx-dl repository to download the extension
RUN git clone --depth 1 "https://github.com/${GIT_USERNAME}/${GIT_REPO}.git" ./crx-dl && \
    chmod +x /app/crx-dl/crx-dl.py

# Copy the main Python script into the working directory
COPY main.py .

# Download the Chrome extension using the crx-dl script
RUN python3 /app/crx-dl/crx-dl.py ${CHROME_WEBSTORE}${EXTENSION_ID} -o /app/${EXTENSION_ID}.crx

# Define the container's entry point
ENTRYPOINT ["python3", "main.py"]