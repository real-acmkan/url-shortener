FROM python:3.12
WORKDIR /app
COPY . .
# COPY requirements.txt .
# COPY app.py .
# COPY templates/ templates/
RUN pip install -r requirements.txt
CMD ["python", "app.py"]