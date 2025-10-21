#!/usr/bin/env python3
import socket
import threading
import time
import os

def handle_request(conn, addr):
    try:
        request = conn.recv(1024).decode()
        if not request:
            return
        
        # Simple routing
        if '/healthz' in request or '/health' in request:
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
        elif 'GET / HTTP' in request:
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"status":"running","service":"EnergyPlus MCP"}'
        else:
            response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found'
        
        conn.send(response.encode())
    except Exception as e:
        print(f"Error handling request: {e}")
    finally:
        conn.close()

def main():
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting ultra-simple server on port {port}")
    print(f"MCP_SERVER_URL=http://0.0.0.0:{port}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    
    print(f"Server listening on 0.0.0.0:{port}")
    
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
