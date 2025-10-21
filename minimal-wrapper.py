from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "service": "EnergyPlus MCP HTTP Wrapper",
        "status": "running",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return "OK", 200

@app.route('/healthz')
def healthz():
    return "OK", 200

@app.route('/status')
def status():
    return jsonify({"status": "healthy"})

@app.route('/tools')
def tools():
    return jsonify({
        "tools": ["get_server_status", "load_idf_model", "run_energyplus_simulation"],
        "count": 3
    })

@app.route('/rpc', methods=['POST'])
def rpc():
    return jsonify({
        "result": "MCP server ready",
        "status": "deployment_ready"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting server on port {port}")
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    print(f"Server starting...")
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        raise
