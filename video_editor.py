import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

class BrunoCesarVideoEditor:
    def __init__(self, assets_dir=None):
        if assets_dir is None:
            self.assets_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.assets_dir = assets_dir

        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        self.avatar_path = os.path.join(self.assets_dir, "avatar.png")
        self.badge_path = os.path.join(self.assets_dir, "badge_extracted.png")

    def _get_font(self, font_name, size):
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            try:
                return ImageFont.truetype("arialbd.ttf" if "b" in font_name else "arial.ttf", size)
            except Exception:
                return ImageFont.load_default()

    def create_template_overlay(self, headline_text, video_w=880, video_h=760, radius=32):
        """
        Generates a 1080x1920 PNG overlay with:
        - Solid white outside
        - Bruno César Profile Header
        - Dynamic Headline text
        - Transparent rounded cutout for video
        - Watermark @brunocesar.2t
        """
        W, H = 1080, 1920
        margin_x = (W - video_w) // 2  # 100px for 880w
        start_y = 390

        # Create overlay base with transparent center cutout
        overlay = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(overlay)

        # 1. Avatar
        av_size = 130
        if os.path.exists(self.avatar_path):
            av_raw = Image.open(self.avatar_path).convert("RGBA")
            av_resized = av_raw.resize((av_size, av_size), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", (av_size, av_size), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.ellipse([(0, 0), (av_size, av_size)], fill=255)

            av_circle = Image.new("RGBA", (av_size, av_size), (0, 0, 0, 0))
            av_circle.paste(av_resized, (0, 0), mask=mask)
            overlay.paste(av_circle, (margin_x, start_y), mask=av_circle)

        # 2. Verified Badge
        if os.path.exists(self.badge_path):
            badge = Image.open(self.badge_path).convert("RGBA")
            b_size = 38
            badge_resized = badge.resize((b_size, b_size), Image.Resampling.LANCZOS)
            overlay.paste(badge_resized, (margin_x + av_size - 28, start_y - 2), mask=badge_resized)

        # 3. Header Text
        font_name = self._get_font("segoeuib.ttf", 36)
        font_user = self._get_font("segoeui.ttf", 26)

        text_x = margin_x + av_size + 20
        text_y = start_y + 22

        draw.text((text_x, text_y), "Bruno César | Tráfego Pago e Orgânico", font=font_name, fill="#000000")
        draw.text((text_x, text_y + 44), "@brunocesar.2t", font=font_user, fill="#6b7280")

        # 4. Headline
        font_headline = self._get_font("segoeuib.ttf", 44)
        headline_y = start_y + av_size + 45

        # Format headline with spacing
        headline_clean = headline_text.strip()
        draw.text((margin_x, headline_y), headline_clean, font=font_headline, fill="#000000", spacing=14)

        # Calculate height of headline to dynamically position video
        bbox = draw.textbbox((margin_x, headline_y), headline_clean, font=font_headline, spacing=14)
        headline_bottom = bbox[3]

        video_y = headline_bottom + 45

        # 5. Cut out the transparent rounded video box
        # Create a mask for rounded rectangle
        cutout_mask = Image.new("L", (W, H), 255)
        cutout_draw = ImageDraw.Draw(cutout_mask)
        cutout_draw.rounded_rectangle(
            [(margin_x, video_y), (margin_x + video_w, video_y + video_h)],
            radius=radius,
            fill=0
        )
        overlay.putalpha(cutout_mask)

        # 6. Watermark @brunocesar.2t over the video
        watermark_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wm_draw = ImageDraw.Draw(watermark_layer)
        font_wm = self._get_font("segoeuib.ttf", 36)

        wm_cx = margin_x + video_w // 2
        wm_cy = video_y + video_h // 2 - 30

        # Subtle shadow
        wm_draw.text((wm_cx + 1, wm_cy + 1), "@brunocesar.2t", font=font_wm, fill=(0, 0, 0, 80), anchor="mm")
        # White text with 35% opacity
        wm_draw.text((wm_cx, wm_cy), "@brunocesar.2t", font=font_wm, fill=(255, 255, 255, 110), anchor="mm")

        # Composite watermark on top
        final_overlay = Image.alpha_composite(overlay, watermark_layer)

        return final_overlay, video_y

    def render_reel(self, input_video, headline_text, output_video=None, progress_callback=None):
        """
        Composites input_video into the Bruno César 1080x1920 template.
        """
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Vídeo de entrada não encontrado: {input_video}")

        if output_video is None:
            dirname = os.path.dirname(input_video)
            basename = os.path.splitext(os.path.basename(input_video))[0]
            output_video = os.path.join(dirname, f"{basename}_pronto_brunocesar.mp4")

        video_w = 880
        video_h = 780

        # 1. Generate Overlay Image
        overlay_img, video_y = self.create_template_overlay(headline_text, video_w=video_w, video_h=video_h)
        temp_overlay = os.path.join(self.assets_dir, "_temp_overlay.png")
        overlay_img.save(temp_overlay, "PNG")

        if progress_callback:
            progress_callback("Renderizando vídeo no molde Bruno César...")

        # 2. FFmpeg command:
        # Background: solid white 1080x1920
        # Scaled video placed at (margin_x, video_y)
        # Overlay with rounded cutout and header placed on top!
        margin_x = (1080 - video_w) // 2

        filter_graph = (
            f"color=c=white:s=1080x1920:d=1[bg];"
            f"[0:v]scale={video_w}:{video_h}:force_original_aspect_ratio=increase,crop={video_w}:{video_h}[vid];"
            f"[bg][vid]overlay={margin_x}:{video_y}:shortest=1[comp1];"
            f"[comp1][1:v]overlay=0:0[outv]"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_video,
            "-i", temp_overlay,
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_video
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            if os.path.exists(temp_overlay):
                os.remove(temp_overlay)

            return {
                "success": True,
                "output_video": output_video,
                "filename": os.path.basename(output_video),
                "size_mb": round(os.path.getsize(output_video) / (1024 * 1024), 2)
            }
        except subprocess.CalledProcessError as e:
            if os.path.exists(temp_overlay):
                os.remove(temp_overlay)
            raise RuntimeError(f"Erro no FFmpeg: {e.stderr[-300:]}")
