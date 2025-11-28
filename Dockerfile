FROM python:3.11-slim

WORKDIR /app

# Clone the GitHub repository
RUN git clone --depth 1 https://github.com/ExcIus1ve/leads-bot-artem.git .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "main.py"]
