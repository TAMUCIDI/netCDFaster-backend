from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from env import TMP_DIR
from fileProcess.fileProcess import read_metadata

app = Flask(__name__)
CORS(app)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400
    # save file to tmp directory
    filename = secure_filename(file.filename)
    tmp_file_path = TMP_DIR / filename
    file.save(tmp_file_path)
    # open file and read content
    metaInfo = read_metadata(tmp_file_path)
    
    return jsonify(metaInfo), 200

if __name__ == '__main__':
    app.run(debug=True)