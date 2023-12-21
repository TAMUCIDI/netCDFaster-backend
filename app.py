from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400
    
    filename = secure_filename(file.filename)
    metadata = {
        'filename': filename,
        'content_type': file.content_type,
        'content_length': file.content_length
    }
    return jsonify(metadata), 200

if __name__ == '__main__':
    app.run(debug=True)