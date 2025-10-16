# Use the official Python 3.12.10 image as the base
FROM python:3.12.10-slim

# Set environment variables to prevent Python from writing bytecode and buffering output
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    xvfb \
    gnupg \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxrandr2 \
    libgbm-dev \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    tzdata\
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | tee -a /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Get time and timezone from host
ENV TZ=Europe/Moscow
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set the working directory
WORKDIR /XX_Auto_Jobs_Applier

# Copy repository into the working directory
COPY data_folder/search_config data_folder/search_config
COPY data_folder/secrets data_folder/secrets
COPY logs logs
COPY src src
COPY main.py .
COPY requirements.txt .
COPY my-client.session .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the shell script
CMD ["python3", "main.py"]
