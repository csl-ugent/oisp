#!/usr/bin/env bash
if ! docker image ls | grep retdec; then
  # need to build the container
  echo "Building the RetDec container"
  docker build . -t retdec
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/installer:/installer $additional_volumes retdec)

echo "The RetDec container runs in daemon mode."
echo " - To install: docker exec -it $container_id /build.sh"
