#!/usr/bin/python3
# Painel das Impressoras Térmicas — GENAI D80 (A4) e Kapbom KA-1445 (58 mm)
# Janela GTK para: conectar por cabo ou Bluetooth, orientação, qualidade (calor),
# tamanho do papel, ajuste horizontal, corte do branco, página de teste e imprimir arquivo.
# Não precisa de senha: usa lpadmin/lpoptions (grupo lpadmin) e os scripts conectar-*.
import os
import re
import sys
import shutil
import subprocess
import urllib.request

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib  # noqa: E402

PERFIS = [
    {
        'id': 'd80', 'nome': 'GENAI D80 (A4)',
        'filas': {'cabo': 'D80', 'bluetooth': 'D80-BT'},
        'usb': '0fe6:811e',
        'conectar': {'cabo': 'conectar-d80-cabo', 'bluetooth': 'conectar-d80-bluetooth'},
        'teste': ['/usr/share/genai-d80/teste.pdf', 'testes/teste-V2-A.pdf'],
        'orientacao_padrao': 'auto',
    },
    {
        'id': 'ka1445', 'nome': 'Kapbom KA-1445 (58 mm)',
        'filas': {'cabo': 'KA1445', 'bluetooth': 'KA1445-BT'},
        'usb': '28e9:0289',
        'conectar': {'cabo': 'conectar-ka1445-cabo', 'bluetooth': 'conectar-ka1445-bluetooth'},
        'teste': ['/usr/share/kapbom-ka1445/teste.pdf', 'testes/teste-KA-8.pdf'],
        'orientacao_padrao': '3',
    },
]

ORIENTACOES = [
    ('auto', 'Automática (gira documentos deitados)'),
    ('3', 'Retrato (nunca gira)'),
    ('4', 'Paisagem (gira 90°)'),
    ('5', 'Paisagem invertida (gira 270°)'),
    ('6', 'Retrato invertido (gira 180°)'),
]

# Opções do PPD mostradas no painel, na ordem; as que a impressora não tiver são ignoradas
OPCOES_PPD = ['Qualidade', 'PageSize', 'Horizontal', 'SavePaper']
ROTULOS = {
    'Qualidade': 'Qualidade (calor da cabeça)',
    'PageSize': 'Tamanho do papel',
    'Horizontal': 'Ajuste horizontal',
    'SavePaper': 'Cortar papel em branco',
}


def rodar(*cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def fila_existe(fila):
    return rodar('lpstat', '-p', fila)[0] == 0


def ler_ppd(fila):
    """Lê o PPD em uso pela fila (via CUPS local) e devolve {opção: (rótulos, padrão)}."""
    try:
        txt = urllib.request.urlopen('http://localhost:631/printers/%s.ppd' % fila, timeout=5) \
            .read().decode('latin-1')
    except OSError:
        return {}
    opcoes = {}
    for chave in OPCOES_PPD:
        escolhas = []
        for m in re.finditer(r'^\*%s ([^/:\s]+)(?:/([^:]*))?:' % re.escape(chave), txt, re.M):
            escolhas.append((m.group(1), (m.group(2) or m.group(1)).strip()))
        m = re.search(r'^\*Default%s:\s*(\S+)' % re.escape(chave), txt, re.M)
        if escolhas:
            opcoes[chave] = (escolhas, m.group(1) if m else escolhas[0][0])
    return opcoes


def orientacao_atual(fila, padrao):
    _, out = rodar('lpoptions', '-p', fila)
    m = re.search(r'orientation-requested=(\d)', out)
    if m:
        return m.group(1)
    return '3' if re.search(r'nopdfAutoRotate(=true)?(\s|$)', out) else 'auto'


def aplicar_orientacao(fila, valor):
    if valor == 'auto':
        rodar('lpadmin', '-p', fila, '-o', 'nopdfAutoRotate-default=false',
              '-R', 'orientation-requested-default')
    else:
        rodar('lpadmin', '-p', fila, '-o', 'nopdfAutoRotate-default=true',
              '-o', 'orientation-requested-default=%s' % valor)


def achar_script(nome):
    caminho = shutil.which(nome)
    if caminho:
        return caminho
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome + '.sh')
    return local if os.path.exists(local) else None


class Aba(Gtk.Box):
    def __init__(self, janela, perfil):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.janela, self.p = janela, perfil
        self.set_border_width(14)
        self.filas = [f for f in perfil['filas'].values() if fila_existe(f)]
        principal = self.filas[0]

        # --- Conexão
        quadro = Gtk.Frame(label=' Conexão ')
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        caixa.set_border_width(10)
        self.status = Gtk.Label(xalign=0)
        self.status.set_line_wrap(True)
        caixa.pack_start(self.status, False, False, 0)
        botoes = Gtk.Box(spacing=8)
        for modo, texto in (('cabo', 'Usar CABO'), ('bluetooth', 'Usar BLUETOOTH')):
            if perfil['filas'][modo] in self.filas:
                b = Gtk.Button(label=texto)
                b.connect('clicked', self.conectar, modo)
                botoes.pack_start(b, True, True, 0)
        caixa.pack_start(botoes, False, False, 0)
        quadro.add(caixa)
        self.pack_start(quadro, False, False, 0)

        # --- Opções de impressão
        quadro = Gtk.Frame(label=' Opções de impressão (valem para cabo e Bluetooth) ')
        grade = Gtk.Grid(column_spacing=12, row_spacing=8)
        grade.set_border_width(10)
        linha = 0
        self.combos = {}

        grade.attach(Gtk.Label(label='Orientação', xalign=0), 0, linha, 1, 1)
        cb = Gtk.ComboBoxText()
        for val, txt in ORIENTACOES:
            cb.append(val, txt)
        cb.set_active_id(orientacao_atual(principal, perfil['orientacao_padrao']))
        grade.attach(cb, 1, linha, 1, 1)
        self.combos['__orientacao'] = cb
        linha += 1

        for chave, (escolhas, padrao) in ler_ppd(principal).items():
            grade.attach(Gtk.Label(label=ROTULOS.get(chave, chave), xalign=0), 0, linha, 1, 1)
            cb = Gtk.ComboBoxText()
            for val, txt in escolhas:
                if chave == 'Horizontal':
                    txt = '%s mm' % val.replace('+', '+ ').replace('-', '− ') if val != '0' else '0 mm (sem ajuste)'
                cb.append(val, txt)
            cb.set_active_id(padrao)
            grade.attach(cb, 1, linha, 1, 1)
            self.combos[chave] = cb
            linha += 1

        grade.attach(Gtk.Label(label='Resolução', xalign=0), 0, linha, 1, 1)
        grade.attach(Gtk.Label(label='203 dpi (fixa, limite físico da cabeça)', xalign=0), 1, linha, 1, 1)
        linha += 1

        salvar = Gtk.Button(label='Salvar opções')
        salvar.get_style_context().add_class('suggested-action')
        salvar.connect('clicked', self.salvar)
        grade.attach(salvar, 1, linha, 1, 1)
        quadro.add(grade)
        self.pack_start(quadro, False, False, 0)

        # --- Imprimir
        quadro = Gtk.Frame(label=' Imprimir ')
        botoes = Gtk.Box(spacing=8)
        botoes.set_border_width(10)
        b = Gtk.Button(label='Página de teste')
        b.connect('clicked', self.teste)
        botoes.pack_start(b, True, True, 0)
        b = Gtk.Button(label='Imprimir arquivo…')
        b.connect('clicked', self.imprimir_arquivo)
        botoes.pack_start(b, True, True, 0)
        quadro.add(botoes)
        self.pack_start(quadro, False, False, 0)

        self.atualizar_status()

    # ---------- ações
    def fila_padrao_atual(self):
        _, out = rodar('lpstat', '-d')
        m = re.search(r':\s*(\S+)\s*$', out)
        return m.group(1) if m else ''

    def atualizar_status(self):
        cabo = rodar('lsusb', '-d', self.p['usb'])[0] == 0
        padrao = self.fila_padrao_atual()
        modo = next((m for m, f in self.p['filas'].items() if f == padrao), None)
        txt = 'Cabo USB: %s' % ('conectado' if cabo else 'desconectado')
        txt += '\nImpressora padrão do sistema: %s' % (
            {'cabo': 'esta impressora, pelo CABO', 'bluetooth': 'esta impressora, pelo BLUETOOTH'}.get(modo)
            or (padrao or 'nenhuma'))
        self.status.set_text(txt)

    def avisar(self, msg, erro=False):
        d = Gtk.MessageDialog(transient_for=self.janela, modal=True,
                              message_type=Gtk.MessageType.ERROR if erro else Gtk.MessageType.INFO,
                              buttons=Gtk.ButtonsType.OK, text=msg)
        d.run()
        d.destroy()

    def conectar(self, _b, modo):
        script = achar_script(self.p['conectar'][modo])
        if not script:
            self.avisar('Script de conexão não encontrado. Rode o instalador de novo.', True)
            return
        self.status.set_text('Conectando pelo %s… (o Bluetooth pode levar até 15 s)' % modo.upper())
        self.janela.set_sensitive(False)

        def fim(rc, out):
            self.janela.set_sensitive(True)
            self.atualizar_status()
            self.avisar(out.splitlines()[0] if out else 'Pronto.', rc != 0)
        GLib.idle_add(lambda: (fim(*rodar('bash', script)), False)[1])

    def salvar(self, _b):
        erros = []
        for fila in self.filas:
            aplicar_orientacao(fila, self.combos['__orientacao'].get_active_id())
            args = []
            for chave, cb in self.combos.items():
                if not chave.startswith('__') and cb.get_active_id():
                    args += ['-o', '%s=%s' % (chave, cb.get_active_id())]
            if args:
                rc, out = rodar('lpadmin', '-p', fila, *args)
                if rc != 0:
                    erros.append('%s: %s' % (fila, out))
        if erros:
            self.avisar('Não consegui salvar:\n' + '\n'.join(erros), True)
        else:
            self.avisar('Opções salvas para: %s' % ', '.join(self.filas))

    def fila_para_imprimir(self):
        padrao = self.fila_padrao_atual()
        return padrao if padrao in self.filas else self.filas[0]

    def teste(self, _b):
        aqui = os.path.dirname(os.path.abspath(__file__))
        arq = next((c for t in self.p['teste'] for c in (t, os.path.join(aqui, t)) if os.path.exists(c)), None)
        if not arq:
            self.avisar('Página de teste não encontrada. Rode o instalador de novo.', True)
            return
        self.enviar(arq, 'Pagina de teste')

    def imprimir_arquivo(self, _b):
        d = Gtk.FileChooserDialog(title='Escolha o arquivo', transient_for=self.janela,
                                  action=Gtk.FileChooserAction.OPEN)
        d.add_buttons('Cancelar', Gtk.ResponseType.CANCEL, 'Imprimir', Gtk.ResponseType.OK)
        filtro = Gtk.FileFilter()
        filtro.set_name('PDF, imagens e texto')
        for padrao in ('*.pdf', '*.PDF', '*.png', '*.jpg', '*.jpeg', '*.txt'):
            filtro.add_pattern(padrao)
        d.add_filter(filtro)
        if d.run() == Gtk.ResponseType.OK:
            arq = d.get_filename()
            d.destroy()
            self.enviar(arq, os.path.basename(arq))
        else:
            d.destroy()

    def enviar(self, arq, titulo):
        fila = self.fila_para_imprimir()
        rc, out = rodar('lp', '-d', fila, '-t', titulo, arq)
        self.avisar(('Enviado para %s.\n%s' % (fila, out)) if rc == 0 else out, rc != 0)


class Janela(Gtk.Window):
    def __init__(self):
        super().__init__(title='Impressoras Térmicas')
        self.set_default_size(560, -1)
        self.set_icon_name('printer')
        abas = self.abas = Gtk.Notebook()
        for perfil in PERFIS:
            if any(fila_existe(f) for f in perfil['filas'].values()):
                abas.append_page(Aba(self, perfil), Gtk.Label(label=perfil['nome']))
        # "painel-impressoras ka1445" abre direto na aba dessa impressora
        ids = [p['id'] for p in PERFIS if any(fila_existe(f) for f in p['filas'].values())]
        self.aba_inicial = ids.index(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] in ids else 0
        if abas.get_n_pages() == 0:
            caixa = Gtk.Label(label='Nenhuma impressora térmica instalada.\n'
                                    'Rode o instalador (sudo bash instalar.sh) do driver primeiro.')
            caixa.set_margin_top(30)
            caixa.set_margin_bottom(30)
            self.add(caixa)
        else:
            self.add(abas)


if __name__ == '__main__':
    j = Janela()
    j.connect('destroy', Gtk.main_quit)
    j.show_all()
    j.abas.set_current_page(j.aba_inicial)   # só funciona depois que as abas estão visíveis
    Gtk.main()
