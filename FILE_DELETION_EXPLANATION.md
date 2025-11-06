# File Deletion Explanation

## 🔍 How Files Are Deleted

The EnergyPlus API uses Python's `tempfile.TemporaryDirectory()` context manager, which **automatically deletes** all files when the context exits.

### Code Location

```python
# Line 336 in energyplus-robust-api.py
with tempfile.TemporaryDirectory() as temp_dir:
    # Write IDF file
    idf_path = os.path.join(temp_dir, 'input.idf')
    # Write weather file
    weather_path = os.path.join(temp_dir, 'weather.epw')
    # Create output directory
    output_dir = os.path.join(temp_dir, 'output')
    # ... run EnergyPlus simulation ...
    # ... parse output files ...
    return self.parse_energyplus_output(output_dir, ...)
# ← When this 'with' block exits, Python automatically deletes
#   the entire temp_dir and ALL its contents
```

---

## 📁 Files That Are Deleted

### 1. Input Files (in `temp_dir/`)
- `input.idf` - The IDF file created from request content
- `weather.epw` - The weather file created from request content

### 2. All EnergyPlus Output Files (in `temp_dir/output/`)

Based on our test, these **19 files** are generated and then deleted:

| File | Size | Description |
|------|------|-------------|
| `eplusout.audit` | 1,525 bytes | Audit trail |
| `eplusout.bnd` | 6,287 bytes | Boundary conditions |
| `eplusout.dxf` | 5,428 bytes | DXF geometry file |
| `eplusout.eio` | 16,304 bytes | EnergyPlus input/output |
| `eplusout.end` | 97 bytes | End marker |
| `eplusout.err` | 1,973 bytes | **Errors and warnings log** |
| `eplusout.eso` | 2,393,466 bytes | EnergyPlus standard output |
| `eplusout.mdd` | 3,793 bytes | Meter data dictionary |
| `eplusout.mtd` | 7,395 bytes | Meter data |
| `eplusout.mtr` | 551,961 bytes | Meter data (time series) |
| `eplusout.rdd` | 28,768 bytes | Report data dictionary |
| `eplusout.shd` | 1,523 bytes | Shading data |
| `eplusout.sql` | 3,379,200 bytes | **SQLite database** (main data source) |
| `eplustbl.csv` | 78,311 bytes | **Summary tables (CSV)** |
| `eplustbl.htm` | 330,085 bytes | **HTML summary report** |
| `eplustbl.tab` | 78,308 bytes | Tabular output |
| `eplustbl.txt` | 156,420 bytes | Text summary |
| `eplustbl.xml` | 223,790 bytes | XML summary |
| `sqlite.err` | 73 bytes | SQLite errors |

**Total Size**: ~7.2 MB of files deleted per simulation

---

## ⏱️ When Deletion Happens

The deletion happens **automatically** when the `with tempfile.TemporaryDirectory()` block exits:

```
1. Request received
   ↓
2. Create temp directory (tempfile.TemporaryDirectory())
   ↓
3. Write input.idf and weather.epw to temp directory
   ↓
4. Run EnergyPlus → generates 19 output files in temp_dir/output/
   ↓
5. Parse output files (read data from SQLite, HTML, CSV, etc.)
   ↓
6. Extract energy data into JSON structure
   ↓
7. Return JSON response
   ↓
8. 'with' block exits → Python automatically deletes entire temp_dir
   ↓
9. All files gone (input.idf, weather.epw, and all 19 output files)
```

**Timing**: Deletion happens **immediately after** the function returns, before the HTTP response is sent.

---

## 🔒 Why Files Are Deleted

1. **Security**: Prevents accumulation of sensitive building data
2. **Storage**: Saves disk space (7+ MB per simulation)
3. **Privacy**: No persistent storage of user's building models
4. **Cleanup**: Automatic cleanup prevents disk filling up
5. **Stateless**: API is stateless - each request is independent

---

## 📊 What Data Is Preserved

The **only** data that persists is what's in the JSON response:

✅ **Preserved in JSON**:
- Energy consumption values (kWh)
- Building metrics (area, EUI, peak demand)
- Warnings/errors (text)
- Metadata (version, timestamps)
- File names and sizes (metadata only)

❌ **NOT Preserved**:
- Actual file contents
- Time series data (hourly values)
- Detailed building geometry
- Material properties
- Full error logs
- SQLite database
- HTML reports
- CSV data files

---

## 🔄 If You Need the Files

If you need access to the actual EnergyPlus output files, you have these options:

### Option 1: Run EnergyPlus Locally
```bash
energyplus -w weather.epw -d output_dir input.idf
# Files will be saved in output_dir/
```

### Option 2: Modify the API (Advanced)
You would need to:
1. Remove the `tempfile.TemporaryDirectory()` context manager
2. Use a persistent directory instead
3. Save files to cloud storage (S3, etc.)
4. Return file URLs in the JSON response
5. Implement cleanup/retention policies

### Option 3: Use the MCP Server
The EnergyPlus MCP Server (`EnergyPlus-MCP/`) can run simulations and keep files if configured to do so.

---

## 📝 Summary

**Files Deleted**:
- ✅ Input IDF file (`input.idf`)
- ✅ Input weather file (`weather.epw`)
- ✅ All 19 EnergyPlus output files (~7.2 MB total)
- ✅ Entire temporary directory

**When**:
- Automatically when the `with tempfile.TemporaryDirectory()` block exits
- Immediately after parsing completes and JSON response is prepared

**Why**:
- Security, storage efficiency, privacy, automatic cleanup

**What's Kept**:
- Only the parsed data in the JSON response
- No actual files are returned to the client

---

**Last Updated**: 2025-01-27

