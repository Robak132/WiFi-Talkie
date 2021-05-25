#!/bin/bash
BR_NAME=buildroot-2020.02
BR_FILE=${BR_NAME}.tar.bz2
BR_DL=../${BR_FILE}
set -e
if [ ! -f ${BR_DL} ] || ! ( bzip2 -q -t ${BR_DL}); then
  (  
     cd ..
     rm -f ${BR_FILE}
     wget https://buildroot.org/downloads/${BR_FILE}
  )
fi
tar -xjf ${BR_DL}
cp BR_config ${BR_NAME}/.config
cd ${BR_NAME}
cd package
rm -Rf python-pyaudio
rm -Rf portaudio
cd ../../
for i in wifitalkie/* ; do
   cp -r $i overlay/root
done
cp -R portaudio ${BR_NAME}/package
cp -R python-pyaudio ${BR_NAME}/package
cp BR_config_RPI ${BR_NAME}/.config
cp BRpackage_config_RPI ${BR_NAME}/package/Config.in
cd ${BR_NAME}
echo "Configuration ended, building..."
make
