FROM python:3.11-alpine AS app

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 

# Install the general dependencies
RUN apk update && \
    # apk add gcc bash postgresql-dev libc-dev libffi-dev
    apk add gcc bash libc-dev libffi-dev
RUN pip install poetry

# Install application dependencies
RUN mkdir /app
WORKDIR /app/
COPY pyproject.toml poetry.lock ./
RUN poetry install

# Copy the code
RUN mkdir /app/src
WORKDIR /app/src
COPY src/ /app/src

# Run the code
CMD poetry run python main.py
