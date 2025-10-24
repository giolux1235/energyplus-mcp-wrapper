#!/usr/bin/env python3
import socket
import threading
import time
import os
import json
import re

def handle_request(conn, addr):
    try:
        request = conn.recv(8192).decode()
        print(f"=== REQUEST FROM {addr} ===")
        print(f"Request: {request[:500]}...")
        print("=" * 50)
        
        if not request:
            return
        
        # Parse the request
        lines = request.split('\n')
        if not lines:
            return
            
        request_line = lines[0]
        method, path, version = request_line.split(' ', 2)
        
        print(f"Method: {method}, Path: {path}")
        
        # Check for POST to /simulate
        if path == '/simulate' and method == 'POST':
            print("Processing POST to /simulate")
            
            # Check content type
            content_type = None
            for line in lines:
                if line.lower().startswith('content-type:'):
                    content_type = line.split(':', 1)[1].strip()
                    break
            
            print(f"Content-Type: {content_type}")
            
            # Find body
            body_start = request.find('\r\n\r\n')
            if body_start != -1:
                body = request[body_start + 4:]
                print(f"Body length: {len(body)}")
                print(f"Body preview: {body[:200]}...")
                
                if 'multipart/form-data' in content_type:
                    print("Processing multipart data")
                    # Extract boundary
                    boundary_match = re.search(r'boundary=([^;]+)', content_type)
                    if boundary_match:
                        boundary = boundary_match.group(1)
                        print(f"Boundary: {boundary}")
                        
                        # Parse multipart
                        parts = body.split(f'--{boundary}')
                        print(f"Found {len(parts)} parts")
                        
                        for i, part in enumerate(parts):
                            print(f"Part {i}: {part[:100]}...")
                            if 'Content-Disposition: form-data' in part:
                                filename_match = re.search(r'filename="([^"]+)"', part)
                                if filename_match:
                                    filename = filename_match.group(1)
                                    print(f"Found file: {filename}")
                                    
                                    # Extract content
                                    content_start = part.find('\r\n\r\n')
                                    if content_start != -1:
                                        file_content = part[content_start + 4:]
                                        print(f"File content length: {len(file_content)}")
                                        print(f"File content preview: {file_content[:200]}...")
                                        
                                        # Simulate different results based on content
                                        if 'Office' in file_content:
                                            result = {
                                                "building_type": "office",
                                                "total_energy_consumption": 50000000.0,
                                                "heating_energy": 10000000.0,
                                                "cooling_energy": 40000000.0,
                                                "data_source": "idf_file",
                                                "file_processed": filename
                                            }
                                        elif 'Residential' in file_content:
                                            result = {
                                                "building_type": "residential", 
                                                "total_energy_consumption": 15000000.0,
                                                "heating_energy": 5000000.0,
                                                "cooling_energy": 10000000.0,
                                                "data_source": "idf_file",
                                                "file_processed": filename
                                            }
                                        else:
                                            result = {
                                                "building_type": "unknown",
                                                "total_energy_consumption": 30000000.0,
                                                "heating_energy": 8000000.0,
                                                "cooling_energy": 22000000.0,
                                                "data_source": "idf_file",
                                                "file_processed": filename
                                            }
                                        
                                        response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
                                        conn.send(response.encode())
                                        conn.close()
                                        return
                
                elif 'application/json' in content_type:
                    print("Processing JSON data")
                    try:
                        data = json.loads(body)
                        print(f"JSON data: {data}")
                        
                        if 'idf_content' in data:
                            content = data['idf_content']
                            print(f"IDF content length: {len(content)}")
                            
                            # Simulate different results
                            if 'Office' in content:
                                result = {
                                    "building_type": "office",
                                    "total_energy_consumption": 45000000.0,
                                    "heating_energy": 9000000.0,
                                    "cooling_energy": 36000000.0,
                                    "data_source": "idf_content"
                                }
                            else:
                                result = {
                                    "building_type": "other",
                                    "total_energy_consumption": 25000000.0,
                                    "heating_energy": 6000000.0,
                                    "cooling_energy": 19000000.0,
                                    "data_source": "idf_content"
                                }
                            
                            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
                            conn.send(response.encode())
                            conn.close()
                            return
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
            
            # Default response
            result = {
                "building_type": "default",
                "total_energy_consumption": 91992000.0,
                "heating_energy": 11424000.0,
                "cooling_energy": 80568000.0,
                "data_source": "default",
                "debug": "No file processed"
            }
            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
        else:
            # Default response for other endpoints
            result = {"status": "debug server", "endpoint": path}
            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(result)}'
        
        conn.send(response.encode())
    except Exception as e:
        print(f"Error handling request: {e}")
        error_response = f'HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{{"error": "{str(e)}"}}'
        conn.send(error_response.encode())
    finally:
        conn.close()

def main():
    port = int(os.environ.get('PORT', 8081))
    print(f"Starting debug server on port {port}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    
    print(f"Debug server listening on 0.0.0.0:{port}")
    
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
