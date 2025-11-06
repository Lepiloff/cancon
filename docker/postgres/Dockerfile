# Custom Postgres image with pgvector extension
ARG POSTGRES_VERSION=13
FROM postgres:${POSTGRES_VERSION}

ARG PGVECTOR_VERSION=v0.7.4

# Install build dependencies and pgvector extension from source
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        make \
        postgresql-server-dev-${PG_MAJOR} \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${PGVECTOR_VERSION} https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector

# Automatically create the extension when initializing a fresh database
COPY docker/postgres/initdb.d /docker-entrypoint-initdb.d
