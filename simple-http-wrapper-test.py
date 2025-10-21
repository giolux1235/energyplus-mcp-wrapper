from flask import Flask, request, jsonify
import os
import json
from pathlib import Path

app = Flask(__name__)

# Add the energyplus-mcp-server to the Python path
current_dir = Path(__file__).parent
mcp_server_dir = current_dir / "EnergyPlus-MCP" / "energyplus-mcp-server"

@app.route('/rpc', methods=['POST'])
def rpc():
    """Execute MCP tool via RPC call - Test version without EnergyPlus"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        tool = data.get('tool')
        if not tool:
            return jsonify({"error": "No tool specified"}), 400
            
        args = data.get('arguments', {})
        
        # Test implementation that works without EnergyPlus
        if tool == "get_server_status":
            return jsonify({
                "result": "Server is running! (Test mode - EnergyPlus not available in cloud)",
                "tool": tool,
                "arguments": args,
                "note": "This is a test deployment. Full EnergyPlus functionality requires local installation."
            })
        
        elif tool == "list_available_files":
            return jsonify({
                "result": "Available files: sample_files/1ZoneUncontrolled.idf, sample_files/5ZoneAirCooled.idf, etc.",
                "tool": tool,
                "arguments": args,
                "note": "Test mode - showing sample file list"
            })
        
        elif tool == "load_idf_model":
            idf_path = args.get('idf_path', 'sample_files/1ZoneUncontrolled.idf')
            return jsonify({
                "result": f"Test: Would load IDF model '{idf_path}' (EnergyPlus not available in cloud)",
                "tool": tool,
                "arguments": args,
                "note": "Test mode - model loading simulation"
            })
        
        else:
            return jsonify({
                "result": f"Test: Would execute tool '{tool}' with arguments: {args}",
                "tool": tool,
                "arguments": args,
                "note": "Test mode - tool execution simulation"
            })
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@app.route('/tools', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    tools = [
        "get_server_status", "load_idf_model", "get_model_summary", 
        "list_zones", "get_surfaces", "get_materials", "validate_idf",
        "run_energyplus_simulation", "create_interactive_plot",
        "inspect_schedules", "inspect_people", "inspect_lights",
        "modify_people", "modify_lights", "modify_electric_equipment"
    ]
    return jsonify({"tools": tools, "count": len(tools)})

@app.route('/status', methods=['GET'])
def status():
    """Get server status"""
    return jsonify({
        "status": "running",
        "mcp_server_path": str(mcp_server_dir),
        "available": os.path.exists(mcp_server_dir),
        "mode": "test",
        "note": "Test deployment - EnergyPlus not available in cloud"
    })

@app.route('/', methods=['GET'])
def index():
    """Simple API documentation"""
    return jsonify({
        "message": "EnergyPlus MCP HTTP Wrapper (Test Mode)",
        "endpoints": {
            "POST /rpc": "Execute MCP tool",
            "GET /tools": "List available tools", 
            "GET /status": "Server status",
            "GET /": "This documentation"
        },
        "note": "This is a test deployment. Full EnergyPlus functionality requires local installation.",
        "example": {
            "tool": "get_server_status",
            "arguments": {}
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (for cloud deployment)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting EnergyPlus MCP HTTP Wrapper (Test Mode)")
    print(f"MCP Server Path: {mcp_server_dir}")
    print(f"Server available: {os.path.exists(mcp_server_dir)}")
    print(f"Server URL: http://0.0.0.0:{port}")
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
