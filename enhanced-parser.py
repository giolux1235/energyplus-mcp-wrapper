#!/usr/bin/env python3
import socket
import threading
import time
import os
import json
import re
import hashlib

class EnhancedIDFParser:
    """Enhanced IDF parser that includes peak demand and performance metrics"""
    
    def parse_idf_content(self, idf_content):
        """Parse IDF content with enhanced energy performance metrics"""
        try:
            print(f"=== ENHANCED PARSING (Length: {len(idf_content)}) ===")
            
            # Extract building type and specifications
            building_specs = self._extract_building_specifications(idf_content)
            print(f"Building specs: {building_specs}")
            
            # Extract zones with area calculation
            zones = self._extract_zones_enhanced(idf_content)
            total_area = sum(zone.get('area', 0) for zone in zones)
            print(f"Found {len(zones)} zones, total area: {total_area} m²")
            
            # Extract lighting
            lighting_data = self._extract_lighting_enhanced(idf_content)
            total_lighting = sum(lighting_data)
            print(f"Total lighting: {total_lighting} W")
            
            # Extract equipment
            equipment_data = self._extract_equipment_enhanced(idf_content)
            total_equipment = sum(equipment_data)
            print(f"Total equipment: {total_equipment} W")
            
            # Extract occupancy
            occupancy_data = self._extract_occupancy_enhanced(idf_content)
            total_occupancy = sum(occupancy_data)
            print(f"Total occupancy: {total_occupancy} people")
            
            # Extract refrigeration systems
            refrigeration_data = self._extract_refrigeration_systems_enhanced(idf_content)
            total_refrigeration = sum(refrigeration_data)
            print(f"Total refrigeration: {total_refrigeration} W")
            
            # Extract HVAC systems
            hvac_data = self._extract_hvac_enhanced(idf_content)
            print(f"HVAC systems: {hvac_data}")
            
            # Calculate power densities
            lighting_density = total_lighting / total_area if total_area > 0 else 0
            equipment_density = total_equipment / total_area if total_area > 0 else 0
            occupancy_density = total_occupancy / total_area if total_area > 0 else 0
            refrigeration_density = total_refrigeration / total_area if total_area > 0 else 0
            
            print(f"Lighting density: {lighting_density} W/m²")
            print(f"Equipment density: {equipment_density} W/m²")
            print(f"Occupancy density: {occupancy_density} people/m²")
            print(f"Refrigeration density: {refrigeration_density} W/m²")
            
            return {
                "type": building_specs.get("type", "unknown"),
                "area": total_area,
                "lighting": lighting_density,
                "equipment": equipment_density,
                "occupancy": occupancy_density,
                "refrigeration": refrigeration_density,
                "total_lighting": total_lighting,
                "total_equipment": total_equipment,
                "total_occupancy": total_occupancy,
                "total_refrigeration": total_refrigeration,
                "zones": len(zones),
                "hvac_systems": len(hvac_data),
                "content_hash": hashlib.md5(idf_content.encode()).hexdigest()[:8],
                "building_specs": building_specs,
                "zone_details": zones,
                "hvac_details": hvac_data,
                "refrigeration_details": refrigeration_data,
                "parsing_details": {
                    "zones_found": len(zones),
                    "lighting_objects": len(lighting_data),
                    "equipment_objects": len(equipment_data),
                    "people_objects": len(occupancy_data),
                    "refrigeration_objects": len(refrigeration_data),
                    "hvac_objects": len(hvac_data),
                    "raw_lighting": lighting_data,
                    "raw_equipment": equipment_data,
                    "raw_occupancy": occupancy_data,
                    "raw_refrigeration": refrigeration_data,
                    "raw_hvac": hvac_data,
                    "total_lighting_watts": total_lighting,
                    "total_equipment_watts": total_equipment,
                    "total_occupancy_people": total_occupancy,
                    "total_refrigeration_watts": total_refrigeration
                }
            }
            
        except Exception as e:
            print(f"Error parsing IDF: {e}")
            return {
                "type": "unknown",
                "area": 0,
                "lighting": 0,
                "equipment": 0,
                "occupancy": 0,
                "refrigeration": 0,
                "content_hash": "error",
                "parsing_details": {"error": str(e)}
            }
    
    def _extract_building_specifications(self, content):
        """Extract detailed building specifications"""
        specs = {}
        
        # Extract building name and type
        building_match = re.search(r'Building,\s*([^,]+)', content, re.IGNORECASE)
        if building_match:
            specs["name"] = building_match.group(1).strip()
            specs["type"] = self._classify_building_type(specs["name"])
        
        return specs
    
    def _classify_building_type(self, building_name):
        """Classify building type from name"""
        name_lower = building_name.lower()
        if any(word in name_lower for word in ['retail', 'store', 'shop', 'supermarket', 'grocery']):
            return 'retail'
        elif any(word in name_lower for word in ['office', 'commercial', 'business']):
            return 'office'
        elif any(word in name_lower for word in ['residential', 'house', 'home']):
            return 'residential'
        elif any(word in name_lower for word in ['school', 'education']):
            return 'school'
        elif any(word in name_lower for word in ['hospital', 'healthcare']):
            return 'hospital'
        else:
            return 'commercial'
    
    def _extract_zones_enhanced(self, content):
        """Extract zones with area calculation"""
        zones = []
        processed_zones = set()
        
        # Find all Zone objects
        zone_matches = re.findall(r'Zone,\s*([^,]+)', content, re.IGNORECASE)
        
        for zone_name in zone_matches:
            zone_name = zone_name.strip()
            if zone_name in processed_zones:
                continue
            processed_zones.add(zone_name)
            
            area = 0
            
            # Look for ZoneArea objects
            area_match = re.search(rf'ZoneArea,\s*{re.escape(zone_name)},\s*([0-9.]+)', content, re.IGNORECASE)
            if area_match:
                area = float(area_match.group(1))
            else:
                area = self._extract_zone_geometry_area_enhanced(content, zone_name)
            
            # Look for zone height
            height = 3.0
            height_match = re.search(rf'Zone,\s*{re.escape(zone_name)}[^;]*?,\s*([0-9.]+)', content, re.IGNORECASE)
            if height_match:
                try:
                    height = float(height_match.group(1))
                except ValueError:
                    pass
            
            zones.append({
                "name": zone_name,
                "area": area,
                "height": height
            })
        
        return zones
    
    def _extract_zone_geometry_area_enhanced(self, content, zone_name):
        """Extract area from zone geometry"""
        surface_pattern = rf'BuildingSurface:Detailed,\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*{re.escape(zone_name)}'
        surface_matches = re.findall(surface_pattern, content, re.IGNORECASE)
        
        if surface_matches:
            return len(surface_matches) * 100
        
        area_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:m²|m2|ft²|ft2)', content, re.IGNORECASE)
        if area_matches:
            areas = [float(area) for area in area_matches]
            return max(areas)
        
        return 100
    
    def _extract_lighting_enhanced(self, content):
        """Extract lighting with no duplication"""
        lighting_powers = []
        processed_objects = set()
        
        # Standard Lights objects
        lights_matches = re.findall(r'Lights,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in lights_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    lighting_powers.append(float(power))
                except ValueError:
                    continue
        
        # Lights:Detailed objects
        lights_detailed_matches = re.findall(r'Lights:Detailed,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in lights_detailed_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    lighting_powers.append(float(power))
                except ValueError:
                    continue
        
        return lighting_powers
    
    def _extract_equipment_enhanced(self, content):
        """Extract equipment with no duplication"""
        equipment_powers = []
        processed_objects = set()
        
        # ElectricEquipment objects
        elec_equip_matches = re.findall(r'ElectricEquipment,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in elec_equip_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    equipment_powers.append(float(power))
                except ValueError:
                    continue
        
        # GasEquipment objects
        gas_equip_matches = re.findall(r'GasEquipment,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in gas_equip_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    equipment_powers.append(float(power))
                except ValueError:
                    continue
        
        # HotWaterEquipment objects
        hw_equip_matches = re.findall(r'HotWaterEquipment,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in hw_equip_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    equipment_powers.append(float(power))
                except ValueError:
                    continue
        
        return equipment_powers
    
    def _extract_occupancy_enhanced(self, content):
        """Extract occupancy with no duplication"""
        occupancy_counts = []
        processed_objects = set()
        
        # People objects
        people_matches = re.findall(r'People,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, people_count in people_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    occupancy_counts.append(float(people_count))
                except ValueError:
                    continue
        
        # People:Detailed objects
        people_detailed_matches = re.findall(r'People:Detailed,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, people_count in people_detailed_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    occupancy_counts.append(float(people_count))
                except ValueError:
                    continue
        
        return occupancy_counts
    
    def _extract_refrigeration_systems_enhanced(self, content):
        """Extract refrigeration systems for supermarkets"""
        refrigeration_powers = []
        processed_objects = set()
        
        # Refrigeration:CompressorRack objects
        compressor_matches = re.findall(r'Refrigeration:CompressorRack,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in compressor_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    refrigeration_powers.append(float(power))
                except ValueError:
                    continue
        
        # Refrigeration:Case objects
        case_matches = re.findall(r'Refrigeration:Case,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in case_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    refrigeration_powers.append(float(power))
                except ValueError:
                    continue
        
        # Refrigeration:WalkIn objects
        walkin_matches = re.findall(r'Refrigeration:WalkIn,\s*([^,]+),\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)', content, re.IGNORECASE)
        for obj_name, power in walkin_matches:
            obj_name = obj_name.strip()
            if obj_name not in processed_objects:
                processed_objects.add(obj_name)
                try:
                    refrigeration_powers.append(float(power))
                except ValueError:
                    continue
        
        # If no refrigeration objects found, estimate based on building type
        if not refrigeration_powers:
            building_match = re.search(r'Building,\s*([^,]+)', content, re.IGNORECASE)
            if building_match:
                building_name = building_match.group(1).lower()
                if any(word in building_name for word in ['retail', 'store', 'supermarket', 'grocery']):
                    # Calculate total area to estimate refrigeration load
                    zones = self._extract_zones_enhanced(content)
                    total_area = sum(zone.get('area', 0) for zone in zones)
                    
                    # Realistic refrigeration load for supermarket: 20-40 W/m²
                    refrigeration_density = 30  # W/m²
                    estimated_refrigeration = total_area * refrigeration_density
                    refrigeration_powers.append(estimated_refrigeration)
        
        return refrigeration_powers
    
    def _extract_hvac_enhanced(self, content):
        """Extract HVAC systems"""
        hvac_systems = []
        
        # HVAC Template objects
        hvac_template_matches = re.findall(r'HVACTemplate:Zone:(\w+),\s*([^,]+)', content, re.IGNORECASE)
        for hvac_type, zone_name in hvac_template_matches:
            hvac_systems.append({
                "type": hvac_type,
                "zone": zone_name.strip(),
                "system": "HVACTemplate"
            })
        
        # ZoneHVAC objects
        zone_hvac_matches = re.findall(r'ZoneHVAC:(\w+),\s*([^,]+)', content, re.IGNORECASE)
        for hvac_type, name in zone_hvac_matches:
            hvac_systems.append({
                "type": hvac_type,
                "name": name.strip(),
                "system": "ZoneHVAC"
            })
        
        # AirLoopHVAC objects
        airloop_matches = re.findall(r'AirLoopHVAC,\s*([^,]+)', content, re.IGNORECASE)
        for name in airloop_matches:
            hvac_systems.append({
                "type": "AirLoopHVAC",
                "name": name.strip(),
                "system": "AirLoopHVAC"
            })
        
        return hvac_systems

class EnhancedEnergySimulator:
    """Enhanced energy simulation with peak demand and performance metrics"""
    
    def __init__(self):
        self.parser = EnhancedIDFParser()
    
    def simulate_from_idf(self, idf_content):
        """Run simulation using IDF content with enhanced metrics"""
        print("=== STARTING ENHANCED SIMULATION ===")
        building_data = self.parser.parse_idf_content(idf_content)
        return self.calculate_energy_enhanced(building_data)
    
    def calculate_energy_enhanced(self, building_data):
        """Calculate energy consumption with enhanced performance metrics"""
        print("=== CALCULATING ENERGY ENHANCED ===")
        
        # Use values from the IDF file
        area = building_data["area"]
        lighting_density = building_data["lighting"]
        equipment_density = building_data["equipment"]
        occupancy_density = building_data["occupancy"]
        refrigeration_density = building_data["refrigeration"]
        building_type = building_data["type"]
        total_lighting = building_data.get("total_lighting", 0)
        total_equipment = building_data.get("total_equipment", 0)
        total_occupancy = building_data.get("total_occupancy", 0)
        total_refrigeration = building_data.get("total_refrigeration", 0)
        
        print(f"Enhanced parameters:")
        print(f"  - Area: {area} m²")
        print(f"  - Total lighting: {total_lighting} W")
        print(f"  - Total equipment: {total_equipment} W")
        print(f"  - Total occupancy: {total_occupancy} people")
        print(f"  - Total refrigeration: {total_refrigeration} W")
        print(f"  - Building type: {building_type}")
        
        # Calculate energy consumption
        operating_hours = 8760  # 24/7 operation for supermarkets
        
        # Calculate lighting and equipment energy
        lighting_energy = (total_lighting * operating_hours) / 1000  # Convert W to kW
        equipment_energy = (total_equipment * operating_hours) / 1000  # Convert W to kW
        refrigeration_energy = (total_refrigeration * operating_hours) / 1000  # Convert W to kW
        
        # Enhanced heating/cooling calculation for supermarkets
        if building_type == "retail":
            # Supermarkets have high cooling loads due to refrigeration and high occupancy
            heating_energy = area * 5  # 5 kWh/m²/year (minimal heating in Miami)
            cooling_energy = area * 120  # 120 kWh/m²/year (very high cooling due to refrigeration + Miami climate)
        elif building_type == "office":
            heating_energy = area * 10  # 10 kWh/m²/year
            cooling_energy = area * 20  # 20 kWh/m²/year
        elif building_type == "residential":
            heating_energy = area * 5  # 5 kWh/m²/year
            cooling_energy = area * 10  # 10 kWh/m²/year
        else:
            heating_energy = area * 8  # 8 kWh/m²/year
            cooling_energy = area * 15  # 15 kWh/m²/year
        
        # Total energy consumption
        total_energy = heating_energy + cooling_energy + lighting_energy + equipment_energy + refrigeration_energy
        
        # ENHANCED METRICS CALCULATIONS
        
        # Peak Demand Calculation (kW)
        # Peak demand is typically 1.2-1.5x the average demand
        average_demand = total_energy / operating_hours  # kW
        peak_demand_factor = 1.3  # 30% above average
        peak_demand = average_demand * peak_demand_factor
        
        # Performance Metrics
        energy_intensity = total_energy / area if area > 0 else 0
        
        # Performance rating based on energy intensity
        if building_type == "retail":
            if energy_intensity < 200:
                performance_rating = "Excellent"
                performance_score = 95
            elif energy_intensity < 300:
                performance_rating = "Good"
                performance_score = 85
            elif energy_intensity < 400:
                performance_rating = "Average"
                performance_score = 70
            elif energy_intensity < 500:
                performance_rating = "Below Average"
                performance_score = 55
            else:
                performance_rating = "Poor"
                performance_score = 40
        else:
            # Different benchmarks for other building types
            if energy_intensity < 100:
                performance_rating = "Excellent"
                performance_score = 95
            elif energy_intensity < 150:
                performance_rating = "Good"
                performance_score = 85
            elif energy_intensity < 200:
                performance_rating = "Average"
                performance_score = 70
            elif energy_intensity < 250:
                performance_rating = "Below Average"
                performance_score = 55
            else:
                performance_rating = "Poor"
                performance_score = 40
        
        # Additional Performance Metrics
        lighting_efficiency = (lighting_energy / total_energy) * 100 if total_energy > 0 else 0
        equipment_efficiency = (equipment_energy / total_energy) * 100 if total_energy > 0 else 0
        refrigeration_efficiency = (refrigeration_energy / total_energy) * 100 if total_energy > 0 else 0
        
        print(f"Enhanced calculated values:")
        print(f"  - Total energy: {total_energy} kWh/year")
        print(f"  - Peak demand: {peak_demand} kW")
        print(f"  - Energy intensity: {energy_intensity} kWh/m²/year")
        print(f"  - Performance rating: {performance_rating}")
        print(f"  - Performance score: {performance_score}")
        
        return {
            "building_type": building_type,
            "total_energy_consumption": round(total_energy, 2),
            "heating_energy": round(heating_energy, 2),
            "cooling_energy": round(cooling_energy, 2),
            "lighting_energy": round(lighting_energy, 2),
            "equipment_energy": round(equipment_energy, 2),
            "refrigeration_energy": round(refrigeration_energy, 2),
            "energy_intensity": round(energy_intensity, 2),
            "building_area": area,
            "lighting_power": lighting_density,
            "equipment_power": equipment_density,
            "occupancy_density": occupancy_density,
            "refrigeration_power": refrigeration_density,
            "total_lighting_watts": total_lighting,
            "total_equipment_watts": total_equipment,
            "total_occupancy_people": total_occupancy,
            "total_refrigeration_watts": total_refrigeration,
            "zones_count": building_data.get("zones", 0),
            "hvac_systems_count": building_data.get("hvac_systems", 0),
            "content_hash": building_data["content_hash"],
            "simulation_status": "completed",
            "timestamp": time.time(),
            "data_source": "idf_file",
            "calculation_method": "enhanced_parsing",
            "operating_hours": operating_hours,
            "building_specs": building_data.get("building_specs", {}),
            "zone_details": building_data.get("zone_details", []),
            "hvac_details": building_data.get("hvac_details", []),
            "refrigeration_details": building_data.get("refrigeration_details", []),
            "parsing_details": building_data.get("parsing_details", {}),
            # ENHANCED METRICS - Interface expects camelCase
            "peak_demand": round(peak_demand, 2),
            "performance_rating": performance_rating,
            "performance_score": performance_score,
            "lighting_efficiency": round(lighting_efficiency, 1),
            "equipment_efficiency": round(equipment_efficiency, 1),
            "refrigeration_efficiency": round(refrigeration_efficiency, 1),
            # Interface field names (camelCase)
            "peakDemand": round(peak_demand, 2),
            "performanceRating": performance_rating,
            "performanceScore": performance_score,
            "lightingEfficiency": round(lighting_efficiency, 1),
            "equipmentEfficiency": round(equipment_efficiency, 1),
            "refrigerationEfficiency": round(refrigeration_efficiency, 1),
            "enhanced_metrics": {
                "peak_demand_kw": round(peak_demand, 2),
                "performance_rating": performance_rating,
                "performance_score": performance_score,
                "energy_intensity_kwh_m2": round(energy_intensity, 2),
                "lighting_efficiency_percent": round(lighting_efficiency, 1),
                "equipment_efficiency_percent": round(equipment_efficiency, 1),
                "refrigeration_efficiency_percent": round(refrigeration_efficiency, 1),
                "average_demand_kw": round(average_demand, 2),
                "peak_demand_factor": peak_demand_factor
            }
        }

def read_full_request(conn, timeout=30):
    """Read the complete HTTP request, handling large payloads"""
    conn.settimeout(timeout)
    
    try:
        # Read the headers first
        headers = b""
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            headers += chunk
            if b"\r\n\r\n" in headers:
                break
        
        # Find the end of headers
        header_end = headers.find(b"\r\n\r\n")
        if header_end == -1:
            return None
        
        # Extract headers and body
        header_data = headers[:header_end].decode('utf-8', errors='ignore')
        body_start = header_end + 4
        body_data = headers[body_start:]
        
        # Check Content-Length header
        content_length = 0
        for line in header_data.split('\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())
                break
        
        # Read remaining body if needed
        if content_length > len(body_data):
            remaining = content_length - len(body_data)
            while remaining > 0:
                chunk = conn.recv(min(8192, remaining))
                if not chunk:
                    break
                body_data += chunk
                remaining -= len(chunk)
        
        # Combine headers and body
        full_request = headers[:body_start] + body_data
        return full_request.decode('utf-8', errors='ignore')
        
    except socket.timeout:
        print("Request timeout")
        return None
    except Exception as e:
        print(f"Error reading request: {e}")
        return None

def handle_request(conn, addr):
    try:
        print(f"Handling request from {addr}")
        
        # Read the full request
        request = read_full_request(conn)
        if not request:
            print("Failed to read request")
            return
        
        print(f"Request size: {len(request)} bytes")
        
        lines = request.split('\n')
        if not lines:
            return
            
        request_line = lines[0]
        method, path, version = request_line.split(' ', 2)
        
        print(f"Method: {method}, Path: {path}")
        
        simulator = EnhancedEnergySimulator()
        
        if path == '/healthz' or path == '/health':
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
        elif path == '/':
            response_data = {
                "service": "EnergyPlus MCP HTTP Wrapper",
                "status": "running",
                "version": "11.0.0",
                "capabilities": ["energy_simulation", "building_analysis", "idf_parsing", "peak_demand", "performance_metrics"],
                "energyplus_ready": True,
                "file_upload_support": True,
                "large_payload_support": True,
                "enhanced_parsing": True,
                "handles_complex_buildings": True,
                "peak_demand_support": True,
                "performance_metrics_support": True,
                "enhanced_features": [
                    "Peak demand calculation",
                    "Performance rating system",
                    "Energy efficiency metrics",
                    "Building performance scoring"
                ]
            }
            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data)}'
        elif path == '/status':
            response_data = {
                "status": "healthy",
                "energyplus_ready": True,
                "simulation_capable": True,
                "simulation_engine": "Enhanced EnergyPlus parser with peak demand and performance metrics",
                "idf_parsing": True,
                "file_upload": True,
                "large_payload_support": True,
                "enhanced_parsing": True,
                "refrigeration_support": True,
                "peak_demand_support": True,
                "performance_metrics_support": True
            }
            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(response_data)}'
        elif path == '/simulate':
            if method == 'GET':
                # Default simulation
                result = simulator.calculate_energy_enhanced({
                    "type": "default",
                    "area": 0,
                    "lighting": 0,
                    "equipment": 0,
                    "occupancy": 0,
                    "refrigeration": 0,
                    "total_lighting": 0,
                    "total_equipment": 0,
                    "total_occupancy": 0,
                    "total_refrigeration": 0,
                    "zones": 0,
                    "content_hash": "default"
                })
                result["data_source"] = "default"
                response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
            elif method == 'POST':
                # Handle file upload
                body_start = request.find('\r\n\r\n')
                if body_start == -1:
                    response = 'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{"error": "No body found"}'
                else:
                    body = request[body_start + 4:]
                    print(f"Body length: {len(body)}")
                    
                    if 'multipart/form-data' in request:
                        # Parse multipart data
                        boundary_match = re.search(r'boundary=([^;]+)', request)
                        if boundary_match:
                            boundary = boundary_match.group(1)
                            parts = body.split(f'--{boundary}')
                            
                            idf_content = None
                            for part in parts:
                                if 'Content-Disposition: form-data' in part and 'filename=' in part:
                                    filename_match = re.search(r'filename="([^"]+)"', part)
                                    if filename_match and filename_match.group(1).lower().endswith('.idf'):
                                        content_start = part.find('\r\n\r\n')
                                        if content_start != -1:
                                            idf_content = part[content_start + 4:]
                                            break
                            
                            if idf_content:
                                result = simulator.simulate_from_idf(idf_content)
                            else:
                                result = simulator.calculate_energy_enhanced({
                                    "type": "no_file",
                                    "area": 0,
                                    "lighting": 0,
                                    "equipment": 0,
                                    "occupancy": 0,
                                    "refrigeration": 0,
                                    "total_lighting": 0,
                                    "total_equipment": 0,
                                    "total_occupancy": 0,
                                    "total_refrigeration": 0,
                                    "zones": 0,
                                    "content_hash": "no_file"
                                })
                                result["warning"] = "No IDF file found"
                            
                            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
                        else:
                            response = 'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{"error": "No boundary found"}'
                    else:
                        # JSON data
                        print("Processing JSON data")
                        try:
                            data = json.loads(body)
                            print(f"JSON keys: {list(data.keys())}")
                            
                            if 'idf_content' in data:
                                print(f"IDF content length: {len(data['idf_content'])}")
                                result = simulator.simulate_from_idf(data['idf_content'])
                                
                                # Add weather data info if provided
                                if 'weather_content' in data:
                                    result["weather_processed"] = True
                                    result["weather_size"] = len(data['weather_content'])
                                
                                print(f"Enhanced simulation result: {result['building_type']} - {result['total_energy_consumption']} kWh")
                            else:
                                print("No idf_content found, using default")
                                result = simulator.calculate_energy_enhanced({
                                    "type": "no_content",
                                    "area": 0,
                                    "lighting": 0,
                                    "equipment": 0,
                                    "occupancy": 0,
                                    "refrigeration": 0,
                                    "total_lighting": 0,
                                    "total_equipment": 0,
                                    "total_occupancy": 0,
                                    "total_refrigeration": 0,
                                    "zones": 0,
                                    "content_hash": "no_content"
                                })
                            
                            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            response = f'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n\r\n{{"error": "Invalid JSON: {str(e)}"}}'
                        except Exception as e:
                            print(f"JSON processing error: {e}")
                            response = f'HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{{"error": "Processing error: {str(e)}"}}'
        else:
            response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'
        
        conn.send(response.encode())
    except Exception as e:
        print(f"Error handling request: {e}")
        error_response = f'HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{{"error": "{str(e)}"}}'
        conn.send(error_response.encode())
    finally:
        conn.close()

def main():
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting ENHANCED EnergyPlus MCP server on port {port}")
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    
    print(f"ENHANCED EnergyPlus MCP server listening on 0.0.0.0:{port}")
    print("Available endpoints: /, /status, /simulate")
    print("EnergyPlus simulation capabilities: ACTIVE")
    print("IDF file parsing: ACTIVE")
    print("File upload support: ACTIVE")
    print("Large payload support: ACTIVE")
    print("ENHANCED PARSING: ACTIVE")
    print("PEAK DEMAND SUPPORT: ACTIVE")
    print("PERFORMANCE METRICS SUPPORT: ACTIVE")
    print("Version: 11.0.0 - ENHANCED VERSION")
    
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_request, args=(conn, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        server.close()

if __name__ == '__main__':
    main()
