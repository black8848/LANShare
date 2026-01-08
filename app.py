#!/usr/bin/env python3
"""内网文件传输工具 - 支持文件上传/下载和文字分享"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, jsonify, redirect, url_for

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
TEXT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'texts.json')
MAX_CONTENT_LENGTH = 5000 * 1024 * 1024  # 500MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_texts():
    """加载保存的文字"""
    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_texts(texts):
    """保存文字到文件"""
    with open(TEXT_FILE, 'w', encoding='utf-8') as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)


def get_files():
    """获取已上传的文件列表"""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                'name': filename,
                'size': format_size(stat.st_size),
                'time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    files.sort(key=lambda x: x['time'], reverse=True)
    return files


def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@app.route('/')
def index():
    """主页"""
    files = get_files()
    texts = load_texts()
    return render_template('index.html', files=files, texts=texts)


@app.route('/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    # 保存文件
    filename = file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 如果文件已存在，添加序号
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1

    file.save(filepath)
    return jsonify({'success': True, 'filename': filename})


@app.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """删除文件"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'error': '文件不存在'}), 404


@app.route('/text', methods=['POST'])
def add_text():
    """添加文字"""
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': '没有内容'}), 400

    content = data['content'].strip()
    if not content:
        return jsonify({'error': '内容不能为空'}), 400

    texts = load_texts()
    texts.insert(0, {
        'id': str(uuid.uuid4())[:8],
        'content': content,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_texts(texts)
    return jsonify({'success': True})


@app.route('/text/<text_id>', methods=['DELETE'])
def delete_text(text_id):
    """删除文字"""
    texts = load_texts()
    texts = [t for t in texts if t['id'] != text_id]
    save_texts(texts)
    return jsonify({'success': True})


@app.route('/clear-texts', methods=['POST'])
def clear_texts():
    """清空所有文字"""
    save_texts([])
    return jsonify({'success': True})


if __name__ == '__main__':
    import socket

    # 获取本机IP
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    port = 8080
    local_ip = get_local_ip()

    print("\n" + "=" * 50)
    print("  内网文件传输工具已启动")
    print("=" * 50)
    print(f"\n  本机访问: http://localhost:{port}")
    print(f"  内网访问: http://{local_ip}:{port}")
    print("\n  按 Ctrl+C 停止服务")
    print("=" * 50 + "\n")

    app.run(host='0.0.0.0', port=port, debug=False)
