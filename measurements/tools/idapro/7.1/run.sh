#!/usr/bin/env bash
if ! docker image ls | grep idapro71; then
  # need to build the container
  echo "Building the IDA Pro 7.1 container"
  docker build . -t idapro71
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run --net=host -dit --env="DISPLAY" -v ${HOME}/.Xauthority:/root/.Xauthority -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/installer:/installer -v ${PWD}/docker/user/conf.idapro:/root/.idapro $additional_volumes --cap-add SYS_PTRACE idapro71)

echo "The IDA Pro 7.1 container runs in daemon mode."
echo " - To install: docker exec -it $container_id /build.sh"
echo " - To run: docker exec -it $container_id /build/ida/ida"
