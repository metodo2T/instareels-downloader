import os
import sys
import re
import time
import shutil
import imageio_ffmpeg
import yt_dlp

class InstagramDownloader:
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos_baixados")
        else:
            self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)
        self.ffmpeg_path = self._ensure_ffmpeg_binary()

    def _ensure_ffmpeg_binary(self):
        """
        Ensures an executable named 'ffmpeg' (or 'ffmpeg.exe') exists so yt-dlp can find it.
        """
        # 1. Check if ffmpeg is already on system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        # 2. Use imageio_ffmpeg binary and make sure an alias named 'ffmpeg' exists
        try:
            raw_exe = imageio_ffmpeg.get_ffmpeg_exe()
            raw_dir = os.path.dirname(raw_exe)
            clean_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            target_exe = os.path.join(raw_dir, clean_name)

            if not os.path.exists(target_exe):
                try:
                    shutil.copyfile(raw_exe, target_exe)
                    # make executable on linux
                    if os.name != "nt":
                        os.chmod(target_exe, 0o755)
                except Exception as e:
                    print(f"Aviso ao copiar ffmpeg: {e}")
                    target_exe = raw_exe

            # Prepend raw_dir to PATH so subprocesses find ffmpeg
            if raw_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = raw_dir + os.pathsep + os.environ.get("PATH", "")

            return target_exe
        except Exception as e:
            print(f"Erro ao obter imageio_ffmpeg: {e}")
            return "ffmpeg"

    def extract_shortcode(self, url):
        match = re.search(r'/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)', url)
        return match.group(1) if match else None

    def clean_url(self, url):
        match = re.search(r'(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1) + "/"
        return url.strip()

    def download_video(self, url, progress_callback=None):
        """
        Downloads video and audio merged into standard H.264 / AAC MP4.
        """
        url = self.clean_url(url)
        shortcode = self.extract_shortcode(url) or f"video_{int(time.time())}"
        
        out_template = os.path.join(self.output_dir, f"Reel_{shortcode}_%(id)s.%(ext)s")

        def ydl_hook(d):
            if progress_callback:
                status = d.get('status')
                if status == 'downloading':
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    percent = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 0.0
                    progress_callback(percent, f"Baixando: {percent:.1f}%")
                elif status == 'finished':
                    progress_callback(100.0, "Juntando áudio e vídeo em MP4...")

        ydl_opts = {
            'outtmpl': out_template,
            # Best format: prioritize AVC/H.264 for mobile compatibility (iPhone/Android)
            'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [ydl_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if progress_callback:
                    progress_callback(5.0, "Conectando ao Instagram...")

                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

                base, _ = os.path.splitext(downloaded_file)
                mp4_file = base + ".mp4"
                final_file = mp4_file if os.path.exists(mp4_file) else downloaded_file

                file_size_mb = os.path.getsize(final_file) / (1024 * 1024) if os.path.exists(final_file) else 0

                return {
                    "success": True,
                    "filepath": final_file,
                    "filename": os.path.basename(final_file),
                    "shortcode": shortcode,
                    "title": info.get('title') or f"Reel {shortcode}",
                    "size_mb": round(file_size_mb, 2)
                }

        except Exception as e:
            err_msg = str(e)
            if "Private video" in err_msg or "login" in err_msg.lower():
                err_clean = "Este vídeo é de uma conta privada ou requer login."
            elif "not found" in err_msg.lower():
                err_clean = "Vídeo não encontrado ou link incorreto."
            else:
                err_clean = f"Erro no download: {err_msg[:120]}"

            return {
                "success": False,
                "error": err_clean
            }
