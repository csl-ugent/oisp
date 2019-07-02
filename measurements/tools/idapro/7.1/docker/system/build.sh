#!/usr/bin/env bash
. /etc/profile

# installer file
installer_file=$(find /installer -name *.run | head -n1)
chmod +x $installer_file

# installation password
installation_password=$(cat $(find /installer -name *.password | head -n1))

$installer_file --mode unattended --prefix /build/ida --installpassword $installation_password

# SDK
cd /build/ida
for i in $(find /installer -name *sdk*.zip); do
  unzip $i
done

# version independent directories
for i in $(ls | egrep "^idasdk[0-9]+"); do
  mv $i $(echo $i | sed -r 's/[0-9]+//')
done

