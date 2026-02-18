# Use a pre-built image that already has dlib and face_recognition installed
# This avoids the long compilation process
FROM datamachines/face_recognition:cpu-latest

# Set the working directory
WORKDIR /app

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy the application code
COPY . .

# Exposure the port the app runs on
EXPOSE 5000

# Start the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]