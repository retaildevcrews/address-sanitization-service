FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

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

# Clone and build libpostal
RUN git clone https://github.com/openvenues/libpostal.git . && \
    ./bootstrap.sh && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    ldconfig

# Install minimal runtime system libraries and necessary build tools
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Refresh shared library cache
RUN ldconfig

# Set environment variable for libpostal
ENV LIBPOSTAL_DATA=/usr/local/share/libpostal

# Install Poetry
RUN pip install poetry
