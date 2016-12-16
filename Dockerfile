FROM ubuntu:xenial

RUN apt-get update && \
    apt-get install -y \
    locales \
    \
    python \
    python-dev \
    python-pip \
    python-numpy \
    python-opencv \
    python-pillow \
    python-psycopg2 \
    python-skimage \
    uwsgi \
    uwsgi-plugin-python \
    \
    ffmpeg

RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN mkdir /player
RUN mkdir /player/player
RUN touch /player/player/__init__.py
ADD setup.py /player

WORKDIR /player
RUN pip install flask
RUN python setup.py develop

RUN rm -rf /player
ADD . /player
