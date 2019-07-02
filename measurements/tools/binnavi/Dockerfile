FROM debian:stretch

RUN dpkg --add-architecture i386 && \
    apt-get update
RUN apt-get install -y git maven openjdk-8-jdk-headless build-essential cmake python \
    libc6-i386 lib32stdc++6 zlib1g:i386 libglib2.0-0:i386 libfontconfig1:i386 libxext6:i386 libxrender1:i386 libsm6:i386 libpython2.7:i386 unzip curl \
    gcc-multilib g++-multilib && \
    apt-get install -y postgresql

RUN echo > /etc/java-8-openjdk/accessibility.properties

COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
