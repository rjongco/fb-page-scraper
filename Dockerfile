FROM python:3.11-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends libc6 && rm -rf /var/lib/apt/lists/*

# Install dependencies for Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    ca-certificates \
    gnupg \
    libx11-6 \
    libxcomposite1 \
    libxrandr2 \
    libgdk-pixbuf2.0-0 \
    libpango1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libnss3 \
    libnspr4 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    libxdamage1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# Retrieve Chrome version, set as environment variable, and use it in the wget command
RUN CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}') && \
    wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" 

# Unzip the downloaded chromedriver
RUN unzip /tmp/chromedriver-linux64.zip 'chromedriver-linux64/chromedriver' -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64

# set display port to avoid crash
ENV DISPLAY=:99

RUN pip install selenium

WORKDIR /app

COPY requirements.txt requirements.txt


RUN pip install --no-cache-dir -r requirements.txt

COPY ./chrome_profile /root/.config/google-chrome

# COPY . .


