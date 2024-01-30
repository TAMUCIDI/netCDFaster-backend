from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app

from .fileProcess import read_metadata

file_bp = Blueprint('file', __name__, url_prefix='/file')

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400
    # save file to tmp directory
    filename = secure_filename(file.filename)
    tmp_file_path = current_app.config['TMP_DIR'] / filename
    file.save(tmp_file_path)

    # open file and read content
    metaInfo = read_metadata(tmp_file_path)

    return jsonify(metaInfo), 200