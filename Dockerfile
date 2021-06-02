FROM python:3.8

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yml ./certs/
COPY ./app .
COPY ./tests .

# CMD [ "python", "api.py" ] # Only dev
CMD gunicorn -w 3 -b 0.0.0.0:5000 api:app
