#!/usr/bin/env bash
tag=TODO
if ! docker image ls | grep $tag; then
  # need to build the container
  echo "Building the $tag container"
  docker build . -t $tag
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build $additional_volumes $tag)

echo "The $tag container runs in daemon mode."
echo " - To build: docker exec -it $container_id /build.sh"
