from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

users = {}


def make_unique_username(uname):
    existing = {info["username"] for info in users.values()}
    if uname not in existing:
        return uname

    counter = 2
    new_name = f"{uname}_{counter}"
    while new_name in existing:
        counter += 1
        new_name = f"{uname}_{counter}"
    return new_name


@app.route("/time", methods=["POST"])
def update_time():
    data = request.json or {}
    user_id = data.get("user_id")
    uname = data.get("username", "Anonymous")
    elapsed = float(data.get("elapsed", 0.0))
    closing = data.get("closing", False)

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if user_id not in users:
        uname = make_unique_username(uname)
        users[user_id] = {
            "username": uname,
            "elapsed": 0.0,
            "last_seen": 0.0,
            "last_reported": elapsed,
        }

    user = users[user_id]
    prev_elapsed = user["last_reported"]

    delta = max(0.0, elapsed - prev_elapsed)
    user["elapsed"] += delta
    user["last_reported"] = elapsed
    user["last_seen"] = time.time()

    if closing:
        print(f"[touchgrass] {user['username']} closed IDA. Total time: {user['elapsed']:.1f}s")
    else:
        print(f"[touchgrass] {user['username']} updated: +{delta:.1f}s (total {user['elapsed']:.1f}s)")

    return jsonify({"ok": True, "username": user["username"], "total": user["elapsed"]})


@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    now = time.time()
    leaderboard_data = []
    for info in users.values():
        online = (now - info["last_seen"]) < 120
        leaderboard_data.append({
            "username": info["username"],
            "elapsed": round(info["elapsed"], 1),
            "online": online
        })

    leaderboard_data.sort(key=lambda x: x["elapsed"], reverse=True)
    return jsonify(leaderboard_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1337)
