# Use uma versão específica para builds reproduzíveis
FROM debian:11-slim

# Definir o diretório de trabalho principal
WORKDIR /app

# Definir variáveis de ambiente (não relacionadas à credencial NP_KEY)
# Estas são usadas principalmente durante o build ou são constantes para o script
ENV CHROME_WEBSTORE=https://chromewebstore.google.com/detail/nodepay-extension/
ENV EXTENSION_ID=lgmpfmgeabnnlemejacfljbmonaomfmm
ENV EXTENSION_URL='https://app.nodepay.ai/'
ENV GIT_USERNAME=sryze
ENV GIT_REPO=crx-dl
# Adicionar o diretório de scripts ao PATH se necessário, ou usar caminhos absolutos
ENV PATH="/app/crx-dl:${PATH}"

# Instalar pacotes necessários e limpar
# Agrupar instalações para reduzir camadas
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
    # python3-requests e python3-selenium podem ser instalados via pip se preferir
    coreutils \
    bash && \
    # Instalar python-dotenv para ler o .env em main.py
    pip3 install --no-cache-dir distro python-dotenv selenium requests && \
    # Limpeza
    apt autoremove --purge -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Clonar o repositório crx-dl para dentro do WORKDIR (/app)
# O clone criará um diretório /app/crx-dl
RUN git clone --depth 1 "https://github.com/${GIT_USERNAME}/${GIT_REPO}.git" ./crx-dl && \
    chmod +x /app/crx-dl/crx-dl.py

# Copiar o script Python principal para o WORKDIR (/app)
# Este arquivo deve estar em './nodepay_src/main.py' no seu host
COPY main.py .

# Baixar a extensão utilizando o script crx-dl.py
# Usando caminho absoluto para clareza e o .crx será salvo em /app
RUN python3 /app/crx-dl/crx-dl.py ${CHROME_WEBSTORE}${EXTENSION_ID} -o /app/${EXTENSION_ID}.crx

# Expor a porta se sua aplicação ouvir em alguma (opcional, depende do main.py)
# EXPOSE 8080

# Definir o ponto de entrada do container
# main.py será executado a partir do WORKDIR (/app)
ENTRYPOINT ["python3", "main.py"]