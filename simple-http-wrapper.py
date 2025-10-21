from flask import Flask, request, jsonify
import subprocess
import json
import sys
import os
from pathlib import Path

app = Flask(__name__)

# Add the energyplus-mcp-server to the Python path
current_dir = Path(__file__).parent
mcp_server_dir = current_dir / "EnergyPlus-MCP" / "energyplus-mcp-server"
sys.path.insert(0, str(mcp_server_dir))

@app.route('/rpc', methods=['POST'])
def rpc():
    """Execute MCP tool via RPC call"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        tool = data.get('tool')
        if not tool:
            return jsonify({"error": "No tool specified"}), 400
            
        args = data.get('arguments', {})
        
        # Set up environment for MCP server
        env = os.environ.copy()
        env['WORKSPACE_ROOT'] = str(mcp_server_dir)
        
        # Create necessary directories
        logs_dir = mcp_server_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Create outputs directory
        outputs_dir = mcp_server_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        # Try to call the actual MCP server
        try:
            # Create a subprocess call to the MCP server with proper environment
            import subprocess
            import json
            
            # Set up environment
            env = os.environ.copy()
            env['WORKSPACE_ROOT'] = str(mcp_server_dir)
            env['PYTHONPATH'] = str(mcp_server_dir) + ':' + env.get('PYTHONPATH', '')
            
            # Create a Python script that will run the MCP tool
            script_content = f'''
import sys
import os
sys.path.insert(0, "{mcp_server_dir}")

# Set environment variables
os.environ['WORKSPACE_ROOT'] = "{mcp_server_dir}"

# Monkey patch the config before importing
import energyplus_mcp_server.config as config_module

class PatchedConfig:
    def __init__(self):
        self.paths = type('Paths', (), {{
            'workspace_root': '{mcp_server_dir}',
            'sample_files_path': '{mcp_server_dir}/sample_files',
            'output_dir': '{mcp_server_dir}/outputs',
            'temp_dir': '/tmp'
        }})()
        self.energyplus = type('EnergyPlus', (), {{
            'version': '24.2.0',
            'executable_path': '/usr/local/bin/energyplus',
            'idd_path': '/usr/local/bin/Energy+.idd',
            'example_files_path': '{mcp_server_dir}/sample_files'
        }})()
        self.server = type('Server', (), {{
            'name': 'energyplus-mcp-server',
            'version': '0.1.0',
            'log_level': 'INFO',
            'debug_mode': False
        }})()
        self.debug_mode = False

# Replace the get_config function
config_module.get_config = lambda: PatchedConfig()

# Now import and use the MCP server
from energyplus_mcp_server.server import mcp
import asyncio
import json

async def run_tool():
    try:
        # Use the MCP server's call_tool method
        if {json.dumps(args)}:
            result = await mcp.call_tool("{tool}", {json.dumps(args)})
        else:
            result = await mcp.call_tool("{tool}", {{}})
        return result
    except Exception as e:
        return f"Error: {{str(e)}}"

result = asyncio.run(run_tool())
# Convert result to string if it's not JSON serializable
try:
    if hasattr(result, 'content'):
        result_str = str(result.content)
    else:
        result_str = str(result)
except:
    result_str = str(result)

print(json.dumps({{"result": result_str}}))
'''
            
            # Write the script to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            try:
                # Run the script
                result = subprocess.run(
                    ['python', script_path],
                    capture_output=True,
                    text=True,
                    cwd=str(mcp_server_dir),
                    env=env,
                    timeout=30
                )
                
                # Clean up the temporary file
                os.unlink(script_path)
                
                if result.returncode == 0:
                    try:
                        response_data = json.loads(result.stdout)
                        return jsonify({
                            "result": response_data.get("result", "No result"),
                            "tool": tool,
                            "arguments": args
                        })
                    except json.JSONDecodeError:
                        return jsonify({
                            "result": result.stdout.strip(),
                            "tool": tool,
                            "arguments": args
                        })
                else:
                    return jsonify({
                        "result": f"MCP server error: {result.stderr}",
                        "tool": tool,
                        "arguments": args,
                        "note": "MCP server execution failed"
                    })
                    
            except subprocess.TimeoutExpired:
                return jsonify({
                    "result": "Tool execution timed out",
                    "tool": tool,
                    "arguments": args,
                    "note": "MCP server timeout"
                })
            except Exception as script_error:
                return jsonify({
                    "result": f"Script execution error: {str(script_error)}",
                    "tool": tool,
                    "arguments": args,
                    "note": "MCP script failed"
                })
            
        except Exception as mcp_error:
            # Fallback to test implementation if MCP fails
            return jsonify({
                "result": f"Tool '{tool}' would be executed with arguments: {args}",
                "note": f"MCP integration error: {str(mcp_error)}. Using test implementation.",
                "tool": tool,
                "arguments": args
            })
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@app.route('/tools', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    try:
        # Try to get tools directly
        import sys
        sys.path.insert(0, str(mcp_server_dir))
        
        try:
            from energyplus_mcp_server.server import mcp
            tools = list(mcp._tools.keys())
            return jsonify({"tools": tools, "count": len(tools)})
        except Exception as import_error:
            # Fallback to a hardcoded list of known tools
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
                "note": f"MCP import failed: {str(import_error)}. Showing known tools."
            })
        
    except Exception as e:
        return jsonify({"error": f"Error listing tools: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def status():
    """Get server status"""
    return jsonify({
        "status": "running",
        "mcp_server_path": str(mcp_server_dir),
        "available": os.path.exists(mcp_server_dir)
    })

@app.route('/', methods=['GET'])
def index():
    """Simple API documentation"""
    return jsonify({
        "message": "EnergyPlus MCP HTTP Wrapper",
        "endpoints": {
            "POST /rpc": "Execute MCP tool",
            "GET /tools": "List available tools", 
            "GET /status": "Server status",
            "GET /": "This documentation"
        },
        "example": {
            "tool": "get_server_status",
            "arguments": {}
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (for cloud deployment)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting EnergyPlus MCP HTTP Wrapper")
    print(f"MCP Server Path: {mcp_server_dir}")
    print(f"Server available: {os.path.exists(mcp_server_dir)}")
    print(f"Server URL: http://0.0.0.0:{port}")
    
    # Print the MCP server URL for other services to use
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
