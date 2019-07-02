#!/usr/bin/env bash
. /etc/profile

# keystone
cd /build
git clone https://github.com/keystone-engine/keystone
cd keystone
mkdir build && cd build
../make-share.sh
make install

# retdec
cd /build
git clone https://github.com/avast/retdec
cd retdec
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/build/retdec-install -DRETDEC_DOC=ON -DRETDEC_DEV_TOOLS=ON
make -j10
make install

# retdec IDA plugin
cd /build

# extract IDA SDK
unzip $(find /installer -name *idasdk*.zip | head -n1)

# clone and build the plugin project
git clone https://github.com/avast/retdec-idaplugin
cd retdec-idaplugin
mkdir build && cd build
cmake .. -DIDA_SDK_DIR=/build/idasdk71/
make -j4
