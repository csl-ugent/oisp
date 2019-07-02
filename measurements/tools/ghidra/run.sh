#!/usr/bin/env bash
if ! docker image ls | grep ghidra; then
  # need to build the container
  echo "Building the Ghidra container"
  docker build . -t ghidra
fi

additional_volumes="-v /bulk/A/measurements:/data -v $HOME/repositories/af-metingen:/af-metingen"
container_id=$(docker run -dit -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ${PWD}/docker/build:/build -v ${PWD}/docker/eclipse-workspace:/eclipse-workspace -v ${PWD}/docker/ghidra-workspace:/ghidra-workspace -v ${PWD}/docker/user/conf.ghidra:/root/.ghidra -v ${PWD}/docker/user/ghidra_scripts:/root/ghidra_scripts -v ${PWD}/docker/user/conf.mozilla:/root/.mozilla $additional_volumes ghidra)

echo "The Ghidra container runs in daemon mode."
echo " - To build Ghidra: docker exec -it $container_id /build.sh"
echo " - To run Ghidra: docker exec -it $container_id /build/ghidra/build/dist/ghidra/ghidraRun"
echo " - To run Eclipse: docker exec -it $container_id /build/eclipse/eclipse"
