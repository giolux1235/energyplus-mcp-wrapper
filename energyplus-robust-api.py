#!/usr/bin/env python3
"""
ROBUST ENERGYPLUS API - Real simulation with proper output parsing
No mock data - only real results or clear errors
"""

import json
import os
import socket
import threading
import subprocess
import tempfile
from datetime import datetime
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustEnergyPlusAPI:
    def __init__(self):
        self.version = "27.1.0"
        self.host = '0.0.0.0'
        self.port = int(os.environ.get('PORT', 8080))
        
        # EnergyPlus paths
        self.energyplus_exe = os.environ.get('ENERGYPLUS_EXE', '/usr/local/EnergyPlus-25-1-0/energyplus')
        self.energyplus_idd = os.environ.get('ENERGYPLUS_IDD', '/usr/local/EnergyPlus-25-1-0/Energy+.idd')
        
        logger.info(f"🚀 Robust EnergyPlus API v{self.version} starting...")
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
    
    def read_request_simple(self, client_socket):
        """Simple request reading with better handling"""
        try:
            request = b''
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                request += chunk
                if b'\r\n\r\n' in request:
                    header_end = request.find(b'\r\n\r\n')
                    headers = request[:header_end].decode('utf-8')
                    
                    if 'Content-Length:' in headers:
                        for line in headers.split('\r\n'):
                            if line.startswith('Content-Length:'):
                                content_length = int(line.split(':')[1].strip())
                                body_start = header_end + 4
                                expected_total = body_start + content_length
                                
                                while len(request) < expected_total:
                                    chunk = client_socket.recv(8192)
                                    if not chunk:
                                        break
                                    request += chunk
                                break
                    break
            
            return request.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f"❌ Error reading request: {e}")
            return ""
    
    def run_energyplus_simulation(self, idf_content, weather_content=None):
        """Run actual EnergyPlus simulation"""
        try:
            logger.info("⚡ Starting REAL EnergyPlus simulation...")
            logger.info(f"📊 IDF size: {len(idf_content)} bytes")
            if weather_content:
                logger.info(f"📊 Weather size: {len(weather_content)} bytes")
            
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write IDF file
                idf_path = os.path.join(temp_dir, 'input.idf')
                with open(idf_path, 'w') as f:
                    f.write(idf_content)
                logger.info(f"📄 IDF file written: {idf_path}")
                
                # Write weather file if provided
                weather_path = None
                if weather_content:
                    weather_path = os.path.join(temp_dir, 'weather.epw')
                    with open(weather_path, 'w') as f:
                        f.write(weather_content)
                    logger.info(f"🌤️ Weather file written: {weather_path}")
                
                # Create output directory
                output_dir = os.path.join(temp_dir, 'output')
                os.makedirs(output_dir, exist_ok=True)
                
                # Build EnergyPlus command
                cmd = [self.energyplus_exe]
                if weather_path:
                    cmd.extend(['-w', weather_path])
                cmd.extend([
                    '-d', output_dir,  # Output directory
                    '-i', self.energyplus_idd,  # IDD file
                    idf_path  # Input IDF file
                ])
                
                logger.info(f"🔧 Running EnergyPlus command...")
                logger.info(f"📋 Command: {' '.join(cmd)}")
                
                # Run EnergyPlus
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                logger.info(f"📊 EnergyPlus exit code: {result.returncode}")
                logger.info(f"📊 STDOUT length: {len(result.stdout)} chars")
                logger.info(f"📊 STDERR length: {len(result.stderr)} chars")
                
                # Check output directory
                output_files = os.listdir(output_dir)
                logger.info(f"📁 Output files generated: {output_files}")
                
                # Parse results - even if exit code != 0, we might have partial results
                if output_files:
                    return self.parse_energyplus_output(output_dir, result.returncode, result.stderr)
                else:
                    error_msg = f"EnergyPlus generated no output files. Exit code: {result.returncode}"
                    if result.stderr:
                        # Get first 500 chars of error
                        error_msg += f"\nError: {result.stderr[:500]}"
                    logger.error(f"❌ {error_msg}")
                    return self.create_error_response(error_msg)
                    
        except subprocess.TimeoutExpired:
            error_msg = "EnergyPlus simulation timed out (5 minutes)"
            logger.error(f"❌ {error_msg}")
            return self.create_error_response(error_msg)
        except Exception as e:
            error_msg = f"Simulation error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self.create_error_response(error_msg)
    
    def parse_energyplus_output(self, output_dir, exit_code, stderr):
        """Parse EnergyPlus output files - ESO, MTR, ERR, etc."""
        try:
            logger.info("📊 Parsing EnergyPlus output (ROBUST VERSION)...")
            
            output_files = os.listdir(output_dir)
            logger.info(f"📁 Files to parse: {output_files}")
            
            # Parse ERR file first to check for errors
            err_file = None
            for file in output_files:
                if file.endswith('.err'):
                    err_file = os.path.join(output_dir, file)
                    break
            
            warnings = []
            fatal_errors = []
            if err_file:
                with open(err_file, 'r') as f:
                    err_content = f.read()
                logger.info(f"📊 Error file content ({len(err_content)} chars):")
                logger.info(err_content[:1000])  # First 1000 chars
                
                # Check for fatal errors
                if '** Fatal' in err_content:
                    for line in err_content.split('\n'):
                        if '** Fatal' in line or '**  Fatal' in line:
                            fatal_errors.append(line.strip())
                
                # Check for warnings
                if '** Warning' in err_content or '** Severe' in err_content:
                    for line in err_content.split('\n'):
                        if '** Warning' in line or '** Severe' in line:
                            warnings.append(line.strip())
            
            # If fatal errors, return error response with details
            if fatal_errors:
                error_msg = f"EnergyPlus simulation failed with fatal errors:\n" + "\n".join(fatal_errors[:5])
                logger.error(f"❌ {error_msg}")
                return self.create_error_response(error_msg, warnings=warnings)
            
            # Parse output data
            energy_data = self.parse_all_output_files(output_dir)
            
            # If no energy data found, explain why
            if not energy_data or energy_data.get('total_energy_consumption', 0) == 0:
                error_msg = "EnergyPlus ran but produced no energy results. "
                error_msg += "This usually means:\n"
                error_msg += "1. IDF file is missing required objects (RunPeriod, Schedules, etc.)\n"
                error_msg += "2. Simulation ran for 0 days\n"
                error_msg += "3. Output:* objects are missing from IDF\n"
                if warnings:
                    error_msg += f"\nWarnings: {len(warnings)} found"
                logger.error(f"❌ {error_msg}")
                return self.create_error_response(error_msg, warnings=warnings[:10])
            
            # Build successful response
            response = {
                "version": self.version,
                "simulation_status": "success",
                "energyplus_version": "25.1.0",
                "real_simulation": True,
                "exit_code": exit_code,
                "warnings_count": len(warnings),
                "warnings": warnings[:10] if warnings else [],
                "processing_time": datetime.now().isoformat(),
                **energy_data
            }
            
            logger.info(f"✅ EnergyPlus output parsed successfully - REAL DATA!")
            logger.info(f"✅ Total energy: {energy_data.get('total_energy_consumption', 0)} kWh")
            return response
            
        except Exception as e:
            error_msg = f"Output parsing failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self.create_error_response(error_msg)
    
    def parse_all_output_files(self, output_dir):
        """Parse all output files - CSV, ESO, MTR, HTML"""
        energy_data = {}
        
        output_files = os.listdir(output_dir)
        
        # Try CSV files first
        for file in output_files:
            if file.endswith('Meter.csv') or file.endswith('Table.csv') or file.endswith('.csv'):
                csv_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing CSV: {file}")
                data = self.parse_energyplus_csv(csv_path)
                if data:
                    energy_data.update(data)
                    logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try MTR files (meter files) - these are also CSV format
        for file in output_files:
            if file.endswith('.mtr'):
                mtr_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing MTR: {file}")
                data = self.parse_energyplus_mtr(mtr_path)
                if data:
                    energy_data.update(data)
                    logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try HTML summary
        for file in output_files:
            if file.endswith('Table.html') or file.endswith('tbl.html') or file.endswith('.html'):
                html_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing HTML: {file}")
                data = self.parse_energyplus_html(html_path)
                if data:
                    energy_data.update(data)
                    logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try ESO file (EnergyPlus Standard Output)
        for file in output_files:
            if file.endswith('.eso'):
                eso_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing ESO: {file}")
                data = self.parse_energyplus_eso(eso_path)
                if data:
                    energy_data.update(data)
                    logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        return energy_data
    
    def parse_energyplus_mtr(self, mtr_path):
        """Parse EnergyPlus MTR (meter) files - CSV format with energy data"""
        try:
            with open(mtr_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 MTR content: {len(content)} chars")
            logger.info(f"📊 First 500 chars:\n{content[:500]}")
            
            energy_data = {}
            total = 0
            heating = 0
            cooling = 0
            lighting = 0
            equipment = 0
            
            lines = content.split('\n')
            for line in lines:
                if not line.strip() or line.startswith('Date'):
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2:
                    continue
                
                # MTR files have format: Date/Time, MeterName [Units], Value
                # Get the meter name and value
                try:
                    # Value is usually the last column
                    value = float(parts[-1])
                    if value <= 0:
                        continue
                    
                    # Get meter name (second column usually)
                    meter_name = parts[1].lower() if len(parts) > 1 else ''
                    
                    # Convert J to kWh if needed (1 J = 2.77778e-7 kWh)
                    if '[j]' in meter_name:
                        value = value * 2.77778e-7
                    
                    # Categorize based on meter name
                    if 'electricity' in meter_name or 'electric' in meter_name:
                        total += value
                        
                        if 'heat' in meter_name:
                            heating += value
                        elif 'cool' in meter_name:
                            cooling += value
                        elif 'light' in meter_name or 'interior lights' in meter_name:
                            lighting += value
                        elif 'equipment' in meter_name or 'interior equipment' in meter_name:
                            equipment += value
                        else:
                            # Generic electricity
                            equipment += value
                    
                    elif 'gas' in meter_name or 'naturalgas' in meter_name:
                        total += value
                        heating += value  # Gas is typically for heating
                        
                except (ValueError, IndexError):
                    continue
            
            if total > 0:
                energy_data['total_energy_consumption'] = round(total, 2)
                energy_data['heating_energy'] = round(heating, 2)
                energy_data['cooling_energy'] = round(cooling, 2)
                energy_data['lighting_energy'] = round(lighting, 2)
                energy_data['equipment_energy'] = round(equipment, 2)
                logger.info(f"✅ MTR parsed: Total={total:.2f} kWh")
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ MTR parse error: {e}")
            return {}
    
    def parse_energyplus_csv(self, csv_path):
        """Parse EnergyPlus CSV files"""
        try:
            with open(csv_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 CSV content: {len(content)} chars")
            logger.info(f"📊 First 500 chars:\n{content[:500]}")
            
            energy_data = {}
            total = 0
            heating = 0
            cooling = 0
            lighting = 0
            equipment = 0
            
            lines = content.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                # Look for energy values
                if any(keyword in line.lower() for keyword in ['electricity', 'gas', 'energy']):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 2:
                        try:
                            value = float(parts[-1])  # Last column is usually the value
                            if value > 0:
                                total += value
                                
                                # Categorize
                                line_lower = line.lower()
                                if 'heat' in line_lower:
                                    heating += value
                                elif 'cool' in line_lower:
                                    cooling += value
                                elif 'light' in line_lower:
                                    lighting += value
                                elif 'equipment' in line_lower or 'plug' in line_lower:
                                    equipment += value
                        except:
                            pass
            
            if total > 0:
                energy_data['total_energy_consumption'] = round(total, 2)
                energy_data['heating_energy'] = round(heating, 2)
                energy_data['cooling_energy'] = round(cooling, 2)
                energy_data['lighting_energy'] = round(lighting, 2)
                energy_data['equipment_energy'] = round(equipment, 2)
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ CSV parse error: {e}")
            return {}
    
    def parse_energyplus_html(self, html_path):
        """Parse EnergyPlus HTML summary"""
        try:
            with open(html_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 HTML content: {len(content)} chars")
            
            energy_data = {}
            
            # Extract values using regex
            patterns = {
                'total_energy_consumption': r'Total\s+Site\s+Energy.*?(\d+\.?\d*)',
                'heating_energy': r'Heating.*?(\d+\.?\d*)\s*(?:GJ|kWh)',
                'cooling_energy': r'Cooling.*?(\d+\.?\d*)\s*(?:GJ|kWh)',
                'lighting_energy': r'(?:Interior\s+)?Lighting.*?(\d+\.?\d*)\s*(?:GJ|kWh)',
                'equipment_energy': r'(?:Interior\s+)?Equipment.*?(\d+\.?\d*)\s*(?:GJ|kWh)',
                'building_area': r'Total\s+(?:Building|Floor)\s+Area.*?(\d+\.?\d*)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        # Convert GJ to kWh if needed
                        if 'GJ' in match.group(0):
                            value = value * 277.778  # 1 GJ = 277.778 kWh
                        energy_data[key] = round(value, 2)
                    except:
                        pass
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ HTML parse error: {e}")
            return {}
    
    def parse_energyplus_eso(self, eso_path):
        """Parse EnergyPlus ESO file (most reliable source)"""
        try:
            with open(eso_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 ESO content: {len(content)} chars")
            logger.info(f"📊 First 1000 chars:\n{content[:1000]}")
            
            # ESO files have a data dictionary and values
            # This is complex - for now, just check if it has data
            lines = content.split('\n')
            data_lines = [l for l in lines if l.strip() and not l.startswith('!') and ',' in l]
            
            logger.info(f"📊 ESO data lines: {len(data_lines)}")
            
            # If we have data, indicate simulation ran
            if len(data_lines) > 10:
                return {'eso_data_lines': len(data_lines)}
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ ESO parse error: {e}")
            return {}
    
    def create_error_response(self, error_msg, warnings=None):
        """Create error response with details"""
        response = {
            "version": self.version,
            "simulation_status": "error",
            "energyplus_version": "25.1.0",
            "real_simulation": True,
            "error_message": error_msg,
            "processing_time": datetime.now().isoformat(),
        }
        if warnings:
            response['warnings'] = warnings
        return response
    
    def handle_request(self, client_socket):
        """Handle incoming HTTP request"""
        try:
            # Read request
            request_text = self.read_request_simple(client_socket)
            
            # Parse request
            if not request_text:
                self.send_error_response(client_socket, "Empty request")
                return
            
            # Check if health check
            if 'GET /health' in request_text or 'GET /healthz' in request_text:
                self.handle_health(client_socket)
                return
            
            # Check if simulate endpoint
            if 'POST /simulate' in request_text:
                self.handle_simulate(client_socket, request_text)
                return
            
            # Unknown endpoint
            self.send_error_response(client_socket, "Unknown endpoint")
            
        except Exception as e:
            logger.error(f"❌ Request handling error: {e}")
            self.send_error_response(client_socket, str(e))
    
    def handle_health(self, client_socket):
        """Handle health check"""
        response = {
            "status": "healthy",
            "version": self.version,
            "energyplus_available": os.path.exists(self.energyplus_exe),
            "timestamp": datetime.now().isoformat()
        }
        self.send_json_response(client_socket, response)
    
    def handle_simulate(self, client_socket, request_text):
        """Handle simulation request"""
        try:
            # Extract JSON body
            body_start = request_text.find('\r\n\r\n') + 4
            body = request_text[body_start:]
            
            logger.info(f"📊 Request body size: {len(body)} bytes")
            
            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parse error: {e}")
                self.send_error_response(client_socket, f"Invalid JSON: {str(e)}")
                return
            
            # Extract IDF and weather content
            idf_content = data.get('idf_content', '')
            weather_content = data.get('weather_content', '')
            
            if not idf_content:
                self.send_error_response(client_socket, "Missing idf_content")
                return
            
            logger.info(f"📊 IDF content: {len(idf_content)} bytes")
            logger.info(f"📊 Weather content: {len(weather_content)} bytes")
            
            # Run simulation
            result = self.run_energyplus_simulation(idf_content, weather_content)
            
            # Send response
            self.send_json_response(client_socket, result)
            
        except Exception as e:
            logger.error(f"❌ Simulate error: {e}")
            self.send_error_response(client_socket, str(e))
    
    def send_json_response(self, client_socket, data):
        """Send JSON HTTP response"""
        try:
            json_data = json.dumps(data, indent=2)
            response = f"HTTP/1.1 200 OK\r\n"
            response += f"Content-Type: application/json\r\n"
            response += f"Content-Length: {len(json_data)}\r\n"
            response += f"Access-Control-Allow-Origin: *\r\n"
            response += f"\r\n"
            response += json_data
            
            client_socket.sendall(response.encode('utf-8'))
        except Exception as e:
            logger.error(f"❌ Send response error: {e}")
        finally:
            client_socket.close()
    
    def send_error_response(self, client_socket, error_msg):
        """Send error HTTP response"""
        try:
            response_data = {
                "version": self.version,
                "simulation_status": "error",
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            self.send_json_response(client_socket, response_data)
        except:
            client_socket.close()
    
    def start_server(self):
        """Start HTTP server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        
        logger.info(f"🚀 Robust EnergyPlus API v{self.version} running on {self.host}:{self.port}")
        logger.info("📊 NO MOCK DATA - Only real simulation results!")
        
        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=self.handle_request, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()

if __name__ == "__main__":
    api = RobustEnergyPlusAPI()
    api.start_server()

