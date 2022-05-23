= How to stop gnome-keyring-daemon prompts

In Gnome there is gnome-keyring-daemon that should be unlocked to provide access to keyrings. By default it unlocks using login password, 
but if you use fingerprint or face unlock then it will prompt you to enter password every time any process try to access keyring. 
For my setup it's 6 times after login and 2 times when I start the browser.
Package removal does not work because it's a dependency of many other packages.
What actually works is to remove all ways of starting gnome-keyring-daemon like so

```
mkdir -p ~/.local/share/dbus-1/services
cp /usr/share/dbus-1/services/{org.freedesktop.impl.portal.Secret.service,org.freedesktop.secrets,org.gnome.keyring.service}.service ~/.local/share/dbus-1/services
# replace last line with "Exec=/usr/bin/true"

cp /etc/xdg/autostart/gnome-keyring-{pkcs11,secrets,ssh}.desktop ~/.config/autostart
for f in ~/.config/autostart/gnome-keyring-*.desktop; do echo "Hidden=true" >> $f; done
```

BTW, may be it's simpler to `sudo chmod -x /usr/bin/gnome-keyring-daemon`
