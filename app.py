from flask import Flask, render_template

app = Flask(__name__)

@app.route("/hw1")
def hw1():
    return render_template("hw1.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
