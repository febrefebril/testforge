
"""TestForge Recorder GUI — tkinter launcher, zero external deps."""
from pathlib import Path
import subprocess
import sys
import threading
from testforge.subprocess_utils import popen_hidden
import platform
import ctypes
from PIL import Image, ImageTk

try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk, font as tkfont
except ModuleNotFoundError:
    sys.exit(
        "[TestForge GUI] tkinter não encontrado.\n"
        "  Windows: reinstale Python de python.org (marque 'tcl/tk').\n"
        "  Linux:   sudo apt install python3-tk   (Debian/Ubuntu)\n"
        "           sudo dnf install python3-tkinter  (RHEL/Fedora)\n"
        "           sudo emerge dev-tcltk/tk  (Gentoo)\n"
    )


# B30: bind Ctrl+V pa Linux — tkinter nao trata por padrao (X11).
def _bind_ctrl_v(entry):
    """Bind Ctrl+V to paste from clipboard (Linux fix)."""

    def _paste(event):
        try:
            text = entry.clipboard_get()
            if not text:
                return "break"

            try:
                entry.delete("sel.first", "sel.last")
            except Exception:
                pass  # no selection

            entry.insert("insert", text)
            return "break"
        except Exception:
            return "break"

    try:
        entry.bind("<Control-v>", _paste)
    except Exception:
        pass


# -- Palette - Design System CAIXA --------------------------------------------

CAIXA_BLUE = "#005CA9"
CAIXA_BLUE_DARK = "#004F92"
CAIXA_BLUE_SECUNDARY = "#D6E3E6"
CAIXA_ORANGE = "#F39200"
CAIXA_ORANGE_DARK = "#D97F00"

GRAY_50 = "#D0E0E3"
GRAY_90 = "#64747a"
GRAY_130 = "#22292E"
COLOR_BG_CARD_INPUT = "#FFFFFF"

# Fundo principal
BG = GRAY_50

# Cards
BG_CARD = COLOR_BG_CARD_INPUT

# Inputs
BG_INPUT = COLOR_BG_CARD_INPUT

# Log
BG_LOG = "#F4F8F9"

# Texto principal
FG = GRAY_130

# Texto secundário
FG_DIM = "#4F5B61"

# Campos obrigatórios
FG_REQ = CAIXA_ORANGE

# Bordas
BORDER = "#B7C4C8"

ACCENT = CAIXA_BLUE
ACCENT2 = CAIXA_ORANGE

# Botões
BTN_START = CAIXA_BLUE
BTN_SECONDARY = CAIXA_ORANGE
BTN_CLEAR = "#E8EFF1"

BTN_NEUTRAL_BG = GRAY_90
BTN_NEUTRAL_FG = COLOR_BG_CARD_INPUT

BTN_NEUTRAL_ACTIVE_BG = COLOR_BG_CARD_INPUT #"#384248"
BTN_NEUTRAL_ACTIVE_FG = COLOR_BG_CARD_INPUT

ACTIVE_BG_BTN_NEUTRAL = CAIXA_BLUE_SECUNDARY

# Loading 
LOADING_BG = CAIXA_BLUE
LOADING_FG = "#FFFFFF"

PROGRESS_BAR_COLOR = CAIXA_ORANGE
PROGRESS_BAR_TROUGH_COLOR = CAIXA_BLUE_DARK

# -- Logo ----------------------------------------------------------------------

LOGO_HEIGHT = 64 #px

# -- Fonts ---------------------------------------------------------------------

FONT_CAPTION = ("Segoe UI", 12)
FONT_BODY = ("Segoe UI", 14)
FONT_LABEL = ("Segoe UI", 14)
FONT_SECTION = ("Segoe UI", 18, "bold")
FONT_PAGE_TITLE = ("Segoe UI", 24, "bold")

FONT_MONO = ("Consolas", 12)

LOG_FONT_COLOR = "#43a555"

# Nomes conhecidos da fonte CAIXA
CAIXA_FONT_CANDIDATES = [
    "CAIXA Std",
    "CAIXAStd",
    "CAIXA Std Regular",
    "CAIXA Regular",
]

def _register_caixa_fonts():
    """
    Registra temporariamente as fontes da pasta assets/fonts.

    Apenas Windows.
    Linux/macOS utilizam fallback.
    """

    if platform.system() != "Windows":
        return

    try:
        fonts_dir = (
            Path(__file__).parent
            / "assets"
            / "fonts"
        )

        if not fonts_dir.exists():
            return

        FR_PRIVATE = 0x10

        for font_file in fonts_dir.glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(
                str(font_file),
                FR_PRIVATE,
                0,
            )

    except Exception as exc:
        print(
            f"Erro registrando fontes CAIXA: {exc}"
        )

def _configure_caixa_fonts(root):
    global FONT_CAPTION
    global FONT_BODY
    global FONT_LABEL
    global FONT_SECTION
    global FONT_PAGE_TITLE

    # força atualização da lista de fontes
    root.update()
    root.update_idletasks()

    families = set(tkfont.families())

    family = None
    print("\nFontes CAIXA encontradas:")
    for candidate in CAIXA_FONT_CANDIDATES:
        if candidate in families:
            family = candidate
            break

    if family:
        print(
            f"Fonte carregada: {family}"
        )
    else:
        family = "Segoe UI"

        print(
            "Fonte CAIXA não encontrada. "
            "Utilizando fallback Segoe UI."
        )

    FONT_CAPTION = (family, 12)
    FONT_BODY = (family, 14)
    FONT_LABEL = (family, 14)
    FONT_SECTION = (family, 18, "bold")
    FONT_PAGE_TITLE = (family, 24, "bold")

# -- Helpers -------------------------------------------------------------------


def _entry(parent, textvariable, width=40, show=None):
    kw = {}
    if show:
        kw["show"] = show

    e = tk.Entry(
        parent,
        textvariable=textvariable,
        width=width,
        bg=BG_INPUT,
        fg=GRAY_130,
        insertbackground=GRAY_130,
        relief="flat",
        highlightthickness=2,
        highlightcolor=CAIXA_BLUE,
        highlightbackground=BORDER,
        font=FONT_BODY,
        **kw,
    )

    return e


def _combo(parent, textvariable, values, width=20):
    style = ttk.Style(parent)
    style.theme_use("default")

    style.configure(
        "TF.TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_INPUT,
        foreground=FG,
        selectbackground=BG_INPUT,
        selectforeground=COLOR_BG_CARD_INPUT,
        bordercolor=BG_INPUT,
        arrowcolor=FG,
        relief="flat",
    )

    style.map(
        "TF.TCombobox",
        fieldbackground=[("readonly", BG_INPUT)],
        foreground=[("readonly", FG)],
        selectbackground=[("readonly", BG_INPUT)],
        selectforeground=[("readonly", FG)],
    )

    c = ttk.Combobox(
        parent,
        textvariable=textvariable,
        values=values,
        width=width,
        state="readonly",
        style="TF.TCombobox",
        font=FONT_BODY,
    )

    return c


def _check(parent, text, variable):
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        bg=BG_CARD,
        fg=FG,
        selectcolor=BG_INPUT,
        activebackground=BG_CARD,
        activeforeground=FG,
        font=FONT_BODY,
        anchor="w",
        highlightthickness=0,
    )


def _section_title(parent, text):
    f = tk.Frame(parent, bg=BG_CARD)

    tk.Label(
        f,
        text=text,
        bg=BG_CARD,
        fg=CAIXA_BLUE,
        font=FONT_SECTION,
    ).pack(side="left", pady=(8, 2))

    tk.Frame(
        f,
        bg=BORDER,
        height=2,
    ).pack(side="left", fill="x", expand=True, padx=(8, 0))

    return f


def _row(grid, row, label, widget, req=False):
    color = FG_REQ if req else FG_DIM

    tk.Label(
        grid,
        text=label,
        bg=BG_CARD,
        fg=color,
        font=FONT_LABEL,
        anchor="e",
        width=16,
    ).grid(row=row, column=0, sticky="e", padx=(0, 6), pady=2)

    widget.grid(row=row, column=1, sticky="ew", pady=2)


def _button_primary(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        bg=BTN_START,
        fg="white",
        font=FONT_LABEL,
        activebackground=CAIXA_BLUE_DARK,
        activeforeground="white",
        relief="flat",
        padx=20,
        pady=8,
        cursor="hand2",
        command=command,
    )


def _button_secondary(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        bg=BTN_SECONDARY,
        fg="white",
        font=FONT_LABEL,
        activebackground=CAIXA_ORANGE_DARK,
        activeforeground="white",
        relief="flat",
        padx=14,
        pady=7,
        cursor="hand2",
        command=command,
    )


def _button_neutral(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        bg=BTN_NEUTRAL_BG,
        fg=BTN_NEUTRAL_FG,
        font=FONT_LABEL,
        activebackground=BTN_NEUTRAL_ACTIVE_BG,
        activeforeground=BTN_NEUTRAL_ACTIVE_FG,
        relief="flat",
        padx=12,
        pady=7,
        cursor="hand2",
        command=command,
    )


def _configure_ttk_styles(root):
    style = ttk.Style(root)
    style.theme_use("default")

    style.configure(
        "TF.Horizontal.TProgressbar",
        troughcolor=PROGRESS_BAR_TROUGH_COLOR,
        background=PROGRESS_BAR_COLOR,
        bordercolor=PROGRESS_BAR_TROUGH_COLOR,
        lightcolor=PROGRESS_BAR_COLOR,
        darkcolor=PROGRESS_BAR_COLOR,
    )

    style.configure(
        "TF.TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_INPUT,
        foreground=FG,
        selectbackground=ACCENT,
        selectforeground="white",
        bordercolor=BORDER,
        arrowcolor=FG,
        relief="flat",
    )


def _find_logo_path():
    images_dir = Path(__file__).parent / "assets" / "images"

    candidates = [
        "caixa.png",
        "logo_caixa.png",
        "logo-caixa.png",
        "caixa_logo.png",
        "logo.png",
        "caixa.gif",
        "logo_caixa.gif",
        "logo.gif",
    ]

    for name in candidates:
        path = images_dir / name
        if path.exists():
            return path

    if images_dir.exists():
        for ext in ("*.png", "*.gif"):
            found = list(images_dir.glob(ext))
            if found:
                return found[0]

    return None

def _load_logo_image(max_height=40):
    """
    Carrega a logo mantendo a proporção original.

    max_height:
        altura máxima desejada em pixels.
    """

    logo_path = _find_logo_path()

    if not logo_path:
        return None

    try:
        image = Image.open(logo_path)

        original_width, original_height = image.size

        ratio = max_height / original_height

        target_width = int(original_width * ratio)
        target_height = int(original_height * ratio)

        image = image.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS
        )

        return ImageTk.PhotoImage(image)

    except Exception as exc:
        print(f"Erro carregando logo: {exc}")
        return None

def _get_application_version() -> str:
    """
    Lê a versão do arquivo VERSION localizado
    na raiz do projeto.

    Exemplo:
        1.2.0
        1.2.0-dev
        2.0.0-beta
    """

    try:
        version_file = (
            Path(__file__)
            .resolve()
            .parents[3]
            / "VERSION"
        )

        return version_file.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        return "dev"

def _bootstrap_auto_update() -> None:
    """Runs updater before opening GUI, without blocking startup on failures."""
    try:
        from testforge.updater import check_and_apply_update

        # project_root = .../AUTOMATA-PRIMUS from .../src/testforge/gui/recorder_launcher.py
        project_root = Path(__file__).resolve().parents[3]
        check_and_apply_update(project_root)
    except Exception:
        # GUI startup must never fail due to update checks.
        pass


# -- Main window ---------------------------------------------------------------


class RecorderLauncher(tk.Tk):
    def __init__(self):
        super().__init__()

        _register_caixa_fonts()

        # força o Tk a recriar a lista de fontes
        self.update()
        self.update_idletasks()

        _configure_caixa_fonts(self)
        _configure_ttk_styles(self)

        title = f"TestForge - {_get_application_version()}"
        self.title(title)
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(620, 720)

        self._proc = None
        self._running = False
        self._progress_tick = 0
        self._progress_job = None
        self._logo_img = None

        # B30: carrega ultimos valores fornecidos para pre-preencher campos
        self._last_values = self._load_last_values()

        self._build_ui()
        self._prefill_from_last_values()
        self._center()

    # -- layout ----------------------------------------------------------------

    def _build_ui(self):
        # Header bar
        tk.Frame(self, bg=CAIXA_BLUE, height=6).pack(fill="x")

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=16, pady=(10, 8))

        logo_path = _find_logo_path()
        if logo_path:
            try:
                #self._logo_img = tk.PhotoImage(file=str(logo_path))
                self._logo_img = _load_logo_image(LOGO_HEIGHT)

                if self._logo_img:

                    logo_frame = tk.Frame(
                        header,
                        bg=BG,
                    )

                    logo_frame.pack(
                        side="right",
                        padx=(0, 10),
                    )

                    tk.Label(
                        logo_frame,
                        image=self._logo_img,
                        bg=BG,
                    ).pack()

                    tk.Label(
                        logo_frame,
                        text="#INTERNO.CAIXA",
                        bg=BG,
                        fg=CAIXA_BLUE,
                        font=FONT_CAPTION,
                    ).pack(pady=(2, 0))

            except Exception:
                self._logo_img = None

        tk.Label(
            header,
            text="TesteForge · Gravador de Testes",
            bg=BG,
            fg=CAIXA_BLUE,
            font=FONT_PAGE_TITLE,
        ).pack(side="left", pady=(6, 0), padx=(0, 10))

        # scrollable main area
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas, bg=BG)
        self._inner_id = canvas.create_window(
            (0, 0),
            window=self._inner,
            anchor="nw",
        )

        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._inner_id, width=e.width),
        )

        # bind mousewheel
        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_wheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        self._build_form(self._inner)

    def _build_form(self, parent):
        pad = {"padx": 12, "pady": (0, 6)}

        # -- Modo Simples: Identificação ---------------------------------------
        card1 = tk.Frame(parent, bg=BG_CARD, padx=20, pady=16)
        card1.pack(fill="x", **pad)

        _section_title(card1, "Identificação da Gravação").pack(fill="x")

        grid1 = tk.Frame(card1, bg=BG_CARD)
        grid1.pack(fill="x", pady=(4, 0))
        grid1.columnconfigure(1, weight=1)

        self.var_url = tk.StringVar()
        self.var_system = tk.StringVar()
        self.var_suite = tk.StringVar()
        self.var_tc = tk.StringVar()
        self.var_name = tk.StringVar()

        url_entry = _entry(grid1, self.var_url)
        _bind_ctrl_v(url_entry)

        _row(grid1, 0, "http/https + URL *", url_entry, req=True)
        _row(grid1, 1, "Sistema", _entry(grid1, self.var_system))
        _row(grid1, 2, "Suite", _entry(grid1, self.var_suite))
        _row(grid1, 3, "Caso de Teste", _entry(grid1, self.var_tc))
        _row(grid1, 4, "Nome do Teste", _entry(grid1, self.var_name))

        # -- Navegador ----------------------------------------------------------
        card_browser = tk.Frame(parent, bg=BG_CARD, padx=16, pady=12)
        card_browser.pack(fill="x", **pad)

        _section_title(card_browser, "Navegador").pack(fill="x")

        brow_grid = tk.Frame(card_browser, bg=BG_CARD)
        brow_grid.pack(fill="x", pady=(4, 0))

        self.var_browser = tk.StringVar(value="chromium")

        tk.Label(
            brow_grid,
            text="Browser",
            bg=BG_CARD,
            fg=CAIXA_BLUE,
            font=FONT_SECTION,
            anchor="e",
            width=16,
        ).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=2)

        _combo(
            brow_grid,
            self.var_browser,
            ["chromium", "chrome", "edge"],
            width=14,
        ).grid(row=0, column=1, sticky="w", pady=2)

        # -- Toggle: Mais Opções -----------------------------------------------
        toggle_frame = tk.Frame(parent, bg=BG)
        toggle_frame.pack(fill="x", padx=12, pady=(0, 0))

        self._advanced_shown = False
        self._advanced_frame = tk.Frame(parent, bg=BG)

        self._toggle_btn = tk.Button(
            toggle_frame,
            text="[+]  Mais Opções",
            bg=BTN_NEUTRAL_BG,
            fg=BTN_NEUTRAL_FG,
            font=FONT_LABEL,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            activebackground=BTN_NEUTRAL_ACTIVE_BG,
            activeforeground=BTN_NEUTRAL_ACTIVE_FG,
            command=self._toggle_advanced,
        )
        self._toggle_btn.pack(side="left")

        # -- Conteúdo avançado -------------------------------------------------
        card_adv = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_adv.pack(fill="x", **pad)

        _section_title(card_adv, "Configurações Avançadas").pack(fill="x")

        adv_grid = tk.Frame(card_adv, bg=BG_CARD)
        adv_grid.pack(fill="x", pady=(4, 0))
        adv_grid.columnconfigure(1, weight=1)

        self.var_app = tk.StringVar()
        self.var_evidence = tk.StringVar(value="light")

        _row(adv_grid, 0, "Aplicação", _entry(adv_grid, self.var_app))

        evid_row = tk.Frame(card_adv, bg=BG_CARD)
        evid_row.pack(fill="x", pady=(2, 0))

        tk.Label(
            evid_row,
            text="Evidência",
            bg=BG_CARD,
            fg=FG_DIM,
            font=FONT_LABEL,
            anchor="e",
            width=16,
        ).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=2)

        _combo(
            evid_row,
            self.var_evidence,
            ["light", "full"],
            width=8,
        ).grid(row=0, column=1, sticky="w", pady=2)

        # -- Opções ------------------------------------------------------------
        card_opts = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_opts.pack(fill="x", **pad)

        _section_title(card_opts, "Opções").pack(fill="x")

        opts = tk.Frame(card_opts, bg=BG_CARD)
        opts.pack(fill="x", pady=(4, 0))

        self.var_headless = tk.BooleanVar()
        self.var_complete = tk.BooleanVar(value=True)
        self.var_no_interact = tk.BooleanVar()
        self.var_validate = tk.BooleanVar(value=True)
        self.var_pilot = tk.BooleanVar(value=True)
        self.var_cdp = tk.BooleanVar(value=True)
        self.var_diagnostic = tk.BooleanVar()
        self.var_pipeline_diag = tk.BooleanVar()

        col0 = tk.Frame(opts, bg=BG_CARD)
        col0.pack(side="left", padx=(0, 24))

        col1 = tk.Frame(opts, bg=BG_CARD)
        col1.pack(side="left")

        for text, var in [
            ("Headless (sem janela)", self.var_headless),
            ("Verificar completude após gravar", self.var_complete),
            ("Sem interação (criar template)", self.var_no_interact),
            ("Captura CDP (trace + AX tree)", self.var_cdp),
        ]:
            _check(col0, text, var).pack(anchor="w", pady=1)

        for text, var in [
            ("Validar antes de marcar como pronto", self.var_validate),
            ("Modo piloto", self.var_pilot),
            ("Modo diagnóstico (só telemetria)", self.var_diagnostic),
            ("Diagnóstico + pipeline (ambos)", self.var_pipeline_diag),
        ]:
            _check(col1, text, var).pack(anchor="w", pady=1)

        # -- Publicação Git ----------------------------------------------------
        card_git = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_git.pack(fill="x", **pad)

        _section_title(card_git, "Publicação Git (opcional)").pack(fill="x")

        tk.Label(
            card_git,
            text="Preencha para enviar a gravação automaticamente ao repositório de testes.",
            bg=BG_CARD,
            fg=FG_DIM,
            font=FONT_CAPTION,
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        git_grid = tk.Frame(card_git, bg=BG_CARD)
        git_grid.pack(fill="x")
        git_grid.columnconfigure(1, weight=1)

        self.var_git_url = tk.StringVar()
        self.var_git_token = tk.StringVar()
        self.var_git_branch = tk.StringVar(value="main")

        _row(git_grid, 0, "URL do repositório", _entry(git_grid, self.var_git_url))
        _row(git_grid, 1, "Token de acesso", _entry(git_grid, self.var_git_token, show="*"))
        _row(git_grid, 2, "Branch", _entry(git_grid, self.var_git_branch, width=20))

        # -- Botões ------------------------------------------------------------
        btn_frame = tk.Frame(parent, bg=BG, pady=6)
        btn_frame.pack(fill="x", padx=12)

        self.btn_start = _button_primary(
            btn_frame,
            "Iniciar Gravação",
            self._start_recording,
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = _button_secondary(
            btn_frame,
            "[STOP]  Parar",
            self._stop_recording,
        )
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_clear = _button_neutral(
            btn_frame,
            "Limpar campos",
            self._clear_fields,
        )
        self.btn_clear.pack(side="left")

        self._progress_var = tk.StringVar(value="Pronto")

        self._progress_bar = ttk.Progressbar(
            btn_frame,
            mode="indeterminate",
            length=220,
            style="TF.Horizontal.TProgressbar",
        )
        self._progress_bar.pack(side="right", padx=(8, 0))

        self._progress_label = tk.Label(
            btn_frame,
            textvariable=self._progress_var,
            bg=GRAY_50,
            fg=CAIXA_BLUE,
            font=FONT_LABEL,
            padx=12,
            pady=4,
        )
        self._progress_label.pack(side="right")

        # -- Log ---------------------------------------------------------------
        log_frame = tk.Frame(parent, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        _section_title_for_log = tk.Frame(log_frame, bg=BG)
        _section_title_for_log.pack(fill="x")

        tk.Label(
            _section_title_for_log,
            text="Log",
            bg=BG,
            fg=CAIXA_BLUE,
            font=FONT_SECTION,
        ).pack(side="left", pady=(8, 2))

        tk.Frame(
            _section_title_for_log,
            bg=BORDER,
            height=1,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.log = scrolledtext.ScrolledText(
            log_frame,
            bg=GRAY_130,
            fg=LOG_FONT_COLOR,
            font=FONT_MONO,
            relief="flat",
            insertbackground=GRAY_130,
            state="disabled",
            height=12,
            highlightthickness=2,
            highlightbackground=BORDER,
            highlightcolor=CAIXA_BLUE,
        )
        self.log.pack(fill="both", expand=True)

    # -- command preview -------------------------------------
        command_frame = tk.Frame(parent, bg=BG)
        command_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        _section_title_for_command = tk.Frame(command_frame, bg=BG)
        _section_title_for_command.pack(fill="x")
    
        self._cmd_var = tk.StringVar()
        tk.Label(
            _section_title_for_command,
            text="Linha de comando",
            bg=BG,
            fg=CAIXA_BLUE,
            font=FONT_SECTION,
        ).pack(side="left", pady=(8, 2))
        
        tk.Frame(
            _section_title_for_command,
            bg=BORDER,
            height=1,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        tk.Label(
            command_frame,
            textvariable=self._cmd_var,
            bg=GRAY_130,
            fg=LOG_FONT_COLOR,
            font=FONT_MONO,
            anchor="w",
            wraplength=1100,
            justify="left",
        ).pack(fill="x", padx=0, pady=(0, 2))

        

    # -- Persistencia de ultimos valores -------------------------------------

    @staticmethod
    def _last_values_path() -> str:
        """Retorna caminho para .testforge/last_values.json."""
        import os
        from testforge.publisher import GitPublisher

        cwd = os.getcwd()
        git_root = GitPublisher._find_git_root(cwd)

        for base in filter(None, [cwd, git_root]):
            candidate = os.path.join(base, ".testforge", "last_values.json")
            if os.path.exists(candidate):
                return candidate

        # fallback: .testforge no git root
        target = os.path.join(git_root or cwd, ".testforge")
        return os.path.join(target, "last_values.json")

    def _load_last_values(self) -> dict:
        """Carrega ultimos valores fornecidos. Retorna {} em caso de erro."""
        import os

        try:
            path = self._last_values_path()
            if not os.path.exists(path):
                return {}

            import json
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_last_values(self) -> None:
        """Salva valores atuais dos campos para preenchimento futuro."""
        try:
            import json
            import os

            data = {
                "system": self.var_system.get().strip(),
                "suite": self.var_suite.get().strip(),
                "test_case": self.var_tc.get().strip(),
            }

            path = self._last_values_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _prefill_from_last_values(self) -> None:
        """Preenche campos com ultimos valores fornecidos."""
        lv = self._last_values

        if lv.get("system"):
            self.var_system.set(lv["system"])

        if lv.get("suite"):
            self.var_suite.set(lv["suite"])

        if lv.get("test_case"):
            self.var_tc.set(lv["test_case"])

    # -- Logic -----------------------------------------------------------------

    def _build_cmd(self):
        cmd = [sys.executable, "-m", "testforge.cli.app", "record"]

        url = self.var_url.get().strip()
        if url:
            cmd.append(url)

        name = self.var_name.get().strip()
        if name:
            cmd += ["--name", name]

        app = self.var_app.get().strip()
        if app:
            cmd += ["--app", app]

        system = self.var_system.get().strip()
        if system:
            cmd += ["--system", system]

        suite = self.var_suite.get().strip()
        if suite:
            cmd += ["--suite", suite]

        tc = self.var_tc.get().strip()
        if tc:
            cmd += ["--test-case", tc]

        browser = self.var_browser.get()
        if browser and browser != "chromium":
            cmd += ["--browser", browser]

        evidence = self.var_evidence.get()
        if evidence and evidence != "light":
            cmd += ["--evidence-level", evidence]

        # B30: GUI ja coleta dados do wizard, nao reprompt no terminal
        cmd.append("--no-wizard")

        if self.var_headless.get():
            cmd.append("--headless")

        if self.var_complete.get():
            cmd.append("--complete")

        if self.var_no_interact.get():
            cmd.append("--no-interactive")

        if self.var_validate.get():
            cmd.append("--validate-before-ready")

        if self.var_pilot.get():
            cmd.append("--pilot-mode")

        # Hotfix 22: CDP default ON; user pode desabilitar. Diagnostic e
        # pipeline-and-diagnostic sao mutuamente exclusivos (o mais recente vence).
        if not self.var_cdp.get():
            cmd.append("--no-cdp-recorder")

        if self.var_pipeline_diag.get():
            cmd.append("--pipeline-and-diagnostic-mode")
        elif self.var_diagnostic.get():
            cmd.append("--diagnostic-mode")

        return cmd

    def _build_env(self):
        import os

        env = os.environ.copy()

        git_url = self.var_git_url.get().strip()
        if git_url:
            env["TESTFORGE_GIT_URL"] = git_url

        git_token = self.var_git_token.get().strip()
        if git_token:
            env["TESTFORGE_GIT_TOKEN"] = git_token

        git_branch = self.var_git_branch.get().strip()
        if git_branch and git_branch != "main":
            env["TESTFORGE_GIT_BRANCH"] = git_branch

        return env

    def _start_recording(self):
        url = self.var_url.get().strip()

        if not url:
            messagebox.showerror(
                "Campo obrigatório",
                "URL é obrigatória para iniciar a gravação.",
            )
            return

        if self._running:
            messagebox.showwarning(
                "Gravação ativa",
                "Uma gravação já está em execução.",
            )
            return

        cmd = self._build_cmd()
        env = self._build_env()

        self._cmd_var.set("$ " + " ".join(cmd))
        self._log_clear()
        self._log(f"Iniciando: {' '.join(cmd)}\n{'-' * 60}\n")

        # B30: persiste ultimos valores para preenchimento futuro
        self._save_last_values()

        self._running = True
        self.btn_start.configure(state="disabled")
        self._set_progress_running(True)

        thread = threading.Thread(
            target=self._run_proc,
            args=(cmd, env),
            daemon=True,
        )
        thread.start()

    def _run_proc(self, cmd, env):
        try:
            self._proc = popen_hidden(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )

            for line in self._proc.stdout:
                self._log(line)

            self._proc.wait()
            rc = self._proc.returncode
            self._log(f"\n{'-' * 60}\nProcesso encerrado (código {rc})\n")

        except FileNotFoundError:
            self._log(
                "[ERRO] testforge não encontrado no PATH. "
                "Execute 'source activate.sh' e tente novamente.\n"
            )
        except Exception as exc:
            self._log(f"[ERRO] {exc}\n")
        finally:
            self._running = False
            self._proc = None
            self.after(0, self._on_process_finished)

    def _toggle_advanced(self):
        """Show/hide advanced options section."""
        self._advanced_shown = not self._advanced_shown

        if self._advanced_shown:
            self._advanced_frame.pack(fill="x", padx=0, pady=0)
            self._toggle_btn.configure(text="[-]  Menos Opções", fg=CAIXA_BLUE)
        else:
            self._advanced_frame.pack_forget()
            self._toggle_btn.configure(text="[+]  Mais Opções", fg=FG_DIM)

        # Recalculate scroll region after toggle
        self._inner.update_idletasks()
        canvas = self._inner.master
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _stop_recording(self):
        if self._proc and self._running:
            self._proc.terminate()
            self._log("\n[GUI] Sinal de parada enviado ao processo.\n")
            self._set_progress_text("Parando")
        else:
            self._log("[GUI] Nenhuma gravação ativa.\n")

    def _clear_fields(self):
        for var in (
            self.var_url,
            self.var_name,
            self.var_app,
            self.var_system,
            self.var_suite,
            self.var_tc,
            self.var_git_url,
            self.var_git_token,
        ):
            var.set("")

        self.var_browser.set("chromium")
        self.var_evidence.set("light")
        self.var_git_branch.set("main")

        for var in (
            self.var_headless,
            self.var_complete,
            self.var_no_interact,
            self.var_validate,
            self.var_pilot,
            self.var_diagnostic,
            self.var_pipeline_diag,
        ):
            var.set(False)

        self.var_cdp.set(True)  # CDP default ON
        self._cmd_var.set("")
        self._log_clear()

    # -- Log helpers -----------------------------------------------------------

    def _log(self, text):
        def _do():
            self.log.configure(state="normal")
            self.log.insert("end", text)
            self.log.see("end")
            self.log.configure(state="disabled")

            lowered = text.lower()

            if "publicando" in lowered:
                self._set_progress_text("Publicando no repositório")
            elif "validando" in lowered:
                self._set_progress_text("Validando gravação")
            elif "normaliza" in lowered or "normalizacao" in lowered:
                self._set_progress_text("Processando gravação")

        self.after(0, _do)

    def _log_clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # -- Misc ------------------------------------------------------------------

    def _center(self):
        self.update_idletasks()

        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        x = (sw - w) // 2
        y = (sh - h) // 2

        self.geometry(f"+{x}+{y}")

    def _set_progress_text(self, base: str):
        if not self._running:
            return

        dots = "." * ((self._progress_tick % 3) + 1)
        self._progress_var.set(f"{base}{dots}")

    def _animate_progress(self):
        if not self._running:
            return

        self._progress_tick += 1
        self._set_progress_text("Processando")
        self._progress_job = self.after(450, self._animate_progress)

    def _set_progress_running(self, running: bool):
        if running:
            self._progress_tick = 0
            self._progress_bar.start(10)
            self._progress_var.set("Processando.")

            if self._progress_job is None:
                self._progress_job = self.after(450, self._animate_progress)
        else:
            self._progress_bar.stop()

            if self._progress_job is not None:
                self.after_cancel(self._progress_job)
                self._progress_job = None

            self._progress_var.set("Pronto")


    def _review_sensitive_submission(self):
        """P0.2-S GUI review. Enabled only by TESTFORGE_SENSITIVE_REVIEW."""
        import os
        if os.getenv("TESTFORGE_SENSITIVE_REVIEW", "0").strip().lower() not in ("1", "true", "yes", "on"):
            return
        recording_id = _sanitize_name(self.var_name.get().strip())
        project_root = Path(__file__).resolve().parents[3]
        rec_dir = project_root / "recordings" / recording_id
        if not rec_dir.is_dir():
            self._log(f"[SEGURANCA] Gravacao nao localizada para revisao: {rec_dir}\n")
            return
        try:
            from testforge.submission import (
                DecisionAction, FindingCategory, FindingDecision, SubmissionDecision,
                prepare_submission, scan_recording,
            )
            scan = scan_recording(rec_dir)
            if not scan.findings:
                messagebox.showinfo("Revisao de dados", "Nenhum dado sensivel detectado. Nenhum envio Git foi executado.")
                return
            counts = {}
            for finding in scan.findings:
                counts[finding.data_type] = counts.get(finding.data_type, 0) + 1
            summary = "\n".join(f"- {kind}: {count}" for kind, count in sorted(counts.items()))
            prompt = (
                f"Foram detectadas {len(scan.findings)} ocorrencias ({scan.blocking_findings} bloqueantes).\n\n"
                f"{summary}\n\n"
                "Sim: preparar copia sanitizada\nNao: cancelar (nenhum arquivo/commit)"
            )
            sanitize = messagebox.askyesno("Dados sensiveis capturados", prompt, icon="warning")
            if not sanitize:
                decision = SubmissionDecision(recording_id=recording_id, environment="DES", cancelled=True)
                report = prepare_submission(rec_dir, project_root / "submissions", decision)
                self._log(f"[SEGURANCA] {report.message}\n")
                return
            decisions = []
            test_findings = [f for f in scan.findings if f.category == FindingCategory.TEST_DATA]
            if test_findings:
                preserve = messagebox.askyesno(
                    "Massa controlada",
                    "Deseja preservar CPF/CNPJ como massa controlada somente neste pacote?\n"
                    "Escolha Nao para sanitizar tambem a massa.", icon="question")
                if preserve:
                    reason = simpledialog.askstring("Justificativa obrigatoria", "Informe a justificativa da massa controlada DES:", parent=self)
                    if not (reason or "").strip():
                        messagebox.showwarning("Cancelado", "Sem justificativa, a massa sera sanitizada.")
                    else:
                        decisions = [FindingDecision(finding_id=f.finding_id, action=DecisionAction.PRESERVE,
                                     confirmed_test_mass=True, justification=reason) for f in test_findings]
            decision = SubmissionDecision(recording_id=recording_id, environment="DES", decisions=decisions)
            report = prepare_submission(rec_dir, project_root / "submissions", decision)
            messagebox.showinfo("Copia preparada", f"Copia sanitizada preparada em:\n{report.output_dir}\n\nNenhum envio Git foi executado.")
            self._log(f"[SEGURANCA] {report.message}: {report.output_dir}\n")
        except Exception as exc:
            messagebox.showerror("Revisao bloqueada", f"Nao foi possivel preparar a submissao. Nenhum envio foi executado.\n\n{exc}")
            self._log(f"[SEGURANCA] FALHA FECHADA: {exc}\n")

    def _on_process_finished(self):
        self.btn_start.configure(state="normal")
        self._set_progress_running(False)
        self.after(0, self._review_sensitive_submission)


def main():
    _bootstrap_auto_update()
    app = RecorderLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()

