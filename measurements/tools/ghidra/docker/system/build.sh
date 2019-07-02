#!/usr/bin/env bash
. /etc/profile

cd /build

# clone
git clone https://github.com/NationalSecurityAgency/ghidra.git
cd ghidra
git checkout tags/Ghidra_9.0.2_build

# download dependencies
mkdir /build/flatRepo

cd /tmp
curl -OL https://github.com/pxb1988/dex2jar/releases/download/2.0/dex-tools-2.0.zip
unzip dex-tools-2.0.zip
cp dex2jar-2.0/lib/dex-*.jar /build/flatRepo/

cd /build/flatRepo
curl -OL https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/android4me/AXMLPrinter2.jar

cd /tmp
curl -OL https://sourceforge.net/projects/catacombae/files/HFSExplorer/0.21/hfsexplorer-0_21-bin.zip
mkdir hfsx && cd hfsx
unzip ../hfsexplorer-0_21-bin.zip
cp lib/{csframework.jar,hfsx_dmglib.jar,hfsx.jar,iharder-base64.jar} /build/flatRepo

mkdir -p /build/ghidra.bin/Ghidra/Features/GhidraServer/ && cd /build/ghidra.bin/Ghidra/Features/GhidraServer/
curl -OL https://sourceforge.net/projects/yajsw/files/yajsw/yajsw-stable-12.12/yajsw-stable-12.12.zip

mkdir -p /build/ghidra.bin/GhidraBuild/EclipsePlugins/GhidraDev/buildDependencies/ && cd /build/ghidra.bin/GhidraBuild/EclipsePlugins/GhidraDev/buildDependencies/
curl -OL http://ftp.snt.utwente.nl/pub/software/eclipse//tools/cdt/releases/8.6/cdt-8.6.0.zip
curl -OL https://downloads.sourceforge.net/project/pydev/pydev/PyDev%206.3.1/PyDev%206.3.1.zip
mv PyDev*.zip 'PyDev 6.3.1.zip'

# prepare and build dependencies
cd /build/ghidra
gradle eclipse
gradle prepDev -x yajswDevUnpack
gradle sleighCompile
gradle decompileLinux64Executable
gradle demangler_gnuLinux64Executable
gradle sleighLinux64Executable

# build dependencies for GhidraServer
gradle yajswDevUnpack

# build Ghidra
gradle buildGhidra

# build GhidraDev plugin for Eclipse
sed -ri 's:^//(.* Eclipse PDE):\1:g' settings.gradle
gradle cdtUnpack pyDevUnpack
gradle eclipse
gradle prepDev
mkdir -p /build/ghidra.bin/GhidraBuild/Eclipse/GhidraDev/

# prepare Ghidra for running
cd build/dist
unzip ghidra*.zip
ln -s ghidra*/ ghidra
cd ghidra/Extensions/Eclipse/GhidraDev
ln -s /build/ghidra.bin/GhidraBuild/Eclipse/GhidraDev/GhidraDev-2.0.0.zip GhidraDev-2.0.0.zip

# download and install eclipse
cd /tmp
curl -OL http://ftp.fau.de/eclipse/technology/epp/downloads/release/2019-03/R/eclipse-java-2019-03-R-linux-gtk-x86_64.tar.gz
cd /build
tar xf /tmp/eclipse*.tar.gz
echo "-Djavax.net.ssl.trustStorePassword=changeit" >> /build/eclipse/eclipse.ini

# Eclipse configuration
# - CDT extension
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository http://download.eclipse.org/tools/orbit/downloads/drops/R20190226160451/repository -installIU javax.xml.bind
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository http://download.eclipse.org/tools/orbit/downloads/drops/R20190226160451/repository -installIU com.sun.xml.bind
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository https://download.eclipse.org/tm/updates/4.5.100-SNAPSHOT/repository/ -installIU org.eclipse.tm.terminal.control
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository http://download.eclipse.org/tools/cdt/releases/9.7 -installIU org.eclipse.cdt.feature.group
# - PyDev extension
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository http://www.pydev.org/updates -installIU 201903251948.PyDev
# - Plugin Development Tools
/build/eclipse/eclipse -application org.eclipse.equinox.p2.director -repository http://download.eclipse.org/eclipse/updates/4.11 -installIU org.eclipse.releng.pde.categoryIU
# - Workspace configuration
mkdir -p /build/eclipse/configuration/.settings/
cat << EOF > /build/eclipse/configuration/.settings/org.eclipse.ui.ide.prefs
MAX_RECENT_WORKSPACES=10
RECENT_WORKSPACES=/eclipse-workspace
RECENT_WORKSPACES_PROTOCOL=3
SHOW_RECENT_WORKSPACES=false
SHOW_WORKSPACE_SELECTION_DIALOG=false
eclipse.preferences.version=1
EOF

# prevent Firefox from crashing
# https://support.mozilla.org/de/questions/1167673
firefox --headless &
sleep 2
killall firefox-esr

pref_file=$(find $HOME/.mozilla/firefox -name prefs.js)
echo 'user_pref("browser.tabs.remote.autostart", false);' >> $pref_file
echo 'user_pref("browser.tabs.remote.autostart.2", false);' >> $pref_file
