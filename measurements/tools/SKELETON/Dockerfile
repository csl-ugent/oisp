FROM debian:stretch

RUN apt-get update
#RUN apt-get install -y TODO

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
