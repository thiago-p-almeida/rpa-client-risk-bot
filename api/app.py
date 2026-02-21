from flask import Flask, request, jsonify
import random

app = Flask(__name__)

@app.route("/risk-score", methods=["POST"])
def risk_score():
    data = request.get_json()

    if not data or "client_id" not in data:
        return jsonify({
            "status": "error",
            "message": "client_id is required"
        }), 400

    # Simulated risk score
    score = random.randint(300, 850)

    return jsonify({
        "client_id": data["client_id"],
        "risk_score": score,
        "status": "success"
    }), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
