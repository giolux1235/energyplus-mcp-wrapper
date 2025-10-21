# EnergyPlus MCP HTTP Wrapper - Deployment Guide

This guide shows how to deploy the EnergyPlus MCP HTTP wrapper to cloud platforms.

## 🚀 Railway Deployment (Recommended - Easiest)

### Prerequisites
- GitHub account
- Railway account (free tier available)

### Steps

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: EnergyPlus MCP HTTP wrapper"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/energyplus-mcp-wrapper.git
   git push -u origin main
   ```

2. **Deploy on Railway:**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the configuration and deploy

3. **Environment Variables (if needed):**
   - In Railway dashboard, go to your project
   - Click "Variables" tab
   - Add any required environment variables

4. **Access your app:**
   - Railway will provide a URL like `https://your-app-name.railway.app`
   - Test: `https://your-app-name.railway.app/status`

## 🛩️ Fly.io Deployment

### Prerequisites
- Fly.io account
- Fly CLI installed: `curl -L https://fly.io/install.sh | sh`

### Steps

1. **Login to Fly.io:**
   ```bash
   fly auth login
   ```

2. **Deploy:**
   ```bash
   fly launch
   # Follow prompts, use default settings
   fly deploy
   ```

3. **Access your app:**
   ```bash
   fly open
   ```

## 🐳 Docker Deployment (Any Platform)

### Build and run locally:
```bash
docker build -t energyplus-mcp .
docker run -p 8080:8080 energyplus-mcp
```

### Deploy to any Docker platform:
- Docker Hub
- AWS ECS
- Google Cloud Run
- Azure Container Instances

## 📱 Building a Web App

Once deployed, you can build a web app that uses the API:

### Example Frontend (HTML/JavaScript):
```html
<!DOCTYPE html>
<html>
<head>
    <title>EnergyPlus Building Simulator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .tool { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: #e9ecef; padding: 10px; margin: 10px 0; border-radius: 5px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ EnergyPlus Building Simulator</h1>
        
        <div class="tool">
            <h3>📊 Server Status</h3>
            <button onclick="getStatus()">Check Status</button>
            <div id="statusResult" class="result"></div>
        </div>
        
        <div class="tool">
            <h3>📁 Available Files</h3>
            <button onclick="listFiles()">List Files</button>
            <div id="filesResult" class="result"></div>
        </div>
        
        <div class="tool">
            <h3>🏢 Load Building Model</h3>
            <input type="text" id="modelPath" placeholder="sample_files/1ZoneUncontrolled.idf" style="width: 300px;">
            <button onclick="loadModel()">Load Model</button>
            <div id="modelResult" class="result"></div>
        </div>
    </div>

    <script>
        const API_URL = 'https://your-app-name.railway.app'; // Replace with your deployed URL
        
        async function callAPI(tool, args = {}) {
            try {
                const response = await fetch(`${API_URL}/rpc`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tool, arguments: args })
                });
                const data = await response.json();
                return data.result;
            } catch (error) {
                return `Error: ${error.message}`;
            }
        }
        
        async function getStatus() {
            const result = await callAPI('get_server_status');
            document.getElementById('statusResult').textContent = result;
        }
        
        async function listFiles() {
            const result = await callAPI('list_available_files');
            document.getElementById('filesResult').textContent = result;
        }
        
        async function loadModel() {
            const modelPath = document.getElementById('modelPath').value;
            const result = await callAPI('load_idf_model', { idf_path: modelPath });
            document.getElementById('modelResult').textContent = result;
        }
    </script>
</body>
</html>
```

### Example React App:
```jsx
import React, { useState } from 'react';

function EnergyPlusApp() {
  const [result, setResult] = useState('');
  
  const callAPI = async (tool, args = {}) => {
    const response = await fetch('/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, arguments: args })
    });
    const data = await response.json();
    return data.result;
  };
  
  const handleGetStatus = async () => {
    const result = await callAPI('get_server_status');
    setResult(result);
  };
  
  return (
    <div>
      <h1>EnergyPlus Building Simulator</h1>
      <button onClick={handleGetStatus}>Get Status</button>
      <pre>{result}</pre>
    </div>
  );
}

export default EnergyPlusApp;
```

## 🔧 Environment Variables

You may need to set these environment variables:

```bash
# For Railway/Fly.io
PORT=8080
WORKSPACE_ROOT=/app/EnergyPlus-MCP/energyplus-mcp-server

# For EnergyPlus (if not in container)
EPLUS_IDD_PATH=/usr/local/bin/Energy+.idd
EPLUS_EXECUTABLE_PATH=/usr/local/bin/energyplus
```

## 📋 API Endpoints

Your deployed app will have these endpoints:

- `GET /` - API documentation
- `GET /status` - Server status
- `GET /tools` - List available tools
- `POST /rpc` - Execute any EnergyPlus tool

## 🎯 Next Steps

1. **Deploy to Railway** (easiest option)
2. **Test the API** with curl or Postman
3. **Build a frontend** using the API
4. **Add authentication** if needed
5. **Scale up** based on usage

## 🆘 Troubleshooting

- **EnergyPlus not found**: Make sure EnergyPlus is installed in the container
- **Port issues**: Ensure PORT environment variable is set
- **Memory issues**: Increase memory allocation for large simulations
- **Timeout issues**: Increase timeout settings for long-running simulations
