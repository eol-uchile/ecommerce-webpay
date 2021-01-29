FROM ubuntu:16.04 
# Ubuntu 16 uses python 2.7 as default :muscle:

RUN apt update && apt-get install libssl-dev libxml2-dev libxmlsec1-dev python-pip -y
RUN pip install pip==20.0.2
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

# CMD [ "python", "api.py" ] # Only dev
CMD gunicorn -w 3 -b 0.0.0.0:5000 api:app
