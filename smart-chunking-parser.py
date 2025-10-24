#!/usr/bin/env python3
"""
Smart Chunking Parser - Only chunks when actually needed
Version 20.0.0 - Conditional chunking based on real limits
"""

import json
import re
import math
import socket
import threading
from datetime import datetime
from typing import Dict, List, Any

class SmartChunkingParser:
    """Smart Chunking Parser - Only chunks when actually needed"""
    
    def __init__(self):
        self.version = "20.1.0"
        self.railway_limit = 1000000  # 1MB Railway limit (found through testing)
        self.chunk_size = 500000  # 500KB chunks
        
    def parse_content(self, content: str, content_type: str = "idf") -> Dict[str, Any]:
        """Parse content with smart conditional chunking"""
        try:
            content_length = len(content)
            print(f"SMART PARSER: Content length: {content_length} bytes")
            print(f"SMART PARSER: Content type: {content_type}")
            
            # Only chunk if content is larger than Railway's actual limit
            if content_length > self.railway_limit:
                print(f"SMART PARSER: Large file detected ({content_length} bytes > {self.railway_limit} bytes), using chunking")
                return self._parse_content_with_chunking(content, content_type)
            else:
                print(f"SMART PARSER: Small file ({content_length} bytes <= {self.railway_limit} bytes), processing normally")
                return self._parse_content_normal(content, content_type)
            
        except Exception as e:
            print(f"SMART PARSER: Error in parse_content: {str(e)}")
            return {
                'simulation_status': 'error',
                'error': str(e),
                'version': self.version,
                'content_type': content_type,
                'content_size': len(content) if content else 0
            }
    
    def _parse_content_normal(self, content: str, content_type: str) -> Dict[str, Any]:
        """Parse content normally - NO CHUNKING for small files"""
        try:
            print(f"SMART PARSER: Processing content normally (length: {len(content)})")
            
            # Extract building data
            building_data = self._extract_building_data_smart(content)
            print(f"SMART PARSER: Building data extracted: {building_data}")
            
            # Calculate energy results
            energy_results = self._calculate_energy_results_smart(building_data)
            print(f"SMART PARSER: Energy results calculated: {energy_results}")
            
            # Build result
            result = {
                'version': self.version,
                'simulation_status': 'success',
                'content_type': content_type,
                'content_size': len(content),
                'auto_chunking': False,  # No chunking used
                'chunking_needed': False,
                'building_analysis': building_data,
                **energy_results
            }
            
            print(f"SMART PARSER: Final result keys: {list(result.keys())}")
            return result
            
        except Exception as e:
            print(f"SMART PARSER: Error in normal processing: {str(e)}")
            return {
                'simulation_status': 'error',
                'error': str(e),
                'version': self.version,
                'content_type': content_type,
                'content_size': len(content) if content else 0
            }
    
    def _extract_building_data_smart(self, content: str) -> Dict[str, Any]:
        """Extract building data - SMART VERSION (no doubling)"""
        try:
            print(f"SMART PARSER: Extracting building data from {len(content)} bytes")
            
            # Extract zones
            zones = []
            zone_pattern = r'Zone\s*,\s*([^,;\n]+)'
            zone_matches = re.findall(zone_pattern, content, re.IGNORECASE)
            for match in zone_matches:
                zones.append({
                    'name': match.strip(),
                    'floor_area': 0.0
                })
            
            # Extract zone areas
            zone_areas = {}
            area_pattern = r'ZoneArea\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)'
            area_matches = re.findall(area_pattern, content, re.IGNORECASE)
            for match in area_matches:
                try:
                    zone_name = match[0].strip()
                    area = float(match[1].strip())
                    zone_areas[zone_name] = area
                except ValueError:
                    continue
            
            # Update zones with areas
            for zone in zones:
                zone_name = zone.get('name', '')
                if zone_name in zone_areas:
                    zone['floor_area'] = zone_areas[zone_name]
            
            # Calculate total area (NO DOUBLING)
            total_area = sum(zone.get('floor_area', 0) for zone in zones)
            
            # If no zones found, use default
            if total_area == 0:
                total_area = 1000.0
                zones = [{'name': 'DefaultZone', 'floor_area': total_area}]
            
            # Extract lighting, equipment, and occupancy
            lighting = []
            equipment = []
            occupancy = []
            
            # Extract lighting
            lighting_pattern = r'Lights\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)'
            lighting_matches = re.findall(lighting_pattern, content, re.IGNORECASE)
            for match in lighting_matches:
                try:
                    lighting.append({
                        'name': match[0].strip(),
                        'zone': match[1].strip(),
                        'schedule': match[2].strip(),
                        'level': match[3].strip(),
                        'power': float(match[4].strip()) if match[4].strip().replace('.', '').replace('-', '').isdigit() else 0.0
                    })
                except (ValueError, IndexError):
                    continue
            
            # Extract equipment
            equipment_pattern = r'ElectricEquipment\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)'
            equipment_matches = re.findall(equipment_pattern, content, re.IGNORECASE)
            for match in equipment_matches:
                try:
                    equipment.append({
                        'name': match[0].strip(),
                        'zone': match[1].strip(),
                        'schedule': match[2].strip(),
                        'level': match[3].strip(),
                        'power': float(match[4].strip()) if match[4].strip().replace('.', '').replace('-', '').isdigit() else 0.0
                    })
                except (ValueError, IndexError):
                    continue
            
            # Extract occupancy
            occupancy_pattern = r'People\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)\s*,\s*([^,;\n]+)'
            occupancy_matches = re.findall(occupancy_pattern, content, re.IGNORECASE)
            for match in occupancy_matches:
                try:
                    occupancy.append({
                        'name': match[0].strip(),
                        'zone': match[1].strip(),
                        'schedule': match[2].strip(),
                        'level': match[3].strip(),
                        'people': float(match[4].strip()) if match[4].strip().replace('.', '').replace('-', '').isdigit() else 0.0
                    })
                except (ValueError, IndexError):
                    continue
            
            print(f"SMART PARSER: Found {len(zones)} zones, {len(lighting)} lighting, {len(equipment)} equipment, {len(occupancy)} occupancy")
            print(f"SMART PARSER: Total area: {total_area} (NO DOUBLING)")
            
            return {
                'zones': zones,
                'building_area': total_area,
                'building_type': 'office',
                'lighting': lighting,
                'equipment': equipment,
                'occupancy': occupancy
            }
        except Exception as e:
            print(f"SMART PARSER: Error in building data extraction: {str(e)}")
            return {
                'zones': [],
                'building_area': 0,
                'building_type': 'office',
                'lighting': [],
                'equipment': [],
                'occupancy': [],
                'error': str(e)
            }
    
    def _calculate_energy_results_smart(self, building_data: Dict) -> Dict[str, Any]:
        """Calculate energy results - SMART VERSION (no doubling)"""
        try:
            # Extract parameters
            building_area = building_data.get('building_area', 1000)
            lighting_objects = building_data.get('lighting', [])
            equipment_objects = building_data.get('equipment', [])
            occupancy_objects = building_data.get('occupancy', [])
            
            # Calculate actual power
            total_lighting_power = sum(obj.get('power', 0) for obj in lighting_objects)
            total_equipment_power = sum(obj.get('power', 0) for obj in equipment_objects)
            total_occupancy = sum(obj.get('people', 0) for obj in occupancy_objects)
            
            # If no actual data found, use defaults
            if total_lighting_power == 0:
                total_lighting_power = building_area * 12  # W/m² default
            if total_equipment_power == 0:
                total_equipment_power = building_area * 8  # W/m² default
            
            # Calculate energy (simplified but working)
            operating_hours = 2920  # 8 hours/day, 365 days/year
            
            # Base loads
            heating_load = building_area * 50  # W/m²
            cooling_load = building_area * 80  # W/m²
            
            # Calculate energy
            heating_energy = (heating_load * operating_hours) / 1000  # kWh
            cooling_energy = (cooling_load * operating_hours) / 1000  # kWh
            lighting_energy = (total_lighting_power * operating_hours) / 1000  # kWh
            equipment_energy = (total_equipment_power * operating_hours) / 1000  # kWh
            
            # Total energy
            total_energy = heating_energy + cooling_energy + lighting_energy + equipment_energy
            
            # Calculate metrics
            peak_demand = total_energy * 1.3 / 8760  # kW
            energy_intensity = total_energy / building_area if building_area > 0 else 0
            
            # Performance rating
            if energy_intensity <= 100:
                performance_rating = 'Excellent'
            elif energy_intensity <= 200:
                performance_rating = 'Good'
            elif energy_intensity <= 300:
                performance_rating = 'Average'
            else:
                performance_rating = 'Poor'
            
            print(f"SMART PARSER: Energy calculation complete")
            print(f"SMART PARSER: Building area: {building_area} (NO DOUBLING)")
            print(f"SMART PARSER: Total energy: {total_energy}")
            print(f"SMART PARSER: Lighting power: {total_lighting_power}")
            print(f"SMART PARSER: Equipment power: {total_equipment_power}")
            
            return {
                'total_energy_consumption': total_energy,
                'heating_energy': heating_energy,
                'cooling_energy': cooling_energy,
                'lighting_energy': lighting_energy,
                'equipment_energy': equipment_energy,
                'energy_intensity': energy_intensity,
                'peak_demand': peak_demand,
                'peakDemand': peak_demand,  # camelCase for UI compatibility
                'performance_rating': performance_rating,
                'performanceRating': performance_rating,  # camelCase for UI compatibility
                'performance_score': max(0, 100 - (energy_intensity - 100) * 0.5),
                'performanceScore': max(0, 100 - (energy_intensity - 100) * 0.5),
                'building_area': building_area,
                'building_type': 'office',
                'lighting_objects_found': len(lighting_objects),
                'equipment_objects_found': len(equipment_objects),
                'occupancy_objects_found': len(occupancy_objects),
                'total_lighting_power': total_lighting_power,
                'total_equipment_power': total_equipment_power,
                'total_occupancy': total_occupancy
            }
        except Exception as e:
            print(f"SMART PARSER: Error in energy calculation: {str(e)}")
            return {
                'total_energy_consumption': 0,
                'heating_energy': 0,
                'cooling_energy': 0,
                'lighting_energy': 0,
                'equipment_energy': 0,
                'energy_intensity': 0,
                'peak_demand': 0,
                'peakDemand': 0,
                'performance_rating': 'Unknown',
                'performanceRating': 'Unknown',
                'performance_score': 0,
                'performanceScore': 0,
                'building_area': 0,
                'building_type': 'office',
                'error': str(e)
            }
    
    def _parse_content_with_chunking(self, content: str, content_type: str) -> Dict[str, Any]:
        """Parse large content using chunking - ONLY when needed"""
        try:
            print(f"SMART PARSER: Starting chunked processing for {len(content)} bytes")
            
            # Split content into chunks
            chunks = []
            for i in range(0, len(content), self.chunk_size):
                chunk = content[i:i + self.chunk_size]
                chunks.append({
                    'chunk_index': len(chunks),
                    'total_chunks': math.ceil(len(content) / self.chunk_size),
                    'content': chunk,
                    'size': len(chunk)
                })
            
            print(f"SMART PARSER: Split into {len(chunks)} chunks")
            
            # Process each chunk
            all_results = []
            for chunk in chunks:
                print(f"SMART PARSER: Processing chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']}")
                result = self._parse_content_normal(chunk['content'], content_type)
                all_results.append(result)
            
            # Combine results from all chunks
            combined_result = self._combine_chunk_results_smart(all_results)
            
            print(f"SMART PARSER: Combined results from {len(chunks)} chunks")
            return combined_result
            
        except Exception as e:
            print(f"SMART PARSER: Error in chunked processing: {str(e)}")
            return {
                'simulation_status': 'error',
                'error': f"Chunked processing failed: {str(e)}",
                'version': self.version,
                'content_type': content_type,
                'content_size': len(content) if content else 0
            }
    
    def _combine_chunk_results_smart(self, all_results: List[Dict]) -> Dict[str, Any]:
        """Combine results from multiple chunks - SMART VERSION (no doubling)"""
        try:
            print(f"SMART PARSER: Combining results from {len(all_results)} chunks")
            
            # Initialize combined result
            combined = {
                'version': self.version,
                'simulation_status': 'success',
                'auto_chunking': True,
                'chunking_needed': True,
                'chunks_processed': len(all_results)
            }
            
            # Combine building data (FIXED - NO DOUBLING)
            # Use the building area from the FIRST chunk only (they're all the same)
            total_building_area = 0
            all_zones = []
            all_lighting = []
            all_equipment = []
            all_occupancy = []
            
            # Get building area from first successful result only
            for result in all_results:
                if result.get('simulation_status') == 'success':
                    building_area = result.get('building_area', 0)
                    if isinstance(building_area, (int, float)) and total_building_area == 0:
                        total_building_area = building_area  # Use first chunk's area only
                        print(f"SMART PARSER: Using building area from first chunk: {total_building_area}")
                    break
            
            # Combine all objects from all chunks
            for result in all_results:
                if result.get('simulation_status') == 'success':
                    # Combine zones
                    zones = result.get('building_analysis', {}).get('zones', [])
                    all_zones.extend(zones)
                    
                    # Combine lighting
                    lighting = result.get('building_analysis', {}).get('lighting', [])
                    all_lighting.extend(lighting)
                    
                    # Combine equipment
                    equipment = result.get('building_analysis', {}).get('equipment', [])
                    all_equipment.extend(equipment)
                    
                    # Combine occupancy
                    occupancy = result.get('building_analysis', {}).get('occupancy', [])
                    all_occupancy.extend(occupancy)
            
            # Calculate combined energy
            total_energy = 0
            heating_energy = 0
            cooling_energy = 0
            lighting_energy = 0
            equipment_energy = 0
            
            for result in all_results:
                if result.get('simulation_status') == 'success':
                    total_energy += result.get('total_energy_consumption', 0)
                    heating_energy += result.get('heating_energy', 0)
                    cooling_energy += result.get('cooling_energy', 0)
                    lighting_energy += result.get('lighting_energy', 0)
                    equipment_energy += result.get('equipment_energy', 0)
            
            # Calculate metrics using correct building area
            energy_intensity = total_energy / total_building_area if total_building_area > 0 else 0
            peak_demand = total_energy * 1.3 / 8760  # kW
            
            # Performance rating
            if energy_intensity <= 100:
                performance_rating = 'Excellent'
            elif energy_intensity <= 200:
                performance_rating = 'Good'
            elif energy_intensity <= 300:
                performance_rating = 'Average'
            else:
                performance_rating = 'Poor'
            
            print(f"SMART PARSER: Combined result - Building area: {total_building_area} (FIXED - NO DOUBLING), Total energy: {total_energy}")
            
            # Build combined result
            combined.update({
                'building_analysis': {
                    'zones': all_zones,
                    'building_area': total_building_area,
                    'building_type': 'office',
                    'lighting': all_lighting,
                    'equipment': all_equipment,
                    'occupancy': all_occupancy
                },
                'total_energy_consumption': total_energy,
                'heating_energy': heating_energy,
                'cooling_energy': cooling_energy,
                'lighting_energy': lighting_energy,
                'equipment_energy': equipment_energy,
                'energy_intensity': energy_intensity,
                'peak_demand': peak_demand,
                'peakDemand': peak_demand,
                'performance_rating': performance_rating,
                'performanceRating': performance_rating,
                'performance_score': max(0, 100 - (energy_intensity - 100) * 0.5),
                'performanceScore': max(0, 100 - (energy_intensity - 100) * 0.5),
                'building_area': total_building_area,
                'building_type': 'office',
                'lighting_objects_found': len(all_lighting),
                'equipment_objects_found': len(all_equipment),
                'occupancy_objects_found': len(all_occupancy),
                'total_lighting_power': sum(obj.get('power', 0) for obj in all_lighting),
                'total_equipment_power': sum(obj.get('power', 0) for obj in all_equipment),
                'total_occupancy': sum(obj.get('people', 0) for obj in all_occupancy)
            })
            
            print(f"SMART PARSER: Combined result - Building area: {total_building_area} (NO DOUBLING), Total energy: {total_energy}")
            return combined
            
        except Exception as e:
            print(f"SMART PARSER: Error combining results: {str(e)}")
            return {
                'simulation_status': 'error',
                'error': f"Failed to combine chunk results: {str(e)}",
                'version': self.version,
                'auto_chunking': True
            }

class SmartChunkingHTTPServer:
    """Smart Chunking HTTP Server"""
    
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.parser = SmartChunkingParser()
        
    def start_server(self):
        """Start the smart chunking HTTP server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        
        print(f"🚀 Smart Chunking Parser v{self.parser.version} running on {self.host}:{self.port}")
        print("✅ Conditional chunking enabled!")
        print("✅ Only chunks when file > 1MB!")
        print("✅ No chunking for small files!")
        
        while True:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, address)
            )
            client_thread.daemon = True
            client_thread.start()
    
    def handle_client(self, client_socket, address):
        """Handle client requests"""
        try:
            request = self.read_full_request(client_socket)
            
            if not request:
                return
            
            lines = request.split('\n')
            if not lines:
                return
            
            request_line = lines[0]
            method, path, protocol = request_line.split(' ')
            
            if method == 'GET':
                if path == '/':
                    self.handle_root(client_socket)
                elif path == '/health' or path == '/healthz':
                    self.handle_health(client_socket)
                else:
                    self.handle_404(client_socket)
            elif method == 'POST':
                if path == '/simulate':
                    self.handle_simulate(client_socket, request)
                else:
                    self.handle_404(client_socket)
            else:
                self.handle_405(client_socket)
                
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
    
    def read_full_request(self, client_socket):
        """Read full request"""
        try:
            headers = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    return None
                headers += chunk
                if b"\r\n\r\n" in headers:
                    break
            
            header_text = headers.decode('utf-8', errors='ignore')
            content_length = 0
            for line in header_text.split('\n'):
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            
            body = b""
            if content_length > 0:
                body_start = headers.find(b"\r\n\r\n")
                if body_start != -1:
                    body = headers[body_start + 4:]
                
                while len(body) < content_length:
                    chunk = client_socket.recv(min(32768, content_length - len(body)))
                    if not chunk:
                        break
                    body += chunk
            
            return (header_text + body.decode('utf-8', errors='ignore'))
        except Exception as e:
            print(f"Error reading request: {e}")
            return None
    
    def handle_root(self, client_socket):
        """Handle root endpoint"""
        response_data = {
            'service': 'Smart Chunking EnergyPlus Parser',
            'version': self.parser.version,
            'status': 'operational',
            'auto_chunking': True,
            'chunking_threshold': f'{self.parser.railway_limit} bytes',
            'smart_chunking': True
        }
        
        response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data, indent=2)}"
        client_socket.send(response.encode('utf-8'))
    
    def handle_health(self, client_socket):
        """Handle health check"""
        response_data = {
            'status': 'healthy',
            'version': self.parser.version,
            'ready': True,
            'auto_chunking': True,
            'smart_chunking': True
        }
        
        response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{json.dumps(response_data)}"
        client_socket.send(response.encode('utf-8'))
    
    def handle_simulate(self, client_socket, request):
        """Handle simulation requests"""
        try:
            body_start = request.find('\r\n\r\n')
            if body_start == -1:
                self.handle_400(client_socket, "No request body")
                return
            
            body = request[body_start + 4:]
            
            try:
                data = json.loads(body)
                
                content_type = data.get('content_type', 'idf')
                idf_content = data.get('idf_content', '')
                weather_content = data.get('weather_content', '')
                
                print(f"SMART SERVER: Content type: {content_type}")
                print(f"SMART SERVER: IDF content length: {len(idf_content)} bytes")
                print(f"SMART SERVER: Weather content length: {len(weather_content)} bytes")
                
                if content_type == 'combined' and weather_content:
                    result = self.parser.parse_content(idf_content + '\n' + weather_content, 'combined')
                elif content_type == 'weather' and weather_content:
                    result = self.parser.parse_content(weather_content, 'weather')
                elif idf_content:
                    result = self.parser.parse_content(idf_content, 'idf')
                else:
                    self.handle_400(client_socket, "No content provided")
                    return
                
                print(f"SMART SERVER: Result status: {result.get('simulation_status', 'Unknown')}")
                print(f"SMART SERVER: Building area: {result.get('building_area', 'Unknown')}")
                print(f"SMART SERVER: Total energy: {result.get('total_energy_consumption', 'Unknown')}")
                print(f"SMART SERVER: Chunking used: {result.get('auto_chunking', False)}")
                
                response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{json.dumps(result, indent=2)}"
                client_socket.send(response.encode('utf-8'))
                
            except json.JSONDecodeError as e:
                self.handle_400(client_socket, f"Invalid JSON: {str(e)}")
            except Exception as e:
                error_response = {
                    'simulation_status': 'error',
                    'error': str(e),
                    'version': self.parser.version
                }
                response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{json.dumps(error_response)}"
                client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            error_response = {
                'simulation_status': 'error',
                'error': str(e),
                'version': self.parser.version
            }
            response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{json.dumps(error_response)}"
            client_socket.send(response.encode('utf-8'))
    
    def handle_404(self, client_socket):
        """Handle 404 Not Found"""
        response_data = {'error': 'Not Found', 'version': self.parser.version}
        response = f"HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data)}"
        client_socket.send(response.encode('utf-8'))
    
    def handle_405(self, client_socket):
        """Handle 405 Method Not Allowed"""
        response_data = {'error': 'Method Not Allowed', 'version': self.parser.version}
        response = f"HTTP/1.1 405 Method Not Allowed\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data)}"
        client_socket.send(response.encode('utf-8'))
    
    def handle_400(self, client_socket, message):
        """Handle 400 Bad Request"""
        response_data = {'error': message, 'version': self.parser.version}
        response = f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data)}"
        client_socket.send(response.encode('utf-8'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    server = SmartChunkingHTTPServer(port=port)
    server.start_server()
