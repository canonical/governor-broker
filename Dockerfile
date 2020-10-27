FROM python:3.8.5

RUN mkdir /usr/share/broker

WORKDIR /usr/share/broker

COPY broker.py /usr/share/broker/
COPY requirements.txt .

RUN pip install -r requirements.txt

CMD [ "python", "/usr/share/broker/broker.py", "-f", "/usr/share/broker/creds.yaml" ]


