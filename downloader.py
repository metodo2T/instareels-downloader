import os
import sys
import re
import time
import shutil
import subprocess
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
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        try:
            raw_exe = imageio_ffmpeg.get_ffmpeg_exe()
            raw_dir = os.path.dirname(raw_exe)
            clean_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            target_exe = os.path.join(raw_dir, clean_name)

            if not os.path.exists(target_exe):
                try:
                    shutil.copyfile(raw_exe, target_exe)
                    if os.name != "nt":
                        os.chmod(target_exe, 0o755)
                except Exception as e:
                    target_exe = raw_exe

            if raw_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = raw_dir + os.pathsep + os.environ.get("PATH", "")

            return target_exe
        except Exception:
            return "ffmpeg"

    def extract_shortcode(self, url):
        match = re.search(r'/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)', url)
        return match.group(1) if match else None

    def clean_url(self, url):
        match = re.search(r'(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1) + "/"
        return url.strip()

    def _ensure_h264_compatibility(self, filepath):
        """
        Inspects the video file. If it uses VP9, AV1, or lacks video stream,
        re-encodes to H.264 (avc1) + AAC for 100% iPhone/Android compatibility.
        """
        if not os.path.exists(filepath):
            return filepath

        try:
            # Check video stream codecs using ffmpeg -i
            probe_cmd = [self.ffmpeg_path, "-i", filepath]
            probe_res = subprocess.run(probe_cmd, stderr=subprocess.PIPE, text=True, errors="ignore")
            probe_text = probe_res.stderr

            needs_transcode = False
            # If video has VP9 or AV1, iPhone CANNOT play the video (only audio plays!)
            if "Video: vp9" in probe_text or "Video: av01" in probe_text or "Video: av1" in probe_text:
                needs_transcode = True
            elif "Video:" not in probe_text:
                needs_transcode = True

            if needs_transcode:
                print(f"[InstagramDownloader] Detectado codec incompatível (VP9/AV1). Convertendo para H.264 Universal...")
                temp_out = filepath.replace(".mp4", "_h264.mp4")
                convert_cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", filepath,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "22",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    temp_out
                ]
                subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                if os.path.exists(temp_out) and os.path.getsize(temp_out) > 1000:
                    os.replace(temp_out, filepath)
                    print(f"[InstagramDownloader] Vídeo convertido com sucesso para H.264!")
        except Exception as e:
            print(f"[InstagramDownloader] Aviso na conversão H.264: {e}")

        return filepath

    def download_video(self, url, progress_callback=None):
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
                    progress_callback(95.0, "Otimizando vídeo para celular (H.264)...")

        # Prioritize H.264 (avc1) first, fallback to best
        ydl_opts = {
            'outtmpl': out_template,
            'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [ydl_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
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

                # Guarantee H.264 format so video always appears on iPhone & Android
                final_file = self._ensure_h264_compatibility(final_file)

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
