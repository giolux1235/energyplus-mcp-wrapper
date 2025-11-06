#!/usr/bin/env python3
"""
Standalone EnergyPlus Energy Extraction Tool
Extracts energy consumption data from EnergyPlus output files locally

Usage:
    python extract-energy-local.py <output_directory>
    python extract-energy-local.py <sqlite_file>
    python extract-energy-local.py <output_directory> --period-days 7
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnergyExtractor:
    """Extract energy data from EnergyPlus output files"""
    
    def __init__(self, simulation_days=7):
        self.simulation_days = simulation_days
        self.energy_data = {}
    
    def extract_from_directory(self, output_dir):
        """Extract energy from all files in output directory"""
        if not os.path.exists(output_dir):
            raise ValueError(f"Output directory not found: {output_dir}")
        
        logger.info(f"📁 Extracting energy from: {output_dir}")
        output_files = os.listdir(output_dir)
        logger.info(f"📁 Found {len(output_files)} files")
        
        # Try SQLite first (most reliable)
        sqlite_files = [f for f in output_files if 
                       (f.endswith('.sql') and ('eplusout' in f.lower() or 'sqlite' in f.lower())) or
                       f.endswith('.sqlite') or f.endswith('.sqlite3') or f.endswith('.db')]
        
        if sqlite_files:
            logger.info(f"📊 Found SQLite files: {sqlite_files}")
            for sql_file in sqlite_files:
                sqlite_path = os.path.join(output_dir, sql_file)
                data = self.extract_from_sqlite(sqlite_path)
                if data:
                    self.energy_data.update(data)
                    logger.info(f"✅ Extracted from {sql_file}")
        
        # Try HTML files
        html_files = [f for f in output_files if 
                     f.endswith('Table.html') or f.endswith('tbl.htm') or 
                     f.endswith('tbl.html') or (f.endswith('.html') and 'table' in f.lower())]
        
        if html_files and not self.energy_data.get('total_energy_consumption'):
            logger.info(f"📊 Found HTML files: {html_files}")
            for html_file in html_files:
                html_path = os.path.join(output_dir, html_file)
                data = self.extract_from_html(html_path)
                if data:
                    self.energy_data.update(data)
                    logger.info(f"✅ Extracted from {html_file}")
        
        # Try CSV files
        csv_files = [f for f in output_files if 
                    f.endswith('Meter.csv') or f.endswith('Table.csv') or 
                    (f.endswith('.csv') and 'meter' in f.lower())]
        
        if csv_files and not self.energy_data.get('total_energy_consumption'):
            logger.info(f"📊 Found CSV files: {csv_files}")
            for csv_file in csv_files:
                csv_path = os.path.join(output_dir, csv_file)
                data = self.extract_from_csv(csv_path)
                if data:
                    self.energy_data.update(data)
                    logger.info(f"✅ Extracted from {csv_file}")
        
        # Validate and correct
        self.validate_and_correct()
        
        return self.energy_data
    
    def extract_from_sqlite(self, sqlite_path):
        """Extract energy from SQLite database"""
        if not os.path.exists(sqlite_path):
            logger.warning(f"⚠️  SQLite file not found: {sqlite_path}")
            return {}
        
        energy_data = {}
        
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            logger.info(f"📊 Extracting from SQLite: {sqlite_path}")
            
            # Get schema info
            cursor.execute("PRAGMA table_info(ReportMeterDataDictionary)")
            dict_columns = [row[1] for row in cursor.fetchall()]
            
            value_col = 'VariableValue' if 'VariableValue' in [c[1] for c in cursor.execute("PRAGMA table_info(ReportMeterData)").fetchall()] else 'Value'
            name_col = 'VariableName' if 'VariableName' in dict_columns else ('KeyValue' if 'KeyValue' in dict_columns else dict_columns[-2] if len(dict_columns) > 1 else 'VariableName')
            
            # Query facility-level meters
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
                        WHERE (rmdd2.VariableName LIKE '%Electricity:Facility%' OR rmdd2.VariableName LIKE '%NaturalGas:Facility%')
                           AND (rmdd2.ReportingFrequency LIKE '%Run Period%' OR rmdd2.ReportingFrequency LIKE '%RunPeriod%')
                        GROUP BY rmdd2.ReportMeterDataDictionaryIndex
                    ) max_times ON rmd.ReportMeterDataDictionaryIndex = max_times.ReportMeterDataDictionaryIndex
                        AND rmd.TimeIndex = max_times.MaxTimeIndex
                    WHERE (rmdd.VariableName LIKE '%Electricity:Facility%' OR rmdd.VariableName LIKE '%NaturalGas:Facility%')
                       AND (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
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
                    WHERE ((rmdd.{name_col} LIKE '%Electricity:Facility%' OR rmdd.{name_col} LIKE '%NaturalGas:Facility%'))
                       AND (rmdd.ReportingFrequency LIKE '%Run Period%' OR rmdd.ReportingFrequency LIKE '%RunPeriod%')
                    GROUP BY rmdd.{name_col}
                """)
            
            meter_results = cursor.fetchall()
            logger.info(f"📊 Found {len(meter_results)} facility meters")
            
            total_energy = 0
            electricity_kwh = 0
            gas_kwh = 0
            
            for result in meter_results:
                if len(result) >= 4:
                    name, freq, units, value = result[0], result[1], result[2], result[3]
                else:
                    name = result[0]
                    value = result[1] if len(result) > 1 else result[-1]
                    units = None
                
                name_lower = name.lower() if name else ''
                
                # Convert units
                if units and units.upper() in ['J', 'JOULES']:
                    value_kwh = value / 3600000
                elif units and units.upper() in ['KWH']:
                    value_kwh = value
                else:
                    value_kwh = value / 3600000
                
                # Extract facility totals
                if 'electricity:facility' in name_lower or 'electricitynet:facility' in name_lower:
                    electricity_kwh += value_kwh
                    total_energy += value_kwh
                elif 'naturalgas:facility' in name_lower or 'gas:facility' in name_lower:
                    gas_kwh += value_kwh
                    total_energy += value_kwh
                
                # Extract breakdown
                elif ('heating' in name_lower or 'heat' in name_lower) and ('electricity' in name_lower or 'gas' in name_lower):
                    if 'heating_energy' not in energy_data:
                        energy_data['heating_energy'] = 0
                    energy_data['heating_energy'] += value_kwh
                elif ('cooling' in name_lower or 'cool' in name_lower):
                    if 'cooling_energy' not in energy_data:
                        energy_data['cooling_energy'] = 0
                    energy_data['cooling_energy'] += value_kwh
                elif ('lighting' in name_lower or 'lights' in name_lower):
                    if 'lighting_energy' not in energy_data:
                        energy_data['lighting_energy'] = 0
                    energy_data['lighting_energy'] += value_kwh
                elif ('equipment' in name_lower or 'plug' in name_lower):
                    if 'equipment_energy' not in energy_data:
                        energy_data['equipment_energy'] = 0
                    energy_data['equipment_energy'] += value_kwh
            
            if total_energy > 0:
                energy_data['total_energy_consumption'] = round(total_energy, 2)
                energy_data['electricity_kwh'] = round(electricity_kwh, 2)
                energy_data['gas_kwh'] = round(gas_kwh, 2)
                logger.info(f"✅ Total energy: {total_energy:.2f} kWh")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ SQLite extraction error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return energy_data
    
    def extract_from_html(self, html_path):
        """Extract energy from HTML summary file"""
        try:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for End Uses table
            if 'End Uses' not in content and 'Annual Building' not in content:
                return {}
            
            energy_data = {}
            # Simple extraction - look for kWh values in tables
            import re
            
            # Find building area
            area_match = re.search(r'Total Building Area[^<]*?(\d+\.?\d*)\s*m²', content, re.IGNORECASE)
            if area_match:
                energy_data['building_area'] = float(area_match.group(1))
            
            # Find energy values (simplified - would need more robust parsing)
            # This is a placeholder - full HTML parsing would be more complex
            logger.info("📊 HTML file found - parsing (simplified)")
            
        except Exception as e:
            logger.error(f"❌ HTML extraction error: {e}")
        
        return energy_data
    
    def extract_from_csv(self, csv_path):
        """Extract energy from CSV file"""
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            energy_data = {}
            lines = content.split('\n')
            
            for line in lines:
                line_lower = line.lower()
                if 'total building area' in line_lower and 'zone' not in line_lower:
                    parts = line.split(',')
                    for part in parts:
                        try:
                            area = float(part.strip())
                            if 50 < area < 50000:
                                energy_data['building_area'] = round(area, 2)
                                break
                        except:
                            continue
            
            logger.info("📊 CSV file found - parsing (simplified)")
            
        except Exception as e:
            logger.error(f"❌ CSV extraction error: {e}")
        
        return energy_data
    
    def validate_and_correct(self):
        """Validate and correct energy values based on simulation period"""
        if self.simulation_days > 0 and self.energy_data.get('total_energy_consumption', 0) > 0:
            total_energy = self.energy_data['total_energy_consumption']
            building_area = self.energy_data.get('building_area', 0)
            
            if building_area > 0:
                min_expected = (self.simulation_days / 365.0) * 100 * building_area
                max_expected = (self.simulation_days / 365.0) * 300 * building_area
                
                if total_energy > max_expected * 10:
                    correction_factor = self.simulation_days / 365.0
                    corrected_total = total_energy * correction_factor
                    
                    if corrected_total <= max_expected * 5:
                        logger.info(f"⚠️  Correcting annual total: {total_energy:.2f} → {corrected_total:.2f} kWh")
                        self.energy_data['total_energy_consumption'] = round(corrected_total, 2)
                        
                        # Correct breakdown
                        for key in ['heating_energy', 'cooling_energy', 'lighting_energy', 'equipment_energy']:
                            if key in self.energy_data and self.energy_data[key] > 0:
                                self.energy_data[key] = round(self.energy_data[key] * correction_factor, 2)


def main():
    parser = argparse.ArgumentParser(description='Extract energy data from EnergyPlus output files')
    parser.add_argument('path', help='Path to output directory or SQLite file')
    parser.add_argument('--period-days', type=int, default=7, help='Simulation period in days (default: 7)')
    parser.add_argument('--output', '-o', help='Output JSON file (default: print to stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    extractor = EnergyExtractor(simulation_days=args.period_days)
    
    path = Path(args.path)
    
    if path.is_file() and (path.suffix in ['.sql', '.sqlite', '.sqlite3', '.db']):
        # Single SQLite file
        logger.info(f"📊 Extracting from SQLite file: {path}")
        energy_data = extractor.extract_from_sqlite(str(path))
        extractor.energy_data = energy_data
        extractor.validate_and_correct()
    elif path.is_dir():
        # Output directory
        energy_data = extractor.extract_from_directory(str(path))
    else:
        logger.error(f"❌ Path not found: {path}")
        sys.exit(1)
    
    # Output results
    result = {
        'simulation_period_days': args.period_days,
        'energy_data': extractor.energy_data,
        'extraction_method': 'local'
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"✅ Results saved to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
    
    # Summary
    logger.info("\n📊 Extraction Summary:")
    logger.info(f"   Total Energy: {extractor.energy_data.get('total_energy_consumption', 0):.2f} kWh")
    logger.info(f"   Building Area: {extractor.energy_data.get('building_area', 0):.2f} m²")
    if extractor.energy_data.get('building_area', 0) > 0:
        eui = extractor.energy_data.get('total_energy_consumption', 0) / extractor.energy_data.get('building_area', 1)
        logger.info(f"   EUI: {eui:.2f} kWh/m²")


if __name__ == '__main__':
    main()

