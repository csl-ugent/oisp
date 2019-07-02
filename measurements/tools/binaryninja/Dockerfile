FROM debian:stretch

RUN apt-get update && \
    apt-get install -y unzip libgl1-mesa-glx libglib2.0-0 libfontconfig1 libxrender1 libdbus-1-3 python libpython2.7 openssl ca-certificates

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
