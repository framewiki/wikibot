FROM python:3.13-alpine

RUN pip install poetry==2.0.0

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache 

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY . .

ENV PRODUCTION = true
RUN poetry install --without dev && rm -rf $POETRY_CACHE_DIR

ENTRYPOINT ["poetry", "run", "python" "src/wikibot.py"]