FROM debian:stretch

RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx libglib2.0-0 libfontconfig1 libxrender1 libdbus-1-3 libxi6 libsm6 libpython2.7 python3 xkb-data unzip curl python-pathlib binutils

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
