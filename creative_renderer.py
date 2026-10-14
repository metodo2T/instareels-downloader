import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

class CreativeVideoRenderer:
    def __init__(self, assets_dir=None):
        if assets_dir is None:
            self.assets_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.assets_dir = assets_dir

        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        self.default_avatar = os.path.join(self.assets_dir, "avatar.png")
        self.badge_icon = os.path.join(self.assets_dir, "badge_extracted.png")

    def _get_font(self, font_name, size):
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            try:
                return ImageFont.truetype("arialbd.ttf" if "b" in font_name else "arial.ttf", size)
            except Exception:
                return ImageFont.load_default()

    def generate_twitter_overlay(
        self,
        name="Bruno César | Tráfego Pago e Orgânico",
        handle="@brunocesar.2t",
        headline="A headline aqui a headline aqui\nA headline aqui a headline aqui\nA headline aqui a headline aqui",
        avatar_path=None,
        verified=True,
        header_y=430,
        headline_y=640,
        headline_size=44,
        video_w=864,
        video_h=740,
        video_y=890,
        corner_radius=36,
        watermark_text="@brunocesar.2t",
        watermark_opacity=0.35,
        watermark_y_offset=0
    ):
        """
        Creates the 1080x1920 PNG template matching the reference layout:
        - Canvas: 1080 x 1920 (#FFFFFF)
        - Header Y: 430px
        - Headline Y: 640px
        - Video Box: width 864px, height 740px, top Y 890px
        - Corner radius: 36px
        - Watermark centered over video
        """
        W, H = 1080, 1920
        margin_x = (W - video_w) // 2

        overlay = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(overlay)

        # 1. Profile Avatar (Diameter 140px)
        av_size = 140
        av_to_use = avatar_path if (avatar_path and os.path.exists(avatar_path)) else self.default_avatar

        if os.path.exists(av_to_use):
            try:
                av_raw = Image.open(av_to_use).convert("RGBA")
                av_resized = av_raw.resize((av_size, av_size), Image.Resampling.LANCZOS)

                mask = Image.new("L", (av_size, av_size), 0)
                m_draw = ImageDraw.Draw(mask)
                m_draw.ellipse([(0, 0), (av_size, av_size)], fill=255)

                av_circle = Image.new("RGBA", (av_size, av_size), (0, 0, 0, 0))
                av_circle.paste(av_resized, (0, 0), mask=mask)
                overlay.paste(av_circle, (margin_x, header_y), mask=av_circle)
            except Exception as e:
                print(f"Erro ao desenhar avatar: {e}")

        # 2. Verified Badge
        if verified and os.path.exists(self.badge_icon):
            try:
                badge = Image.open(self.badge_icon).convert("RGBA")
                b_size = 38
                badge_resized = badge.resize((b_size, b_size), Image.Resampling.LANCZOS)
                overlay.paste(badge_resized, (margin_x + av_size - 28, header_y - 2), mask=badge_resized)
            except Exception:
                pass

        # 3. Header Names
        font_name = self._get_font("segoeuib.ttf", 36)
        font_user = self._get_font("segoeui.ttf", 26)

        text_x = margin_x + av_size + 20
        draw.text((text_x, header_y + 24), name, font=font_name, fill="#000000")
        draw.text((text_x, header_y + 68), handle, font=font_user, fill="#6b7280")

        # 4. Headline
        font_headline = self._get_font("segoeuib.ttf", int(headline_size))
        clean_headline = headline.strip()
        draw.text((margin_x, headline_y), clean_headline, font=font_headline, fill="#000000", spacing=14)

        # 5. Transparent Rounded Cutout for Video
        cutout_mask = Image.new("L", (W, H), 255)
        cutout_draw = ImageDraw.Draw(cutout_mask)
        cutout_draw.rounded_rectangle(
            [(margin_x, video_y), (margin_x + video_w, video_y + video_h)],
            radius=int(corner_radius),
            fill=0
        )
        overlay.putalpha(cutout_mask)

        # 6. Watermark over video
        if watermark_text and watermark_text.strip():
            watermark_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            wm_draw = ImageDraw.Draw(watermark_layer)
            font_wm = self._get_font("segoeuib.ttf", 36)

            wm_cx = margin_x + video_w // 2
            wm_cy = video_y + video_h // 2 - 20 + int(watermark_y_offset)

            alpha_int = int(255 * watermark_opacity)
            wm_draw.text((wm_cx + 1, wm_cy + 1), watermark_text.strip(), font=font_wm, fill=(0, 0, 0, int(alpha_int * 0.7)), anchor="mm")
            wm_draw.text((wm_cx, wm_cy), watermark_text.strip(), font=font_wm, fill=(255, 255, 255, alpha_int), anchor="mm")

            overlay = Image.alpha_composite(overlay, watermark_layer)

        return overlay, video_y, margin_x

    def render_creative(
        self,
        input_video,
        output_video=None,
        name="Bruno César | Tráfego Pago e Orgânico",
        handle="@brunocesar.2t",
        headline="A headline aqui a headline aqui\nA headline aqui a headline aqui\nA headline aqui a headline aqui",
        avatar_path=None,
        verified=True,
        header_y=430,
        headline_y=640,
        headline_size=44,
        video_w=864,
        video_h=740,
        video_y=890,
        video_zoom=1.0,
        video_pan_x=0.5,
        video_pan_y=0.5,
        corner_radius=36,
        watermark_text="@brunocesar.2t",
        watermark_opacity=0.35,
        watermark_y_offset=0
    ):
        """
        Renders the final 1080x1920 MP4 video with exact layout and zoom controls.
        """
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Vídeo de entrada não encontrado: {input_video}")

        if output_video is None:
            dirname = os.path.dirname(input_video)
            base = os.path.splitext(os.path.basename(input_video))[0]
            output_video = os.path.join(dirname, f"{base}_criativo.mp4")

        # Generate overlay template image
        overlay_img, actual_video_y, margin_x = self.generate_twitter_overlay(
            name=name,
            handle=handle,
            headline=headline,
            avatar_path=avatar_path,
            verified=verified,
            header_y=int(header_y),
            headline_y=int(headline_y),
            headline_size=int(headline_size),
            video_w=int(video_w),
            video_h=int(video_h),
            video_y=int(video_y),
            corner_radius=int(corner_radius),
            watermark_text=watermark_text,
            watermark_opacity=float(watermark_opacity),
            watermark_y_offset=int(watermark_y_offset)
        )

        temp_overlay = os.path.join(self.assets_dir, f"_temp_overlay_{os.getpid()}.png")
        overlay_img.save(temp_overlay, "PNG")

        zoom = max(1.0, float(video_zoom))
        crop_filter = f"crop=in_w/{zoom}:in_h/{zoom}:(in_w-in_w/{zoom})*{video_pan_x}:(in_h-in_h/{zoom})*{video_pan_y}"
        scale_filter = f"scale={int(video_w)}:{int(video_h)}:force_original_aspect_ratio=increase,crop={int(video_w)}:{int(video_h)}"

        filter_graph = (
            f"color=c=white:s=1080x1920:d=1[bg];"
            f"[0:v]{crop_filter},{scale_filter}[vid];"
            f"[bg][vid]overlay={margin_x}:{actual_video_y}:shortest=1[comp];"
            f"[comp][1:v]overlay=0:0[outv]"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-threads", "2",
            "-i", input_video,
            "-i", temp_overlay,
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_video
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
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
            raise RuntimeError(f"Erro na renderização do criativo: {e.stderr[-300:]}")
