#!/usr/bin/env bash
# Conectar KA-1445 Cabo — deixa a Kapbom KA-1445 (USB) como impressora padrão.
avisar() { echo "$1"; command -v notify-send >/dev/null && notify-send -i printer "Kapbom KA-1445" "$1"; }

if ! lsusb -d 28e9:0289 >/dev/null 2>&1; then
  avisar "Cabo não detectado. Ligue a KA-1445 e conecte o cabo USB, depois tente de novo."
  exit 1
fi
if ! lpstat -p KA1445 >/dev/null 2>&1; then
  avisar "A fila KA1445 não existe. Rode primeiro: sudo bash instalar.sh"
  exit 1
fi
cupsenable KA1445 2>/dev/null
cupsaccept KA1445 2>/dev/null
lpadmin -d KA1445 2>/dev/null
avisar "KA-1445 conectada pelo CABO e definida como impressora padrão."
lpstat -d
