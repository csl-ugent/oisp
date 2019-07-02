#!/usr/bin/env bash
tag=binnavi
if ! docker image ls | grep $tag; then
  # need to build the container
  echo "Building the $tag container"
  docker build . -t $tag
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
tool_volumes="-v ${PWD}/../idapro/6.8/docker/build:/ida-6.8 -v ${PWD}/../idapro/7.1/docker/build:/ida-7.1"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/docker/user/etc.postgresql:/etc/postgresql -v ${PWD}/docker/user/var.log.postgresql:/var/log/postgresql -v ${PWD}/docker/user/var.lib.postgresql:/var/lib/postgresql -v ${PWD}/docker/user/conf.zynamics:/root/.zynamics $additional_volumes $tool_volumes $tag)

# docker exec -it $container_id bash -c 'chown -R $(id -u postgres):$(id -g postgres) /var/lib/postgresql/'
docker exec -it $container_id su -c "/etc/init.d/postgresql start" postgres

echo "The $tag container runs in daemon mode."
echo " - To build: docker exec -it $container_id /build.sh"
echo " - To run: docker exec -it $container_id bash -c 'java -jar /build/binnavi/target/binnavi-all.jar'"
