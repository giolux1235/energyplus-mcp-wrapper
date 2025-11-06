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

## 🔗 Using as a Backend Service

This MCP server is designed to be used as a **backend service** for other projects. After deployment, you'll get a public URL that you can use in your other applications.

### Getting the MCP Server URL

After deployment, run:
```bash
./get-mcp-url.sh
```

This will output the `MCP_SERVER_URL` that you can use in your other projects.

### Using in Your Other Project

**Node.js/JavaScript:**
```javascript
const API_URL = process.env.ENERGYPLUS_API_URL || 'https://your-app-name.railway.app';

// Run EnergyPlus simulation with IDF and weather files
async function runSimulation(idfContent, weatherContent) {
  const response = await fetch(`${API_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idf_content: idfContent,      // IDF file content as string
      weather_content: weatherContent // EPW weather file content as string
    })
  });
  return response.json();
}

// Example usage
const idfContent = await fetch('path/to/building.idf').then(r => r.text());
const weatherContent = await fetch('path/to/weather.epw').then(r => r.text());

const result = await runSimulation(idfContent, weatherContent);
if (result.simulation_status === 'success') {
  console.log(`Total Energy: ${result.total_energy_consumption} kWh`);
  console.log(`EUI: ${result.energy_intensity} kWh/m²`);
}
```

**Python:**
```python
import os
import requests

API_URL = os.getenv('ENERGYPLUS_API_URL', 'https://your-app-name.railway.app')

def run_simulation(idf_content, weather_content):
    """Run EnergyPlus simulation with IDF and weather files"""
    response = requests.post(
        f"{API_URL}/simulate",
        json={
            'idf_content': idf_content,      # IDF file content as string
            'weather_content': weather_content # EPW weather file content as string
        },
        timeout=600  # 10 minutes timeout for long simulations
    )
    return response.json()

# Example usage
with open('building.idf', 'r') as f:
    idf_content = f.read()

with open('weather.epw', 'r') as f:
    weather_content = f.read()

result = run_simulation(idf_content, weather_content)
if result['simulation_status'] == 'success':
    print(f"Total Energy: {result['total_energy_consumption']} kWh")
    print(f"EUI: {result['energy_intensity']} kWh/m²")
```

**Environment Variables:**
```bash
# Add to your other project's .env
ENERGYPLUS_API_URL=https://your-app-name.railway.app
```

**Important Notes:**
- **Weather files (`.epw`) are required** for annual simulations. The API accepts weather file content as a string in the `weather_content` field.
- Weather files can be:
  - Downloaded from NREL's weather database (https://energyplus.net/weather)
  - Generated from climate data
  - Provided by users
- The API will automatically use the weather file location data if it differs from the IDF's location settings (this is normal and expected).
- Both `idf_content` and `weather_content` must be the **full file contents as strings** (not file paths).

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
            <h3>⚡ Run Simulation</h3>
            <p>Upload IDF and weather files to run a simulation:</p>
            <input type="file" id="idfFile" accept=".idf" style="margin: 10px 0;">
            <label>IDF File (.idf)</label><br>
            <input type="file" id="weatherFile" accept=".epw" style="margin: 10px 0;">
            <label>Weather File (.epw)</label><br>
            <button onclick="runSimulation()">Run Simulation</button>
            <div id="simulationResult" class="result"></div>
        </div>
    </div>

    <script>
        const API_URL = 'https://your-app-name.railway.app'; // Replace with your deployed URL
        
        // Check server health
        async function getStatus() {
            try {
                const response = await fetch(`${API_URL}/health`);
                const data = await response.json();
                document.getElementById('statusResult').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('statusResult').textContent = `Error: ${error.message}`;
            }
        }
        
        // Run simulation with IDF and weather files
        async function runSimulation() {
            const idfFile = document.getElementById('idfFile').files[0];
            const weatherFile = document.getElementById('weatherFile').files[0];
            
            if (!idfFile || !weatherFile) {
                alert('Please select both IDF and weather files');
                return;
            }
            
            try {
                const idfContent = await idfFile.text();
                const weatherContent = await weatherFile.text();
                
                const response = await fetch(`${API_URL}/simulate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        idf_content: idfContent,
                        weather_content: weatherContent
                    })
                });
                
                const data = await response.json();
                document.getElementById('simulationResult').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('simulationResult').textContent = `Error: ${error.message}`;
            }
        }
    </script>
</body>
</html>
```

### Example React App:
```jsx
import React, { useState } from 'react';

function EnergyPlusApp() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const API_URL = process.env.REACT_APP_ENERGYPLUS_API_URL || 'https://your-app-name.railway.app';
  
  const runSimulation = async (idfFile, weatherFile) => {
    setLoading(true);
    try {
      const idfContent = await idfFile.text();
      const weatherContent = await weatherFile.text();
      
      const response = await fetch(`${API_URL}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idf_content: idfContent,
          weather_content: weatherContent
        })
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };
  
  const handleFileUpload = async (e) => {
    e.preventDefault();
    const idfFile = e.target.idfFile.files[0];
    const weatherFile = e.target.weatherFile.files[0];
    
    if (idfFile && weatherFile) {
      await runSimulation(idfFile, weatherFile);
    }
  };
  
  return (
    <div>
      <h1>EnergyPlus Building Simulator</h1>
      <form onSubmit={handleFileUpload}>
        <input type="file" name="idfFile" accept=".idf" required />
        <label>IDF File</label>
        <input type="file" name="weatherFile" accept=".epw" required />
        <label>Weather File (.epw)</label>
        <button type="submit" disabled={loading}>
          {loading ? 'Running...' : 'Run Simulation'}
        </button>
      </form>
      {result && (
        <pre>{JSON.stringify(result, null, 2)}</pre>
      )}
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

- `GET /` - API information
- `GET /health` - Server health check (returns EnergyPlus availability status)
- `POST /simulate` - Run EnergyPlus simulation with IDF and weather files
  - **Request Body:**
    ```json
    {
      "idf_content": "string",      // IDF file content as string
      "weather_content": "string"   // EPW weather file content as string (required for annual simulations)
    }
    ```
  - **Response:** JSON with simulation results, energy data, and download URLs for output files
- `GET /download/{simulation_id}/{filename}` - Download simulation output files

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
