#!/usr/bin/env bash
# Instalador do driver Linux da Kapbom KA-1445 (mini impressora térmica 58 mm, cabeça de 48 mm / 384 pontos)
#   - filtro CUPS rastertoka1445 + PPD kapbom-ka1445.ppd
#   - fila "KA1445"    pelo cabo USB
#   - fila "KA1445-BT" pelo Bluetooth (porta serial /dev/rfcomm1)
#   - atalhos no menu: "Conectar KA-1445 Cabo" e "Conectar KA-1445 Bluetooth"
# Uso (na pasta do projeto):  sudo bash instalar.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Rode com: sudo bash $0"; exit 1; }
DIR=$(cd "$(dirname "$0")" && pwd)
CONF=/etc/kapbom-ka1445.conf
PPD=/usr/share/cups/model/kapbom/kapbom-ka1445.ppd
RFCOMM=1

echo "== 1/5 Filtro e PPD =="
command -v python3 >/dev/null || apt-get install -y python3
install -m 755 -o root -g root "$DIR/rastertoka1445" /usr/lib/cups/filter/rastertoka1445
install -D -m 644 "$DIR/kapbom-ka1445.ppd" "$PPD"

echo "== 2/5 Fila pelo cabo (KA1445) =="
# O sistema às vezes cria sozinho uma fila com driver errado para esta impressora ("-Printer-demo")
for q in $(lpstat -v 2>/dev/null | awk -F'[ :]' '/YICHIP/ {print $3}'); do
  [ "$q" = KA1445 ] || lpadmin -x"$q" 2>/dev/null || true
done
USB_URI=$(lpinfo --include-schemes usb -v 2>/dev/null | awk '/YICHIP/ {print $2; exit}')
USB_URI=${USB_URI:-'usb://YICHIP/-Printer%20demo?serial=000000000004'}
echo "URI: $USB_URI"
lpadmin -x KA1445 2>/dev/null || true
lpadmin -p KA1445 -E -v "$USB_URI" -P "$PPD" -D "Kapbom KA-1445 (cabo)" -o printer-is-shared=false 2>/dev/null

echo "== 3/5 Bluetooth =="
MAC=${KA1445_MAC:-}
if [ -z "$MAC" ]; then
  echo "Procurando a KA-1445 no Bluetooth (deixe ligada)..."
  bluetoothctl power on >/dev/null 2>&1 || true
  MAC=$(timeout 15 bluetoothctl --timeout 12 scan on 2>/dev/null \
        | grep -oE '([0-9A-F]{2}:){5}[0-9A-F]{2} KA-1445$' | awk '{print $1; exit}' || true)
  [ -n "$MAC" ] || MAC=$(bluetoothctl devices | awk '/ KA-1445$/ {print $2; exit}')
fi
if [ -n "$MAC" ]; then
  echo "KA-1445 Bluetooth: $MAC"
  echo "KA1445_MAC=$MAC" > "$CONF"
  bluetoothctl trust "$MAC" >/dev/null 2>&1 || true
  cat >/etc/systemd/system/rfcomm-ka1445.service <<EOF
[Unit]
Description=Porta serial Bluetooth da Kapbom KA-1445
After=bluetooth.service
Requires=bluetooth.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/rfcomm bind $RFCOMM $MAC 1
ExecStop=/usr/bin/rfcomm release $RFCOMM
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable rfcomm-ka1445.service >/dev/null
  systemctl restart rfcomm-ka1445.service
  # O AppArmor do cupsd bloqueia /dev/rfcomm* por padrão
  LOCAL=/etc/apparmor.d/local/usr.sbin.cupsd
  if [ -e /etc/apparmor.d/usr.sbin.cupsd ]; then
    touch "$LOCAL"
    grep -q '/dev/rfcomm\* rw,' "$LOCAL" || echo '/dev/rfcomm* rw,   # impressoras Bluetooth (KA-1445)' >> "$LOCAL"
    apparmor_parser -r /etc/apparmor.d/usr.sbin.cupsd
  fi
  lpadmin -x KA1445-BT 2>/dev/null || true
  lpadmin -p KA1445-BT -E -v "serial:/dev/rfcomm$RFCOMM?baud=115200" -P "$PPD" \
          -D "Kapbom KA-1445 (Bluetooth)" -o printer-is-shared=false 2>/dev/null
else
  echo "KA-1445 não encontrada no Bluetooth: pulei esta parte."
  echo "Para instalar depois: ligue a impressora e rode de novo (ou KA1445_MAC=XX:XX:... sudo -E bash instalar.sh)."
fi

echo "== 4/5 Atalhos no menu =="
install -m 755 "$DIR/conectar-ka1445-cabo.sh" /usr/local/bin/conectar-ka1445-cabo
install -m 755 "$DIR/conectar-ka1445-bluetooth.sh" /usr/local/bin/conectar-ka1445-bluetooth
for k in cabo:Cabo bluetooth:Bluetooth; do
  cat > /usr/share/applications/conectar-ka1445-${k%%:*}.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Conectar KA-1445 ${k#*:}
Comment=Define a Kapbom KA-1445 (${k%%:*}) como impressora padrão
Exec=/usr/local/bin/conectar-ka1445-${k%%:*}
Icon=printer
Terminal=false
Categories=Utility;Settings;
EOF
done

echo "== 5/5 Página de teste =="
lp -d KA1445 -t "TESTE KA-8" "$DIR/testes/teste-KA-8.pdf" 2>/dev/null \
  || echo "(cabo desconectado: teste pelo cabo não enviado)"
echo
lpstat -v | grep KA1445
echo
echo "Pronto. Para deixar a KA-1445 como padrão use o atalho 'Conectar KA-1445 Cabo' ou 'Bluetooth'."
