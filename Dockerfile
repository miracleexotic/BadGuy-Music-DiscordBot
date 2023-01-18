# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

RUN apt-get update \
    && apt-get dist-upgrade \
    && apt-get install -y software-properties-common \
    && add-apt-repository ppa:mc3man/trusty-media \
    && apt-get install -y --no-install-recommends \
        ffmpeg 
        
WORKDIR /BadGuyBot

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "/BadGuyBot/main.py" ]


