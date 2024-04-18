FROM python:3.10-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/Moscow

RUN apt-get -qqy update && apt-get -qqy  install gcc git && apt-get -qqy install python-setuptools && pip install poetry && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
WORKDIR /scrapyLivemaster
COPY poetry.lock pyproject.toml /scrapyLivemaster/
RUN poetry config virtualenvs.create false && python -m pip install --upgrade pip && pip install setuptools
RUN poetry install --no-dev

COPY . /scrapyLivemaster
WORKDIR /scrapyLivemaster
# run entrypoint.sh

