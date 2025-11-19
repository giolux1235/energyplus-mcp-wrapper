# File Download Feature

## ✅ New Feature: Download EnergyPlus Output Files

The API now **saves all EnergyPlus output files** and provides download URLs before deleting them. Engineers can download the files for detailed analysis.

---

## 📥 How It Works

### 1. Files Are Saved
When a simulation completes, all output files are:
- ✅ Saved to persistent storage (not deleted immediately)
- ✅ Organized by simulation ID (UUID)
- ✅ Available for download via HTTP

### 2. Download URLs in Response
The JSON response now includes:
```json
{
  "simulation_status": "success",
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "output_files_download": {
    "eplusout.sql": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.sql",
      "size_bytes": 3379200,
      "size_mb": 3.22
    },
    "eplusout.html": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.html",
      "size_bytes": 330085,
      "size_mb": 0.31
    },
    "eplusout.csv": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.csv",
      "size_bytes": 78311,
      "size_mb": 0.07
    }
    // ... all 19 files
  },
  "files_available_until": "2025-01-28T10:30:45.123456",
  "download_base_url": "https://web-production-1d1be.up.railway.app"
}
```

### 3. Download Files
Use the URLs to download files:
```bash
# Full URL
https://web-production-1d1be.up.railway.app/download/{simulation_id}/eplusout.sql

# Or construct from response
${download_base_url}${output_files_download['eplusout.sql'].url}
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_STORAGE_DIR` | `/tmp/energyplus_outputs` | Directory to store output files |
| `FILE_RETENTION_HOURS` | `24` | Hours to keep files before deletion |
| `BASE_URL` | (auto-detected) | Base URL for download links |

### Example Configuration
```bash
export OUTPUT_STORAGE_DIR="/app/storage/outputs"
export FILE_RETENTION_HOURS=48
export BASE_URL="https://your-api-domain.com"
```

---

## 📋 Available Files

All 19 EnergyPlus output files are available for download:

| File | Description | Typical Size |
|------|-------------|--------------|
| `eplusout.sql` | SQLite database (main data) | 3-5 MB |
| `eplusout.html` | HTML summary report | 300-500 KB |
| `eplusout.csv` | CSV summary tables | 50-100 KB |
| `eplusout.err` | Errors and warnings | 1-5 KB |
| `eplusout.eso` | EnergyPlus standard output | 1-3 MB |
| `eplusout.mtr` | Meter data (time series) | 500 KB - 2 MB |
| `eplusout.mdd` | Meter data dictionary | 3-5 KB |
| `eplusout.rdd` | Report data dictionary | 20-30 KB |
| `eplusout.bnd` | Boundary conditions | 5-10 KB |
| `eplusout.dxf` | DXF geometry | 5-10 KB |
| `eplusout.eio` | EnergyPlus I/O | 15-20 KB |
| `eplusout.shd` | Shading data | 1-2 KB |
| `eplusout.audit` | Audit trail | 1-2 KB |
| `eplusout.end` | End marker | < 100 bytes |
| `eplustbl.tab` | Tabular output | 50-100 KB |
| `eplustbl.txt` | Text summary | 100-200 KB |
| `eplustbl.xml` | XML summary | 200-300 KB |
| `sqlite.err` | SQLite errors | < 100 bytes |

---

## 🔄 File Lifecycle

```
1. Simulation runs → Files generated in temp directory
   ↓
2. Files copied to persistent storage (by simulation_id)
   ↓
3. Files parsed → JSON response with download URLs
   ↓
4. Temp directory deleted (original files gone)
   ↓
5. Files available for download (24 hours default)
   ↓
6. Cleanup thread removes old files automatically
```

---

## 🧹 Automatic Cleanup

- **Cleanup runs**: Every hour (background thread)
- **Retention period**: 24 hours (configurable)
- **What gets deleted**: Files older than retention period
- **Logging**: Cleanup actions are logged

---

## 📥 Download Examples

### Using curl
```bash
# Get simulation response
RESPONSE=$(curl -X POST https://api-url/simulate \
  -H "Content-Type: application/json" \
  -d '{"idf_content": "...", "weather_content": "..."}')

# Extract simulation_id and download URL
SIM_ID=$(echo $RESPONSE | jq -r '.simulation_id')
BASE_URL=$(echo $RESPONSE | jq -r '.download_base_url')

# Download SQLite database
curl -O "${BASE_URL}/download/${SIM_ID}/eplusout.sql"

# Download HTML report
curl -O "${BASE_URL}/download/${SIM_ID}/eplusout.html"
```

### Using JavaScript/TypeScript
```typescript
const response = await fetch('https://api-url/simulate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ idf_content, weather_content })
});

const data = await response.json();

// Download SQLite file
if (data.output_files_download?.['eplusout.sql']) {
  const fileUrl = `${data.download_base_url}${data.output_files_download['eplusout.sql'].url}`;
  window.open(fileUrl, '_blank');
}

// Or download all files
Object.entries(data.output_files_download || {}).forEach(([filename, fileInfo]) => {
  const fileUrl = `${data.download_base_url}${fileInfo.url}`;
  console.log(`Download ${filename}: ${fileUrl}`);
});
```

### Using Python
```python
import requests
import json

# Run simulation
response = requests.post('https://api-url/simulate', json={
    'idf_content': idf_content,
    'weather_content': weather_content
})

data = response.json()

# Download SQLite file
if 'output_files_download' in data and 'eplusout.sql' in data['output_files_download']:
    sim_id = data['simulation_id']
    base_url = data['download_base_url']
    file_url = f"{base_url}/download/{sim_id}/eplusout.sql"
    
    file_response = requests.get(file_url)
    with open('eplusout.sql', 'wb') as f:
        f.write(file_response.content)
    print(f"Downloaded: eplusout.sql")
```

---

## 🔒 Security Features

- ✅ **Directory traversal protection**: Prevents `../` attacks
- ✅ **File existence checks**: Validates files exist before serving
- ✅ **Retention period enforcement**: Files expire after retention period
- ✅ **UUID-based paths**: Simulation IDs are UUIDs (hard to guess)

---

## 📊 Storage Considerations

### Storage Size
- **Per simulation**: ~7-10 MB (all files)
- **100 simulations**: ~700 MB - 1 GB
- **1000 simulations**: ~7-10 GB

### Recommendations
1. **Set retention period** based on your needs (24-48 hours is typical)
2. **Monitor storage** usage if running many simulations
3. **Use cloud storage** (S3, etc.) for production (modify `save_output_files` method)
4. **Cleanup is automatic** but you can manually clean if needed

---

## 🚀 Migration Notes

### Existing Code
**No changes required!** The API is backward compatible:
- ✅ Existing JSON response format unchanged
- ✅ New fields are **additions** (not breaking changes)
- ✅ Files are optional - if download fails, JSON still works

### New Fields in Response
- `simulation_id` - Unique ID for this simulation
- `output_files_download` - Object with file URLs
- `files_available_until` - Expiration timestamp
- `download_base_url` - Base URL for constructing full URLs

---

## 🐛 Troubleshooting

### Files Not Available
- **Check retention period**: Files expire after `FILE_RETENTION_HOURS`
- **Check storage directory**: Ensure `OUTPUT_STORAGE_DIR` is writable
- **Check logs**: Look for file save errors

### Download Fails
- **Check URL format**: Must be `/download/{simulation_id}/{filename}`
- **Check file exists**: Verify file is in storage directory
- **Check permissions**: Ensure storage directory is readable

### Storage Full
- **Reduce retention period**: Lower `FILE_RETENTION_HOURS`
- **Manual cleanup**: Delete old directories in `OUTPUT_STORAGE_DIR`
- **Use cloud storage**: Modify code to use S3/cloud storage

---

## 📝 Example Full Response

```json
{
  "version": "33.0.0",
  "simulation_status": "success",
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_energy_consumption": 38104.25,
  "energy_intensity": 164.06,
  "building_area": 232.26,
  "output_files_download": {
    "eplusout.sql": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.sql",
      "size_bytes": 3379200,
      "size_mb": 3.22
    },
    "eplusout.html": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.html",
      "size_bytes": 330085,
      "size_mb": 0.31
    }
    // ... 17 more files
  },
  "files_available_until": "2025-01-28T10:30:45.123456",
  "download_base_url": "https://web-production-1d1be.up.railway.app"
}
```

---

**Last Updated**: 2025-01-27

