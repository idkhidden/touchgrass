from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from collections import deque

app = Flask(__name__)
CORS(app)

users = {}
new_user_timestamps = deque(maxlen=1000)
MAX_NEW_USERS_PER_SECOND = 1


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


def too_many_new_users():
    now = time.time()
    while new_user_timestamps and now - new_user_timestamps[0] > 1:
        new_user_timestamps.popleft()
    return len(new_user_timestamps) >= MAX_NEW_USERS_PER_SECOND


@app.route("/time", methods=["POST"])
def update_time():
    data = request.json or {}
    user_id = data.get("user_id")
    uname = data.get("username", "Anonymous")
    elapsed = float(data.get("elapsed", 0.0))
    closing = data.get("closing", False)

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    now = time.time()

    if user_id not in users:
        if too_many_new_users():
            return jsonify({"error": "Too many new users, try again later"}), 429
        new_user_timestamps.append(now)

        uname = make_unique_username(uname)
        users[user_id] = {
            "username": uname,
            "elapsed": 0.0,
            "last_seen": now,
            "last_reported": elapsed,
            "last_update_time": now, 
        }

    user = users[user_id]
    prev_elapsed = user["last_reported"]
    prev_update_time = user["last_update_time"]
    delta = elapsed - prev_elapsed
    real_delta = now - prev_update_time

    # Sanity checks
    if delta < 0:
        return jsonify({"error": "Elapsed time cannot decrease"}), 400
    elif delta > 120:
        return jsonify({"error": "Elapsed time increment too large"}), 400

    if abs(delta - real_delta) > 10:
        return jsonify({"error": "Elapsed time mismatch with real time"}), 400

    user["elapsed"] += delta
    user["last_reported"] = elapsed
    user["last_seen"] = now
    user["last_update_time"] = now

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
