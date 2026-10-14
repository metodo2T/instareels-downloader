import os
import sys
import threading
import subprocess
import time
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

from downloader import InstagramDownloader

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class InstaReelsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("InstaReels Studio - Downloader & Edição")
        self.geometry("740x680")
        self.minsize(680, 600)

        # Base directories
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.videos_dir = os.path.join(self.app_dir, "videos_baixados")
        os.makedirs(self.videos_dir, exist_ok=True)

        # Set window icon
        icon_path = os.path.join(self.app_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.downloader = InstagramDownloader(output_dir=self.videos_dir)
        self.is_downloading = False

        self._build_ui()
        self._refresh_history()

    def _build_ui(self):
        # Main padding container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=20)

        # 1. Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="#181a24", corner_radius=14, border_width=1, border_color="#2c3040")
        header_frame.pack(fill="x", pady=(0, 16), ipady=10)

        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(fill="x", padx=18, pady=4)

        title_label = ctk.CTkLabel(
            header_content,
            text="🎬 InstaReels Studio",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_content,
            text="Cole o link do Reels do Instagram para baixar na melhor qualidade e preparar para clipar.",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # 2. Input Section Card
        input_card = ctk.CTkFrame(self.main_container, fg_color="#1e2230", corner_radius=14, border_width=1, border_color="#2d3345")
        input_card.pack(fill="x", pady=(0, 16), padx=0, ipady=12)

        input_inner = ctk.CTkFrame(input_card, fg_color="transparent")
        input_inner.pack(fill="x", padx=16, pady=4)

        url_label = ctk.CTkLabel(
            input_inner,
            text="Link do Vídeo ou Reel:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e5e7eb"
        )
        url_label.pack(anchor="w", pady=(0, 6))

        # Input Row
        entry_row = ctk.CTkFrame(input_inner, fg_color="transparent")
        entry_row.pack(fill="x", pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="https://www.instagram.com/reel/...",
            font=ctk.CTkFont(size=13),
            height=42,
            corner_radius=10,
            fg_color="#12141c",
            border_color="#374151"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.paste_btn = ctk.CTkButton(
            entry_row,
            text="📋 Colar",
            width=80,
            height=42,
            corner_radius=10,
            fg_color="#374151",
            hover_color="#4b5563",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            entry_row,
            text="✕",
            width=42,
            height=42,
            corner_radius=10,
            fg_color="#2b3040",
            hover_color="#ef4444",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.url_entry.delete(0, "end")
        )
        self.clear_btn.pack(side="left")

        # Action Button
        self.download_btn = ctk.CTkButton(
            input_inner,
            text="⬇  BAIXAR VÍDEO AGORA",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#e1306c",
            hover_color="#c1275d",
            command=self._start_download
        )
        self.download_btn.pack(fill="x", pady=(4, 8))

        # Progress & Status
        self.progress_bar = ctk.CTkProgressBar(input_inner, height=8, corner_radius=4)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(4, 6))

        self.status_label = ctk.CTkLabel(
            input_inner,
            text="Pronto para baixar.",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        self.status_label.pack(anchor="w")

        # 3. Destination Directory Row
        dir_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(0, 14))

        self.dir_label = ctk.CTkLabel(
            dir_frame,
            text=f"📁 Salvar em: {self.videos_dir}",
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af"
        )
        self.dir_label.pack(side="left", fill="x", expand=True)

        self.open_folder_btn = ctk.CTkButton(
            dir_frame,
            text="Abrir Pasta",
            width=90,
            height=28,
            corner_radius=8,
            fg_color="#2b3040",
            hover_color="#374151",
            font=ctk.CTkFont(size=11),
            command=self._open_folder
        )
        self.open_folder_btn.pack(side="right", padx=(6, 0))

        self.change_folder_btn = ctk.CTkButton(
            dir_frame,
            text="Alterar",
            width=70,
            height=28,
            corner_radius=8,
            fg_color="#2b3040",
            hover_color="#374151",
            font=ctk.CTkFont(size=11),
            command=self._change_folder
        )
        self.change_folder_btn.pack(side="right")

        # 4. History / Downloaded Files Section
        history_header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        history_header.pack(fill="x", pady=(0, 6))

        h_title = ctk.CTkLabel(
            history_header,
            text="Vídeos Baixados Recentes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        h_title.pack(side="left")

        refresh_btn = ctk.CTkButton(
            history_header,
            text="🔄 Atualizar",
            width=75,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#2b3040",
            font=ctk.CTkFont(size=11),
            command=self._refresh_history
        )
        refresh_btn.pack(side="right")

        self.history_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="#181a24",
            corner_radius=12,
            border_width=1,
            border_color="#2c3040"
        )
        self.history_scroll.pack(fill="both", expand=True)

    def _paste_clipboard(self):
        try:
            content = self.clipboard_get()
            if content:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, content.strip())
                self.status_label.configure(text="Link colado da área de transferência.", text_color="#60a5fa")
        except Exception:
            pass

    def _open_folder(self):
        if os.path.exists(self.videos_dir):
            if sys.platform == "win32":
                os.startfile(self.videos_dir)
            else:
                subprocess.run(["xdg-open", self.videos_dir])

    def _change_folder(self):
        new_dir = filedialog.askdirectory(initialdir=self.videos_dir, title="Selecione a pasta para salvar os vídeos")
        if new_dir:
            self.videos_dir = new_dir
            self.downloader.output_dir = new_dir
            self.dir_label.configure(text=f"📁 Salvar em: {self.videos_dir}")
            self._refresh_history()

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Por favor, cole um link do Instagram antes de baixar.")
            return

        if "instagram.com" not in url:
            messagebox.showwarning("Link Inválido", "O link informado não parece ser do Instagram.")
            return

        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ BAIXANDO VÍDEO...")
        self.progress_bar.set(0.05)
        self.status_label.configure(text="Iniciando download...", text_color="#60a5fa")

        # Run download on a background worker thread
        threading.Thread(target=self._download_worker, args=(url,), daemon=True).start()

    def _download_worker(self, url):
        def progress_cb(percent, msg):
            self.after(0, lambda: self._update_progress(percent, msg))

        result = self.downloader.download_video(url, progress_callback=progress_cb)

        self.after(0, lambda: self._download_finished(result))

    def _update_progress(self, percent, msg):
        self.progress_bar.set(percent / 100.0)
        self.status_label.configure(text=msg, text_color="#60a5fa")

    def _download_finished(self, result):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇  BAIXAR VÍDEO AGORA")

        if result.get("success"):
            self.progress_bar.set(1.0)
            self.status_label.configure(
                text=f"✓ Concluído: {result['filename']} ({result['size_mb']} MB)",
                text_color="#10b981"
            )
            self.url_entry.delete(0, "end")
            self._refresh_history()
        else:
            self.progress_bar.set(0)
            err = result.get("error", "Erro desconhecido")
            self.status_label.configure(text=f"Erro: {err}", text_color="#ef4444")
            messagebox.showerror("Falha no Download", f"Não foi possível baixar o vídeo:\n\n{err}")

    def _refresh_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not os.path.exists(self.videos_dir):
            return

        files = [
            f for f in os.listdir(self.videos_dir)
            if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm'))
        ]

        if not files:
            empty_lbl = ctk.CTkLabel(
                self.history_scroll,
                text="Nenhum vídeo baixado ainda.\nCole um link acima para começar!",
                font=ctk.CTkFont(size=12),
                text_color="#6b7280",
                justify="center"
            )
            empty_lbl.pack(pady=30)
            return

        # Sort by modification time (most recent first)
        files.sort(
            key=lambda f: os.path.getmtime(os.path.join(self.videos_dir, f)),
            reverse=True
        )

        for filename in files[:30]:
            filepath = os.path.join(self.videos_dir, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            mtime = os.path.getmtime(filepath)
            date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")

            item_frame = ctk.CTkFrame(
                self.history_scroll,
                fg_color="#1f2330",
                corner_radius=10,
                border_width=1,
                border_color="#2b3040"
            )
            item_frame.pack(fill="x", pady=4, padx=4, ipady=4)

            # Left side: File info
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=4)

            name_lbl = ctk.CTkLabel(
                info_frame,
                text=filename,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#e5e7eb",
                anchor="w"
            )
            name_lbl.pack(fill="x")

            meta_lbl = ctk.CTkLabel(
                info_frame,
                text=f"{size_mb:.1f} MB  •  {date_str}",
                font=ctk.CTkFont(size=11),
                text_color="#9ca3af",
                anchor="w"
            )
            meta_lbl.pack(fill="x")

            # Right side: Action buttons
            actions_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            actions_frame.pack(side="right", padx=10)

            play_btn = ctk.CTkButton(
                actions_frame,
                text="▶ Assistir",
                width=80,
                height=30,
                corner_radius=8,
                fg_color="#374151",
                hover_color="#4b5563",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=filepath: self._play_video(p)
            )
            play_btn.pack(side="left", padx=4)

    def _play_video(self, filepath):
        if os.path.exists(filepath):
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                subprocess.run(["xdg-open", filepath])

if __name__ == "__main__":
    app = InstaReelsApp()
    app.mainloop()
