#!/usr/bin/env bash
if ! docker image ls | grep idapro68; then
  # need to build the container
  echo "Building the IDA Pro 6.8 container"
  docker build . -t idapro68
fi

additional_volumes="-v $HOME/actc-data:/data -v $HOME/repositories/af-metingen:/af-metingen"
if [ $(hostname) == "pegasus.elis.ugent.be" ]; then
  additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
fi
container_id=$(docker run --net=host -dit --env="DISPLAY" -v ${HOME}/.Xauthority:/root/.Xauthority -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/installer:/installer -v ${PWD}/docker/user/conf.idapro:/root/.idapro $additional_volumes --cap-add SYS_PTRACE idapro68)

echo "The IDA Pro 6.8 container runs in daemon mode."
echo " - To install: docker exec -it $container_id /build.sh"
echo " - To run: docker exec -it $container_id /build/ida/ida"
