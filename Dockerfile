# ----------------------------
# Stage 1: Build libpostal
# ----------------------------
    FROM python:3.12-slim AS libpostal-builder

    # Install build dependencies for libpostal
    RUN apt-get update && apt-get install -y \
            build-essential \
            automake \
            autoconf \
            libtool \
            pkg-config \
            git \
            curl \
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /opt/libpostal

    # Declare the build argument
    ARG TARGETARCH

    # Clone and build libpostal
    RUN git clone https://github.com/openvenues/libpostal.git . && \
        ./bootstrap.sh && \
        if [ "$TARGETARCH" = "arm64" ]; then \
            ./configure --prefix=/usr/local --disable-sse2; \
        else \
            ./configure --prefix=/usr/local; \
        fi && \
        make && \
        make install && \
        ldconfig

    # ----------------------------
    # Stage 2: Build Application Environment
    # ----------------------------
    FROM python:3.12-slim

    # Install minimal runtime system libraries and necessary build tools
    RUN apt-get update && apt-get install -y \
        libstdc++6 \
        gcc \
        g++ \
        && rm -rf /var/lib/apt/lists/*

    # Copy libpostal binaries, libraries, headers, and data from the builder stage
    COPY --from=libpostal-builder /usr/local/bin/ /usr/local/bin/
    COPY --from=libpostal-builder /usr/local/lib/ /usr/local/lib/
    COPY --from=libpostal-builder /usr/local/include/ /usr/local/include/
    COPY --from=libpostal-builder /usr/local/share/libpostal/ /usr/local/share/libpostal/

    # Refresh shared library cache
    RUN ldconfig

    # Set environment variable for libpostal
    ENV LIBPOSTAL_DATA=/usr/local/share/libpostal

    # Install Poetry
    RUN pip install poetry

    # Set a working directory
    WORKDIR /app

    # Copy dependency files
    COPY pyproject.toml poetry.lock ./

    # Install dependencies (without virtual environment)
    RUN poetry config virtualenvs.create false && \
        poetry install --no-root --no-interaction --no-ansi

    # Copy application source code
    COPY app/ ./app/

    # Expose the port FastAPI will run on
    EXPOSE 80

    # Default command to run the FastAPI server
    CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
