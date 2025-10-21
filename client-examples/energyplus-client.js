/**
 * EnergyPlus MCP Client Library
 * Easy integration with the EnergyPlus MCP HTTP wrapper
 */

class EnergyPlusClient {
  constructor(mcpServerUrl) {
    this.baseUrl = mcpServerUrl;
  }

  /**
   * Call any EnergyPlus MCP tool
   * @param {string} tool - Tool name (e.g., 'load_idf_model', 'run_energyplus_simulation')
   * @param {object} args - Tool arguments
   * @returns {Promise<object>} Tool result
   */
  async callTool(tool, args = {}) {
    try {
      const response = await fetch(`${this.baseUrl}/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool, arguments: args })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.result;
    } catch (error) {
      throw new Error(`EnergyPlus MCP Error: ${error.message}`);
    }
  }

  /**
   * Get server status
   */
  async getStatus() {
    return this.callTool('get_server_status');
  }

  /**
   * List available files
   */
  async listFiles() {
    return this.callTool('list_available_files');
  }

  /**
   * Load an IDF model
   * @param {string} idfPath - Path to IDF file
   */
  async loadModel(idfPath) {
    return this.callTool('load_idf_model', { idf_path: idfPath });
  }

  /**
   * Get model summary
   * @param {string} idfPath - Path to IDF file
   */
  async getModelSummary(idfPath) {
    return this.callTool('get_model_summary', { idf_path: idfPath });
  }

  /**
   * List zones in a model
   * @param {string} idfPath - Path to IDF file
   */
  async listZones(idfPath) {
    return this.callTool('list_zones', { idf_path: idfPath });
  }

  /**
   * Run EnergyPlus simulation
   * @param {string} idfPath - Path to IDF file
   * @param {string} weatherFile - Path to weather file (optional)
   * @param {boolean} annual - Run annual simulation (default: true)
   */
  async runSimulation(idfPath, weatherFile = null, annual = true) {
    const args = { idf_path: idfPath, annual };
    if (weatherFile) args.weather_file = weatherFile;
    return this.callTool('run_energyplus_simulation', args);
  }

  /**
   * Create interactive plot
   * @param {string} outputDirectory - Output directory path
   * @param {string} fileType - Type of file to plot (default: 'auto')
   */
  async createPlot(outputDirectory, fileType = 'auto') {
    return this.callTool('create_interactive_plot', { 
      output_directory: outputDirectory, 
      file_type: fileType 
    });
  }

  /**
   * Validate IDF file
   * @param {string} idfPath - Path to IDF file
   */
  async validateModel(idfPath) {
    return this.callTool('validate_idf', { idf_path: idfPath });
  }

  /**
   * Discover HVAC loops
   * @param {string} idfPath - Path to IDF file
   */
  async discoverHVACLoops(idfPath) {
    return this.callTool('discover_hvac_loops', { idf_path: idfPath });
  }
}

// Usage examples
async function example() {
  // Initialize client
  const mcpUrl = process.env.MCP_SERVER_URL || 'https://your-app-name.railway.app';
  const client = new EnergyPlusClient(mcpUrl);

  try {
    // Check server status
    console.log('Server Status:', await client.getStatus());

    // List available files
    console.log('Available Files:', await client.listFiles());

    // Load a model
    const modelInfo = await client.loadModel('sample_files/1ZoneUncontrolled.idf');
    console.log('Model Loaded:', modelInfo);

    // Get zones
    const zones = await client.listZones('sample_files/1ZoneUncontrolled.idf');
    console.log('Zones:', zones);

    // Run simulation
    const simResult = await client.runSimulation(
      'sample_files/1ZoneUncontrolled.idf',
      'USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
    );
    console.log('Simulation Result:', simResult);

  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EnergyPlusClient;
}

// Run example if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
  example();
}
