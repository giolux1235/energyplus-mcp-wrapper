#!/usr/bin/env python3
"""
Comprehensive Test Suite for Auto-Chunking Parser
Tests various large file scenarios to ensure robustness
"""

import json
import subprocess
import time
import sys

def create_test_file(size_mb, file_type="idf"):
    """Create test files of different sizes"""
    if file_type == "idf":
        content = 'Building,Test Building,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\n'
        content += 'Site:Location,Test Location,40.0,-74.0,-5.0,10.0;\n'
        content += 'Zone,MainZone,0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\n'
        content += 'ZoneArea,MainZone,1000.0;\n'
        
        # Add objects to reach target size
        target_size = size_mb * 1024 * 1024
        objects_per_mb = 4000  # Approximate objects per MB
        total_objects = int((target_size / len(content)) * objects_per_mb)
        
        for i in range(total_objects):
            content += f'Lights,Lighting{i},MainZone,Schedule1,LightingLevel,100.0,0.0,0.0,0.0,0.0;\n'
            content += f'ElectricEquipment,Equipment{i},MainZone,Schedule1,EquipmentLevel,50.0,0.0,0.0,0.0,0.0;\n'
            content += f'People,People{i},MainZone,Schedule1,People,1.0,0.0,0.0,0.0,0.0;\n'
            
            if len(content) >= target_size:
                break
    
    return content

def test_api_call(payload, test_name):
    """Test API call and return results"""
    print(f"\n=== {test_name} ===")
    print(f"Payload size: {len(json.dumps(payload))} bytes")
    
    try:
        result = subprocess.run([
            'curl', '-X', 'POST', 
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload),
            'https://web-production-1d1be.up.railway.app/simulate'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return analyze_results(data, test_name)
            except json.JSONDecodeError:
                print(f"❌ JSON Parse Error: {result.stdout[:200]}")
                return False
        else:
            print(f"❌ CURL Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Request took too long")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def analyze_results(data, test_name):
    """Analyze API results for validity"""
    print(f"✅ API Response received")
    
    # Check basic fields
    status = data.get('simulation_status', 'Unknown')
    version = data.get('version', 'Unknown')
    content_size = data.get('content_size', 0)
    building_area = data.get('building_area', 0)
    total_energy = data.get('total_energy_consumption', 0)
    
    print(f"Status: {status}")
    print(f"Version: {version}")
    print(f"Content Size: {content_size} bytes")
    print(f"Building Area: {building_area} m²")
    print(f"Total Energy: {total_energy} kWh")
    
    # Check for auto-chunking
    auto_chunking = data.get('auto_chunking', False)
    chunks_processed = data.get('chunks_processed', 1)
    auto_chunking_used = data.get('auto_chunking_used', False)
    
    print(f"Auto-Chunking: {auto_chunking}")
    print(f"Chunks Processed: {chunks_processed}")
    print(f"Auto-Chunking Used: {auto_chunking_used}")
    
    # Validate results
    issues = []
    
    if status != 'success':
        issues.append(f"Status is not 'success': {status}")
    
    if content_size == 0:
        issues.append("Content size is 0 (truncation)")
    
    if building_area == 0:
        issues.append("Building area is 0")
    
    if total_energy == 0:
        issues.append("Total energy is 0")
    
    if total_energy < 0:
        issues.append(f"Total energy is negative: {total_energy}")
    
    if total_energy > 10000000:  # 10M kWh seems unrealistic
        issues.append(f"Total energy seems too high: {total_energy} kWh")
    
    # Check lighting and equipment
    lighting_objects = data.get('lighting_objects_found', 0)
    equipment_objects = data.get('equipment_objects_found', 0)
    
    print(f"Lighting Objects: {lighting_objects}")
    print(f"Equipment Objects: {equipment_objects}")
    
    if lighting_objects == 0 and content_size > 1000:
        issues.append("No lighting objects found despite large content")
    
    if equipment_objects == 0 and content_size > 1000:
        issues.append("No equipment objects found despite large content")
    
    # Check energy breakdown
    heating_energy = data.get('heating_energy', 0)
    cooling_energy = data.get('cooling_energy', 0)
    lighting_energy = data.get('lighting_energy', 0)
    equipment_energy = data.get('equipment_energy', 0)
    
    print(f"Heating Energy: {heating_energy} kWh")
    print(f"Cooling Energy: {cooling_energy} kWh")
    print(f"Lighting Energy: {lighting_energy} kWh")
    print(f"Equipment Energy: {equipment_energy} kWh")
    
    # Check for reasonable energy distribution
    if total_energy > 0:
        if heating_energy < 0 or cooling_energy < 0 or lighting_energy < 0 or equipment_energy < 0:
            issues.append("Negative energy values found")
        
        if heating_energy + cooling_energy + lighting_energy + equipment_energy != total_energy:
            issues.append("Energy breakdown doesn't sum to total")
    
    # Check performance metrics
    peak_demand = data.get('peak_demand', 0)
    performance_rating = data.get('performance_rating', 'Unknown')
    
    print(f"Peak Demand: {peak_demand} kW")
    print(f"Performance Rating: {performance_rating}")
    
    if peak_demand < 0:
        issues.append(f"Negative peak demand: {peak_demand}")
    
    if performance_rating not in ['Excellent', 'Good', 'Average', 'Poor']:
        issues.append(f"Invalid performance rating: {performance_rating}")
    
    # Report results
    if issues:
        print(f"⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ ALL CHECKS PASSED - Results are valid!")
        return True

def run_comprehensive_tests():
    """Run comprehensive test suite"""
    print("🧪 COMPREHENSIVE AUTO-CHUNKING PARSER TEST SUITE")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Small file (should not trigger chunking)
    print("\n🔬 TEST 1: Small File (No Chunking)")
    small_idf = create_test_file(0.1)  # 100KB
    payload = {'content_type': 'idf', 'idf_content': small_idf}
    tests_total += 1
    if test_api_call(payload, "Small File Test"):
        tests_passed += 1
    
    # Test 2: Medium file (should trigger chunking)
    print("\n🔬 TEST 2: Medium File (Auto-Chunking)")
    medium_idf = create_test_file(1.0)  # 1MB
    payload = {'content_type': 'idf', 'idf_content': medium_idf}
    tests_total += 1
    if test_api_call(payload, "Medium File Test"):
        tests_passed += 1
    
    # Test 3: Large file (definitely chunking)
    print("\n🔬 TEST 3: Large File (Auto-Chunking)")
    large_idf = create_test_file(2.0)  # 2MB
    payload = {'content_type': 'idf', 'idf_content': large_idf}
    tests_total += 1
    if test_api_call(payload, "Large File Test"):
        tests_passed += 1
    
    # Test 4: Very large file (stress test)
    print("\n🔬 TEST 4: Very Large File (Stress Test)")
    very_large_idf = create_test_file(5.0)  # 5MB
    payload = {'content_type': 'idf', 'idf_content': very_large_idf}
    tests_total += 1
    if test_api_call(payload, "Very Large File Test"):
        tests_passed += 1
    
    # Test 5: Combined IDF + Weather
    print("\n🔬 TEST 5: Combined IDF + Weather")
    idf_content = create_test_file(1.0)
    weather_content = "LOCATION,Test Location,40.0,-74.0,-5.0,10.0;\n" * 1000  # Simulate weather file
    payload = {
        'content_type': 'combined',
        'idf_content': idf_content,
        'weather_content': weather_content
    }
    tests_total += 1
    if test_api_call(payload, "Combined Content Test"):
        tests_passed += 1
    
    # Test 6: Malformed content (error handling)
    print("\n🔬 TEST 6: Malformed Content (Error Handling)")
    malformed_content = "This is not a valid IDF file content with random text and no proper structure"
    payload = {'content_type': 'idf', 'idf_content': malformed_content}
    tests_total += 1
    if test_api_call(payload, "Malformed Content Test"):
        tests_passed += 1
    
    # Test 7: Empty content
    print("\n🔬 TEST 7: Empty Content")
    payload = {'content_type': 'idf', 'idf_content': ''}
    tests_total += 1
    if test_api_call(payload, "Empty Content Test"):
        tests_passed += 1
    
    # Test 8: Retail building (different building type)
    print("\n🔬 TEST 8: Retail Building")
    retail_idf = 'Building,Retail Store,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\n'
    retail_idf += 'Site:Location,Retail Location,40.0,-74.0,-5.0,10.0;\n'
    retail_idf += 'Zone,SalesFloor,0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\n'
    retail_idf += 'ZoneArea,SalesFloor,2000.0;\n'
    retail_idf += create_test_file(1.0)[100:]  # Add more content
    payload = {'content_type': 'idf', 'idf_content': retail_idf}
    tests_total += 1
    if test_api_call(payload, "Retail Building Test"):
        tests_passed += 1
    
    # Final Results
    print("\n" + "=" * 60)
    print(f"🏆 COMPREHENSIVE TEST RESULTS")
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print(f"Success Rate: {(tests_passed/tests_total)*100:.1f}%")
    
    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED! Auto-chunking parser is robust and reliable!")
    else:
        print(f"⚠️  {tests_total - tests_passed} tests failed. Check issues above.")
    
    return tests_passed == tests_total

if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
