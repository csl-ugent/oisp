FROM debian:stretch

RUN echo "deb http://deb.debian.org/debian stretch-backports main" > /etc/apt/sources.list.d/backports.list
RUN apt-get update && \
    apt-get install -y git openjdk-11-jdk curl bison flex g++ unzip libswt-webkit-gtk-3-jni libwebkitgtk-3.0-0 firefox-esr python3 python3-dev python-pathlib

# bugfix https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=922720
RUN sed -i 's/"$arch" == /"$arch" = /g' /etc/ca-certificates/update.d/jks-keystore && \
    apt-get install -y --reinstall ca-certificates-java

# Gradle, needs to be version 5.0 for Ghidra
RUN cd /tmp && \
    curl -OL https://downloads.gradle.org/distributions/gradle-5.0-bin.zip && \
    mkdir -p /opt/gradle && cd /opt/gradle && \
    unzip /tmp/gradle-5.0-bin.zip

COPY docker/system/repos.gradle /root/.gradle/init.d/repos.gradle
COPY docker/system/profile.d-gradle.sh /etc/profile.d/gradle.sh
COPY docker/system/profile.d-java.sh /etc/profile.d/java.sh
COPY docker/system/build.sh /build.sh
COPY docker/system/entry.sh /entry.sh

ENTRYPOINT [ "/entry.sh" ]
