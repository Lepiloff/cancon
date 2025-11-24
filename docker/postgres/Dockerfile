# Use official pgvector image instead of building from source
FROM pgvector/pgvector:pg13

# Automatically create the extension when initializing a fresh database
COPY docker/postgres/initdb.d /docker-entrypoint-initdb.d
