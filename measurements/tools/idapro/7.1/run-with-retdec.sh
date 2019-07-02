#!/usr/bin/env bash
if ! docker image ls | grep idapro71; then
  # need to build the container
  echo "Building the IDA Pro 7.1 container"
  docker build . -t idapro71
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/installer:/installer -v ${PWD}/docker/user/conf.idapro:/root/.idapro -v ${PWD}/../../retdec/docker/build:/build/retdec $additional_volumes idapro71)

docker exec -it $container_id bash -c 'cp /build/retdec/retdec-idaplugin/build/src/idaplugin/retdec.so /build/ida/plugins/'
docker exec -it $container_id bash -c 'cp /build/retdec/retdec-idaplugin/build/src/idaplugin/retdec64.so /build/ida/plugins/'

echo "The IDA Pro 7.1 container runs in daemon mode."
echo " - To install: docker exec -it $container_id /build.sh"
echo " - To run: docker exec -it $container_id /build/ida/ida"
