import os
import sys
import zipfile
import io
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file

from downloader import InstagramDownloader

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos_baixados")
os.makedirs(VIDEOS_DIR, exist_ok=True)

downloader = InstagramDownloader(output_dir=VIDEOS_DIR)

@app.route('/')
def index():
    return render_template('index.html')

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
        items.append({
            "name": f,
            "size_mb": size_mb,
            "date": date_str
        })

    return jsonify(items)

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(VIDEOS_DIR, filename, as_attachment=True)

@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    """Generates a zip of all downloaded videos for bulk mobile/desktop download"""
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

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    if os.path.exists(VIDEOS_DIR):
        if sys.platform == 'win32':
            os.startfile(VIDEOS_DIR)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Pasta não encontrada."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando InstaReels Batch Downloader em http://0.0.0.0:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
