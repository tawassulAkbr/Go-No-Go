ARG PYTHON_IMAGE=python:3.12.16-slim-bookworm
FROM ${PYTHON_IMAGE} AS build
WORKDIR /build
COPY libs/contracts contracts
COPY libs/foundation foundation
COPY jobs/ingestion ingestion
RUN pip install --no-cache-dir --prefix=/install ./contracts ./foundation ./ingestion

FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY --from=build /install /usr/local
COPY data/snapshot/ /app/data/snapshot/
USER 10001:10001
CMD ["python","-m","ingestion"]
