import flask
from flask import Flask, request
from flask import render_template
app = Flask(__name__)
app.secret_key = 'parse'


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get('query')

    return 'ok'


if __name__ == '__main__':
    app.run('0.0.0.0', 8888)
