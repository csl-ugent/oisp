FROM debian:stretch

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y libc6-i386 lib32stdc++6 zlib1g:i386 libglib2.0-0:i386 libfontconfig1:i386 libxext6:i386 libxrender1:i386 libsm6:i386 libpython2.7:i386 unzip curl && \
    apt-get install -y python-pathlib binutils python3

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
