# kapbom-ka1445-linux

Driver Linux (CUPS) para a **Kapbom KA-1445 "Mini Printer"**, uma mini impressora térmica portátil de 58 mm com cabo USB e Bluetooth, vendida no Brasil. No computador ela aparece como **YICHIP "YC Printer demo"** (USB `28e9:0289`) e, no Bluetooth, como `KA-1445`.

*English: CUPS driver for the Kapbom KA-1445 58 mm portable thermal printer (YICHIP "YC Printer demo", USB 28e9:0289, Bluetooth SPP). Run `sudo bash instalar.sh`.*

## O que funciona

- Impressão de qualquer programa: recibos, PDFs e imagens.
- **Largura máxima da cabeça:** 48 mm (384 pontos), sem margem extra.
- **Qualidade máxima:** calor da cabeça em 220, o maior valor estável, testado no papel.
- **Economia de papel:** corta o branco no começo e no fim, então um recibo curto gasta só o necessário.
- Tons de cinza e logotipos em trama de pontos, com o texto nítido.
- Impressão pelo **cabo USB** (fila `KA1445`) e pelo **Bluetooth** (fila `KA1445-BT`).
- Atalhos no menu do sistema: **Conectar KA-1445 Cabo** e **Conectar KA-1445 Bluetooth**.

Testado no Linux Mint 22.3 (base Ubuntu 24.04) com CUPS 2.4.

## Instalação

Deixe a impressora ligada e, se quiser, conectada pelo cabo.

```bash
git clone https://github.com/turmadorock/kapbom-ka1445-linux.git
cd kapbom-ka1445-linux
sudo bash instalar.sh
```

O instalador:
1. Copia o filtro `rastertoka1445` para `/usr/lib/cups/filter/` e o `kapbom-ka1445.ppd` para `/usr/share/cups/model/kapbom/`.
2. Remove a fila com driver errado que o sistema às vezes cria sozinho (`-Printer-demo`, com driver de HP) e cria a fila `KA1445` pelo cabo.
3. Procura a impressora no Bluetooth e cria a porta `/dev/rfcomm1` (serviço `rfcomm-ka1445`). Também libera essa porta para o CUPS no AppArmor e cria a fila `KA1445-BT`.
4. Instala os atalhos no menu.
5. Imprime o recibo de teste `testes/teste-KA-8.pdf`.

Para remover tudo: `sudo bash desinstalar.sh`.

## Opções

| Opção | Valores | Padrão |
|---|---|---|
| `Qualidade` | `Normal`, `Escuro` (calor 160), `Maximo` (calor 220) | `Maximo` |
| `SavePaper` | `Yes` (corta o branco), `No` | `Yes` |
| `Horizontal` | `-5` a `+5` mm | `0` |
| `PageSize` | recibo 48 mm (corta o branco), 48×50 até 48×200 mm, rolo de 1 m | recibo |

Exemplos:

```bash
lp -d KA1445 -o Qualidade=Escuro recibo.pdf
lpadmin -p KA1445 -o Qualidade=Normal        # muda o padrão da fila
```

## Como funciona

- A cabeça tem **384 pontos (48 mm a 203 dpi)**. Linhas mais largas passam para a linha de baixo (testado com 392 e 448 pontos).
- A impressão usa ESC/POS: `ESC @` para iniciar, `ESC 7 n1 n2 n3` para o calor e blocos de imagem `GS v 0`.
- **Atenção:** um calor acima de cerca de 230 (por exemplo 240 ou 255) faz a impressora rejeitar o comando e imprimir lixo. O driver usa 220.
- O filtro, em Python 3 sem dependências, lê o raster do CUPS e aplica uma curva de contraste e uma trama Bayer 8×8 nos cinzas. Também corta o branco e envia a imagem em blocos de 128 linhas.
- A cabeça fica cerca de 0,5 mm fora do centro do papel, o que é normal nessas mini impressoras. O driver prefere a largura máxima a centralizar.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `rastertoka1445` | Filtro CUPS (raster → ESC/POS) |
| `kapbom-ka1445.ppd` | Descrição da impressora para o CUPS |
| `instalar.sh` / `desinstalar.sh` | Instalação e remoção |
| `conectar-ka1445-cabo.sh` / `conectar-ka1445-bluetooth.sh` | Trocar a impressora padrão entre cabo e Bluetooth |
| `testes/teste-KA-8.pdf` | Recibo de teste |

Veja também o projeto irmão [genai-d80-linux](https://github.com/turmadorock/genai-d80-linux), para a impressora térmica A4 GENAI D80.

## Licença

MIT. Veja [LICENSE](LICENSE). Este projeto não é afiliado à Kapbom nem à YICHIP.
