# Use a specific version for reproducible builds
FROM debian:11-slim

# Define the main working directory
WORKDIR /app

# Define environment variables (not related to the NP_KEY credential)
# These are mainly used during the build or are constants for the script
ENV CHROME_WEBSTORE=https://chromewebstore.google.com/detail/nodepay-extension/
ENV EXTENSION_ID=lgmpfmgeabnnlemejacfljbmonaomfmm
ENV EXTENSION_URL='https://app.nodepay.ai/'
ENV GIT_USERNAME=sryze
ENV GIT_REPO=crx-dl
# Add the scripts directory to PATH if necessary, or use absolute paths
ENV PATH="/app/crx-dl:${PATH}"

# Install necessary packages and clean up
# Group installations to reduce layers
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
    # python3-requests and python3-selenium can be installed via pip if preferred
    coreutils \
    bash && \
    # Install python-dotenv to read .env in main.py
    pip3 install --no-cache-dir distro python-dotenv selenium requests && \
    # Cleanup
    apt autoremove --purge -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Clone the crx-dl repository into the WORKDIR (/app)
# The clone will create a directory /app/crx-dl
RUN git clone --depth 1 "https://github.com/${GIT_USERNAME}/${GIT_REPO}.git" ./crx-dl && \
    chmod +x /app/crx-dl/crx-dl.py

# Copy the main Python script to the WORKDIR (/app)
# This file should be in './nodepay_src/main.py' on your host
COPY main.py .

# Download the extension using the crx-dl.py script
# Using absolute path for clarity and the .crx will be saved in /app
RUN python3 /app/crx-dl/crx-dl.py ${CHROME_WEBSTORE}${EXTENSION_ID} -o /app/${EXTENSION_ID}.crx

# Expose the port if your application listens on one (optional, depends on main.py)
# EXPOSE 8080

# Define the container's entry point
# main.py will be executed from the WORKDIR (/app)
ENTRYPOINT ["python3", "main.py"]