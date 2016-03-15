#!/bin/sh

echo "************************************************************"
echo "Load the kernel drivers  and packages for ppp!!!"
echo " ***********************************************************"
opkg update
echo "************************************************************"
sleep 2
opkg install kernel-module-cdc-acm
opkg install kernel-module-ppp-async
opkg install kernel-module-ppp-deflate
opkg install kernel-module-ppp-generic
opkg install kernel-module-ppp-mppe
opkg install kernel-module-ppp-synctty
opkg install kernel-module-pppoe
opkg install kernel-module-pppox
opkg install kernel-module-slhc
opkg install kernel-module-usbserial
opkg install kernel-module-option
opkg install kernel-module-bsd-comp
opkg install iptables
opkg install libusb-0.1-4
opkg install libc6
opkg install libpcap1
sleep 2


#DEP="$(uname -r)"
#depmod -a $DEP


[ -e /etc/modules-load.d/usbserial.conf ] && rm -rf /etc/modules-load.d/usbserial.conf && echo "Disable startup driver usbserial ..."
echo " "
[ -e /etc/modules-load.d/belkin_sa.conf ] && rm -rf /etc/modules-load.d/belkin_sa.conf && echo "Disable startup driver belkin_sa ..."
echo " "
[ -e /etc/modules-load.d/keyspan.conf ] && rm -rf /etc/modules-load.d/keyspan.conf && echo "Disable startup driver keyspan ..."
echo " "
[ -e /etc/modules-load.d/ftdi_sio.conf ] && rm -rf /etc/modules-load.d/ftdi_sio.conf && echo "Disable startup driver ftdi_sio ..."
echo " "
[ -e /usr/sbin/update-modules ] && update-modules force || true
echo " "
echo "***********************************************************************"
echo "Please reboot your receiver, for the changes to take effect !!!"
echo "***********************************************************************"
echo " "

exit 0
