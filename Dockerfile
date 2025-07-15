# Use a lightweight Python image
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    TZ=Asia/Dhaka

# Set timezone and install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    aria2 \
    ffmpeg\ 
    fonts-dejavu-core \
    procps \
    wget \
    gnupg \
    ca-certificates \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

COPY wood.ttf /app/wood.ttf

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create download directory and fix permissions
RUN mkdir -p downloads \
    && chmod 777 downloads

 # Fix permissions for authorized_users.json
RUN if [ -f "authorized_users.json" ]; then chmod 664 authorized_users.json; fi   

# Install psutil explicitly (might not be in requirements)
RUN pip install --no-cache-dir psutil

# Copy and prepare entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose Flask port
EXPOSE 8080
# Expose DHT ports
# EXPOSE 6881-6999/tcp
# EXPOSE 6881-6999/udp

# Start the bot directly
# CMD ["python", "test.py"] ✅
# CMD ["python", "bot.py"]

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "angel.py"]
