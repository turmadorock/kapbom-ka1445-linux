#!/usr/bin/env bash
# Remove o driver da Kapbom KA-1445 instalado por instalar.sh
# Uso:  sudo bash desinstalar.sh
set -u
[ "$(id -u)" = 0 ] || { echo "Rode com: sudo bash $0"; exit 1; }
lpadmin -x KA1445 2>/dev/null
lpadmin -x KA1445-BT 2>/dev/null
systemctl disable --now rfcomm-ka1445.service 2>/dev/null
rm -f /etc/systemd/system/rfcomm-ka1445.service /etc/kapbom-ka1445.conf
systemctl daemon-reload
LOCAL=/etc/apparmor.d/local/usr.sbin.cupsd
# a regra do AppArmor é comum às impressoras Bluetooth: só sai se a outra não usa Bluetooth
if [ -e "$LOCAL" ] && [ ! -e /etc/systemd/system/rfcomm-d80.service ]; then
  sed -i '/dev\/rfcomm/d' "$LOCAL"
  apparmor_parser -r /etc/apparmor.d/usr.sbin.cupsd
fi
rm -f /usr/lib/cups/filter/rastertoka1445 /usr/share/cups/model/kapbom/kapbom-ka1445.ppd
rmdir /usr/share/cups/model/kapbom 2>/dev/null
rm -f /usr/local/bin/conectar-ka1445-cabo /usr/local/bin/conectar-ka1445-bluetooth \
      /usr/share/applications/conectar-ka1445-cabo.desktop /usr/share/applications/conectar-ka1445-bluetooth.desktop
rm -rf /usr/share/kapbom-ka1445
# o painel é comum às duas impressoras: só sai se a outra também não estiver instalada
if [ ! -e /usr/lib/cups/filter/rastertod80 ]; then
  rm -f /usr/local/bin/painel-impressoras /usr/share/applications/painel-impressoras.desktop
fi
echo "Driver da Kapbom KA-1445 removido."
