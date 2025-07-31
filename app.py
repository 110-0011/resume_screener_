print(f"✅ Flask is starting on port {port}")

from flask import Flask
print(f"✅ Flask is starting on port {port}")

app = Flask(__name__)
print(f"✅ Flask is starting on port {port}")

@app.route("/")
def home():
    return "✅ Hello"

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
