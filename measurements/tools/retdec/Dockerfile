FROM debian:stretch

RUN apt-get update && \
    apt-get install -y build-essential cmake git perl python3 bison flex libfl-dev autoconf automake libtool pkg-config m4 zlib1g-dev upx doxygen graphviz unzip python3-pygments

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
