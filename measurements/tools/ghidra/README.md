# GHIDRA

## Building the Docker container
`docker build . -t ghidra`

## Running
First run the container in daemon mode:
`docker run -d -it -e DISPLAY=:0.0 -v /tmp/.X11-unix:/tmp/.X11-unix ghidra`

To prepare the build environment and build Ghidra:
`docker exec -it CONTAINER_ID /build.sh`

To run Ghidra:
`docker exec -it CONTAINER_ID /build/ghidra/build/dist/ghidra/ghidraRun`

To run Eclipse:
`docker exec -it CONTAINER_ID /build/eclipse/eclipse`

## Building GhidraDev plugin
Run eclipse.

Install additional software
* CDT - http://download.eclipse.org/tools/cdt/releases/9.7
  * C/C++ Development Tools
* PyDev - http://www.pydev.org/updates (all)
* Eclipse Plugin Development Tools (all)

Import the Ghidra projects.
* File -> Import... -> General -> Existing Projects into Workspace
* Select root directory to be /build/ghidra
* Check "Search for nested projects"
* ONLY select "Eclipse GhidraDevFeature" and "Eclipse GhidraDevPlugin"
* Finish

Build the GhidraDev plugin (also see Eclipse GhidraDevPlugin/build_README.txt).
* File -> Export... -> Plug-in Development -> Deployable features
* Check "ghidra.ghidradev"
* Select "Archive file", `/build/ghidra.bin/GhidraBuild/Eclipse/GhidraDev/GhidraDev-2.0.0.zip`
* Options tab
  * "Categorize repository": `/build/ghidra/GhidraBuild/EclipsePlugins/GhidraDev/GhidraDevFeature/category.xml`
  * Check "Qualifier replacement", clear value
  * Finish
