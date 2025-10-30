"""
Configuration loader for the pipeline
Supports YAML and JSON configuration files
"""
import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Loads and manages configuration from YAML or JSON files"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
                        If None, will look for config.yaml, config.yml, or config.json
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        if config_path:
            self.load(config_path)
        else:
            # Try to find a config file automatically
            self._auto_load()
    
    def _auto_load(self):
        """Automatically find and load a config file"""
        # Check common config file locations
        possible_paths = [
            'config/config.yaml',
            'config/config.yml',
            'config/config.json',
            'config.yaml',
            'config.yml',
            'config.json',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"📁 Found configuration file: {path}")
                self.load(path)
                return
        
        print("⚠️ No configuration file found, using defaults")
    
    def load(self, config_path: str):
        """Load configuration from file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        self.config_path = config_path
        
        # Determine file type from extension
        ext = Path(config_path).suffix.lower()
        
        with open(config_path, 'r') as f:
            if ext in ['.yaml', '.yml']:
                self.config = yaml.safe_load(f)
            elif ext == '.json':
                self.config = json.load(f)
            else:
                raise ValueError(f"Unsupported config file type: {ext}. Use .yaml, .yml, or .json")
        
        print(f"✓ Loaded configuration from {config_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_converter_config(self, converter_type: str = 'image_to_latex') -> Dict[str, Any]:
        """Get converter-specific configuration"""
        return self.get(f'converters.{converter_type}', {})
    
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration"""
        return self.get('pipeline', {})
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access"""
        return self.get(key)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists"""
        return self.get(key) is not None
