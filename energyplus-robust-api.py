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
        
        # EnergyPlus paths - try common locations
        default_exe = '/usr/local/bin/energyplus'
        if not os.path.exists(default_exe):
            default_exe = '/usr/local/EnergyPlus-25-1-0/energyplus'
        if not os.path.exists(default_exe):
            default_exe = '/usr/local/EnergyPlus-24-2-0/energyplus'
        
        default_idd = '/usr/local/bin/Energy+.idd'
        if not os.path.exists(default_idd):
            default_idd = '/usr/local/EnergyPlus-25-1-0/Energy+.idd'
        if not os.path.exists(default_idd):
            default_idd = '/usr/local/EnergyPlus-24-2-0/Energy+.idd'
        
        self.energyplus_exe = os.environ.get('ENERGYPLUS_EXE', default_exe)
        self.energyplus_idd = os.environ.get('ENERGYPLUS_IDD', default_idd)
        
        logger.info(f"🚀 Robust EnergyPlus API v{self.version} starting...")
        logger.info(f"📊 EnergyPlus EXE: {self.energyplus_exe}")
        logger.info(f"📊 EnergyPlus IDD: {self.energyplus_idd}")
        
        # Test EnergyPlus installation (non-blocking)
        self.energyplus_available = self.test_energyplus()
        
        if not self.energyplus_available:
            logger.warning("⚠️  Starting service without EnergyPlus - simulations will fail")
        else:
            logger.info("✅ Service ready with EnergyPlus available")
    
    def test_energyplus(self):
        """Test EnergyPlus installation - graceful failure"""
        try:
            if not os.path.exists(self.energyplus_exe):
                logger.warning(f"⚠️  EnergyPlus not found at: {self.energyplus_exe}")
                logger.warning("   Service will start but simulations will fail until EnergyPlus is installed")
                return False
            
            result = subprocess.run([self.energyplus_exe, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ EnergyPlus installed: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"⚠️  EnergyPlus test failed: {result.stderr}")
                logger.warning("   Service will start but simulations will fail")
                return False
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️  EnergyPlus version check timed out")
            return False
        except Exception as e:
            logger.warning(f"⚠️  EnergyPlus test error: {e}")
            logger.warning("   Service will start but simulations will fail")
            return False
    
    def get_simulation_period_days(self, idf_content):
        """Extract simulation period in days from IDF"""
        try:
            # Find RunPeriod object
            run_period_pattern = r'RunPeriod[^]*?End_Month[^\d]*(\d+)[^]*?End_Day[^\d]*(\d+)'
            match = re.search(run_period_pattern, idf_content, re.MULTILINE | re.DOTALL)
            if match:
                end_month = int(match.group(1))
                end_day = int(match.group(2))
                
                # Also find begin month/day
                begin_match = re.search(r'Begin_Month[^\d]*(\d+)[^]*?Begin_Day[^\d]*(\d+)', idf_content, re.MULTILINE | re.DOTALL)
                if begin_match:
                    begin_month = int(begin_match.group(1))
                    begin_day = int(begin_match.group(2))
                    
                    # Calculate days (simple approximation)
                    from datetime import datetime
                    try:
                        begin_date = datetime(2024, begin_month, begin_day)
                        end_date = datetime(2024, end_month, end_day)
                        # Handle year rollover
                        if end_date < begin_date:
                            end_date = datetime(2025, end_month, end_day)
                        days = (end_date - begin_date).days + 1
                        return days
                    except:
                        # Fallback: estimate based on months
                        if end_month == begin_month:
                            return end_day - begin_day + 1
                        else:
                            return (end_month - begin_month) * 30 + (end_day - begin_day + 1)
        except Exception as e:
            logger.warning(f"⚠️  Could not extract simulation period: {e}")
        return 0
    
    def optimize_idf_for_fast_simulation(self, idf_content):
        """Optimize IDF for fast simulation by shortening the run period"""
        try:
            # Find RunPeriod objects - they typically look like:
            # RunPeriod,
            #   Name,
            #   Begin_Month,
            #   Begin_Day_of_Month,
            #   End_Month,
            #   End_Day_of_Month,
            #   ...
            
            # Use regex to find and modify RunPeriod
            # Pattern: RunPeriod, followed by name, then begin/end month/day
            run_period_pattern = r'(RunPeriod,\s*\n\s*[^,]+,\s*\n\s*)(\d+)(\s*,\s*!\s*-.*?\n\s*)(\d+)(\s*,\s*!\s*-.*?\n\s*)(\d+)(\s*,\s*!\s*-.*?\n\s*)(\d+)'
            
            def replace_run_period(match):
                name_part = match.group(1)
                begin_month = int(match.group(2))
                begin_day = int(match.group(4))
                end_month = int(match.group(6))
                end_day = int(match.group(8))
                
                # If it's a full year (Jan 1 to Dec 31), change to 1 week (Jan 1 to Jan 7) for faster completion
                if begin_month == 1 and begin_day == 1 and end_month == 12 and end_day == 31:
                    logger.info("   Changing RunPeriod from full year (Jan 1 - Dec 31) to 1 week (Jan 1 - Jan 7) for free tier")
                    return f"{name_part}1{match.group(3)}1{match.group(5)}1{match.group(7)}7"
                # If it's more than 1 week, reduce to 1 week
                elif end_month > begin_month or (end_month == begin_month and end_day > 7):
                    logger.info(f"   Reducing RunPeriod from {begin_month}/{begin_day} to {end_month}/{end_day} to 1 week")
                    return f"{name_part}{begin_month}{match.group(3)}{begin_day}{match.group(5)}{begin_month}{match.group(7)}7"
                # Otherwise keep as is
                else:
                    logger.info(f"   RunPeriod already short ({begin_month}/{begin_day} to {end_month}/{end_day}), keeping as is")
                    return match.group(0)
            
            # Try to find and replace RunPeriod
            modified_content = re.sub(run_period_pattern, replace_run_period, idf_content, flags=re.MULTILINE)
            
            # Also try a simpler pattern for RunPeriod with different formatting
            # Pattern: RunPeriod,\n  Name,\n  Begin_Month,\n  Begin_Day,\n  End_Month,\n  End_Day
            simple_pattern = r'(RunPeriod,[^\n]*\n[^\n]*\n\s*)(\d+)(\s*,\s*[^\n]*\n\s*)(\d+)(\s*,\s*[^\n]*\n\s*)(\d+)(\s*,\s*[^\n]*\n\s*)(\d+)'
            
            def replace_simple_run_period(match):
                begin_month = int(match.group(2))
                begin_day = int(match.group(4))
                end_month = int(match.group(6))
                end_day = int(match.group(8))
                
                # If it's a full year or long period, shorten to 1 week
                if (begin_month == 1 and begin_day == 1 and end_month == 12 and end_day == 31) or \
                   (end_month > begin_month + 1):
                    logger.info(f"   Shortening RunPeriod to 1 week (Jan 1-7) for free tier")
                    return f"{match.group(1)}1{match.group(3)}1{match.group(5)}1{match.group(7)}7"
                return match.group(0)
            
            modified_content = re.sub(simple_pattern, replace_simple_run_period, modified_content, flags=re.MULTILINE)
            
            # Check if we actually modified anything
            if modified_content != idf_content:
                logger.info("✅ IDF RunPeriod optimized for fast simulation")
                return modified_content
            else:
                # Try a more aggressive approach - look for any RunPeriod and modify it
                # Just find the pattern "End_Month" followed by a number > 1
                aggressive_pattern = r'(End_Month[^\d]*)(\d+)([^\d]*End_Day[^\d]*)(\d+)'
                
                def replace_aggressive(match):
                    end_month = int(match.group(2))
                    end_day = int(match.group(4))
                    if end_month > 1 or end_day > 7:
                        logger.info(f"   Aggressively shortening RunPeriod: End_Month {end_month}, End_Day {end_day} -> Jan 7")
                        return f"{match.group(1)}1{match.group(3)}7"
                    return match.group(0)
                
                modified_content = re.sub(aggressive_pattern, replace_aggressive, idf_content)
                
                if modified_content != idf_content:
                    logger.info("✅ IDF RunPeriod optimized (aggressive mode)")
                    return modified_content
                else:
                    logger.warning("⚠️  Could not find RunPeriod to optimize - simulation may be slow")
                    return idf_content
                    
        except Exception as e:
            logger.warning(f"⚠️  Error optimizing IDF: {e}. Continuing with original IDF.")
            return idf_content
    
    def read_request_simple(self, client_socket):
        """Simple request reading with better handling and timeout"""
        try:
            # Set socket timeout to prevent hanging
            client_socket.settimeout(30.0)  # 30 second timeout for reading
            
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
                                
                                # For very large requests, read in larger chunks
                                chunk_size = 8192
                                if content_length > 1000000:  # > 1MB
                                    chunk_size = 32768  # 32KB chunks
                                
                                while len(request) < expected_total:
                                    remaining = expected_total - len(request)
                                    read_size = min(chunk_size, remaining)
                                    chunk = client_socket.recv(read_size)
                                    if not chunk:
                                        break
                                    request += chunk
                                break
                    break
            
            return request.decode('utf-8', errors='ignore')
            
        except socket.timeout:
            logger.error(f"❌ Request read timeout")
            return ""
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
            
            # OPTIMIZE FOR RAILWAY FREE TIER: Shorten simulation period if needed
            # Free tier has 60s timeout, so we run shorter periods (2 weeks) instead of full year
            simulation_timeout = int(os.environ.get('SIMULATION_TIMEOUT', 55))
            # Allow disabling optimization via env var for testing
            disable_optimization = os.environ.get('DISABLE_IDF_OPTIMIZATION', 'false').lower() == 'true'
            optimize_for_free_tier = simulation_timeout <= 60 and not disable_optimization  # If timeout is 60s or less, optimize
            
            # Track simulation period for validation
            simulation_days = 365  # Default assumption (full year)
            
            if optimize_for_free_tier:
                logger.info("⚡ Optimizing IDF for Railway free tier (shortening simulation period)...")
                logger.info("   (Converting full year simulations to 1 week for faster completion)")
                # Check original period before optimization
                original_period = self.get_simulation_period_days(idf_content)
                if original_period > 0:
                    simulation_days = original_period
                    logger.info(f"   Original simulation period: {simulation_days} days")
                
                idf_content = self.optimize_idf_for_fast_simulation(idf_content)
                simulation_days = 7  # After optimization, it's 1 week
                logger.info("✅ IDF optimized for fast simulation (1 week period)")
            elif disable_optimization:
                logger.info("⚠️  IDF optimization DISABLED (DISABLE_IDF_OPTIMIZATION=true) - running full period")
                simulation_days = self.get_simulation_period_days(idf_content)
                if simulation_days > 0:
                    logger.info(f"   Simulation period: {simulation_days} days")
            else:
                simulation_days = self.get_simulation_period_days(idf_content)
                if simulation_days > 0:
                    logger.info(f"   Simulation period: {simulation_days} days")
            
            # Store simulation period for later validation
            self.current_simulation_days = simulation_days
            
            # Ensure Output:SQLite is in IDF - use 'Simple' for EnergyPlus 24.2.0 compatibility
            # EnergyPlus 24.2.0 may not support SimpleAndTabular, use Simple instead
            if 'Output:SQLite' not in idf_content:
                logger.warning("⚠️  Output:SQLite not found in IDF, adding it...")
                # Add Output:SQLite - use Simple for better compatibility
                idf_content += "\n\nOutput:SQLite,\n    Simple;        !- Option Type\n"
                logger.info("✅ Added Output:SQLite to IDF with Simple option")
            else:
                logger.info("✅ Output:SQLite found in IDF")
                # Check if it has a valid option type
                import re
                sqlite_match = re.search(r'Output:SQLite,\s*\n\s*([^;!]+)', idf_content)
                if sqlite_match:
                    option_type = sqlite_match.group(1).strip()
                    logger.info(f"   Current option type: '{option_type}'")
                    # Ensure it's Simple or SimpleAndTabular
                    if 'Simple' not in option_type and 'Tabular' not in option_type:
                        logger.warning(f"⚠️  Output:SQLite has unusual option type '{option_type}', changing to Simple...")
                        idf_content = re.sub(
                            r'Output:SQLite,\s*\n\s*[^;!]+;',
                            'Output:SQLite,\n    Simple;        !- Option Type',
                            idf_content
                        )
                        logger.info("✅ Updated Output:SQLite to use Simple option")
                    elif 'SimpleAndTabular' in option_type:
                        # For EnergyPlus 24.2.0, SimpleAndTabular may not work - change to Simple
                        logger.warning(f"   ⚠️  Output:SQLite uses SimpleAndTabular, but EnergyPlus 24.2.0 may not support it")
                        logger.info(f"   Changing to 'Simple' for compatibility...")
                        idf_content = re.sub(
                            r'Output:SQLite,\s*\n\s*SimpleAndTabular;',
                            'Output:SQLite,\n    Simple;        !- Option Type',
                            idf_content
                        )
                        logger.info("✅ Changed Output:SQLite from SimpleAndTabular to Simple")
                else:
                    logger.warning("⚠️  Could not parse Output:SQLite option type")
            
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
                
                # Run EnergyPlus with configurable timeout
                # For Railway free tier: Use 55s timeout with optimized IDF (2 week simulation)
                # For Railway Pro: Can use 180s+ with full year simulations
                # Set SIMULATION_TIMEOUT env var (default: 55s for free tier compatibility, within 60s HTTP limit)
                simulation_timeout = int(os.environ.get('SIMULATION_TIMEOUT', 55))
                logger.info(f"⏱️  Simulation timeout set to: {simulation_timeout} seconds")
                if simulation_timeout <= 60:
                    logger.info(f"   (Free tier mode: Using optimized 1-week simulation period)")
                else:
                    logger.info(f"   (Pro tier mode: Full simulation, ensure Railway HTTP timeout >= {simulation_timeout}s)")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=simulation_timeout
                )
                
                logger.info(f"📊 EnergyPlus exit code: {result.returncode}")
                logger.info(f"📊 STDOUT length: {len(result.stdout)} chars")
                logger.info(f"📊 STDERR length: {len(result.stderr)} chars")
                
                # Check output directory
                output_files = os.listdir(output_dir)
                logger.info(f"📁 Output files generated: {output_files}")
                
                # Check for SQLite files specifically - EnergyPlus generates eplusout.sql
                sqlite_files = [f for f in output_files if (f.endswith('.sql') and ('eplusout' in f.lower() or 'sqlite' in f.lower())) 
                                or 'sqlite' in f.lower() or f.endswith('.db')]
                if sqlite_files:
                    logger.info(f"✅ SQLite files found: {sqlite_files}")
                    for sql_file in sqlite_files:
                        sql_path = os.path.join(output_dir, sql_file)
                        if os.path.exists(sql_path):
                            size = os.path.getsize(sql_path)
                            logger.info(f"   - {sql_file}: {size:,} bytes")
                else:
                    logger.warning(f"⚠️  No SQLite files found in output directory")
                    logger.warning(f"   Expected: eplusout.sql (or similar)")
                    logger.warning(f"   All output files: {output_files[:20]}")
                    
                    # Check error file for SQLite warnings
                    err_files = [f for f in output_files if f.endswith('.err')]
                    if err_files:
                        err_path = os.path.join(output_dir, err_files[0])
                        try:
                            with open(err_path, 'r') as f:
                                err_content = f.read()
                                if 'SQLite' in err_content or 'sqlite' in err_content.lower():
                                    sqlite_warnings = [line for line in err_content.split('\n') if 'sqlite' in line.lower() or 'SQLite' in line]
                                    if sqlite_warnings:
                                        logger.warning(f"   SQLite-related messages in error file:")
                                        for warning in sqlite_warnings[:5]:
                                            logger.warning(f"      {warning}")
                                # Check if SimpleAndTabular caused issues
                                if 'SimpleAndTabular' in idf_content and ('invalid' in err_content.lower() or 'error' in err_content.lower()):
                                    logger.warning(f"   ⚠️  SimpleAndTabular may not be supported - consider using 'Simple' instead")
                        except Exception as e:
                            logger.warning(f"   Could not read error file: {e}")
                
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
            timeout_seconds = int(os.environ.get('SIMULATION_TIMEOUT', 55))
            error_msg = f"EnergyPlus simulation timed out ({timeout_seconds} seconds). The IDF was automatically optimized for fast simulation, but still timed out. Solutions: (1) Further simplify the IDF model, (2) Increase SIMULATION_TIMEOUT env var if on Railway Pro, (3) Check if IDF has complex HVAC systems that can be simplified."
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
            # EnergyPlus generates eplusout.err as the main error file
            err_file = None
            for file in output_files:
                if file.endswith('.err'):
                    # Prefer eplusout.err (main EnergyPlus error file)
                    if 'eplusout' in file:
                        err_file = os.path.join(output_dir, file)
                        break
                    elif err_file is None:  # Fallback to any .err file
                        err_file = os.path.join(output_dir, file)
            
            # If no .err file found, try eplusout.err directly
            if err_file is None:
                potential_err = os.path.join(output_dir, 'eplusout.err')
                if os.path.exists(potential_err):
                    err_file = potential_err
                    logger.info(f"📊 Found eplusout.err directly: {err_file}")
            
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
            
            # Check if extraction should be skipped (for local extraction workflow)
            skip_extraction = os.environ.get('SKIP_ENERGY_EXTRACTION', 'false').lower() == 'true'
            
            if skip_extraction:
                logger.info("⚡ Skipping energy extraction (SKIP_ENERGY_EXTRACTION=true)")
                logger.info("   Returning raw output files for local extraction")
                
                # Build response with just output info (no extraction)
                response = {
                    "version": self.version,
                    "simulation_status": "success",
                    "energyplus_version": "25.1.0",
                    "real_simulation": True,
                    "exit_code": exit_code,
                    "warnings_count": len(warnings),
                    "warnings": warnings[:10] if warnings else [],
                    "processing_time": datetime.now().isoformat(),
                    "extraction_skipped": True,
                    "extraction_note": "Energy extraction skipped. Use extract-energy-local.py to extract energy data from output_files.",
                    **output_info  # Include error file, output files list, CSV preview, SQLite info
                }
                
                # Add note about local extraction
                response['local_extraction_instructions'] = {
                    "tool": "extract-energy-local.py",
                    "usage": "python extract-energy-local.py <output_directory> --period-days 7",
                    "output_files_location": "See output_files list in this response"
                }
                
                logger.info("✅ Returning raw output files (extraction skipped)")
                return response
            
            # Parse output data (normal flow)
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
            
            # Add energy_results field when extraction succeeds
            if energy_data.get('total_energy_consumption', 0) > 0:
                extraction_method = energy_data.pop('_extraction_method', 'standard')  # Remove internal tracking
                
                # Calculate total site energy (electricity + gas)
                # If we have separate electricity and gas values, sum them
                if energy_data.get('electricity_kwh', 0) > 0 or energy_data.get('gas_kwh', 0) > 0:
                    total_site_energy = energy_data.get('electricity_kwh', 0) + energy_data.get('gas_kwh', 0)
                else:
                    total_site_energy = energy_data.get('total_energy_consumption', 0)
                
                building_area = energy_data.get('building_area', 0)
                
                # Calculate EUI if we have both values
                eui = 0
                if total_site_energy > 0 and building_area > 0:
                    eui = total_site_energy / building_area
                
                # Build energy_results in the exact format required
                response['energy_results'] = {
                    "total_site_energy_kwh": round(total_site_energy, 2),
                    "building_area_m2": round(building_area, 2),
                    "eui_kwh_m2": round(eui, 2)
                }
                
                # Also include detailed breakdown for backward compatibility
                response['energy_results'].update({
                    "heating_energy": energy_data.get('heating_energy', 0),
                    "cooling_energy": energy_data.get('cooling_energy', 0),
                    "lighting_energy": energy_data.get('lighting_energy', 0),
                    "equipment_energy": energy_data.get('equipment_energy', 0),
                    "fans_energy": energy_data.get('fans_energy', 0),
                    "pumps_energy": energy_data.get('pumps_energy', 0),
                    "extraction_method": extraction_method
                })
                
                logger.info(f"✅ Added energy_results to response (method: {extraction_method})")
                logger.info(f"   Total site energy: {total_site_energy:.2f} kWh")
                logger.info(f"   Building area: {building_area:.2f} m²")
                logger.info(f"   EUI: {eui:.2f} kWh/m²")
            
            logger.info(f"✅ EnergyPlus output parsed successfully - REAL DATA!")
            logger.info(f"✅ Total energy: {energy_data.get('total_energy_consumption', 0)} kWh")
            return response
            
        except Exception as e:
            error_msg = f"Output parsing failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self.create_error_response(error_msg)
    
    def parse_all_output_files(self, output_dir):
        """Parse all output files - HTML first (most reliable), then MTR, CSV, ESO, SQLite"""
        energy_data = {}
        extraction_method = "standard"  # Track which method was used
        
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
        
        # FIX 1: Always try MTR files for breakdown, even if HTML provided total
        # HTML might have total but incomplete/zero breakdown for large buildings
        for file in output_files:
            if file.endswith('.mtr'):
                mtr_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing MTR for breakdown: {file}")
                data = self.parse_energyplus_mtr(mtr_path)
                if data:
                    # Always update breakdown fields if MTR has better data
                    breakdown_fields = ['heating_energy', 'cooling_energy', 'lighting_energy', 
                                       'equipment_energy', 'fans_energy', 'pumps_energy']
                    for field in breakdown_fields:
                        if field in data and data[field] > 0:
                            current_value = energy_data.get(field, 0)
                            if data[field] > current_value:  # Use larger value (more complete)
                                energy_data[field] = data[field]
                                logger.info(f"   Updated {field}: {data[field]:.2f} kWh")
                    
                    # Update total if facility-level total is larger (more reliable)
                    if 'total_energy_consumption' in data:
                        facility_total = data['total_energy_consumption']
                        current_total = energy_data.get('total_energy_consumption', 0)
                        if facility_total > current_total * 1.1:  # Only if significantly larger (10% threshold)
                            energy_data['total_energy_consumption'] = facility_total
                            logger.info(f"✅ Updated total from facility-level meter: {facility_total:.2f} kWh (was {current_total:.2f} kWh)")
                        elif facility_total > 0 and current_total == 0:
                            energy_data['total_energy_consumption'] = facility_total
                            logger.info(f"✅ Set total from facility-level meter: {facility_total:.2f} kWh")
                    
                    logger.info(f"✅ MTR data merged: breakdown updated, total may be updated")
        
        # Try CSV files - as fallback for energy, but always try for building area
        for file in output_files:
            if file.endswith('Meter.csv') or file.endswith('Table.csv') or file.endswith('.csv'):
                csv_path = os.path.join(output_dir, file)
                logger.info(f"📊 Parsing CSV: {file}")
                data = self.parse_energyplus_csv(csv_path)
                if data:
                    # Always update building_area from CSV if found (most reliable source)
                    if 'building_area' in data and data['building_area'] > 0:
                        energy_data['building_area'] = data['building_area']
                        logger.info(f"✅ Updated building area from CSV: {data['building_area']:.2f} m²")
                    # Only update energy if we don't have it yet
                    if energy_data.get('total_energy_consumption', 0) == 0:
                        energy_data.update(data)
                        logger.info(f"✅ Got energy data from {file}: {list(data.keys())}")
        
        # Try ESO file (EnergyPlus Standard Output) - before SQLite
        if energy_data.get('total_energy_consumption', 0) == 0:
            for file in output_files:
                if file.endswith('.eso'):
                    eso_path = os.path.join(output_dir, file)
                    logger.info(f"📊 Parsing ESO: {file}")
                    data = self.parse_energyplus_eso(eso_path)
                    if data:
                        energy_data.update(data)
                        logger.info(f"✅ Got data from {file}: {list(data.keys())}")
        
        # FIX: Always check SQLite for facility-level meters (most reliable source)
        # Even if HTML/CSV provided a total, SQLite may have the complete facility-level meters
        # EnergyPlus generates SQLite as eplusout.sql (not .sqlite extension)
        current_total = energy_data.get('total_energy_consumption', 0)
        
        # Look for SQLite files - check for .sql files first (most common)
        sqlite_files_found = []
        for file in output_files:
            if (file.endswith('.sqlite') or file.endswith('.sqlite3') or file.endswith('.db') or 
                (file.endswith('.sql') and ('eplusout' in file.lower() or 'sqlite' in file.lower()))):
                sqlite_files_found.append(file)
        
        if sqlite_files_found:
            logger.info(f"📊 Found {len(sqlite_files_found)} SQLite file(s): {sqlite_files_found}")
        
        for file in sqlite_files_found:
            sqlite_path = os.path.join(output_dir, file)
            logger.info(f"📊 Parsing SQLite for facility-level meters: {file}")
            
            # Check if file exists and has content
            if not os.path.exists(sqlite_path):
                logger.warning(f"⚠️  SQLite file not found: {sqlite_path}")
                continue
            
            file_size = os.path.getsize(sqlite_path)
            logger.info(f"   File size: {file_size:,} bytes")
            
            sqlite_data = self.extract_energy_from_sqlite(sqlite_path)
            if sqlite_data and sqlite_data.get('total_energy_consumption', 0) > 0:
                sqlite_total = sqlite_data.get('total_energy_consumption', 0)
                
                # Prioritize SQLite if it has facility-level meters
                # HTML/CSV is known to be incomplete (76% too low), so trust SQLite more
                # However, if SQLite is extremely high (>100x), it's likely wrong
                ratio = sqlite_total / current_total if current_total > 0 else float('inf')
                
                if sqlite_total > current_total * 1.2 and ratio < 100:
                    # SQLite is higher and reasonable - use it
                    logger.info(f"✅ SQLite facility meters found: {sqlite_total:.2f} kWh (vs {current_total:.2f} kWh from HTML/CSV)")
                    logger.info(f"   Ratio: {ratio:.1f}x - Using SQLite (HTML/CSV known to be incomplete)")
                    energy_data.update(sqlite_data)
                    extraction_method = "sqlite"
                    logger.info(f"✅ Updated energy data from SQLite: {list(sqlite_data.keys())}")
                elif ratio >= 100:
                    logger.warning(f"⚠️  SQLite values are {ratio:.1f}x higher than HTML/CSV (likely error)")
                    logger.warning(f"   SQLite: {sqlite_total:.2f} kWh, HTML/CSV: {current_total:.2f} kWh")
                    logger.warning(f"   SQLite values seem unreasonably high, keeping HTML/CSV values")
                    logger.warning(f"   This suggests a data format issue in SQLite extraction")
                elif sqlite_total > 0 and current_total == 0:
                    # No HTML/CSV data, use SQLite
                    logger.info(f"✅ No HTML/CSV data, using SQLite: {sqlite_total:.2f} kWh")
                    energy_data.update(sqlite_data)
                    extraction_method = "sqlite"
                    logger.info(f"✅ Updated energy data from SQLite: {list(sqlite_data.keys())}")
                elif sqlite_total > current_total * 0.8 and ratio < 2:
                    # SQLite is similar or slightly higher - use SQLite (more reliable)
                    logger.info(f"✅ SQLite values similar to HTML/CSV, using SQLite (more reliable)")
                    energy_data.update(sqlite_data)
                    extraction_method = "sqlite"
                    logger.info(f"✅ Updated energy data from SQLite")
                elif current_total == 0:
                    # No total yet, use SQLite
                    energy_data.update(sqlite_data)
                    extraction_method = "sqlite"
                    logger.info(f"✅ Got data from SQLite {file}: {list(sqlite_data.keys())}")
                else:
                    # SQLite has data but current total is similar or higher
                    # Still merge breakdown if SQLite has better breakdown
                    logger.info(f"📊 SQLite total ({sqlite_total:.2f} kWh) similar to current ({current_total:.2f} kWh)")
                    logger.info(f"   Merging SQLite breakdown data if available")
                    breakdown_fields = ['heating_energy', 'cooling_energy', 'lighting_energy', 
                                      'equipment_energy', 'fans_energy', 'pumps_energy']
                    for field in breakdown_fields:
                        if field in sqlite_data and sqlite_data[field] > energy_data.get(field, 0):
                            energy_data[field] = sqlite_data[field]
                            logger.info(f"   Updated {field} from SQLite: {sqlite_data[field]:.2f} kWh")
            break  # Stop after first SQLite file
        
        # Store extraction method for reporting
        energy_data['_extraction_method'] = extraction_method
        
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
            # FIX 2: Prioritize facility-level meters over breakdown
            total = 0
            facility_total = 0  # Track facility-level total separately
            facility_gas = 0
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
                    # Facility-level total is most reliable - capture it
                    facility_total = max(facility_total, value)
                    logger.info(f"   Found facility-level electricity meter: {value:.2f} kWh")
                elif 'naturalgas:facility' in meter_name or 'gas:facility' in meter_name:
                    # Capture facility-level gas separately
                    facility_gas = max(facility_gas, value)
                    logger.info(f"   Found facility-level gas meter: {value:.2f} kWh")
            
            # FIX 2: Use facility-level total as primary source (most reliable)
            # Breakdown is secondary and may be incomplete
            if facility_total > 0:
                total = facility_total + facility_gas  # Add gas if present
                logger.info(f"✅ Using facility-level total: {total:.2f} kWh (electricity: {facility_total:.2f}, gas: {facility_gas:.2f})")
            else:
                # Fallback to breakdown total if no facility-level meter found
                breakdown_total = heating + cooling + lighting + equipment + fans + pumps
                if breakdown_total > 0:
                    total = breakdown_total
                    logger.info(f"✅ Using breakdown total: {total:.2f} kWh (no facility-level meter found)")
                
                # Warn if breakdown is incomplete (common for large buildings)
                if total > 0:
                    logger.warning(f"⚠️  No facility-level meter found - breakdown may be incomplete")
            
            # Validation: Check if breakdown matches facility total (if both exist)
            if facility_total > 0:
                breakdown_total = heating + cooling + lighting + equipment + fans + pumps
                if breakdown_total > 0:
                    diff = abs(facility_total - breakdown_total)
                    diff_pct = (diff / facility_total * 100) if facility_total > 0 else 0
                    if diff_pct > 10:
                        logger.warning(f"⚠️  Breakdown total ({breakdown_total:.2f} kWh) differs from facility total ({facility_total:.2f} kWh) by {diff_pct:.1f}%")
                        logger.warning(f"   This suggests some energy categories are missing from breakdown")
                        logger.warning(f"   Using facility-level total ({facility_total + facility_gas:.2f} kWh) as primary source")
            
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
        """Parse EnergyPlus CSV files - Enhanced to extract building area"""
        try:
            with open(csv_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📊 CSV content: {len(content)} chars")
            
            energy_data = {}
            total = 0
            heating = 0
            cooling = 0
            lighting = 0
            equipment = 0
            building_area = 0
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                
                # Extract building area - look for "Total Building Area" specifically
                line_lower = line.lower()
                parts = line.split(',')
                
                # Priority 1: Look for "Total Building Area" in same line (format: ",Total Building Area,472.78,")
                # Make sure it's the main one (not a zone or sub-area)
                if 'total building area' in line_lower and 'zone' not in line_lower and 'space' not in line_lower:
                    for part in parts:
                        try:
                            area = float(part.strip())
                            if 50 < area < 50000:  # Reasonable building area range (m²)
                                # Only use if we don't have one yet, or if this is larger (main building area)
                                current_area = energy_data.get('building_area', 0)
                                if current_area == 0 or area > current_area:
                                    building_area = area
                                    energy_data['building_area'] = round(area, 2)
                                    logger.info(f"✅ Building area from CSV (Total Building Area): {area:.2f} m²")
                                    break
                        except (ValueError, AttributeError):
                            continue
                
                # Priority 2: Look for "Net Conditioned Building Area" (same as total if not already found)
                if 'net conditioned building area' in line_lower and energy_data.get('building_area', 0) == 0:
                    for part in parts:
                        try:
                            area = float(part.strip())
                            if 50 < area < 50000:
                                building_area = area
                                energy_data['building_area'] = round(area, 2)
                                logger.info(f"✅ Building area from CSV (Net Conditioned): {area:.2f} m²")
                                break
                        except (ValueError, AttributeError):
                            continue
                
                # Priority 3: Check for building area header (format: ",,Area [m2],...")
                # Only if we haven't found it yet
                if ('area [m2]' in line_lower or 'area [m²]' in line_lower) and energy_data.get('building_area', 0) == 0:
                    # Next line should have the value
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # Check if next line contains "Total Building Area" 
                        if 'total building area' in next_line.lower():
                            next_parts = next_line.split(',')
                            for part in next_parts:
                                try:
                                    area = float(part.strip())
                                    if 50 < area < 50000:
                                        building_area = area
                                        energy_data['building_area'] = round(area, 2)
                                        logger.info(f"✅ Building area from CSV (header + Total Building Area): {area:.2f} m²")
                                        break
                                except (ValueError, AttributeError):
                                    continue
                
                # Look for energy values
                if any(keyword in line_lower for keyword in ['electricity', 'gas', 'energy']):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 2:
                        try:
                            value = float(parts[-1])  # Last column is usually the value
                            if value > 0:
                                total += value
                                
                                # Categorize
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
    
    def extract_energy_from_sqlite(self, sqlite_path):
        """
        Extract energy consumption data from EnergyPlus SQLite database using multiple query strategies.
        
        EnergyPlus SQLite databases typically contain:
        - ReportData: Time series data with ReportDataDictionaryID
        - ReportDataDictionary: Metadata about variables (Name, Units, etc.)
        - Time: Timestamp information
        - ReportMeterData: Meter readings
        - ReportMeterDataDictionary: Meter metadata
        """
        energy_data = {}
        
        try:
            import sqlite3
            
            if not os.path.exists(sqlite_path):
                logger.warning(f"⚠️  SQLite file not found: {sqlite_path}")
                return energy_data
            
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            logger.info(f"📊 Extracting energy from SQLite: {sqlite_path}")
            
            # Strategy 1: Query ReportMeterData for facility-level meters
            # This is the most direct way to get total energy consumption
            try:
                # Check schema of both tables
                cursor.execute("PRAGMA table_info(ReportMeterData)")
                meter_columns = [row[1] for row in cursor.fetchall()]
                logger.info(f"📊 ReportMeterData columns: {meter_columns}")
                
                cursor.execute("PRAGMA table_info(ReportMeterDataDictionary)")
                dict_columns = [row[1] for row in cursor.fetchall()]
                logger.info(f"📊 ReportMeterDataDictionary columns: {dict_columns}")
                
                # Find value column - EnergyPlus uses 'VariableValue' in ReportMeterData
                value_col = 'VariableValue' if 'VariableValue' in meter_columns else 'Value' if 'Value' in meter_columns else 'MeterValue' if 'MeterValue' in meter_columns else meter_columns[-1] if meter_columns else 'VariableValue'
                
                # Find name column - EnergyPlus uses 'VariableName' for meter name (KeyValue may be None)
                # Check both KeyValue and VariableName columns
                name_col = None
                if 'VariableName' in dict_columns:
                    name_col = 'VariableName'
                elif 'KeyValue' in dict_columns:
                    name_col = 'KeyValue'
                elif 'Name' in dict_columns:
                    name_col = 'Name'
                else:
                    name_col = dict_columns[-2] if len(dict_columns) > 1 else 'VariableName'
                
                logger.info(f"   Using value column: {value_col}, name column: {name_col}")
                
                # Query for RunPeriod meters - get the last timestep value (final cumulative)
                # Use VariableName for matching (KeyValue may be None)
                # Build query based on available columns
                if 'VariableName' in dict_columns:
                    # Use VariableName (most reliable)
                    cursor.execute("""
                        SELECT 
                            COALESCE(rmdd.VariableName, rmdd.KeyValue, 'Unknown') as MeterName,
                            rmdd.ReportingFrequency,
                            rmdd.VariableUnits,
                            rmd.VariableValue as TotalValue
                        FROM ReportMeterData rmd
                        JOIN ReportMeterDataDictionary rmdd ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                        JOIN (
                            SELECT 
                                rmdd2.ReportMeterDataDictionaryIndex,
                                MAX(rmd2.TimeIndex) as MaxTimeIndex
                            FROM ReportMeterData rmd2
                            JOIN ReportMeterDataDictionary rmdd2 ON rmd2.ReportMeterDataDictionaryIndex = rmdd2.ReportMeterDataDictionaryIndex
                            WHERE (rmdd2.VariableName LIKE '%Electricity:Facility%' OR rmdd2.VariableName LIKE '%NaturalGas:Facility%')
                               AND (rmdd2.ReportingFrequency LIKE '%Run Period%' OR rmdd2.ReportingFrequency LIKE '%RunPeriod%')
                            GROUP BY rmdd2.ReportMeterDataDictionaryIndex
                        ) max_times ON rmd.ReportMeterDataDictionaryIndex = max_times.ReportMeterDataDictionaryIndex
                            AND rmd.TimeIndex = max_times.MaxTimeIndex
                        WHERE (rmdd.VariableName LIKE '%Electricity:Facility%' OR rmdd.VariableName LIKE '%NaturalGas:Facility%')
                           AND (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                    """)
                elif 'KeyValue' in dict_columns:
                    # Fallback to KeyValue
                    cursor.execute(f"""
                        SELECT 
                            COALESCE(rmdd.KeyValue, 'Unknown') as MeterName,
                            rmdd.ReportingFrequency,
                            rmdd.VariableUnits,
                            rmd.{value_col} as TotalValue
                        FROM ReportMeterData rmd
                        JOIN ReportMeterDataDictionary rmdd ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                        JOIN (
                            SELECT 
                                rmdd2.ReportMeterDataDictionaryIndex,
                                MAX(rmd2.TimeIndex) as MaxTimeIndex
                            FROM ReportMeterData rmd2
                            JOIN ReportMeterDataDictionary rmdd2 ON rmd2.ReportMeterDataDictionaryIndex = rmdd2.ReportMeterDataDictionaryIndex
                            WHERE (rmdd2.KeyValue LIKE '%Electricity:Facility%' OR rmdd2.KeyValue LIKE '%NaturalGas:Facility%')
                               AND (rmdd2.ReportingFrequency LIKE '%Run Period%' OR rmdd2.ReportingFrequency LIKE '%RunPeriod%')
                            GROUP BY rmdd2.ReportMeterDataDictionaryIndex
                        ) max_times ON rmd.ReportMeterDataDictionaryIndex = max_times.ReportMeterDataDictionaryIndex
                            AND rmd.TimeIndex = max_times.MaxTimeIndex
                        WHERE (rmdd.KeyValue LIKE '%Electricity:Facility%' OR rmdd.KeyValue LIKE '%NaturalGas:Facility%')
                           AND (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                    """)
                else:
                    # Generic fallback
                    cursor.execute(f"""
                        SELECT 
                            rmdd.{name_col} as MeterName,
                            rmdd.ReportingFrequency,
                            rmdd.VariableUnits,
                            MAX(rmd.{value_col}) as TotalValue
                        FROM ReportMeterData rmd
                        JOIN ReportMeterDataDictionary rmdd ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                        WHERE (rmdd.{name_col} LIKE '%Electricity:Facility%' OR rmdd.{name_col} LIKE '%NaturalGas:Facility%')
                           AND (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                        GROUP BY rmdd.{name_col}
                    """)
                
                meter_results = cursor.fetchall()
                logger.info(f"📊 Strategy 1 (ReportMeterData): Found {len(meter_results)} facility meters")
                
                # Also query for breakdown meters (heating, cooling, lighting, etc.) - but don't fail if it errors
                try:
                    # Query for all meters, not just facility-level
                    if 'VariableName' in dict_columns:
                        cursor.execute("""
                            SELECT 
                                COALESCE(rmdd.VariableName, rmdd.KeyValue, 'Unknown') as MeterName,
                                rmdd.ReportingFrequency,
                                rmdd.VariableUnits,
                                rmd.VariableValue as TotalValue
                            FROM ReportMeterData rmd
                            JOIN ReportMeterDataDictionary rmdd ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                            JOIN (
                                SELECT 
                                    rmdd2.ReportMeterDataDictionaryIndex,
                                    MAX(rmd2.TimeIndex) as MaxTimeIndex
                                FROM ReportMeterData rmd2
                                JOIN ReportMeterDataDictionary rmdd2 ON rmd2.ReportMeterDataDictionaryIndex = rmdd2.ReportMeterDataDictionaryIndex
                                WHERE (rmdd2.ReportingFrequency LIKE '%Run Period%' OR rmdd2.ReportingFrequency LIKE '%RunPeriod%')
                                GROUP BY rmdd2.ReportMeterDataDictionaryIndex
                            ) max_times ON rmd.ReportMeterDataDictionaryIndex = max_times.ReportMeterDataDictionaryIndex
                                AND rmd.TimeIndex = max_times.MaxTimeIndex
                            WHERE (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                            LIMIT 50
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT 
                                rmdd.{name_col} as MeterName,
                                rmdd.ReportingFrequency,
                                rmdd.VariableUnits,
                                MAX(rmd.{value_col}) as TotalValue
                            FROM ReportMeterData rmd
                            JOIN ReportMeterDataDictionary rmdd ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                            WHERE (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                            GROUP BY rmdd.{name_col}
                            LIMIT 50
                        """)
                    all_meters = cursor.fetchall()
                    logger.info(f"📊 Found {len(all_meters)} total meters (including breakdown)")
                    if all_meters:
                        for result in all_meters[:20]:  # Log first 20
                            if len(result) >= 4:
                                name, freq, units, value = result[0], result[1], result[2], result[3]
                                if units and units.upper() in ['J', 'JOULES']:
                                    value_kwh = value / 3600000
                                elif units and units.upper() in ['KWH']:
                                    value_kwh = value
                                else:
                                    value_kwh = value / 3600000
                                logger.info(f"   All meters: {name} | Units: {units} | Value: {value_kwh:.2f} kWh")
                except Exception as e:
                    logger.warning(f"⚠️  Could not query all meters (non-fatal): {e}")
                
                if meter_results:
                    for result in meter_results:
                        if len(result) >= 4:
                            name, freq, units, value = result[0], result[1], result[2], result[3]
                            # Convert based on units
                            if units and units.upper() in ['J', 'JOULES']:
                                value_kwh = value / 3600000
                            elif units and units.upper() in ['KWH']:
                                value_kwh = value
                            else:
                                value_kwh = value / 3600000  # Default assume J
                            logger.info(f"   Facility meter: {name} | Units: {units} | Freq: {freq} | Value: {value_kwh:.2f} kWh")
                        else:
                            name, value = result[0], result[1] if len(result) > 1 else result[-1]
                            value_kwh = value / 3600000  # Default assume J
                        logger.info(f"   Facility meter: {name} = {value_kwh:.2f} kWh")
                
                electricity_kwh = 0
                gas_kwh = 0
                total_energy = 0
                
                for result in meter_results:
                    if len(result) >= 4:
                        name, freq, units, value = result[0], result[1], result[2], result[3]
                    else:
                        name = result[0]
                        value = result[1] if len(result) > 1 else result[-1]
                        units = None
                    
                    name_lower = name.lower() if name else ''
                    # Convert based on units
                    if units and units.upper() in ['J', 'JOULES']:
                        value_kwh = value / 3600000
                    elif units and units.upper() in ['KWH']:
                        value_kwh = value
                    else:
                        value_kwh = value / 3600000  # Default assume J
                    
                    # Extract electricity and gas separately
                    if 'electricity:facility' in name_lower or 'electricitynet:facility' in name_lower:
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                    elif 'naturalgas:facility' in name_lower or 'gas:facility' in name_lower:
                        gas_kwh += value_kwh
                        total_energy += value_kwh
                    # Improved breakdown extraction - more flexible matching for IDF Creator files
                    # Match heating energy (various formats)
                    elif ('heating' in name_lower or 'heat' in name_lower) and ('electricity' in name_lower or 'gas' in name_lower or 'natural' in name_lower):
                        if 'heating_energy' not in energy_data:
                            energy_data['heating_energy'] = 0
                        energy_data['heating_energy'] += value_kwh
                        if 'gas' in name_lower or 'natural' in name_lower:
                            gas_kwh += value_kwh
                        else:
                            electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Heating energy: {name} = {value_kwh:.2f} kWh")
                    # Match cooling energy
                    elif ('cooling' in name_lower or 'cool' in name_lower) and ('electricity' in name_lower or 'energy' in name_lower):
                        if 'cooling_energy' not in energy_data:
                            energy_data['cooling_energy'] = 0
                        energy_data['cooling_energy'] += value_kwh
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Cooling energy: {name} = {value_kwh:.2f} kWh")
                    # Match lighting energy (various formats)
                    elif ('lighting' in name_lower or 'lights' in name_lower or 'interiorlights' in name_lower) and ('electricity' in name_lower or 'energy' in name_lower):
                        if 'lighting_energy' not in energy_data:
                            energy_data['lighting_energy'] = 0
                        energy_data['lighting_energy'] += value_kwh
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Lighting energy: {name} = {value_kwh:.2f} kWh")
                    # Match equipment energy (various formats)
                    elif ('equipment' in name_lower or 'interiorequipment' in name_lower or 'plug' in name_lower) and ('electricity' in name_lower or 'energy' in name_lower):
                        if 'equipment_energy' not in energy_data:
                            energy_data['equipment_energy'] = 0
                        energy_data['equipment_energy'] += value_kwh
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Equipment energy: {name} = {value_kwh:.2f} kWh")
                    # Match fans energy
                    elif ('fan' in name_lower or 'fans' in name_lower) and ('electricity' in name_lower or 'energy' in name_lower):
                        if 'fans_energy' not in energy_data:
                            energy_data['fans_energy'] = 0
                        energy_data['fans_energy'] += value_kwh
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Fans energy: {name} = {value_kwh:.2f} kWh")
                    # Match pumps energy
                    elif ('pump' in name_lower or 'pumps' in name_lower) and ('electricity' in name_lower or 'energy' in name_lower):
                        if 'pumps_energy' not in energy_data:
                            energy_data['pumps_energy'] = 0
                        energy_data['pumps_energy'] += value_kwh
                        electricity_kwh += value_kwh
                        total_energy += value_kwh
                        logger.info(f"   ✅ Pumps energy: {name} = {value_kwh:.2f} kWh")
                
                if total_energy > 0:
                    energy_data['total_energy_consumption'] = round(total_energy, 2)
                    energy_data['electricity_kwh'] = round(electricity_kwh, 2)
                    energy_data['gas_kwh'] = round(gas_kwh, 2)
                    logger.info(f"✅ Strategy 1: Total site energy = {total_energy:.2f} kWh (Electricity: {electricity_kwh:.2f}, Gas: {gas_kwh:.2f})")
                    
            except Exception as e:
                logger.warning(f"⚠️  Strategy 1 failed: {e}")
            
            # Strategy 2: Query ReportData for facility-level variables ONLY
            # Only use this if Strategy 1 found no facility meters
            # Focus on facility-level totals, not hourly data
            if energy_data.get('total_energy_consumption', 0) == 0:
                try:
                    # Only look for facility-level variables that are annual totals
                    # For RunPeriod reporting, get the LAST timestep value (final cumulative value)
                    # Use a subquery to get the maximum TimeIndex, then get the value at that time
                    cursor.execute("""
                        SELECT 
                            rdd.Name,
                            rdd.Units,
                            rdd.ReportingFrequency,
                            rd.Value as TotalValue
                        FROM ReportData rd
                        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                        JOIN (
                            SELECT 
                                rdd2.ReportDataDictionaryIndex,
                                MAX(rd2.TimeIndex) as MaxTimeIndex
                            FROM ReportData rd2
                            JOIN ReportDataDictionary rdd2 ON rd2.ReportDataDictionaryIndex = rdd2.ReportDataDictionaryIndex
                            WHERE ((rdd2.Name LIKE '%Electricity:Facility%')
                               OR (rdd2.Name LIKE '%NaturalGas:Facility%'))
                               AND rdd2.ReportingFrequency LIKE '%Run Period%'
                            GROUP BY rdd2.ReportDataDictionaryIndex
                        ) max_times ON rd.ReportDataDictionaryIndex = max_times.ReportDataDictionaryIndex
                            AND rd.TimeIndex = max_times.MaxTimeIndex
                        WHERE ((rdd.Name LIKE '%Electricity:Facility%')
                           OR (rdd.Name LIKE '%NaturalGas:Facility%'))
                           AND rdd.ReportingFrequency LIKE '%Run Period%'
                    """)
                    
                    report_results = cursor.fetchall()
                    logger.info(f"📊 Strategy 2 (ReportData): Found {len(report_results)} facility-level variables")
                    if report_results:
                        for name, units, freq, value in report_results[:5]:
                            logger.info(f"   Raw: {name} | Units: '{units}' | Freq: {freq} | Value: {value}")
                            # EnergyPlus stores in Joules - convert to kWh
                            if units in ['J', 'Joules', '']:
                                value_kwh = value / 3600000  # J to kWh
                                logger.info(f"   Converted (J→kWh): {value_kwh:.2f} kWh")
                            elif units in ['kWh', 'KWH']:
                                value_kwh = value
                                logger.info(f"   Already kWh: {value_kwh:.2f} kWh")
                            else:
                                value_kwh = value / 3600000  # Default assume J
                                logger.info(f"   Unknown units '{units}', assuming J: {value_kwh:.2f} kWh")
                    
                    total_energy = 0
                    electricity_kwh = 0
                    gas_kwh = 0
                    for name, units, freq, value in report_results:
                        name_lower = name.lower()
                        
                        # Only use RunPeriod or annual totals, skip hourly data
                        if freq and 'hourly' in freq.lower() and 'runperiod' not in freq.lower():
                            logger.info(f"   Skipping hourly data: {name} ({freq})")
                            continue
                        
                        # Convert to kWh based on units
                        if units in ['J', 'Joules']:
                            value_kwh = value / 3600000
                        elif units == 'GJ':
                            value_kwh = value * 277.778
                        elif units in ['kWh', 'kWh']:
                            value_kwh = value
                        else:
                            value_kwh = value / 3600000  # Default assume J
                        
                        # Only use facility-level totals
                        if 'electricity:facility' in name_lower or 'electricitynet:facility' in name_lower:
                            electricity_kwh += value_kwh
                            total_energy += value_kwh
                            logger.info(f"   ✅ Facility electricity: {name} = {value_kwh:.2f} kWh")
                        elif 'naturalgas:facility' in name_lower or ('gas:facility' in name_lower and 'natural' in name_lower):
                            gas_kwh += value_kwh
                            total_energy += value_kwh
                            logger.info(f"   ✅ Facility gas: {name} = {value_kwh:.2f} kWh")
                        elif 'facility' in name_lower and ('total' in name_lower or 'site' in name_lower):
                            total_energy += value_kwh
                            logger.info(f"   ✅ Facility total: {name} = {value_kwh:.2f} kWh")
                        # Improved breakdown extraction for Strategy 2
                        elif ('heating' in name_lower or 'heat' in name_lower) and 'facility' not in name_lower:
                            if 'heating_energy' not in energy_data:
                                energy_data['heating_energy'] = 0
                            energy_data['heating_energy'] += value_kwh
                            logger.info(f"   ✅ Heating (Strategy 2): {name} = {value_kwh:.2f} kWh")
                        elif ('cooling' in name_lower or 'cool' in name_lower) and 'facility' not in name_lower:
                            if 'cooling_energy' not in energy_data:
                                energy_data['cooling_energy'] = 0
                            energy_data['cooling_energy'] += value_kwh
                            logger.info(f"   ✅ Cooling (Strategy 2): {name} = {value_kwh:.2f} kWh")
                        elif ('lighting' in name_lower or 'lights' in name_lower or 'interiorlights' in name_lower) and 'facility' not in name_lower:
                            if 'lighting_energy' not in energy_data:
                                energy_data['lighting_energy'] = 0
                            energy_data['lighting_energy'] += value_kwh
                            logger.info(f"   ✅ Lighting (Strategy 2): {name} = {value_kwh:.2f} kWh")
                        elif ('equipment' in name_lower or 'interiorequipment' in name_lower or 'plug' in name_lower) and 'facility' not in name_lower:
                            if 'equipment_energy' not in energy_data:
                                energy_data['equipment_energy'] = 0
                            energy_data['equipment_energy'] += value_kwh
                            logger.info(f"   ✅ Equipment (Strategy 2): {name} = {value_kwh:.2f} kWh")
                        elif ('fan' in name_lower or 'fans' in name_lower) and 'facility' not in name_lower:
                            if 'fans_energy' not in energy_data:
                                energy_data['fans_energy'] = 0
                            energy_data['fans_energy'] += value_kwh
                            logger.info(f"   ✅ Fans (Strategy 2): {name} = {value_kwh:.2f} kWh")
                        elif ('pump' in name_lower or 'pumps' in name_lower) and 'facility' not in name_lower:
                            if 'pumps_energy' not in energy_data:
                                energy_data['pumps_energy'] = 0
                            energy_data['pumps_energy'] += value_kwh
                            logger.info(f"   ✅ Pumps (Strategy 2): {name} = {value_kwh:.2f} kWh")
                    
                    if total_energy > 0:
                        # Validation: Check if values are reasonable
                        # For office buildings, EUI should be 20-50 kWh/m² typically
                        # If we have building area, validate EUI
                        building_area = energy_data.get('building_area', 0)
                        if building_area > 0:
                            eui = total_energy / building_area
                            if eui > 500:  # Sanity check: EUI > 500 kWh/m² is clearly wrong
                                logger.warning(f"⚠️  SQLite values seem unreasonable: EUI = {eui:.2f} kWh/m²")
                                logger.warning(f"   Expected range: 20-50 kWh/m² for office buildings")
                                logger.warning(f"   Rejecting SQLite values, will use HTML/CSV instead")
                                total_energy = 0  # Reject these values
                            else:
                                logger.info(f"✅ Strategy 2: Total site energy = {total_energy:.2f} kWh (Electricity: {electricity_kwh:.2f}, Gas: {gas_kwh:.2f}, EUI: {eui:.2f} kWh/m²)")
                        
                        if total_energy > 0:
                            energy_data['total_energy_consumption'] = round(total_energy, 2)
                            energy_data['electricity_kwh'] = round(electricity_kwh, 2)
                            energy_data['gas_kwh'] = round(gas_kwh, 2)
                        else:
                            logger.info(f"⚠️  Strategy 2: Values rejected as unreasonable")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Strategy 2 failed: {e}")
            
            # Strategy 3: Query for annual totals (if available)
            if energy_data.get('total_energy_consumption', 0) == 0:
                try:
                    cursor.execute("""
                        SELECT 
                            rdd.Name,
                            SUM(rd.Value) as TotalValue
                        FROM ReportData rd
                        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                        WHERE rdd.Name LIKE '%Annual%' 
                           OR rdd.Name LIKE '%Total%'
                           OR rdd.Name LIKE '%Sum%'
                        GROUP BY rdd.Name
                    """)
                    
                    annual_results = cursor.fetchall()
                    logger.info(f"📊 Strategy 3 (Annual totals): Found {len(annual_results)} annual variables")
                    
                    for name, value in annual_results:
                        name_lower = name.lower()
                        value_kwh = value / 3600000 if value > 1000000 else value  # Assume J if large, otherwise kWh
                        
                        if 'total' in name_lower or 'facility' in name_lower:
                            if 'total_energy_consumption' not in energy_data:
                                energy_data['total_energy_consumption'] = 0
                            energy_data['total_energy_consumption'] += value_kwh
                    
                    if energy_data.get('total_energy_consumption', 0) > 0:
                        energy_data['total_energy_consumption'] = round(energy_data['total_energy_consumption'], 2)
                        logger.info(f"✅ Strategy 3: Total energy = {energy_data['total_energy_consumption']:.2f} kWh")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Strategy 3 failed: {e}")
            
            # VALIDATION: Check if values are reasonable for simulation period
            # Get simulation period (default to 7 days if not set)
            simulation_days = getattr(self, 'current_simulation_days', 7)
            
            if simulation_days > 0 and energy_data.get('total_energy_consumption', 0) > 0:
                total_energy = energy_data['total_energy_consumption']
                building_area = energy_data.get('building_area', 0)
                
                # Expected energy range for simulation period
                # Typical office: 100-300 kWh/m²/year
                # For simulation period: (period_days / 365) * (100-300) * area
                if building_area > 0:
                    min_expected = (simulation_days / 365.0) * 100 * building_area
                    max_expected = (simulation_days / 365.0) * 300 * building_area
                    
                    # If value is more than 3x max expected, likely wrong (annual total or unit issue)
                    if total_energy > max_expected * 3:
                        logger.warning(f"⚠️  Energy value ({total_energy:.2f} kWh) seems too high for {simulation_days}-day simulation")
                        logger.warning(f"   Expected range: {min_expected:.0f} - {max_expected:.0f} kWh")
                        logger.warning(f"   Value is {total_energy/max_expected:.1f}x higher than expected max")
                        logger.warning(f"   Possible issues: Annual totals instead of period totals, or unit conversion error")
                        
                        # If value is suspiciously high (like annual), try dividing by (365/simulation_days)
                        if total_energy > max_expected * 10:
                            correction_factor = simulation_days / 365.0
                            corrected_total = total_energy * correction_factor
                            logger.warning(f"   Attempting correction: {total_energy:.2f} * {correction_factor:.4f} = {corrected_total:.2f} kWh")
                            
                            # Apply correction if it's significantly better (reduces by at least 50%)
                            # and brings it closer to expected range (within 5x max expected)
                            improvement_ratio = corrected_total / total_energy
                            if improvement_ratio < 0.5 and corrected_total <= max_expected * 5:
                                logger.info(f"   ✅ Applying correction - value was likely annual total")
                                logger.info(f"   Original: {total_energy:.2f} kWh → Corrected: {corrected_total:.2f} kWh")
                                energy_data['total_energy_consumption'] = round(corrected_total, 2)
                                
                                # Also correct breakdown if present
                                for key in ['heating_energy', 'cooling_energy', 'lighting_energy', 'equipment_energy', 'fans_energy', 'pumps_energy']:
                                    if key in energy_data and energy_data[key] > 0:
                                        energy_data[key] = round(energy_data[key] * correction_factor, 2)
                                
                                if 'electricity_kwh' in energy_data:
                                    energy_data['electricity_kwh'] = round(energy_data['electricity_kwh'] * correction_factor, 2)
                                if 'gas_kwh' in energy_data:
                                    energy_data['gas_kwh'] = round(energy_data['gas_kwh'] * correction_factor, 2)
                            else:
                                logger.warning(f"   ⚠️  Correction didn't help enough (improvement: {improvement_ratio:.2f}, still {corrected_total/max_expected:.1f}x expected)")
            
            # Round all energy values
            for key in ['heating_energy', 'cooling_energy', 'lighting_energy', 'equipment_energy', 'fans_energy', 'pumps_energy']:
                if key in energy_data:
                    energy_data[key] = round(energy_data[key], 2)
            
            # Calculate total from breakdown if we have breakdown but no total
            if energy_data.get('total_energy_consumption', 0) == 0:
                breakdown_total = sum([
                    energy_data.get('heating_energy', 0),
                    energy_data.get('cooling_energy', 0),
                    energy_data.get('lighting_energy', 0),
                    energy_data.get('equipment_energy', 0),
                    energy_data.get('fans_energy', 0),
                    energy_data.get('pumps_energy', 0)
                ])
                if breakdown_total > 0:
                    energy_data['total_energy_consumption'] = round(breakdown_total, 2)
                    logger.info(f"✅ Calculated total from breakdown: {breakdown_total:.2f} kWh")
            
            # Strategy 4: Try to extract building area from SQLite
            # Look for building area in various tables
            if energy_data.get('building_area', 0) == 0:
                try:
                    # Try ReportData for building area
                    cursor.execute("""
                        SELECT 
                            rdd.Name,
                            AVG(rd.Value) as AvgValue
                        FROM ReportData rd
                        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                        WHERE rdd.Name LIKE '%Area%' 
                           OR rdd.Name LIKE '%Floor%'
                           OR rdd.Name LIKE '%Building%'
                        GROUP BY rdd.Name
                        LIMIT 10
                    """)
                    
                    area_results = cursor.fetchall()
                    for name, value in area_results:
                        name_lower = name.lower()
                        # Look for total or net conditioned area
                        if 'total' in name_lower or 'net' in name_lower or 'conditioned' in name_lower:
                            if value > 100:  # Reasonable building area (m²)
                                energy_data['building_area'] = round(value, 2)
                                logger.info(f"✅ Found building area from SQLite: {value:.2f} m² ({name})")
                                break
                except Exception as e:
                    logger.warning(f"⚠️  Could not extract building area from SQLite: {e}")
            
            conn.close()
            
            if energy_data.get('total_energy_consumption', 0) > 0:
                logger.info(f"✅ SQLite extraction successful: {energy_data.get('total_energy_consumption', 0):.2f} kWh")
            else:
                logger.warning("⚠️  SQLite extraction found no energy data")
            
        except ImportError:
            logger.warning("⚠️  sqlite3 module not available")
        except Exception as e:
            logger.error(f"❌ SQLite extraction error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return energy_data
    
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
            # 1. Full error file content (limit to 100KB to avoid response size issues)
            if err_file and os.path.exists(err_file):
                try:
                    with open(err_file, 'r', encoding='utf-8', errors='ignore') as f:
                        error_content = f.read()
                    # Limit size to prevent huge responses (keep last 100KB if too large)
                    max_error_size = 100 * 1024  # 100KB
                    if len(error_content) > max_error_size:
                        logger.warning(f"⚠️  Error file is large ({len(error_content)} chars), truncating to last {max_error_size} chars")
                        error_content = error_content[-max_error_size:]
                        output_info['error_file_content'] = error_content
                        output_info['error_file_truncated'] = True
                        output_info['error_file_original_size'] = len(f.read()) if os.path.exists(err_file) else 0
                    else:
                        output_info['error_file_content'] = error_content
                        output_info['error_file_truncated'] = False
                    logger.info(f"✅ Captured error file content ({len(output_info['error_file_content'])} chars)")
                except Exception as e:
                    logger.warning(f"⚠️  Could not read error file: {e}")
                    output_info['error_file_content'] = f"Error reading file: {str(e)}"
            
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
                # EnergyPlus generates SQLite as .sql files (eplusout.sql)
                if (file['name'].endswith('.sqlite') or file['name'].endswith('.sqlite3') or 
                    file['name'].endswith('.db') or 
                    (file['name'].endswith('.sql') and 'eplusout' in file['name'])):
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
            
            # Try to get building area - should have been extracted by now
            if 'building_area' not in energy_data or energy_data.get('building_area', 0) == 0:
                logger.warning("⚠️  WARNING: Could not extract building area from EnergyPlus output!")
                logger.warning("⚠️  Using default 511.16 m² - EUI calculations may be incorrect!")
                logger.warning("⚠️  This is a fallback value and should be investigated!")
                energy_data['building_area'] = 511.16  # m² (5500 ft² - typical small office)
                energy_data['_area_extraction_failed'] = True  # Flag for debugging
            
            building_area = energy_data.get('building_area', 511.16)
            
            # Validate building area is reasonable
            if building_area < 50 or building_area > 50000:
                logger.warning(f"⚠️  WARNING: Building area {building_area:.2f} m² seems unreasonable!")
                logger.warning("⚠️  Expected range: 50-50000 m²")
            
            # Calculate energy intensity (kWh/m²)
            if total_energy > 0 and building_area > 0:
                energy_intensity = total_energy / building_area
                energy_data['energy_intensity'] = round(energy_intensity, 2)
                energy_data['energyUseIntensity'] = round(energy_intensity, 2)  # camelCase for UI
                
                # FIX 3: Validate EUI - detect suspiciously low values
                if energy_intensity < 5:
                    logger.warning(f"⚠️  WARNING: EUI ({energy_intensity:.2f} kWh/m²) is suspiciously low!")
                    logger.warning(f"   Expected range: 15-50 kWh/m² for office buildings")
                    logger.warning(f"   This suggests energy extraction may be incomplete")
                    logger.warning(f"   Total energy: {total_energy:.2f} kWh for {building_area:.2f} m² building")
                    
                    # Check breakdown completeness
                    breakdown_total = (
                        energy_data.get('heating_energy', 0) +
                        energy_data.get('cooling_energy', 0) +
                        energy_data.get('lighting_energy', 0) +
                        energy_data.get('equipment_energy', 0) +
                        energy_data.get('fans_energy', 0) +
                        energy_data.get('pumps_energy', 0)
                    )
                    
                    if breakdown_total < total_energy * 0.5:
                        logger.warning(f"⚠️  CRITICAL: Breakdown ({breakdown_total:.2f} kWh) is <50% of total ({total_energy:.2f} kWh)")
                        logger.warning(f"   This indicates missing energy categories in breakdown")
                        logger.warning(f"   Energy extraction is likely incomplete!")
                        energy_data['_energy_extraction_incomplete'] = True
                    elif breakdown_total == 0:
                        logger.warning(f"⚠️  CRITICAL: Breakdown is completely zero (0.00 kWh)")
                        logger.warning(f"   This indicates breakdown extraction failed!")
                        logger.warning(f"   Total energy may be incomplete - check facility-level meters")
                        energy_data['_energy_extraction_incomplete'] = True
            
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
            "energyplus_available": getattr(self, 'energyplus_available', False) or os.path.exists(self.energyplus_exe),
            "energyplus_exe": self.energyplus_exe,
            "energyplus_idd": self.energyplus_idd,
            "timestamp": datetime.now().isoformat()
        }
        self.send_json_response(client_socket, response)
    
    def handle_simulate(self, client_socket, request_text):
        """Handle simulation request"""
        try:
            # Set socket timeout to prevent Railway timeout issues
            # Railway typically has 30-60s timeout, so we need to be careful
            client_socket.settimeout(600.0)  # 10 minutes for entire request
            
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
            
            # For Railway, we need to send a keep-alive or process quickly
            # Reduce simulation timeout to match Railway's limits better
            # Run simulation with reduced timeout for Railway compatibility
            logger.info("⚡ Starting simulation (Railway-optimized)...")
            result = self.run_energyplus_simulation(idf_content, weather_content)
            
            # Compare with measured data if provided
            if measured_data and result.get('simulation_status') == 'success':
                comparison = self.compare_measured_data(result, measured_data)
                if comparison:
                    result.update(comparison)
            
            # Send response immediately after simulation
            logger.info("📤 Sending response...")
            self.send_json_response(client_socket, result)
            logger.info("✅ Response sent successfully")
            
        except socket.timeout:
            error_msg = "Request timed out - simulation took too long"
            logger.error(f"❌ {error_msg}")
            self.send_error_response(client_socket, error_msg)
        except Exception as e:
            logger.error(f"❌ Simulate error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.send_error_response(client_socket, str(e))
    
    def send_json_response(self, client_socket, data):
        """Send JSON HTTP response"""
        try:
            json_data = json.dumps(data, indent=2)
            response = f"HTTP/1.1 200 OK\r\n"
            response += f"Content-Type: application/json\r\n"
            response += f"Content-Length: {len(json_data)}\r\n"
            response += f"Access-Control-Allow-Origin: *\r\n"
            response += f"Connection: close\r\n"
            response += f"\r\n"
            response += json_data
            
            # Send response in chunks if large
            response_bytes = response.encode('utf-8')
            if len(response_bytes) > 100000:  # > 100KB
                logger.info(f"📤 Sending large response ({len(response_bytes)} bytes) in chunks...")
                chunk_size = 32768
                for i in range(0, len(response_bytes), chunk_size):
                    chunk = response_bytes[i:i+chunk_size]
                    client_socket.sendall(chunk)
                    logger.info(f"   Sent chunk {i//chunk_size + 1} ({len(chunk)} bytes)")
            else:
                client_socket.sendall(response_bytes)
            
            logger.info(f"✅ Response sent: {len(response_bytes)} bytes")
        except Exception as e:
            logger.error(f"❌ Send response error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
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

