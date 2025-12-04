from flask import Flask, request, jsonify
import time
app = Flask(__name__)

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json or {}
    mode = data.get('mode', 'ok')
    if mode == 'ok':
        return jsonify({'status': 'ok'}), 200
    if mode == 'delayed':
        time.sleep(2)
        return jsonify({'status': 'ok', 'delayed': True}), 200
    if mode == 'fail':
        return jsonify({'status': 'error'}), 500
    if mode == 'flaky':
        # simple flakiness using epoch seconds
        if int(time.time()) % 2 == 0:
            return jsonify({'status': 'ok'}), 200
        else:
            return jsonify({'status': 'error'}), 500
    return jsonify({'status': 'unknown mode'}), 400

if __name__ == '__main__':
    app.run(port=5005)
