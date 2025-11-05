# 1. Start from a lightweight official Python image (3.9 is stable)
FROM python:3.9-slim

# 2. Install necessary Linux system dependencies (libjpeg and zlib)
# We use 'build-essential' to allow for C/C++ compilation if needed, 
# and the -y flag confirms the installation.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy required Python dependencies first
COPY requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code (including app.py and photos folder)
COPY . .

# 7. Define the command to run the application when the container starts
# $PORT is automatically set by Render
CMD streamlit run app.py --server.port $PORT