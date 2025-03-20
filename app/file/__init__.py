from werkzeug.utils import secure_filename
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app, session, send_file

from .fileProcess import read_metadata, query_variable, plot_subset

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

    # save file path to session
    session['file_path'] = str(tmp_file_path)

    # open file and read content
    metaInfo = read_metadata(tmp_file_path)

    return jsonify(metaInfo), 200

@file_bp.route('/detail/<string:var_name>', methods=['GET'])
def variable_name(var_name):
    # get file path from session cache
    try:
        file_path = session['file_path']
    except KeyError:
        return jsonify({'Session Error': 'No Uploaded File Found'}), 400

    file_path = Path(file_path)

    # open file and read content
    variable_info = query_variable(file_path, var_name)
    session[var_name] = variable_info

    return jsonify(variable_info), 200

@file_bp.route('/varplot', methods=['GET'])
def plot_variable():
    try:
        file_path = session['file_path']
    except KeyError:
        return jsonify({'Session Error': 'No Uploaded File Found'}), 400
    
    file_path = Path(file_path)
    # TODO: check request args format
    queryDict = request.args.to_dict()

    fig_buf = plot_subset(file_path, queryDict, session)

    return send_file(fig_buf, mimetype='image/png'), 200