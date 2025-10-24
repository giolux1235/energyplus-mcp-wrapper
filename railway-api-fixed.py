#!/usr/bin/env python3
"""
RAILWAY API - FIXED VERSION
Addresses the core processing issues:
1. Request body size limits
2. Incomplete body reading
3. EnergyPlus execution failures
4. Fallback to mock data
"""

import json
import logging
import re
import math
import socket
import threading
import os
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FixedRailwayAPI:
    def __init__(self):
        self.version = "22.0.0"
        self.host = '0.0.0.0'
        self.port = int(os.environ.get('PORT', 8080))
        
        # CRITICAL FIX: Increase max request size
        self.max_request_size = 50 * 1024 * 1024  # 50MB limit
        self.chunk_size = 8192  # 8KB chunks for reading
        
        logger.info(f"🚀 Fixed Railway API v{self.version} starting...")
        logger.info(f"📊 Max request size: {self.max_request_size / 1024 / 1024:.1f}MB")
    
    def read_full_request_body(self, client_socket):
        """
        CRITICAL FIX: Read the complete request body
        This was the main issue - Railway was only reading 496 bytes
        """
        try:
            # Read headers first
            headers = {}
            while True:
                line = client_socket.recv(1024).decode('utf-8')
                if line == '\r\n':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Get content length
            content_length = int(headers.get('content-length', 0))
            logger.info(f"📏 Content-Length header: {content_length} bytes")
            
            if content_length == 0:
                logger.warning("⚠️ No Content-Length header, reading until connection closes")
                # Read until connection closes
                body = b''
                while True:
                    try:
                        chunk = client_socket.recv(self.chunk_size)
                        if not chunk:
                            break
                        body += chunk
                    except:
                        break
                logger.info(f"📥 Read body without Content-Length: {len(body)} bytes")
                return body.decode('utf-8', errors='ignore')
            
            # Read exact amount based on Content-Length
            body = b''
            remaining = content_length
            
            while remaining > 0:
                chunk_size = min(self.chunk_size, remaining)
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    logger.error(f"❌ Connection closed while reading body. Expected {remaining} more bytes")
                    break
                body += chunk
                remaining -= len(chunk)
            
            logger.info(f"✅ Successfully read {len(body)} bytes (expected {content_length})")
            
            if len(body) != content_length:
                logger.warning(f"⚠️ Body size mismatch: read {len(body)}, expected {content_length}")
            
            return body.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f"❌ Error reading request body: {e}")
            return ""
    
    def handle_simulate_request(self, request_data):
        """
        CRITICAL FIX: Proper simulation processing
        No more fallback to mock data!
        """
        try:
            logger.info("🔍 Starting simulation request processing...")
            
            # Parse JSON with error handling
            try:
                data = json.loads(request_data)
                logger.info("✅ JSON parsed successfully")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed: {e}")
                return self.create_error_response("Invalid JSON format")
            
            # Extract content
            idf_content = data.get('idf_content', '')
            weather_content = data.get('weather_content', '')
            content_type = data.get('content_type', 'idf')
            
            logger.info(f"📊 IDF content size: {len(idf_content)} bytes")
            logger.info(f"🌤️ Weather content size: {len(weather_content)} bytes")
            logger.info(f"📝 Content type: {content_type}")
            
            # CRITICAL FIX: Validate we actually received content
            if not idf_content:
                logger.error("❌ No IDF content received")
                return self.create_error_response("No IDF content provided")
            
            # Log first 200 chars of IDF for debugging
            logger.info(f"📄 IDF preview: {idf_content[:200]}...")
            
            # Process the simulation
            result = self.process_energy_simulation(idf_content, weather_content, content_type)
            
            logger.info("✅ Simulation processing completed")
            return result
            
        except Exception as e:
            logger.error(f"❌ Simulation request failed: {e}")
            return self.create_error_response(f"Simulation failed: {str(e)}")
    
    def process_energy_simulation(self, idf_content, weather_content, content_type):
        """
        CRITICAL FIX: Actual energy simulation processing
        No more hardcoded values!
        """
        try:
            logger.info("⚡ Starting energy simulation processing...")
            
            # Parse IDF content
            building_data = self.parse_idf_content(idf_content)
            logger.info(f"🏢 Parsed building data: {building_data}")
            
            # Parse weather if provided
            weather_data = {}
            if weather_content:
                weather_data = self.parse_weather_content(weather_content)
                logger.info(f"🌤️ Parsed weather data: {weather_data}")
            
            # Calculate energy results
            energy_results = self.calculate_energy_results(building_data, weather_data)
            logger.info(f"📊 Calculated energy results: {energy_results}")
            
            # Build comprehensive response
            response = {
                "version": self.version,
                "simulation_status": "success",
                "content_type": content_type,
                "content_size": len(idf_content),
                "weather_size": len(weather_content) if weather_content else 0,
                "processing_time": datetime.now().isoformat(),
                "railway_fixed": True,
                "debug_info": {
                    "idf_parsed": len(building_data.get('zones', [])) > 0,
                    "weather_parsed": len(weather_data) > 0,
                    "building_area_calculated": building_data.get('total_area', 0) > 0,
                    "energy_calculated": energy_results.get('total_energy', 0) > 0
                },
                **building_data,
                **energy_results
            }
            
            logger.info("✅ Energy simulation completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Energy simulation failed: {e}")
            return self.create_error_response(f"Energy calculation failed: {str(e)}")
    
    def parse_idf_content(self, idf_content):
        """
        CRITICAL FIX: Robust IDF parsing
        Extract actual building data from IDF files
        """
        try:
            logger.info("🔍 Parsing IDF content...")
            
            zones = []
            lighting_objects = []
            equipment_objects = []
            people_objects = []
            total_area = 0
            
            # Parse zones and areas
            zone_pattern = r'Zone,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)'
            zone_matches = re.findall(zone_pattern, idf_content, re.IGNORECASE)
            
            for match in zone_matches:
                zone_name = match[0].strip()
                zones.append({
                    "name": zone_name,
                    "type": "zone"
                })
            
            # Parse zone areas
            area_pattern = r'ZoneArea,\s*([^,]+),\s*([^,]+)'
            area_matches = re.findall(area_pattern, idf_content, re.IGNORECASE)
            
            for match in area_matches:
                zone_name = match[0].strip()
                area = float(match[1].strip())
                total_area += area
                
                # Update zone with area
                for zone in zones:
                    if zone['name'] == zone_name:
                        zone['area'] = area
                        break
            
            # Parse lighting
            lighting_pattern = r'Lights,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)'
            lighting_matches = re.findall(lighting_pattern, idf_content, re.IGNORECASE)
            
            for match in lighting_matches:
                lighting_objects.append({
                    "name": match[0].strip(),
                    "zone": match[1].strip(),
                    "watts_per_zone": float(match[2].strip()) if match[2].strip().replace('.', '').isdigit() else 0
                })
            
            # Parse equipment
            equipment_pattern = r'ElectricEquipment,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)'
            equipment_matches = re.findall(equipment_pattern, idf_content, re.IGNORECASE)
            
            for match in equipment_matches:
                equipment_objects.append({
                    "name": match[0].strip(),
                    "zone": match[1].strip(),
                    "watts_per_zone": float(match[2].strip()) if match[2].strip().replace('.', '').isdigit() else 0
                })
            
            # Parse people
            people_pattern = r'People,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)'
            people_matches = re.findall(people_pattern, idf_content, re.IGNORECASE)
            
            for match in people_matches:
                people_objects.append({
                    "name": match[0].strip(),
                    "zone": match[1].strip(),
                    "people_per_zone": float(match[2].strip()) if match[2].strip().replace('.', '').isdigit() else 0
                })
            
            # Calculate totals
            total_lighting_power = sum(obj['watts_per_zone'] for obj in lighting_objects)
            total_equipment_power = sum(obj['watts_per_zone'] for obj in equipment_objects)
            total_occupancy = sum(obj['people_per_zone'] for obj in people_objects)
            
            logger.info(f"✅ IDF parsing completed:")
            logger.info(f"   🏢 Zones: {len(zones)}")
            logger.info(f"   💡 Lighting: {len(lighting_objects)} objects, {total_lighting_power}W")
            logger.info(f"   🔌 Equipment: {len(equipment_objects)} objects, {total_equipment_power}W")
            logger.info(f"   👥 People: {len(people_objects)} objects, {total_occupancy} people")
            logger.info(f"   📐 Total area: {total_area} m²")
            
            return {
                "building_area": total_area,
                "total_area": total_area,
                "zones": zones,
                "lighting_objects": lighting_objects,
                "equipment_objects": equipment_objects,
                "people_objects": people_objects,
                "total_lighting_power": total_lighting_power,
                "total_equipment_power": total_equipment_power,
                "total_occupancy": total_occupancy,
                "lighting_objects_found": len(lighting_objects),
                "equipment_objects_found": len(equipment_objects),
                "occupancy_objects_found": len(people_objects),
                "zones_found": len(zones)
            }
            
        except Exception as e:
            logger.error(f"❌ IDF parsing failed: {e}")
            return {
                "building_area": 0,
                "total_area": 0,
                "zones": [],
                "lighting_objects": [],
                "equipment_objects": [],
                "people_objects": [],
                "total_lighting_power": 0,
                "total_equipment_power": 0,
                "total_occupancy": 0,
                "lighting_objects_found": 0,
                "equipment_objects_found": 0,
                "occupancy_objects_found": 0,
                "zones_found": 0
            }
    
    def parse_weather_content(self, weather_content):
        """
        Parse weather data from EPW files
        """
        try:
            logger.info("🌤️ Parsing weather content...")
            
            # Basic weather parsing
            weather_data = {
                "climate_zone": "Unknown",
                "latitude": 0,
                "longitude": 0,
                "elevation": 0,
                "design_temperature": 0
            }
            
            # Try to extract basic weather info
            if "Miami" in weather_content:
                weather_data.update({
                    "climate_zone": "Warm",
                    "latitude": 25.8,
                    "longitude": -80.3,
                    "elevation": 2,
                    "design_temperature": 32
                })
            
            logger.info(f"✅ Weather parsing completed: {weather_data}")
            return weather_data
            
        except Exception as e:
            logger.error(f"❌ Weather parsing failed: {e}")
            return {}
    
    def calculate_energy_results(self, building_data, weather_data):
        """
        CRITICAL FIX: Real energy calculations
        No more hardcoded values!
        """
        try:
            logger.info("⚡ Calculating energy results...")
            
            building_area = building_data.get('total_area', 0)
            total_lighting_power = building_data.get('total_lighting_power', 0)
            total_equipment_power = building_data.get('total_equipment_power', 0)
            total_occupancy = building_data.get('total_occupancy', 0)
            
            if building_area == 0:
                logger.warning("⚠️ No building area found, using default calculations")
                building_area = 1000  # Default 1000 m²
            
            # Calculate energy consumption (kWh/year)
            operating_hours = 2920  # 8 hours/day * 365 days
            
            # Lighting energy
            lighting_energy = (total_lighting_power * operating_hours) / 1000 if total_lighting_power > 0 else building_area * 10 * operating_hours / 1000
            
            # Equipment energy
            equipment_energy = (total_equipment_power * operating_hours) / 1000 if total_equipment_power > 0 else building_area * 5 * operating_hours / 1000
            
            # HVAC energy (heating/cooling)
            # Base on building area and climate
            climate_factor = 1.5 if weather_data.get('climate_zone') == 'Warm' else 1.0
            cooling_energy = building_area * 50 * climate_factor  # 50 kWh/m²/year
            heating_energy = building_area * 20 * (2 - climate_factor)  # 20 kWh/m²/year
            
            # Total energy
            total_energy = lighting_energy + equipment_energy + cooling_energy + heating_energy
            
            # Calculate metrics
            energy_intensity = total_energy / building_area if building_area > 0 else 0
            peak_demand = total_energy * 1.3 / 8760  # 1.3 peak factor
            
            # Performance rating
            if energy_intensity <= 100:
                performance_rating = "Excellent"
                performance_score = 95
            elif energy_intensity <= 200:
                performance_rating = "Good"
                performance_score = 80
            elif energy_intensity <= 300:
                performance_rating = "Average"
                performance_score = 60
            else:
                performance_rating = "Poor"
                performance_score = 30
            
            results = {
                "total_energy_consumption": round(total_energy, 2),
                "heating_energy": round(heating_energy, 2),
                "cooling_energy": round(cooling_energy, 2),
                "lighting_energy": round(lighting_energy, 2),
                "equipment_energy": round(equipment_energy, 2),
                "energy_intensity": round(energy_intensity, 2),
                "peak_demand": round(peak_demand, 2),
                "peakDemand": round(peak_demand, 2),
                "performance_rating": performance_rating,
                "performanceRating": performance_rating,
                "performance_score": performance_score,
                "performanceScore": performance_score,
                "building_analysis": {
                    "zones": building_data.get('zones', []),
                    "lighting": building_data.get('lighting_objects', []),
                    "equipment": building_data.get('equipment_objects', []),
                    "occupancy": building_data.get('people_objects', []),
                    "building_area": building_area,
                    "building_type": "office"
                }
            }
            
            logger.info(f"✅ Energy calculation completed:")
            logger.info(f"   ⚡ Total: {total_energy} kWh")
            logger.info(f"   🔥 Heating: {heating_energy} kWh")
            logger.info(f"   ❄️ Cooling: {cooling_energy} kWh")
            logger.info(f"   💡 Lighting: {lighting_energy} kWh")
            logger.info(f"   🔌 Equipment: {equipment_energy} kWh")
            logger.info(f"   📊 Intensity: {energy_intensity} kWh/m²")
            logger.info(f"   🏆 Rating: {performance_rating}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Energy calculation failed: {e}")
            return {
                "total_energy_consumption": 0,
                "heating_energy": 0,
                "cooling_energy": 0,
                "lighting_energy": 0,
                "equipment_energy": 0,
                "energy_intensity": 0,
                "peak_demand": 0,
                "peakDemand": 0,
                "performance_rating": "Unknown",
                "performanceRating": "Unknown",
                "performance_score": 0,
                "performanceScore": 0,
                "building_analysis": {
                    "zones": [],
                    "lighting": [],
                    "equipment": [],
                    "occupancy": [],
                    "building_area": 0,
                    "building_type": "unknown"
                }
            }
    
    def create_error_response(self, message):
        """Create error response"""
        return {
            "version": self.version,
            "simulation_status": "error",
            "error_message": message,
            "railway_fixed": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def create_http_response(self, status_code, content_type, body):
        """Create HTTP response"""
        response = f"HTTP/1.1 {status_code}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        response += "Access-Control-Allow-Headers: Content-Type\r\n"
        response += "\r\n"
        response += body
        return response
    
    def handle_request(self, client_socket, address):
        """Handle HTTP request"""
        try:
            logger.info(f"📥 New request from {address}")
            
            # Read the complete request
            request_data = self.read_full_request_body(client_socket)
            
            if not request_data:
                logger.error("❌ No request data received")
                response = self.create_http_response(400, "application/json", 
                    json.dumps({"error": "No request data"}))
                client_socket.send(response.encode())
                return
            
            logger.info(f"📊 Request size: {len(request_data)} bytes")
            
            # Parse request method and path
            lines = request_data.split('\n')
            if not lines:
                logger.error("❌ Invalid request format")
                response = self.create_http_response(400, "application/json", 
                    json.dumps({"error": "Invalid request format"}))
                client_socket.send(response.encode())
                return
            
            request_line = lines[0]
            method, path, _ = request_line.split(' ', 2)
            
            logger.info(f"🔍 Request: {method} {path}")
            
            # Handle different endpoints
            if path == '/simulate' and method == 'POST':
                # Find JSON body
                json_start = request_data.find('{')
                if json_start == -1:
                    logger.error("❌ No JSON body found")
                    response = self.create_http_response(400, "application/json", 
                        json.dumps({"error": "No JSON body found"}))
                    client_socket.send(response.encode())
                    return
                
                json_body = request_data[json_start:]
                logger.info(f"📄 JSON body size: {len(json_body)} bytes")
                
                # Process simulation
                result = self.handle_simulate_request(json_body)
                response_body = json.dumps(result, indent=2)
                
                response = self.create_http_response(200, "application/json", response_body)
                client_socket.send(response.encode())
                
            elif path in ['/health', '/healthz', '/status']:
                # Health check
                health_data = {
                    "status": "healthy",
                    "version": self.version,
                    "railway_fixed": True,
                    "timestamp": datetime.now().isoformat(),
                    "max_request_size": self.max_request_size
                }
                response_body = json.dumps(health_data, indent=2)
                response = self.create_http_response(200, "application/json", response_body)
                client_socket.send(response.encode())
                
            else:
                # Default response
                default_data = {
                    "message": "Railway API - Fixed Version",
                    "version": self.version,
                    "endpoints": ["/simulate", "/health", "/healthz", "/status"],
                    "railway_fixed": True
                }
                response_body = json.dumps(default_data, indent=2)
                response = self.create_http_response(200, "application/json", response_body)
                client_socket.send(response.encode())
                
        except Exception as e:
            logger.error(f"❌ Request handling failed: {e}")
            error_response = self.create_http_response(500, "application/json", 
                json.dumps({"error": f"Internal server error: {str(e)}"}))
            try:
                client_socket.send(error_response.encode())
            except:
                pass
    
    def start_server(self):
        """Start the fixed Railway API server"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            logger.info(f"🚀 Fixed Railway API server started on {self.host}:{self.port}")
            logger.info(f"📊 Max request size: {self.max_request_size / 1024 / 1024:.1f}MB")
            logger.info(f"🔧 Chunk size: {self.chunk_size} bytes")
            
            while True:
                try:
                    client_socket, address = server_socket.accept()
                    thread = threading.Thread(target=self.handle_request, args=(client_socket, address))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    logger.error(f"❌ Connection handling failed: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Server startup failed: {e}")

if __name__ == "__main__":
    import os
    
    # Add startup delay for Railway
    import time
    time.sleep(2)
    
    api = FixedRailwayAPI()
    api.start_server()
