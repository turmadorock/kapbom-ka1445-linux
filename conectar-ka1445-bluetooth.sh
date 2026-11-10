#!/usr/bin/env bash
# Conectar KA-1445 Bluetooth — deixa a Kapbom KA-1445 sem fio (KA1445-BT) como impressora padrão.
MAC=''
[ -r /etc/kapbom-ka1445.conf ] && . /etc/kapbom-ka1445.conf && MAC=${KA1445_MAC:-}
[ -n "$MAC" ] || MAC=$(bluetoothctl devices | awk '/ KA-1445$/ {print $2; exit}')

avisar() { echo "$1"; command -v notify-send >/dev/null && notify-send -i printer "Kapbom KA-1445" "$1"; }

if [ -z "$MAC" ]; then
  avisar "Endereço Bluetooth da KA-1445 desconhecido. Ligue a impressora e rode: sudo bash instalar.sh"
  exit 1
fi
if ! lpstat -p KA1445-BT >/dev/null 2>&1; then
  avisar "A fila KA1445-BT não existe. Rode primeiro: sudo bash instalar.sh"
  exit 1
fi

# 1) Bluetooth do computador ligado
if ! bluetoothctl show | grep -q "Powered: yes"; then
  bluetoothctl power on >/dev/null 2>&1
  sleep 2
fi
if ! bluetoothctl show | grep -q "Powered: yes"; then
  avisar "Não consegui ligar o Bluetooth do computador. Ligue-o nas configurações e tente de novo."
  exit 1
fi

# 2) Impressora ligada e ao alcance AGORA (não confia no cache)
if ! timeout 12 bluetoothctl --timeout 10 scan on 2>/dev/null | grep -q "$MAC"; then
  avisar "KA-1445 não respondeu no Bluetooth. Ligue a impressora, deixe perto do computador e tente de novo."
  exit 1
fi
bluetoothctl trust "$MAC" >/dev/null 2>&1

# 3) Porta serial /dev/rfcomm1 ligada à impressora (pede senha só se precisar)
if ! rfcomm -a 2>/dev/null | grep -q "rfcomm1: $MAC"; then
  pkexec systemctl restart rfcomm-ka1445.service || {
    avisar "Não consegui criar a porta /dev/rfcomm1."; exit 1; }
fi

# 4) O CUPS precisa de permissão do AppArmor para abrir a porta Bluetooth
if [ -e /etc/apparmor.d/usr.sbin.cupsd ] && ! grep -qs '/dev/rfcomm' /etc/apparmor.d/local/usr.sbin.cupsd; then
  avisar "Falta liberar o Bluetooth para o CUPS. Rode de novo: sudo bash instalar.sh"
  exit 1
fi

# 5) Fila sem fio como padrão
cupsenable KA1445-BT 2>/dev/null
cupsaccept KA1445-BT 2>/dev/null
lpadmin -d KA1445-BT 2>/dev/null
avisar "KA-1445 encontrada no Bluetooth e definida como impressora padrão."
lpstat -d
