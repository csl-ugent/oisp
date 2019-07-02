#!/usr/bin/env bash
. /etc/profile

# binnavi
cd /build
git clone https://github.com/google/binnavi.git
cd binnavi
mvn dependency:copy-dependencies
ant build-binnavi-fat-jar

# binexport
cd /build
git clone https://github.com/thomasdullien/binexport.git
cd binexport
cp -r /ida-6.8/ida/idasdk68 third_party/idasdk
sed -i 's+82b124816eb8e9e99e8312b6c751c68ec690e2b1eaef7fa2c20743152367ec80+21c8db3d001e2e71c4c43d1e967a91c0cb965e0393b5dda8c6b45d2149c1535e+' ExternalProtobuf.cmake
echo "#endif" >> third_party/idasdk/include/strlist.hpp
sed -ri 's:^(#define o_ymmreg.*):\1\n#define o_zmmreg o_idpspec5+2 // zmm register:' third_party/idasdk/include/intel.hpp
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
cp zynamics_binexport_9.plx* /ida-6.8/ida/plugins/

# create cluster
killall postgres
pg_createcluster --locale C.UTF-8 9.6 main
su -c "/etc/init.d/postgresql start" postgres

# configure postgres
su -c "psql --command \"CREATE USER binnavi WITH SUPERUSER PASSWORD 'binnavi';\"" postgres
su -c "createdb -O binnavi binnavi" postgres
