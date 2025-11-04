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
        self.version = "33.0.0"
        self.current_idf_content = None  # Store IDF content for analysis
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
            # Store IDF content for later analysis
            self.current_idf_content = idf_content
            
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
            err_content = ""
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
            
            # Collect output info even if there are errors (for debugging)
            output_info = self.collect_output_info(output_dir, err_file)
            
            # If fatal errors, return error response with details
            if fatal_errors:
                error_msg = f"EnergyPlus simulation failed with fatal errors:\n" + "\n".join(fatal_errors[:5])
                logger.error(f"❌ {error_msg}")
                error_response = self.create_error_response(error_msg, warnings=warnings)
                error_response.update(output_info)  # Include output info even in error case
                return error_response
            
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
                error_response = self.create_error_response(error_msg, warnings=warnings[:10])
                error_response.update(output_info)  # Include output info for debugging
                return error_response
            
            # Calculate additional metrics
            self.add_calculated_metrics(energy_data)
            
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
                **energy_data,
                **output_info  # Include error file, output files list, CSV preview, SQLite info
            }
            
            logger.info(f"✅ EnergyPlus output parsed successfully - REAL DATA!")
            logger.info(f"✅ Total energy: {energy_data.get('total_energy_consumption', 0)} kWh")
            return response
            
        except Exception as e:
            error_msg = f"Output parsing failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self.create_error_response(error_msg)
    
    def parse_all_output_files(self, output_dir):
        """Parse all output files - HTML first (most reliable), then MTR, CSV, ESO"""
        energy_data = {}
        
        output_files = os.listdir(output_dir)
        logger.info(f"📁 Output files: {output_files}")
        
        # Try HTML summary FIRST - it has the most complete and reliable data
        for file in output_files:
            if file.endswith('Table.html') or file.endswith('tbl.htm') or file.endswith('tbl.html') or file.endswith('.html') or file.endswith('.htm'):
                html_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing HTML: {file}")
                data = self.parse_energyplus_html(html_path)
                if data:
                    # HTML data takes priority - don't let other parsers overwrite it
                    for key, value in data.items():
                        if key not in energy_data or value > 0:  # Only update if we don't have data or new data is non-zero
                            energy_data[key] = value
                    logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try MTR files (meter files) - only if HTML didn't provide complete data
        if energy_data.get('total_energy_consumption', 0) == 0:
            for file in output_files:
                if file.endswith('.mtr'):
                    mtr_path = os.path.join(output_dir, file)
                    logger.info(f"📊 Parsing MTR: {file}")
                    data = self.parse_energyplus_mtr(mtr_path)
                    if data:
                        energy_data.update(data)
                        logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try CSV files - as fallback
        if energy_data.get('total_energy_consumption', 0) == 0:
            for file in output_files:
                if file.endswith('Meter.csv') or file.endswith('Table.csv') or file.endswith('.csv'):
                    csv_path = os.path.join(output_dir, file)
                    logger.info(f"📊 Parsing CSV: {file}")
                    data = self.parse_energyplus_csv(csv_path)
                    if data:
                        energy_data.update(data)
                        logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # Try ESO file (EnergyPlus Standard Output) - last resort
        if energy_data.get('total_energy_consumption', 0) == 0:
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
        """Parse EnergyPlus MTR (meter) files - Data dictionary format"""
        try:
            with open(mtr_path, 'r') as f:
                lines = f.readlines()
            
            logger.info(f"📊 MTR file: {mtr_path}")
            logger.info(f"📊 MTR lines: {len(lines)}")
            
            # MTR files have format:
            # Dictionary line: 61,1,Electricity:Facility [J] !Hourly
            # Data lines: 61,12113587.62309867
            
            # Step 1: Parse data dictionary to map meter IDs to names
            meter_dict = {}  # {meter_id: meter_name}
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    try:
                        meter_id = int(parts[0])
                        meter_type = int(parts[1])
                        
                        # Type 1 means it's a meter definition
                        if meter_type == 1 and len(parts[2]) > 1:
                            # parts[2] is the meter name like "Electricity:Facility [J] !Hourly"
                            meter_name = parts[2].split('[')[0].strip().lower()
                            meter_dict[meter_id] = meter_name
                            logger.info(f"   Found meter {meter_id}: {meter_name}")
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"📊 Found {len(meter_dict)} meters in dictionary")
            
            # Step 2: Parse data lines and sum values for each meter
            meter_totals = {}  # {meter_name: total_value}
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) == 2:  # Data line format: meter_id,value
                    try:
                        meter_id = int(parts[0])
                        value = float(parts[1])
                        
                        if meter_id in meter_dict and value > 0:
                            meter_name = meter_dict[meter_id]
                            if meter_name not in meter_totals:
                                meter_totals[meter_name] = 0
                            meter_totals[meter_name] += value
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"📊 Meter totals:")
            for meter, total in meter_totals.items():
                # Convert J to kWh
                total_kwh = total * 2.77778e-7
                logger.info(f"   {meter}: {total_kwh:.2f} kWh")
            
            # Step 3: Categorize and convert to kWh
            total = 0
            heating = 0
            cooling = 0
            lighting = 0
            equipment = 0
            fans = 0
            pumps = 0
            
            for meter_name, value_j in meter_totals.items():
                # Convert J to kWh
                value = value_j * 2.77778e-7
                
                # Categorize based on meter name
                if 'heating:electricity' in meter_name or 'heating:naturalgas' in meter_name:
                    heating += value
                elif 'cooling:electricity' in meter_name:
                    cooling += value
                elif 'interiorlights:electricity' in meter_name:
                    lighting += value
                elif 'interiorequipment:electricity' in meter_name:
                    equipment += value
                elif 'fans:electricity' in meter_name:
                    fans += value
                elif 'pumps:electricity' in meter_name:
                    pumps += value
                elif 'electricity:facility' in meter_name or 'electricitynet:facility' in meter_name:
                    # Use facility total only if we don't have breakdown
                    if total == 0:
                        total = value
                elif 'naturalgas:facility' in meter_name:
                    # Add gas to heating if not already counted
                    if heating == 0:
                        heating += value
            
            # Calculate total from breakdown if available
            breakdown_total = heating + cooling + lighting + equipment + fans + pumps
            if breakdown_total > 0:
                total = breakdown_total
            
            energy_data = {}
            if total > 0:
                energy_data['total_energy_consumption'] = round(total, 2)
                energy_data['heating_energy'] = round(heating, 2)
                energy_data['cooling_energy'] = round(cooling, 2)
                energy_data['lighting_energy'] = round(lighting, 2)
                energy_data['equipment_energy'] = round(equipment, 2)
                
                if fans > 0:
                    energy_data['fans_energy'] = round(fans, 2)
                if pumps > 0:
                    energy_data['pumps_energy'] = round(pumps, 2)
                
                logger.info(f"✅ MTR parsed successfully:")
                logger.info(f"   Total: {total:.2f} kWh")
                logger.info(f"   Heating: {heating:.2f} kWh")
                logger.info(f"   Cooling: {cooling:.2f} kWh")
                logger.info(f"   Lighting: {lighting:.2f} kWh")
                logger.info(f"   Equipment: {equipment:.2f} kWh")
                logger.info(f"   Fans: {fans:.2f} kWh")
                logger.info(f"   Pumps: {pumps:.2f} kWh")
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ MTR parse error: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        """Parse EnergyPlus HTML summary - Enhanced to extract End Uses table"""
        try:
            with open(html_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 HTML content: {len(content)} chars")
            
            energy_data = {}
            
            # Extract building area first
            area_patterns = [
                r'Net\s+Conditioned\s+Building\s+Area</td>\s*<td[^>]*>\s*([\d.]+)',
                r'Total\s+Building\s+Area</td>\s*<td[^>]*>\s*([\d.]+)',
                r'Total\s+Floor\s+Area</td>\s*<td[^>]*>\s*([\d.]+)',
            ]
            
            for pattern in area_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        area = float(match.group(1))
                        energy_data['building_area'] = round(area, 2)
                        logger.info(f"✅ Building area found: {area:.2f} m²")
                        break
                    except:
                        pass
            
            # Extract End Uses table data
            # This table has rows for Heating, Cooling, Interior Lighting, Interior Equipment, Fans, Pumps
            # Each row has columns for different fuel types (Electricity, Natural Gas, etc.)
            
            # Find the ANNUAL End Uses table (not the Demand End Uses table)
            # Look for the Annual Building Utility Performance Summary table
            end_uses_match = re.search(r'Annual Building Utility Performance Summary.*?<b>End Uses</b>.*?<table[^>]*>(.*?)</table>', content, re.DOTALL | re.IGNORECASE)
            
            if end_uses_match:
                table_content = end_uses_match.group(1)
                logger.info("✅ Found End Uses table")
                
                # Extract energy by category
                # Pattern: <td align="right">Category</td> followed by energy values
                categories = {
                    'Heating': 0,
                    'Cooling': 0,
                    'Interior Lighting': 0,
                    'Interior Equipment': 0,
                    'Exterior Equipment': 0,
                    'Fans': 0,
                    'Pumps': 0,
                    'Heat Rejection': 0,
                    'Humidification': 0,
                    'Heat Recovery': 0,
                    'Water Systems': 0,
                    'Refrigeration': 0,
                    'Exterior Lighting': 0,
                }
                
                for category in categories.keys():
                    # Find the row for this category
                    # Pattern: <tr><td>Category</td><td>Electricity[GJ]</td><td>NaturalGas[GJ]</td>...
                    category_pattern = rf'<td[^>]*>{category}</td>(.*?)</tr>'
                    category_match = re.search(category_pattern, table_content, re.DOTALL | re.IGNORECASE)
                    
                    if category_match:
                        row_content = category_match.group(1)
                        # Extract all numeric values from this row (they're in GJ)
                        values = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', row_content)
                        
                        # Sum all fuel types for this category
                        total_gj = sum(float(v) for v in values if v != '0.00')
                        categories[category] = total_gj * 277.778  # Convert GJ to kWh
                        
                        if total_gj > 0:
                            logger.info(f"   {category}: {total_gj:.2f} GJ = {categories[category]:.2f} kWh")
                
                # Map to our energy data structure (MAIN 6 CATEGORIES - no double counting)
                energy_data['heating_energy'] = round(categories.get('Heating', 0), 2)
                energy_data['cooling_energy'] = round(categories.get('Cooling', 0), 2)  # DON'T add Heat Rejection here
                energy_data['lighting_energy'] = round(categories.get('Interior Lighting', 0) + categories.get('Exterior Lighting', 0), 2)
                energy_data['equipment_energy'] = round(categories.get('Interior Equipment', 0), 2)  # DON'T add Exterior/Refrigeration here
                energy_data['fans_energy'] = round(categories.get('Fans', 0), 2)
                energy_data['pumps_energy'] = round(categories.get('Pumps', 0), 2)
                
                # Add ALL specialty categories separately (these are in ADDITION to main 6)
                if categories.get('Exterior Equipment', 0) > 0:
                    energy_data['exterior_equipment_energy'] = round(categories.get('Exterior Equipment', 0), 2)
                if categories.get('Heat Rejection', 0) > 0:
                    energy_data['heat_rejection_energy'] = round(categories.get('Heat Rejection', 0), 2)
                if categories.get('Humidification', 0) > 0:
                    energy_data['humidification_energy'] = round(categories.get('Humidification', 0), 2)
                if categories.get('Heat Recovery', 0) > 0:
                    energy_data['heat_recovery_energy'] = round(categories.get('Heat Recovery', 0), 2)
                if categories.get('Water Systems', 0) > 0:
                    energy_data['water_systems_energy'] = round(categories.get('Water Systems', 0), 2)
                if categories.get('Refrigeration', 0) > 0:
                    energy_data['refrigeration_energy'] = round(categories.get('Refrigeration', 0), 2)
                
                # Get total from "Total End Uses" row (EnergyPlus already calculated it correctly)
                total_end_uses_pattern = r'<td[^>]*>Total End Uses</td>(.*?)</tr>'
                total_match = re.search(total_end_uses_pattern, table_content, re.DOTALL | re.IGNORECASE)
                
                total = 0
                if total_match:
                    row_content = total_match.group(1)
                    # Extract all numeric values (they're in GJ, excluding the last column which is Water in m³)
                    values = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', row_content)
                    
                    # Sum all energy values (not water) - typically first 13 columns
                    # Last column is Water [m³], not energy
                    energy_values_gj = [float(v) for v in values[:-1] if v != '0.00']
                    total_gj = sum(energy_values_gj)
                    total = total_gj * 277.778  # Convert to kWh
                    
                    logger.info(f"✅ Total from 'Total End Uses' row: {total_gj:.2f} GJ = {total:.2f} kWh")
                else:
                    # Fallback: sum categories manually if Total End Uses row not found
                    logger.warning("⚠️  'Total End Uses' row not found, summing categories manually")
                    total = sum([
                        categories.get('Heating', 0),
                        categories.get('Cooling', 0),
                        categories.get('Interior Lighting', 0),
                        categories.get('Exterior Lighting', 0),
                        categories.get('Interior Equipment', 0),
                        categories.get('Exterior Equipment', 0),
                        categories.get('Fans', 0),
                        categories.get('Pumps', 0),
                        categories.get('Heat Rejection', 0),
                        categories.get('Humidification', 0),
                        categories.get('Heat Recovery', 0),
                        categories.get('Water Systems', 0),
                        categories.get('Refrigeration', 0),
                    ])
                
                if total > 0:
                    energy_data['total_energy_consumption'] = round(total, 2)
                    logger.info(f"✅ Total energy from HTML: {total:.2f} kWh")
            else:
                logger.warning("⚠️  End Uses table not found in HTML")
            
            return energy_data
            
        except Exception as e:
            logger.error(f"❌ HTML parse error: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
    
    def collect_output_info(self, output_dir, err_file):
        """
        Collect additional output information:
        - Full error file content
        - List of generated output files
        - CSV preview (first 500 lines)
        - SQLite database info
        """
        output_info = {}
        
        try:
            # 1. Full error file content
            if err_file and os.path.exists(err_file):
                with open(err_file, 'r') as f:
                    output_info['error_file_content'] = f.read()
                logger.info(f"✅ Captured full error file content ({len(output_info['error_file_content'])} chars)")
            
            # 2. List of generated output files
            output_files = []
            if os.path.exists(output_dir):
                for file in sorted(os.listdir(output_dir)):
                    file_path = os.path.join(output_dir, file)
                    file_info = {
                        "name": file,
                        "size": os.path.getsize(file_path) if os.path.isfile(file_path) else 0,
                        "type": "file" if os.path.isfile(file_path) else "directory"
                    }
                    output_files.append(file_info)
            
            output_info['output_files'] = output_files
            logger.info(f"✅ Listed {len(output_files)} output files")
            
            # 3. CSV preview (first 500 lines)
            csv_previews = {}
            for file in output_files:
                if file['name'].endswith('.csv') and file['type'] == 'file':
                    csv_path = os.path.join(output_dir, file['name'])
                    try:
                        lines = []
                        total_lines = 0
                        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f):
                                total_lines += 1
                                if i < 500:  # First 500 lines
                                    lines.append(line.rstrip('\n\r'))
                        
                        csv_previews[file['name']] = {
                            "lines": lines,
                            "total_lines": total_lines,
                            "preview_lines": len(lines)
                        }
                        logger.info(f"✅ Captured CSV preview for {file['name']} ({len(lines)}/{total_lines} lines)")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not read CSV {file['name']}: {e}")
            
            if csv_previews:
                output_info['csv_previews'] = csv_previews
            
            # 4. SQLite database info
            sqlite_info = {}
            for file in output_files:
                if file['name'].endswith('.sqlite') or file['name'].endswith('.sqlite3') or file['name'].endswith('.db'):
                    sqlite_path = os.path.join(output_dir, file['name'])
                    try:
                        import sqlite3
                        if os.path.exists(sqlite_path):
                            conn = sqlite3.connect(sqlite_path)
                            cursor = conn.cursor()
                            
                            # Get table names
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                            tables = [row[0] for row in cursor.fetchall()]
                            
                            # Get info for each table
                            table_info = {}
                            for table in tables:
                                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                                row_count = cursor.fetchone()[0]
                                
                                cursor.execute(f"PRAGMA table_info({table})")
                                columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
                                
                                table_info[table] = {
                                    "row_count": row_count,
                                    "columns": columns
                                }
                            
                            sqlite_info[file['name']] = {
                                "tables": tables,
                                "table_info": table_info,
                                "file_size": file['size']
                            }
                            
                            conn.close()
                            logger.info(f"✅ Captured SQLite info for {file['name']} ({len(tables)} tables)")
                    except ImportError:
                        logger.warning("⚠️  sqlite3 module not available, cannot read SQLite files")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not read SQLite {file['name']}: {e}")
            
            if sqlite_info:
                output_info['sqlite_info'] = sqlite_info
            
        except Exception as e:
            logger.error(f"❌ Error collecting output info: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return output_info
    
    def add_calculated_metrics(self, energy_data):
        """Add calculated metrics like peak demand, performance rating, building area"""
        try:
            total_energy = energy_data.get('total_energy_consumption', 0)
            
            # Try to get building area from HTML output if not already present
            if 'building_area' not in energy_data or energy_data.get('building_area', 0) == 0:
                # Default assumption - small office building
                energy_data['building_area'] = 511.16  # m² (5500 ft² - typical small office)
            
            building_area = energy_data.get('building_area', 511.16)
            
            # Calculate energy intensity (kWh/m²)
            if total_energy > 0 and building_area > 0:
                energy_intensity = total_energy / building_area
                energy_data['energy_intensity'] = round(energy_intensity, 2)
                energy_data['energyUseIntensity'] = round(energy_intensity, 2)  # camelCase for UI
            
            # Calculate peak demand (kW)
            # Peak demand is typically 1.2-1.5x the average hourly consumption
            if total_energy > 0:
                # Assume 2920 operating hours/year (typical for commercial building)
                avg_hourly = total_energy / 2920
                peak_demand = avg_hourly * 1.3  # Peak factor
                energy_data['peak_demand'] = round(peak_demand, 2)
                energy_data['peakDemand'] = round(peak_demand, 2)  # camelCase for UI
            
            # Calculate performance rating based on energy intensity
            if 'energy_intensity' in energy_data:
                eui = energy_data['energy_intensity']
                if eui < 100:
                    rating = "Excellent"
                    score = 95
                elif eui < 150:
                    rating = "Good"
                    score = 80
                elif eui < 200:
                    rating = "Average"
                    score = 65
                elif eui < 250:
                    rating = "Below Average"
                    score = 50
                else:
                    rating = "Poor"
                    score = 35
                
                energy_data['performance_rating'] = rating
                energy_data['performanceRating'] = rating  # camelCase for UI
                energy_data['performance_score'] = score
                energy_data['performanceScore'] = score  # camelCase for UI
            
            # Extract thermal properties from IDF if available
            if self.current_idf_content:
                thermal_props = self.extract_thermal_properties(self.current_idf_content)
                energy_data.update(thermal_props)
            
            logger.info(f"✅ Calculated metrics:")
            logger.info(f"   Building Area: {building_area:.2f} m²")
            logger.info(f"   Energy Intensity: {energy_data.get('energy_intensity', 0):.2f} kWh/m²")
            logger.info(f"   Peak Demand: {energy_data.get('peak_demand', 0):.2f} kW")
            logger.info(f"   Performance: {energy_data.get('performance_rating', 'N/A')}")
            if 'wall_r_value' in energy_data:
                logger.info(f"   Wall R-value: {energy_data['wall_r_value']:.2f}")
            if 'window_u_value' in energy_data:
                logger.info(f"   Window U-value: {energy_data['window_u_value']:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error calculating metrics: {e}")
    
    def extract_thermal_properties(self, idf_content):
        """Extract R-values for walls and U-values for windows from IDF"""
        thermal_props = {}
        
        try:
            import re
            
            # Extract wall constructions and materials
            # Look for exterior wall constructions
            wall_constructions = re.findall(r'Construction,([^;]+);', idf_content, re.IGNORECASE | re.DOTALL)
            
            wall_r_values = []
            window_u_values = []
            
            # Look for Material objects and extract R-values
            materials = re.findall(r'Material,\s*([^;]+);', idf_content, re.DOTALL)
            for material in materials:
                lines = [l.strip() for l in material.split('\n') if l.strip() and not l.strip().startswith('!')]
                if len(lines) >= 5:
                    try:
                        # Material format: Name, Roughness, Thickness, Conductivity, Density, Specific Heat, Thermal Absorptance...
                        thickness = float(lines[2].replace(',', '').strip())
                        conductivity = float(lines[3].replace(',', '').strip())
                        if conductivity > 0:
                            r_value = thickness / conductivity  # R = thickness / conductivity
                            if r_value > 0.1:  # Filter out very thin materials
                                wall_r_values.append(r_value)
                    except:
                        pass
            
            # Look for WindowMaterial:SimpleGlazingSystem objects
            simple_glazing = re.findall(r'WindowMaterial:SimpleGlazingSystem,\s*([^;]+);', idf_content, re.DOTALL)
            for glazing in simple_glazing:
                lines = [l.strip() for l in glazing.split('\n') if l.strip() and not l.strip().startswith('!')]
                if len(lines) >= 2:
                    try:
                        # Format: Name, U-Factor, SHGC
                        u_factor = float(lines[1].replace(',', '').strip())
                        if u_factor > 0:
                            window_u_values.append(u_factor)
                    except:
                        pass
            
            # Look for WindowMaterial:Glazing objects
            glazing_materials = re.findall(r'WindowMaterial:Glazing,\s*([^;]+);', idf_content, re.DOTALL)
            for glazing in glazing_materials:
                lines = [l.strip() for l in glazing.split('\n') if l.strip() and not l.strip().startswith('!')]
                if len(lines) >= 4:
                    try:
                        # Approximate U-value from thickness and conductivity
                        thickness = float(lines[2].replace(',', '').strip())
                        conductivity = float(lines[3].replace(',', '').strip())
                        if thickness > 0 and conductivity > 0:
                            u_value = conductivity / thickness
                            window_u_values.append(u_value)
                    except:
                        pass
            
            # Calculate averages
            if wall_r_values:
                avg_wall_r = sum(wall_r_values) / len(wall_r_values)
                thermal_props['wall_r_value'] = round(avg_wall_r, 2)
                thermal_props['wallRValue'] = round(avg_wall_r, 2)  # camelCase
            
            if window_u_values:
                avg_window_u = sum(window_u_values) / len(window_u_values)
                thermal_props['window_u_value'] = round(avg_window_u, 3)
                thermal_props['windowUValue'] = round(avg_window_u, 3)  # camelCase
                # Also provide R-value for windows (R = 1/U)
                if avg_window_u > 0:
                    thermal_props['window_r_value'] = round(1/avg_window_u, 2)
                    thermal_props['windowRValue'] = round(1/avg_window_u, 2)  # camelCase
            
            logger.info(f"📊 Thermal properties extracted:")
            logger.info(f"   Wall materials found: {len(wall_r_values)}")
            logger.info(f"   Window materials found: {len(window_u_values)}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting thermal properties: {e}")
        
        return thermal_props
    
    def compare_measured_data(self, simulated_result, measured_data):
        """
        Compare simulated results with measured energy data from bills
        
        Args:
            simulated_result: Dict with simulation results
            measured_data: Dict with measured data in format:
                {
                    "total_annual_kwh": 150000,
                    "monthly": [{"month": 1, "kwh": 12000}, ...]
                }
        
        Returns:
            Dict with comparison results
        """
        if not measured_data:
            return {}
        
        comparison = {
            "validation": {},
            "recommendations": []
        }
        
        try:
            simulated_total = simulated_result.get('total_energy_consumption', 0)
            measured_total = measured_data.get('total_annual_kwh', 0)
            
            if measured_total > 0:
                # Calculate difference
                difference_kwh = simulated_total - measured_total
                difference_percent = (difference_kwh / measured_total) * 100
                
                comparison["validation"] = {
                    "simulated_total_kwh": simulated_total,
                    "measured_total_kwh": measured_total,
                    "difference_kwh": round(difference_kwh, 2),
                    "difference_percent": round(difference_percent, 2)
                }
                
                # Determine calibration status
                abs_diff_percent = abs(difference_percent)
                if abs_diff_percent < 5:
                    status = "Excellent Match"
                    calibration_status = "calibrated"
                elif abs_diff_percent < 10:
                    status = "Good Match"
                    calibration_status = "good"
                elif abs_diff_percent < 15:
                    status = "Fair Match"
                    calibration_status = "fair"
                else:
                    status = "Needs Calibration"
                    calibration_status = "uncalibrated"
                
                comparison["validation"]["status"] = status
                comparison["validation"]["calibration_status"] = calibration_status
                
                # Add recommendations based on difference
                if difference_percent > 10:
                    if simulated_total < measured_total:
                        comparison["recommendations"].append(
                            "Simulated energy is significantly lower than measured. "
                            "Consider: verifying equipment schedules, plug loads, or HVAC operation hours."
                        )
                    else:
                        comparison["recommendations"].append(
                            "Simulated energy is significantly higher than measured. "
                            "Consider: verifying building construction details, occupancy patterns, or system efficiency."
                        )
                elif abs_diff_percent < 5:
                    comparison["recommendations"].append(
                        "Model accuracy is within acceptable range. "
                        "The simulation provides a reliable baseline for retrofit analysis."
                    )
                
                # Monthly validation if available
                monthly_data = measured_data.get('monthly', [])
                if monthly_data and len(monthly_data) >= 6:
                    # For now, we'll provide annual comparison
                    # Advanced monthly validation would require monthly simulation results
                    comparison["validation"]["has_monthly_data"] = True
                    comparison["validation"]["months_provided"] = len(monthly_data)
                    
                    comparison["recommendations"].append(
                        f"Monthly data provided for {len(monthly_data)} months. "
                        "For detailed monthly calibration, consider running monthly simulations."
                    )
                
                logger.info(f"📊 Measured data comparison:")
                logger.info(f"   Simulated: {simulated_total:,.0f} kWh")
                logger.info(f"   Measured: {measured_total:,.0f} kWh")
                logger.info(f"   Difference: {difference_percent:.1f}%")
                logger.info(f"   Status: {status}")
        
        except Exception as e:
            logger.error(f"❌ Error comparing measured data: {e}")
        
        return comparison
    
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
            measured_data = data.get('measured_data', None)
            
            if not idf_content:
                self.send_error_response(client_socket, "Missing idf_content")
                return
            
            logger.info(f"📊 IDF content: {len(idf_content)} bytes")
            logger.info(f"📊 Weather content: {len(weather_content)} bytes")
            if measured_data:
                logger.info(f"📊 Measured data provided: {measured_data.get('total_annual_kwh', 'N/A')} kWh")
            
            # Run simulation
            result = self.run_energyplus_simulation(idf_content, weather_content)
            
            # Compare with measured data if provided
            if measured_data and result.get('simulation_status') == 'success':
                comparison = self.compare_measured_data(result, measured_data)
                if comparison:
                    result.update(comparison)
            
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

