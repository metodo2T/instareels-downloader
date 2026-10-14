import os
import sys
import zipfile
import io
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename

from downloader import InstagramDownloader
from creative_renderer import CreativeVideoRenderer

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos_baixados")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

downloader = InstagramDownloader(output_dir=VIDEOS_DIR)
creative_renderer = CreativeVideoRenderer(assets_dir=BASE_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/avatar.png')
def serve_avatar():
    return send_from_directory(BASE_DIR, 'avatar.png')

@app.route('/badge.png')
def serve_badge():
    return send_from_directory(BASE_DIR, 'badge_extracted.png')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)

@app.route('/api/upload-avatar', methods=['POST'])
def api_upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado."}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nome de arquivo vazio."}), 400

    fname = f"avatar_{int(time.time())}_{secure_filename(file.filename)}"
    fpath = os.path.join(UPLOADS_DIR, fname)
    file.save(fpath)

    return jsonify({
        "success": True,
        "avatar_path": fpath,
        "avatar_url": f"/uploads/{fname}"
    })

@app.route('/api/upload-video', methods=['POST'])
def api_upload_video():
    if 'video' not in request.files:
        return jsonify({"success": False, "error": "Nenhum vídeo enviado."}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nome de arquivo vazio."}), 400

    fname = f"video_{int(time.time())}_{secure_filename(file.filename)}"
    fpath = os.path.join(VIDEOS_DIR, fname)
    file.save(fpath)

    return jsonify({
        "success": True,
        "filename": fname,
        "size_mb": round(os.path.getsize(fpath) / (1024 * 1024), 2)
    })

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json() or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"success": False, "error": "Nenhum link fornecido."}), 400

    if "instagram.com" not in url:
        return jsonify({"success": False, "error": "Link inválido. Deve ser do Instagram."}), 400

    result = downloader.download_video(url)
    return jsonify(result)

@app.route('/api/render-creative', methods=['POST'])
def api_render_creative():
    data = request.get_json() or {}
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({"success": False, "error": "Nome do vídeo não informado."}), 400

    input_path = os.path.join(VIDEOS_DIR, filename)
    if not os.path.exists(input_path):
        return jsonify({"success": False, "error": "Vídeo original não encontrado no servidor."}), 404

    try:
        render_res = creative_renderer.render_creative(
            input_video=input_path,
            name=data.get('name', 'Bruno César | Tráfego Pago e Orgânico'),
            handle=data.get('handle', '@brunocesar.2t'),
            headline=data.get('headline', 'A headline aqui...'),
            avatar_path=data.get('avatar_path'),
            verified=data.get('verified', True),
            video_w=int(data.get('video_w', 880)),
            video_h=int(data.get('video_h', 760)),
            video_y=data.get('video_y'),
            video_zoom=float(data.get('video_zoom', 1.0)),
            video_pan_x=float(data.get('video_pan_x', 0.5)),
            video_pan_y=float(data.get('video_pan_y', 0.5)),
            corner_radius=int(data.get('corner_radius', 32)),
            watermark_text=data.get('watermark_text', '@brunocesar.2t'),
            watermark_opacity=float(data.get('watermark_opacity', 0.35))
        )
        return jsonify(render_res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/videos', methods=['GET'])
def api_videos():
    if not os.path.exists(VIDEOS_DIR):
        return jsonify([])

    files = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm'))]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(VIDEOS_DIR, f)), reverse=True)

    items = []
    for f in files:
        fpath = os.path.join(VIDEOS_DIR, f)
        size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
        mtime = os.path.getmtime(fpath)
        date_str = datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
        is_creative = "_criativo" in f or "_pronto" in f
        items.append({
            "name": f,
            "size_mb": size_mb,
            "date": date_str,
            "is_creative": is_creative
        })

    return jsonify(items)

@app.route('/videos/<path:filename>')
def serve_video(filename):
    download = request.args.get('download', '0') == '1'
    return send_from_directory(
        VIDEOS_DIR,
        filename,
        as_attachment=download,
        mimetype='video/mp4',
        conditional=True
    )

@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    files = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.webm'))]
    if not files:
        return jsonify({"error": "Nenhum vídeo disponível para compactar."}), 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            fpath = os.path.join(VIDEOS_DIR, f)
            zf.write(fpath, arcname=f)

    memory_file.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'reels_baixados_{timestamp}.zip'
    )

@app.route('/api/clear-videos', methods=['POST'])
def clear_videos():
    try:
        count = 0
        for f in os.listdir(VIDEOS_DIR):
            fpath = os.path.join(VIDEOS_DIR, f)
            if os.path.isfile(fpath):
                os.remove(fpath)
                count += 1
        return jsonify({"success": True, "deleted_count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando InstaReels Studio em http://0.0.0.0:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
