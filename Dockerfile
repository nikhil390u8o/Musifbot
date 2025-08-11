FROM python:3.9

# Set work directory
WORKDIR /app

# Copy requirements and install with forced reinstall to avoid bad cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --upgrade --force-reinstall

# Copy all your code
COPY . .

# Run the bot
CMD ["python3", "main.py"]
