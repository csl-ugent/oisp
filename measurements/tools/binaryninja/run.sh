#!/usr/bin/env bash
if ! docker image ls | grep binaryninja; then
  # need to build the container
  echo "Building the BinaryNinja container"
  docker build . -t binaryninja
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/installer:/installer -v ${PWD}/docker/user/conf.binaryninja:/root/.binaryninja $additional_volumes binaryninja)

echo "The Ghidra container runs in daemon mode."
echo " - To install: docker exec -it $container_id /build.sh"
echo " - To run: docker exec -it $container_id /build/binaryninja/binaryninja"
