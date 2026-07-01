"""TestForge Recorder GUI — tkinter launcher, zero external deps."""
import subprocess
import sys
import threading

try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
except ModuleNotFoundError:
    sys.exit(
        "[TestForge GUI] tkinter não encontrado.\n"
        "  Windows: reinstale Python de python.org (marque 'tcl/tk').\n"
        "  Linux:   sudo apt install python3-tk   (Debian/Ubuntu)\n"
        "           sudo dnf install python3-tkinter  (RHEL/Fedora)\n"
        "           sudo emerge dev-tcltk/tk  (Gentoo)\n"
    )


# -- Palette ------------------------------------------------------------------
BG        = "#1e1e2e"
BG_CARD   = "#2a2a3e"
BG_INPUT  = "#313149"
FG        = "#cdd6f4"
FG_DIM    = "#6c7086"
FG_REQ    = "#f38ba8"
ACCENT    = "#89b4fa"
ACCENT2   = "#a6e3a1"
BTN_START = "#89dceb"
BTN_CLEAR = "#585b70"
BORDER    = "#45475a"


# -- Helpers -------------------------------------------------------------------

def _entry(parent, textvariable, width=40, show=None):
    kw = {}
    if show:
        kw["show"] = show
    e = tk.Entry(parent, textvariable=textvariable, width=width,
                 bg=BG_INPUT, fg=FG, insertbackground=FG,
                 relief="flat", highlightthickness=1,
                 highlightcolor=ACCENT, highlightbackground=BORDER,
                 font=("Segoe UI", 9), **kw)
    return e


def _combo(parent, textvariable, values, width=20):
    style = ttk.Style(parent)
    style.theme_use("default")
    style.configure("TF.TCombobox",
                    fieldbackground=BG_INPUT, background=BG_INPUT,
                    foreground=FG, selectbackground=ACCENT,
                    selectforeground=BG, bordercolor=BORDER,
                    arrowcolor=FG, relief="flat")
    style.map("TF.TCombobox",
              fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", FG)],
              selectbackground=[("readonly", ACCENT)],
              selectforeground=[("readonly", BG)])
    c = ttk.Combobox(parent, textvariable=textvariable, values=values,
                     width=width, state="readonly", style="TF.TCombobox",
                     font=("Segoe UI", 9))
    return c


def _check(parent, text, variable):
    return tk.Checkbutton(parent, text=text, variable=variable,
                          bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                          activebackground=BG_CARD, activeforeground=FG,
                          font=("Segoe UI", 9), anchor="w",
                          highlightthickness=0)


def _section_title(parent, text):
    f = tk.Frame(parent, bg=BG_CARD)
    tk.Label(f, text=text, bg=BG_CARD, fg=ACCENT,
             font=("Segoe UI", 9, "bold")).pack(side="left", pady=(8, 2))
    tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                          expand=True, padx=(6, 0))
    return f


def _row(grid, row, label, widget, req=False):
    color = FG_REQ if req else FG_DIM
    tk.Label(grid, text=label, bg=BG_CARD, fg=color,
             font=("Segoe UI", 9), anchor="e", width=16
             ).grid(row=row, column=0, sticky="e", padx=(0, 6), pady=2)
    widget.grid(row=row, column=1, sticky="ew", pady=2)


# -- Main window ---------------------------------------------------------------

class RecorderLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("testforge")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(620, 720)

        self._proc = None
        self._running = False

        self._build_ui()
        self._center()

    # -- layout ----------------------------------------------------------------

    def _build_ui(self):
        # header bar
        tk.Frame(self, bg=ACCENT, height=4).pack(fill="x")
        tk.Label(self, text="TestForge  ·  Gravador de Testes",
                 bg=BG, fg=ACCENT, font=("Segoe UI", 13, "bold"),
                 pady=10).pack(fill="x", padx=16)

        # scrollable main area
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas, bg=BG)
        self._inner_id = canvas.create_window((0, 0), window=self._inner,
                                              anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: canvas.configure(
                             scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._inner_id,
                                                width=e.width))

        # bind mousewheel
        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_wheel)
        canvas.bind_all("<Button-4>",
                        lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>",
                        lambda e: canvas.yview_scroll(1, "units"))

        self._build_form(self._inner)

    def _build_form(self, parent):
        pad = {"padx": 12, "pady": (0, 6)}

        # -- Modo Simples: Identificação ---------------------------------------
        card1 = tk.Frame(parent, bg=BG_CARD, padx=16, pady=12)
        card1.pack(fill="x", **pad)
        _section_title(card1, "Identificação da Gravação").pack(fill="x")

        grid1 = tk.Frame(card1, bg=BG_CARD)
        grid1.pack(fill="x", pady=(4, 0))
        grid1.columnconfigure(1, weight=1)

        self.var_url  = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_suite  = tk.StringVar()
        self.var_tc     = tk.StringVar()

        _row(grid1, 0, "URL *",         _entry(grid1, self.var_url),  req=True)
        _row(grid1, 1, "Nome",          _entry(grid1, self.var_name))
        _row(grid1, 2, "Suite",         _entry(grid1, self.var_suite))
        _row(grid1, 3, "Caso de Teste", _entry(grid1, self.var_tc))

        # -- Navegador (sempre visível) ----------------------------------------
        card_browser = tk.Frame(parent, bg=BG_CARD, padx=16, pady=12)
        card_browser.pack(fill="x", **pad)
        _section_title(card_browser, "Navegador").pack(fill="x")

        brow_grid = tk.Frame(card_browser, bg=BG_CARD)
        brow_grid.pack(fill="x", pady=(4, 0))

        self.var_browser = tk.StringVar(value="chromium")
        tk.Label(brow_grid, text="Browser", bg=BG_CARD, fg=ACCENT,
                 font=("Segoe UI", 9, "bold"), anchor="e", width=16
                 ).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=2)
        _combo(brow_grid, self.var_browser, ["chromium", "chrome", "edge"],
               width=14).grid(row=0, column=1, sticky="w", pady=2)

        # -- Toggle: Mais Opções -----------------------------------------------
        toggle_frame = tk.Frame(parent, bg=BG)
        toggle_frame.pack(fill="x", padx=12, pady=(0, 0))

        self._advanced_shown = False
        self._advanced_frame = tk.Frame(parent, bg=BG)

        arrow = "▼"
        self._toggle_btn = tk.Button(
            toggle_frame, text=f"{arrow}  Mais Opções",
            bg=BG_CARD, fg=FG_DIM, font=("Segoe UI", 9),
            relief="flat", padx=12, pady=4, cursor="hand2",
            activebackground=BORDER, activeforeground=ACCENT,
            command=self._toggle_advanced,
        )
        self._toggle_btn.pack(side="left")

        # -- Conteúdo avançado (inicia oculto) ---------------------------------
        # Tudo dentro de self._advanced_frame que é pack/forget conforme toggle

        # -- Aplicação / Sistema / Evidência (avançado) ------------------------
        card_adv = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_adv.pack(fill="x", **pad)
        _section_title(card_adv, "Configurações Avançadas").pack(fill="x")

        adv_grid = tk.Frame(card_adv, bg=BG_CARD)
        adv_grid.pack(fill="x", pady=(4, 0))
        adv_grid.columnconfigure(1, weight=1)

        self.var_app    = tk.StringVar()
        self.var_system = tk.StringVar()
        self.var_evidence = tk.StringVar(value="light")

        _row(adv_grid, 0, "Aplicação",  _entry(adv_grid, self.var_app))
        _row(adv_grid, 1, "Sistema",    _entry(adv_grid, self.var_system))

        evid_row = tk.Frame(card_adv, bg=BG_CARD)
        evid_row.pack(fill="x", pady=(2, 0))
        tk.Label(evid_row, text="Evidência", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), anchor="e", width=16
                 ).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=2)
        _combo(evid_row, self.var_evidence, ["light", "full"],
               width=8).grid(row=0, column=1, sticky="w", pady=2)

        # -- Opções (avançado) -------------------------------------------------
        card_opts = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_opts.pack(fill="x", **pad)
        _section_title(card_opts, "Opções").pack(fill="x")

        opts = tk.Frame(card_opts, bg=BG_CARD)
        opts.pack(fill="x", pady=(4, 0))

        self.var_headless    = tk.BooleanVar()
        self.var_complete    = tk.BooleanVar()
        self.var_no_interact = tk.BooleanVar()
        self.var_validate    = tk.BooleanVar()
        self.var_pilot       = tk.BooleanVar()
        # Hotfix 22: CDP + diagnostic mode exposed no GUI. CDP eh default ON.
        self.var_cdp         = tk.BooleanVar(value=True)
        self.var_diagnostic  = tk.BooleanVar()
        self.var_pipeline_diag = tk.BooleanVar()

        col0 = tk.Frame(opts, bg=BG_CARD)
        col0.pack(side="left", padx=(0, 24))
        col1 = tk.Frame(opts, bg=BG_CARD)
        col1.pack(side="left")

        for text, var in [
            ("Headless (sem janela)",           self.var_headless),
            ("Verificar completude após gravar", self.var_complete),
            ("Sem interação (criar template)",   self.var_no_interact),
            ("Captura CDP (trace + AX tree)",    self.var_cdp),
        ]:
            _check(col0, text, var).pack(anchor="w", pady=1)
        for text, var in [
            ("Validar antes de marcar como pronto", self.var_validate),
            ("Modo piloto",                          self.var_pilot),
            ("Modo diagnóstico (só telemetria)",     self.var_diagnostic),
            ("Diagnóstico + pipeline (ambos)",       self.var_pipeline_diag),
        ]:
            _check(col1, text, var).pack(anchor="w", pady=1)

        # -- Publicação Git (avançado) -----------------------------------------
        card_git = tk.Frame(self._advanced_frame, bg=BG_CARD, padx=16, pady=12)
        card_git.pack(fill="x", **pad)
        _section_title(card_git, "Publicação Git (opcional)").pack(fill="x")

        tk.Label(card_git,
                 text="Preencha para enviar a gravação automaticamente ao repositório de testes.",
                 bg=BG_CARD, fg=FG_DIM, font=("Segoe UI", 8),
                 anchor="w").pack(fill="x", pady=(0, 4))

        git_grid = tk.Frame(card_git, bg=BG_CARD)
        git_grid.pack(fill="x")
        git_grid.columnconfigure(1, weight=1)

        self.var_git_url    = tk.StringVar()
        self.var_git_token  = tk.StringVar()
        self.var_git_branch = tk.StringVar(value="main")

        _row(git_grid, 0, "URL do repositório",
             _entry(git_grid, self.var_git_url))
        _row(git_grid, 1, "Token de acesso",
             _entry(git_grid, self.var_git_token, show="*"))
        _row(git_grid, 2, "Branch",
             _entry(git_grid, self.var_git_branch, width=20))

        # -- Botões ------------------------------------------------------------
        btn_frame = tk.Frame(parent, bg=BG, pady=6)
        btn_frame.pack(fill="x", padx=12)

        self.btn_start = tk.Button(
            btn_frame, text="[PLAY]  Iniciar Gravação",
            bg=BTN_START, fg=BG, font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6, cursor="hand2",
            activebackground=ACCENT2, activeforeground=BG,
            command=self._start_recording,
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="[STOP]  Parar",
            bg=BTN_CLEAR, fg=FG, font=("Segoe UI", 10),
            relief="flat", padx=12, pady=6, cursor="hand2",
            activebackground=BORDER, activeforeground=FG,
            command=self._stop_recording,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Limpar campos",
            bg=BG_CARD, fg=FG_DIM, font=("Segoe UI", 9),
            relief="flat", padx=12, pady=6, cursor="hand2",
            activebackground=BORDER, activeforeground=FG,
            command=self._clear_fields,
        ).pack(side="left")

        # command preview
        self._cmd_var = tk.StringVar()
        tk.Label(parent, textvariable=self._cmd_var, bg=BG, fg=FG_DIM,
                 font=("Courier New", 8), anchor="w", wraplength=590,
                 justify="left").pack(fill="x", padx=14, pady=(0, 2))

        # -- Log --------------------------------------------------------------
        log_frame = tk.Frame(parent, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        tk.Label(log_frame, text="Log", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        self.log = scrolledtext.ScrolledText(
            log_frame, bg="#11111b", fg=ACCENT2,
            font=("Courier New", 8), relief="flat",
            insertbackground=FG, state="disabled",
            height=12,
        )
        self.log.pack(fill="both", expand=True)

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
            messagebox.showerror("Campo obrigatório",
                                 "URL é obrigatória para iniciar a gravação.")
            return

        if self._running:
            messagebox.showwarning("Gravação ativa",
                                   "Uma gravação já está em execução.")
            return

        cmd = self._build_cmd()
        env = self._build_env()
        self._cmd_var.set("$ " + " ".join(cmd))
        self._log_clear()
        self._log(f"Iniciando: {' '.join(cmd)}\n{'-'*60}\n")

        self._running = True
        self.btn_start.configure(state="disabled")
        thread = threading.Thread(target=self._run_proc,
                                  args=(cmd, env), daemon=True)
        thread.start()

    def _run_proc(self, cmd, env):
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            for line in self._proc.stdout:
                self._log(line)
            self._proc.wait()
            rc = self._proc.returncode
            self._log(f"\n{'-'*60}\nProcesso encerrado (código {rc})\n")
        except FileNotFoundError:
            self._log("[ERRO] testforge não encontrado no PATH. "
                      "Execute 'source activate.sh' e tente novamente.\n")
        except Exception as exc:
            self._log(f"[ERRO] {exc}\n")
        finally:
            self._running = False
            self._proc = None
            self.after(0, lambda: self.btn_start.configure(state="normal"))

    def _toggle_advanced(self):
        """Show/hide advanced options section."""
        self._advanced_shown = not self._advanced_shown
        if self._advanced_shown:
            self._advanced_frame.pack(fill="x", padx=0, pady=0)
            self._toggle_btn.configure(text="▲  Menos Opções", fg=ACCENT)
        else:
            self._advanced_frame.pack_forget()
            self._toggle_btn.configure(text="▼  Mais Opções", fg=FG_DIM)
        # Recalculate scroll region after toggle
        self._inner.update_idletasks()
        canvas = self._inner.master
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _stop_recording(self):
        if self._proc and self._running:
            self._proc.terminate()
            self._log("\n[GUI] Sinal de parada enviado ao processo.\n")
        else:
            self._log("[GUI] Nenhuma gravação ativa.\n")

    def _clear_fields(self):
        for var in (self.var_url, self.var_name, self.var_app,
                    self.var_system, self.var_suite, self.var_tc,
                    self.var_git_url, self.var_git_token):
            var.set("")
        self.var_browser.set("chromium")
        self.var_evidence.set("light")
        self.var_git_branch.set("main")
        for var in (self.var_headless, self.var_complete, self.var_no_interact,
                    self.var_validate, self.var_pilot,
                    self.var_diagnostic, self.var_pipeline_diag):
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
        self.after(0, _do)

    def _log_clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # -- Misc ------------------------------------------------------------------

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")


def main():
    app = RecorderLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
