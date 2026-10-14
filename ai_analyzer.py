import os
import json
import subprocess
from PIL import Image
import imageio_ffmpeg

class VideoAIAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def set_api_key(self, api_key):
        self.api_key = api_key.strip() if api_key else ""

    def extract_keyframes(self, video_path, num_frames=3, output_dir=None):
        """Extracts keyframes from the first few seconds of the video."""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(video_path), "frames_temp")
        os.makedirs(output_dir, exist_ok=True)

        frame_paths = []
        timestamps = ["00:00:01.000", "00:00:02.000", "00:00:03.000"][:num_frames]

        for i, ts in enumerate(timestamps):
            out_img = os.path.join(output_dir, f"frame_{i+1}.jpg")
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss", ts,
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                out_img
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(out_img):
                    frame_paths.append(out_img)
            except Exception as e:
                print(f"Erro ao extrair frame {ts}: {e}")

        return frame_paths

    def analyze_video(self, video_path, original_title="", original_desc=""):
        """
        Analyzes video frames and metadata to detect text on screen and generate hooks + captions.
        """
        frames = self.extract_keyframes(video_path)

        # If Gemini API Key is available, use Gemini 2.5 Flash Multimodal Vision
        if self.api_key:
            try:
                return self._analyze_with_gemini(frames, original_title, original_desc)
            except Exception as e:
                print(f"Falha na API do Gemini: {e}. Usando gerador alternativo...")

        # Fallback heuristic generator
        return self._fallback_analysis(frames, original_title, original_desc)

    def _analyze_with_gemini(self, frame_paths, original_title, original_desc):
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        # Prepare images for upload/inline
        contents = []
        for fp in frame_paths:
            try:
                img = Image.open(fp)
                contents.append(img)
            except Exception:
                pass

        prompt = f"""
Você é o estrategista chefe de marketing digital e conteúdo viral para Bruno César (@brunocesar.2t - Tráfego Pago e Orgânico).
Você recebeu frames dos primeiros segundos de um Reel do Instagram para produzir uma versão teste de alta conversão.

Contexto do vídeo:
- Título/Autor original: {original_title}
- Descrição original: {original_desc[:500]}

SUA MISSÃO:
1. Analise atentamente as imagens: leia e identifique TUDO o que está escrito no vídeo (título na tela, legendas, texto em destaque, elementos visuais).
2. Identifique o tema central, a dor ou o segredo revelado no vídeo.
3. Crie 4 variações de GANCHOS / HEADLINES magnéticos para colocar no topo do vídeo no molde do Bruno César.
   - O gancho deve ter de 2 a 3 linhas curtas (cada linha com poucas palavras, fácil de bater o olho em 1 segundo).
   - Deve gerar curiosidade irresistível, quebra de padrão ou promessa forte.
4. Crie uma LEGENDA completa pronta para postar no Instagram do Bruno César:
   - Gancho forte na primeira linha
   - Explicação / lição de valor em tópicos
   - Chamada para ação (CTA): "Siga @brunocesar.2t para mais estratégias de tráfego pago e orgânico"
   - 5 a 8 hashtags altamente relevantes

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "texto_detectado_no_video": "o que você leu escrito nos frames",
  "tema": "resumo do tema",
  "hooks": [
    "Linha 1 do gancho 1\\nLinha 2 do gancho 1",
    "Linha 1 do gancho 2\\nLinha 2 do gancho 2",
    "Linha 1 do gancho 3\\nLinha 2 do gancho 3",
    "Linha 1 do gancho 4\\nLinha 2 do gancho 4"
  ],
  "legenda": "texto completo da legenda..."
}}
"""
        contents.append(prompt)

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )

        data = json.loads(response.text)
        return {
            "success": True,
            "source": "gemini_vision",
            "texto_detectado": data.get("texto_detectado_no_video", ""),
            "tema": data.get("tema", ""),
            "hooks": data.get("hooks", []),
            "legenda": data.get("legenda", "")
        }

    def _fallback_analysis(self, frame_paths, original_title, original_desc):
        # Extracts primary keywords from title / description
        text = f"{original_title} {original_desc}".strip()
        subject = original_title if original_title else "este segredo"
        if len(subject) > 40:
            subject = subject[:40] + "..."

        default_hooks = [
            f"O que ninguém te conta sobre\n{subject}\n(Assista até o final)",
            f"Faça isso antes que seja tarde:\n{subject}\nO método definitivo",
            f"Como ter resultados insanos com\n{subject}\nsem perder tempo",
            f"O segredo que os grandes usam:\n{subject}\nRevelado passo a passo"
        ]

        default_caption = f"""O que você acha dessa estratégia? 👇

{subject}

Se você quer dominar as melhores técnicas de tráfego pago e orgânico para escalar seus resultados, salve esse post para consultar depois!

👉 Siga @brunocesar.2t para receber conteúdo diário sobre vendas, tráfego e escala.

#trafegopago #trafegoorganico #marketingdigital #reelsbrasil #brunocesar"""

        return {
            "success": True,
            "source": "fallback",
            "texto_detectado": "Análise visual requer Chave de API Gemini",
            "tema": subject,
            "hooks": default_hooks,
            "legenda": default_caption
        }
