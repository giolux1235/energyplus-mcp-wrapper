from flask import Flask, request, jsonify
import os
import sys
from pathlib import Path

app = Flask(__name__)

# Get the MCP server directory
mcp_server_dir = Path(__file__).parent / "EnergyPlus-MCP" / "energyplus-mcp-server"

@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "EnergyPlus MCP HTTP Wrapper",
        "version": "1.0.0",
        "mcp_server_available": mcp_server_dir.exists()
    })

@app.route('/health', methods=['GET'])
def health():
    """Simple health check for Railway"""
    return "OK", 200

@app.route('/tools', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    # Return a list of known EnergyPlus MCP tools
    known_tools = [
        "get_server_status", "load_idf_model", "get_model_summary", 
        "list_zones", "get_surfaces", "get_materials", "validate_idf",
        "run_energyplus_simulation", "create_interactive_plot",
        "inspect_schedules", "inspect_people", "inspect_lights",
        "modify_people", "modify_lights", "modify_electric_equipment"
    ]
    return jsonify({
        "tools": known_tools, 
        "count": len(known_tools),
        "note": "MCP server tools available (EnergyPlus integration ready)"
    })

@app.route('/rpc', methods=['POST'])
def rpc():
    """Handle MCP tool calls"""
    data = request.json
    tool = data.get('tool')
    args = data.get('arguments', {})
    
    # For deployment testing, return a mock response
    return jsonify({
        "result": f"Tool '{tool}' would be executed with arguments: {args}",
        "note": "MCP server ready for EnergyPlus integration",
        "tool": tool,
        "arguments": args,
        "status": "deployment_ready"
    })

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        "service": "EnergyPlus MCP HTTP Wrapper",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/status": "Health check",
            "/tools": "List available tools",
            "/rpc": "Execute MCP tools (POST)"
        },
        "mcp_server_url": f"http://0.0.0.0:{os.environ.get('PORT', 8080)}"
    })

if __name__ == '__main__':
    # Get port from environment variable (for cloud deployment)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting EnergyPlus MCP HTTP Wrapper")
    print(f"MCP Server Path: {mcp_server_dir}")
    print(f"Server available: {mcp_server_dir.exists()}")
    print(f"Server URL: http://0.0.0.0:{port}")
    
    # Print the MCP server URL for other services to use
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
