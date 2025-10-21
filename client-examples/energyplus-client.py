"""
EnergyPlus MCP Client Library
Easy integration with the EnergyPlus MCP HTTP wrapper
"""

import os
import requests
from typing import Dict, Any, Optional


class EnergyPlusClient:
    """Client for interacting with EnergyPlus MCP HTTP wrapper"""
    
    def __init__(self, mcp_server_url: str = None):
        """
        Initialize the EnergyPlus client
        
        Args:
            mcp_server_url: URL of the MCP server (defaults to environment variable)
        """
        self.base_url = mcp_server_url or os.getenv('MCP_SERVER_URL', 'https://your-app-name.railway.app')
        if not self.base_url.startswith('http'):
            self.base_url = f'https://{self.base_url}'
    
    def call_tool(self, tool: str, args: Dict[str, Any] = None) -> str:
        """
        Call any EnergyPlus MCP tool
        
        Args:
            tool: Tool name (e.g., 'load_idf_model', 'run_energyplus_simulation')
            args: Tool arguments
            
        Returns:
            Tool result as string
            
        Raises:
            Exception: If the API call fails
        """
        if args is None:
            args = {}
            
        try:
            response = requests.post(
                f"{self.base_url}/rpc",
                json={"tool": tool, "arguments": args},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('result', 'No result returned')
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"EnergyPlus MCP Error: {str(e)}")
    
    def get_status(self) -> str:
        """Get server status"""
        return self.call_tool('get_server_status')
    
    def list_files(self) -> str:
        """List available files"""
        return self.call_tool('list_available_files')
    
    def load_model(self, idf_path: str) -> str:
        """
        Load an IDF model
        
        Args:
            idf_path: Path to IDF file
        """
        return self.call_tool('load_idf_model', {'idf_path': idf_path})
    
    def get_model_summary(self, idf_path: str) -> str:
        """
        Get model summary
        
        Args:
            idf_path: Path to IDF file
        """
        return self.call_tool('get_model_summary', {'idf_path': idf_path})
    
    def list_zones(self, idf_path: str) -> str:
        """
        List zones in a model
        
        Args:
            idf_path: Path to IDF file
        """
        return self.call_tool('list_zones', {'idf_path': idf_path})
    
    def run_simulation(self, idf_path: str, weather_file: str = None, annual: bool = True) -> str:
        """
        Run EnergyPlus simulation
        
        Args:
            idf_path: Path to IDF file
            weather_file: Path to weather file (optional)
            annual: Run annual simulation (default: True)
        """
        args = {'idf_path': idf_path, 'annual': annual}
        if weather_file:
            args['weather_file'] = weather_file
        return self.call_tool('run_energyplus_simulation', args)
    
    def create_plot(self, output_directory: str, file_type: str = 'auto') -> str:
        """
        Create interactive plot
        
        Args:
            output_directory: Output directory path
            file_type: Type of file to plot (default: 'auto')
        """
        return self.call_tool('create_interactive_plot', {
            'output_directory': output_directory,
            'file_type': file_type
        })
    
    def validate_model(self, idf_path: str) -> str:
        """
        Validate IDF file
        
        Args:
            idf_path: Path to IDF file
        """
        return self.call_tool('validate_idf', {'idf_path': idf_path})
    
    def discover_hvac_loops(self, idf_path: str) -> str:
        """
        Discover HVAC loops
        
        Args:
            idf_path: Path to IDF file
        """
        return self.call_tool('discover_hvac_loops', {'idf_path': idf_path})


def example():
    """Example usage of the EnergyPlus client"""
    
    # Initialize client
    client = EnergyPlusClient()
    
    try:
        # Check server status
        print("Server Status:", client.get_status())
        
        # List available files
        print("Available Files:", client.list_files())
        
        # Load a model
        model_info = client.load_model('sample_files/1ZoneUncontrolled.idf')
        print("Model Loaded:", model_info)
        
        # Get zones
        zones = client.list_zones('sample_files/1ZoneUncontrolled.idf')
        print("Zones:", zones)
        
        # Run simulation
        sim_result = client.run_simulation(
            'sample_files/1ZoneUncontrolled.idf',
            'USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
        )
        print("Simulation Result:", sim_result)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    example()
