#!/usr/bin/env python3
"""
HTTP Wrapper for EnergyPlus MCP Server

This script provides an HTTP API interface to the EnergyPlus MCP server,
allowing web-based access to EnergyPlus building energy simulation tools.

Usage:
    python http-wrapper.py [--host HOST] [--port PORT]

Example:
    python http-wrapper.py --host 0.0.0.0 --port 8080
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add the energyplus-mcp-server to the Python path
current_dir = Path(__file__).parent
mcp_server_dir = current_dir / "EnergyPlus-MCP" / "energyplus-mcp-server"
sys.path.insert(0, str(mcp_server_dir))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("Error: Required packages not installed.")
    print("Please install with: pip install fastapi uvicorn")
    sys.exit(1)

# Import MCP server components
try:
    from energyplus_mcp_server.server import mcp, ep_manager, config
    from energyplus_mcp_server.config import get_config
except ImportError as e:
    print(f"Error importing MCP server: {e}")
    print("Make sure you're running this from the correct directory with the EnergyPlus-MCP repository.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="EnergyPlus MCP HTTP Wrapper",
    description="HTTP API wrapper for EnergyPlus Model Context Protocol server",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store available tools
available_tools = {}

def get_available_tools():
    """Get list of available MCP tools"""
    global available_tools
    if not available_tools:
        # Extract tools from the MCP server
        for tool_name, tool_func in mcp._tools.items():
            available_tools[tool_name] = {
                "name": tool_name,
                "description": tool_func.__doc__ or "No description available",
                "parameters": getattr(tool_func, '__annotations__', {})
            }
    return available_tools

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>EnergyPlus MCP HTTP Wrapper</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .method { color: #0066cc; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>EnergyPlus MCP HTTP Wrapper</h1>
        <p>HTTP API wrapper for EnergyPlus Model Context Protocol server</p>
        
        <h2>Available Endpoints:</h2>
        <div class="endpoint">
            <span class="method">GET</span> / - This page
        </div>
        <div class="endpoint">
            <span class="method">GET</span> /tools - List all available tools
        </div>
        <div class="endpoint">
            <span class="method">POST</span> /tools/{tool_name} - Execute a specific tool
        </div>
        <div class="endpoint">
            <span class="method">GET</span> /status - Server status
        </div>
        <div class="endpoint">
            <span class="method">GET</span> /health - Health check
        </div>
        
        <h2>Example Usage:</h2>
        <pre>
# List available tools
curl http://localhost:8080/tools

# Execute a tool
curl -X POST http://localhost:8080/tools/get_server_status

# Execute tool with parameters
curl -X POST http://localhost:8080/tools/load_idf_model \\
  -H "Content-Type: application/json" \\
  -d '{"idf_path": "sample_files/1ZoneUncontrolled.idf"}'
        </pre>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status")
async def get_status():
    """Get server status"""
    try:
        # Use the MCP tool to get status
        result = await mcp._tools["get_server_status"]()
        return {"status": "running", "details": result}
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/tools")
async def list_tools():
    """List all available tools"""
    try:
        tools = get_available_tools()
        return {
            "tools": list(tools.values()),
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Get information about a specific tool"""
    try:
        tools = get_available_tools()
        if tool_name not in tools:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        return tools[tool_name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: Request):
    """Execute a specific tool with parameters"""
    try:
        # Get the tool function
        if tool_name not in mcp._tools:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        tool_func = mcp._tools[tool_name]
        
        # Get request body
        try:
            body = await request.json()
        except:
            body = {}
        
        # Extract parameters from request body
        params = body.get("parameters", {})
        
        # Execute the tool
        logger.info(f"Executing tool '{tool_name}' with parameters: {params}")
        
        # Call the tool function with parameters
        if params:
            result = await tool_func(**params)
        else:
            result = await tool_func()
        
        return {
            "tool": tool_name,
            "parameters": params,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")

@app.get("/files")
async def list_files():
    """List available sample files"""
    try:
        # Use the MCP tool to list files
        result = await mcp._tools["list_available_files"]()
        return {"files": result}
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate")
async def run_simulation(request: Request):
    """Run an EnergyPlus simulation"""
    try:
        body = await request.json()
        
        # Extract required parameters
        idf_path = body.get("idf_path")
        if not idf_path:
            raise HTTPException(status_code=400, detail="idf_path is required")
        
        # Optional parameters
        weather_file = body.get("weather_file")
        output_directory = body.get("output_directory")
        annual = body.get("annual", True)
        design_day = body.get("design_day", False)
        readvars = body.get("readvars", True)
        expandobjects = body.get("expandobjects", True)
        
        # Execute simulation
        result = await mcp._tools["run_energyplus_simulation"](
            idf_path=idf_path,
            weather_file=weather_file,
            output_directory=output_directory,
            annual=annual,
            design_day=design_day,
            readvars=readvars,
            expandobjects=expandobjects
        )
        
        return {
            "simulation": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Main function to run the HTTP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EnergyPlus MCP HTTP Wrapper")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    logger.info(f"Starting EnergyPlus MCP HTTP Wrapper on {args.host}:{args.port}")
    logger.info(f"Available tools: {len(get_available_tools())}")
    
    uvicorn.run(
        "http-wrapper:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()
