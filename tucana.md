# How to install Magisk on Xiaomi Mi Note 10 (tucana)

 1. unlock bootloader
 1. install [MagiskManager](https://github.com/topjohnwu/Magisk/releases/latest)
 1. download [TWRP](https://eu.dl.twrp.me/tucana/)
 1. enable USB debugging and connect adb
 1. reboot to fastboot `adb reboot bootloader`
 1. boot to TWRP `fastboot boot twrp.img`
 1. after booting twrp decrypt /sdcard using your pin/pattern
 1. connect to device using adb `adb shell`
 1. copy boot partition to sdcard `dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/boot.img`
 1. reboot to system `adb reboot`
 1. launch MagiskManager
 1. press "Install" in "Magisk" card
 1. uncheck "Recovery Mode"
 1. press next
 1. select boot.img file on the sdcard root
 1. after successeful patch pull patched boot image to pc `adb pull /sdcard/Download/magisk_patched-*.img ./`
 1. reboot to bootloader again `adb reboot bootloader`
 1. flash patched boot image `fastboot flash boot magisk_patched-*.img`
 1. reboot to system `fastboot reboot`
 1. profit!
