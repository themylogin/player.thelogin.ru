FROM ubuntu:xenial

RUN apt-get update && \
    apt-get install -y locales
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN apt-get install -y \
    python \
    python-dev \
    python-pip \
    python-numpy \
    python-opencv \
    python-pillow \
    python-psycopg2 \
    python-skimage \
    uwsgi \
    uwsgi-plugin-python

RUN apt-get install -y ffmpeg

RUN pip install flask

ADD . /player
RUN cd /player && python setup.py develop
