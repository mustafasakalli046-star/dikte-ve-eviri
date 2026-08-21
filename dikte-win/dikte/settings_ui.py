"""Minimal ayarlar penceresi (Tkinter - stdlib, PyQt6'ya gerek yok).

Orijinal projedeki sekmeli PyQt6 penceresinin cok sadelestirilmis hali:
tek pencerede etiket + giris alanlari, "Kaydet" ve "Kapat".
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import config as cfgmod


class SettingsWindow:
    def __init__(self, cfg: cfgmod.Config, on_save=None):
        self.cfg = cfg
        self.on_save = on_save or (lambda c: None)
        self.root = tk.Tk()
        self.root.title("Dikte - Ayarlar")
        self.root.geometry("520x640")
        self._vars: dict[str, tk.Variable] = {}
        self._build()

    def _row(self, parent, label: str, key: str, default: str, row: int, is_bool: bool = False) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        if is_bool:
            var = tk.BooleanVar(value=bool(default))
            ttk.Checkbutton(parent, variable=var).grid(row=row, column=1, sticky="w", padx=8, pady=4)
        else:
            var = tk.StringVar(value=str(default))
            ttk.Entry(parent, textvariable=var, width=38).grid(row=row, column=1, sticky="w", padx=8, pady=4)
        self._vars[key] = var

    def _build(self) -> None:
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        general = ttk.Frame(nb)
        nb.add(general, text="Genel")
        r = 0
        for label, key in [
            ("Kayit kisayolu", "record_hotkey"),
            ("Iptal kisayolu", "cancel_hotkey"),
            ("Ceviri kisayolu (Ctrl+V yerine varsayilan Ctrl+Alt+V)", "translate_hotkey"),
            ("Arayuz dili (tr/en)", "language"),
        ]:
            self._row(general, label, key, getattr(self.cfg, key), r)
            r += 1

        api = ttk.Frame(nb)
        nb.add(api, text="API ve Modeller")
        r = 0
        for label, key in [
            ("Transkripsiyon (local/openai/groq)", "transcriber"),
            ("Yerel whisper.cpp sunucu URL", "whisper_server_url"),
            ("OpenAI transkripsiyon modeli", "transcribe_model"),
            ("Temizlik saglayicisi (local/openrouter)", "cleanup_provider"),
            ("Yerel llama.cpp sunucu URL", "llama_server_url"),
            ("OpenRouter modeli", "openrouter_model"),
            ("OpenAI API anahtari", "openai_api_key"),
            ("Groq API anahtari", "groq_api_key"),
            ("OpenRouter API anahtari", "openrouter_api_key"),
        ]:
            self._row(api, label, key, getattr(self.cfg, key), r)
            r += 1
        self._row(api, "Temizlik acik mi", "cleanup_enabled", self.cfg.cleanup_enabled, r, is_bool=True)
        r += 1

        agent = ttk.Frame(nb)
        nb.add(agent, text="Ajan")
        r = 0
        for label, key in [
            ("Ajan saglayicisi (claude/codex/openrouter)", "agent_provider"),
            ("Ajan calisma dizini", "agent_working_dir"),
        ]:
            self._row(agent, label, key, getattr(self.cfg, key), r)
            r += 1

        vad_tab = ttk.Frame(nb)
        nb.add(vad_tab, text="Sessizlik (VAD)")
        r = 0
        for label, key in [
            ("Yukselme esigi (dB)", "vad_rise_db"),
            ("Minimum sure (s)", "vad_min_duration_s"),
            ("Mutlak taban (dBFS)", "vad_floor_dbfs"),
        ]:
            self._row(vad_tab, label, key, getattr(self.cfg, key), r)
            r += 1

        gloss = ttk.Frame(nb)
        nb.add(gloss, text="Sozluk")
        ttk.Label(gloss, text="Ozel isimler (virgulle ayirin):").pack(anchor="w", padx=8, pady=4)
        self._glossary_text = tk.Text(gloss, height=10, width=50)
        self._glossary_text.insert("1.0", ", ".join(self.cfg.glossary))
        self._glossary_text.pack(padx=8, pady=4, fill="both", expand=True)

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Kaydet", command=self._save).pack(side="left")
        ttk.Button(btns, text="Kapat", command=self.root.destroy).pack(side="left", padx=8)

    def _save(self) -> None:
        for key, var in self._vars.items():
            current = getattr(self.cfg, key)
            value = var.get()
            if isinstance(current, bool):
                setattr(self.cfg, key, bool(value))
            elif isinstance(current, float):
                try:
                    setattr(self.cfg, key, float(value))
                except ValueError:
                    pass
            elif isinstance(current, int):
                try:
                    setattr(self.cfg, key, int(value))
                except ValueError:
                    pass
            else:
                setattr(self.cfg, key, value)

        glossary_raw = self._glossary_text.get("1.0", "end").strip()
        self.cfg.glossary = [g.strip() for g in glossary_raw.split(",") if g.strip()]

        cfgmod.save_config(self.cfg)
        self.on_save(self.cfg)

    def show(self) -> None:
        self.root.mainloop()
