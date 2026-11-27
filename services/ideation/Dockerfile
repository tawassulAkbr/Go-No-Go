ARG PYTHON_IMAGE=python:3.12.10-slim-bookworm
FROM ${PYTHON_IMAGE} AS build
WORKDIR /build
COPY libs/contracts /build/contracts
COPY libs/platform_stub /build/platform_stub
COPY libs/tracing /build/tracing
COPY services/ideation/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt /build/contracts /build/tracing /build/platform_stub

FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY --from=build /install /usr/local
COPY services/ideation/src/ /app/src/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
