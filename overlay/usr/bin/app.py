#!/usr/bin/env python3

import os.path

from flask import Flask, Response, url_for, flash, request, redirect
from os import walk
from flask import request
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = '/static'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def show_files():
    file_list = ""
    for f in os.listdir('/usr/bin/static/'):
            link = url_for('static',filename=f)
            file_list = file_list + '<a href="%s">%s</a>  <a href="/delete/%s">Delete</a><br>' % (link, f, f)
    return file_list

@app.route('/delete/<file_name>', methods=['GET'])
def delete(file_name):
    os.remove("/usr/bin/static/" + file_name)
    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():  # pragma: no cover
    return \
    '''
    <html>
    <body>
    <h2>Download file: </h2> </br>
    %s </br>
    </body>
    </html>
    ''' % (show_files())

if __name__ == '__main__':  # pragma: no cover
    app.run(host='0.0.0.0',port=8000)