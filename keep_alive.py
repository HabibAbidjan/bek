from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port}).start()
