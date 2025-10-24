#!/usr/bin/env python3
"""
REAL ENERGYPLUS API - Step by Step Implementation
Uses actual EnergyPlus simulation engine
"""

import json
import os
import socket
import threading
import subprocess
import tempfile
import shutil
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealEnergyPlusAPI:
    def __init__(self):
        self.version = "25.0.0"
        self.host = '0.0.0.0'
        self.port = int(os.environ.get('PORT', 8080))
        
        # EnergyPlus paths
        self.energyplus_exe = os.environ.get('ENERGYPLUS_EXE', '/usr/local/EnergyPlus-23-2-0/energyplus')
        self.energyplus_idd = os.environ.get('ENERGYPLUS_IDD', '/usr/local/EnergyPlus-23-2-0/Energy+.idd')
        
        # Working directories
        self.inputs_dir = '/app/inputs'
        self.outputs_dir = '/app/outputs'
        self.logs_dir = '/app/logs'
        
        # Create directories
        os.makedirs(self.inputs_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        logger.info(f"🚀 Real EnergyPlus API v{self.version} starting...")
        logger.info(f"📊 EnergyPlus EXE: {self.energyplus_exe}")
        logger.info(f"📊 EnergyPlus IDD: {self.energyplus_idd}")
        
        # Test EnergyPlus installation
        self.test_energyplus()
    
    def test_energyplus(self):
        """Test EnergyPlus installation"""
        try:
            result = subprocess.run([self.energyplus_exe, '--version'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"✅ EnergyPlus installed: {result.stdout.strip()}")
            else:
                logger.error(f"❌ EnergyPlus test failed: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ EnergyPlus test error: {e}")
    
    def create_response(self, status_code, body):
        """Create HTTP response"""
        response = f"HTTP/1.1 {status_code}\r\n"
        response += f"Content-Type: application/json\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "\r\n"
        response += body
        return response
    
    def run_energyplus_simulation(self, idf_content, weather_content=None):
        """Run actual EnergyPlus simulation"""
        try:
            logger.info("⚡ Starting EnergyPlus simulation...")
            
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write IDF file
                idf_path = os.path.join(temp_dir, 'input.idf')
                with open(idf_path, 'w') as f:
                    f.write(idf_content)
                
                # Write weather file if provided
                weather_path = None
                if weather_content:
                    weather_path = os.path.join(temp_dir, 'input.epw')
                    with open(weather_path, 'w') as f:
                        f.write(weather_content)
                
                # Set output directory
                output_dir = os.path.join(temp_dir, 'output')
                os.makedirs(output_dir, exist_ok=True)
                
                # Build EnergyPlus command
                cmd = [
                    self.energyplus_exe,
                    '--idd', self.energyplus_idd,
                    '--output-directory', output_dir,
                    '--readvars',
                    '--expandobjects'
                ]
                
                if weather_path:
                    cmd.extend(['--weather', weather_path])
                
                cmd.append(idf_path)
                
                logger.info(f"🔧 Running: {' '.join(cmd)}")
                
                # Run EnergyPlus
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                logger.info(f"📊 EnergyPlus exit code: {result.returncode}")
                logger.info(f"📊 EnergyPlus stdout: {result.stdout[:500]}...")
                if result.stderr:
                    logger.warning(f"⚠️ EnergyPlus stderr: {result.stderr[:500]}...")
                
                # Parse results
                if result.returncode == 0:
                    return self.parse_energyplus_output(output_dir)
                else:
                    logger.error(f"❌ EnergyPlus simulation failed with exit code {result.returncode}")
                    return self.create_error_response(f"EnergyPlus simulation failed: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            logger.error("❌ EnergyPlus simulation timed out")
            return self.create_error_response("EnergyPlus simulation timed out")
        except Exception as e:
            logger.error(f"❌ EnergyPlus simulation error: {e}")
            return self.create_error_response(f"Simulation error: {str(e)}")
    
    def parse_energyplus_output(self, output_dir):
        """Parse EnergyPlus output files"""
        try:
            logger.info("📊 Parsing EnergyPlus output...")
            
            # Look for output files
            output_files = os.listdir(output_dir)
            logger.info(f"📁 Output files: {output_files}")
            
            # Parse CSV files for energy data
            energy_data = {}
            for file in output_files:
                if file.endswith('.csv'):
                    csv_path = os.path.join(output_dir, file)
                    energy_data.update(self.parse_csv_file(csv_path))
            
            # Parse HTML files for summary
            for file in output_files:
                if file.endswith('.html'):
                    html_path = os.path.join(output_dir, file)
                    energy_data.update(self.parse_html_file(html_path))
            
            # Build response
            response = {
                "version": self.version,
                "simulation_status": "success",
                "energyplus_version": "23.2.0",
                "real_simulation": True,
                "processing_time": datetime.now().isoformat(),
                **energy_data
            }
            
            logger.info("✅ EnergyPlus output parsed successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Output parsing failed: {e}")
            return self.create_error_response(f"Output parsing failed: {str(e)}")
    
    def parse_csv_file(self, csv_path):
        """Parse EnergyPlus CSV output file"""
        try:
            energy_data = {}
            
            with open(csv_path, 'r') as f:
                lines = f.readlines()
            
            # Look for energy consumption data
            for line in lines:
                if 'Electricity' in line or 'Gas' in line or 'District Heating' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            value = float(parts[1].strip())
                            energy_data[parts[0].strip()] = value
                        except:
                            pass
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ CSV parsing failed: {e}")
            return {}
    
    def parse_html_file(self, html_path):
        """Parse EnergyPlus HTML summary file"""
        try:
            energy_data = {}
            
            with open(html_path, 'r') as f:
                content = f.read()
            
            # Extract key metrics from HTML
            # This is a simplified parser - you might need to enhance it
            if 'Total Site Energy' in content:
                # Extract total energy consumption
                pass
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ HTML parsing failed: {e}")
            return {}
    
    def create_error_response(self, message):
        """Create error response"""
        return {
            "version": self.version,
            "simulation_status": "error",
            "error_message": message,
            "real_simulation": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_request(self, client_socket, address):
        """Handle HTTP request"""
        try:
            logger.info(f"📥 Request from {address}")
            
            # Read request
            request = client_socket.recv(4096).decode('utf-8')
            
            # Parse request
            lines = request.split('\n')
            if not lines:
                response = self.create_response(400, json.dumps({"error": "Invalid request"}))
                client_socket.send(response.encode())
                return
            
            request_line = lines[0]
            parts = request_line.split(' ')
            if len(parts) < 2:
                response = self.create_response(400, json.dumps({"error": "Invalid request line"}))
                client_socket.send(response.encode())
                return
            
            method = parts[0]
            path = parts[1]
            
            logger.info(f"🔍 {method} {path}")
            
            # Handle endpoints
            if path == '/healthz' or path == '/health' or path == '/status':
                # Health check
                health_data = {
                    "status": "healthy",
                    "version": self.version,
                    "energyplus_available": os.path.exists(self.energyplus_exe),
                    "timestamp": datetime.now().isoformat()
                }
                response_body = json.dumps(health_data)
                response = self.create_response(200, response_body)
                client_socket.send(response.encode())
                
            elif path == '/simulate' and method == 'POST':
                # Simulation endpoint
                try:
                    # Find JSON in request
                    json_start = request.find('{')
                    if json_start == -1:
                        response = self.create_response(400, json.dumps({"error": "No JSON body"}))
                        client_socket.send(response.encode())
                        return
                    
                    json_body = request[json_start:]
                    data = json.loads(json_body)
                    
                    # Extract content
                    idf_content = data.get('idf_content', '')
                    weather_content = data.get('weather_content', '')
                    
                    logger.info(f"📊 Processing: IDF {len(idf_content)} bytes, Weather {len(weather_content)} bytes")
                    
                    if not idf_content:
                        response = self.create_response(400, json.dumps({"error": "No IDF content"}))
                        client_socket.send(response.encode())
                        return
                    
                    # Run EnergyPlus simulation
                    result = self.run_energyplus_simulation(idf_content, weather_content)
                    response_body = json.dumps(result, indent=2)
                    
                    response = self.create_response(200, response_body)
                    client_socket.send(response.encode())
                    
                except Exception as e:
                    logger.error(f"❌ Simulation error: {e}")
                    error_response = self.create_error_response(str(e))
                    response_body = json.dumps(error_response)
                    response = self.create_response(500, response_body)
                    client_socket.send(response.encode())
                    
            else:
                # Default response
                default_data = {
                    "message": "Real EnergyPlus API",
                    "version": self.version,
                    "endpoints": ["/simulate", "/health", "/healthz", "/status"],
                    "real_simulation": True
                }
                response_body = json.dumps(default_data, indent=2)
                response = self.create_response(200, response_body)
                client_socket.send(response.encode())
                
        except Exception as e:
            logger.error(f"❌ Request handling error: {e}")
            try:
                error_response = self.create_response(500, json.dumps({"error": str(e)}))
                client_socket.send(error_response.encode())
            except:
                pass
    
    def start_server(self):
        """Start server"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            logger.info(f"🚀 Real EnergyPlus API server started on {self.host}:{self.port}")
            
            while True:
                try:
                    client_socket, address = server_socket.accept()
                    thread = threading.Thread(target=self.handle_request, args=(client_socket, address))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    logger.error(f"❌ Connection error: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Server startup error: {e}")

if __name__ == "__main__":
    import time
    time.sleep(2)  # Startup delay
    
    api = RealEnergyPlusAPI()
    api.start_server()
