ARG PYTHON_IMAGE=python:3.12.16-alpine3.23
FROM ${PYTHON_IMAGE} AS build
WORKDIR /build
COPY libs/contracts /build/contracts
COPY libs/platform_stub /build/platform_stub
COPY libs/tracing /build/tracing
COPY services/profile/requirements.txt /build/requirements.txt
COPY libs/foundation /build/foundation
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt /build/contracts /build/tracing /build/platform_stub /build/foundation

FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY --from=build /install /usr/local
COPY services/profile/src/ /app/src/
COPY services/profile/alembic.ini /app/alembic.ini
COPY services/profile/migrations /app/migrations
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
