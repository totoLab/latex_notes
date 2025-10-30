"""
Workspace Manager for organizing multiple document conversions
Allows operating on different documents without specifying paths each time
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class WorkspaceManager:
    """Manages workspaces for organizing multiple document conversion projects"""
    
    def __init__(self, base_dir: str = "workspaces"):
        """
        Initialize workspace manager
        
        Args:
            base_dir: Base directory for all workspaces
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.base_dir / "workspaces.json"
        self.workspaces = self._load_workspaces()
        self.current_workspace = self._load_current_workspace()
    
    def _load_workspaces(self) -> Dict:
        """Load workspace configurations"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_workspaces(self):
        """Save workspace configurations"""
        with open(self.config_file, 'w') as f:
            json.dump(self.workspaces, f, indent=2)
    
    def _load_current_workspace(self) -> Optional[str]:
        """Load the current active workspace"""
        current_file = self.base_dir / ".current"
        if current_file.exists():
            return current_file.read_text().strip()
        return None
    
    def _save_current_workspace(self, workspace_name: Optional[str]):
        """Save the current active workspace"""
        current_file = self.base_dir / ".current"
        if workspace_name:
            current_file.write_text(workspace_name)
        elif current_file.exists():
            current_file.unlink()
    
    def create_workspace(
        self, 
        name: str, 
        pdf_path: str, 
        description: str = "",
        set_as_current: bool = True
    ) -> Dict:
        """
        Create a new workspace
        
        Args:
            name: Workspace name (alphanumeric, dashes, underscores)
            pdf_path: Path to the PDF file for this workspace
            description: Optional description
            set_as_current: Whether to set this as the current workspace
            
        Returns:
            Workspace configuration dict
        """
        # Validate workspace name
        if not name.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Workspace name must contain only alphanumeric characters, dashes, and underscores")
        
        if name in self.workspaces:
            raise ValueError(f"Workspace '{name}' already exists")
        
        # Resolve PDF path
        pdf_path = str(Path(pdf_path).resolve())
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Create workspace directory structure
        workspace_dir = self.base_dir / name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (workspace_dir / "images").mkdir(exist_ok=True)
        (workspace_dir / "latex").mkdir(exist_ok=True)
        
        # Create workspace config
        workspace_config = {
            'name': name,
            'pdf_path': pdf_path,
            'workspace_dir': str(workspace_dir),
            'description': description,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'status': 'created'
        }
        
        self.workspaces[name] = workspace_config
        self._save_workspaces()
        
        if set_as_current:
            self.set_current_workspace(name)
        
        print(f"✅ Created workspace '{name}'")
        print(f"   PDF: {pdf_path}")
        print(f"   Location: {workspace_dir}")
        
        return workspace_config
    
    def set_current_workspace(self, name: str):
        """Set the current active workspace"""
        if name not in self.workspaces:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        self.current_workspace = name
        self._save_current_workspace(name)
        
        # Update last accessed time
        self.workspaces[name]['last_accessed'] = datetime.now().isoformat()
        self._save_workspaces()
        
        print(f"📂 Switched to workspace '{name}'")
    
    def get_current_workspace(self) -> Optional[Dict]:
        """Get the current workspace configuration"""
        if not self.current_workspace:
            return None
        return self.workspaces.get(self.current_workspace)
    
    def get_workspace(self, name: str) -> Optional[Dict]:
        """Get a specific workspace configuration"""
        return self.workspaces.get(name)
    
    def list_workspaces(self) -> List[Dict]:
        """List all workspaces"""
        workspaces_list = []
        for name, config in self.workspaces.items():
            config_copy = config.copy()
            config_copy['is_current'] = (name == self.current_workspace)
            workspaces_list.append(config_copy)
        
        # Sort by last accessed time (most recent first)
        workspaces_list.sort(
            key=lambda x: x.get('last_accessed', ''), 
            reverse=True
        )
        
        return workspaces_list
    
    def delete_workspace(self, name: str, delete_files: bool = False):
        """
        Delete a workspace
        
        Args:
            name: Workspace name
            delete_files: If True, also delete the workspace directory
        """
        if name not in self.workspaces:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        workspace_dir = Path(self.workspaces[name]['workspace_dir'])
        
        # Remove from config
        del self.workspaces[name]
        self._save_workspaces()
        
        # Clear current workspace if it was deleted
        if self.current_workspace == name:
            self.current_workspace = None
            self._save_current_workspace(None)
        
        # Optionally delete files
        if delete_files and workspace_dir.exists():
            import shutil
            shutil.rmtree(workspace_dir)
            print(f"🗑️  Deleted workspace '{name}' and its files")
        else:
            print(f"🗑️  Deleted workspace '{name}' (files preserved)")
    
    def update_workspace_status(self, name: str, status: str):
        """Update workspace status (e.g., 'processing', 'complete', 'error')"""
        if name not in self.workspaces:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        self.workspaces[name]['status'] = status
        self.workspaces[name]['last_accessed'] = datetime.now().isoformat()
        self._save_workspaces()
    
    def get_workspace_paths(self, name: Optional[str] = None) -> Dict[str, str]:
        """
        Get all relevant paths for a workspace
        
        Args:
            name: Workspace name (uses current if None)
            
        Returns:
            Dict with keys: workspace_dir, pdf_path, images_dir, latex_dir, 
                          checkpoint_file, main_doc
        """
        if name is None:
            name = self.current_workspace
        
        if name is None:
            raise ValueError("No workspace specified and no current workspace set")
        
        if name not in self.workspaces:
            raise ValueError(f"Workspace '{name}' does not exist")
        
        config = self.workspaces[name]
        workspace_dir = Path(config['workspace_dir'])
        
        return {
            'workspace_dir': str(workspace_dir),
            'pdf_path': config['pdf_path'],
            'images_dir': str(workspace_dir / "images"),
            'latex_dir': str(workspace_dir / "latex"),
            'checkpoint_file': str(workspace_dir / "checkpoint.json"),
            'main_doc': str(workspace_dir / "main.tex")
        }
    
    def print_workspace_info(self, name: Optional[str] = None):
        """Print detailed information about a workspace"""
        if name is None:
            name = self.current_workspace
        
        if name is None:
            print("⚠️  No current workspace set")
            return
        
        if name not in self.workspaces:
            print(f"❌ Workspace '{name}' does not exist")
            return
        
        config = self.workspaces[name]
        is_current = (name == self.current_workspace)
        
        print(f"\n{'='*60}")
        print(f"Workspace: {name} {'(CURRENT)' if is_current else ''}")
        print(f"{'='*60}")
        print(f"Description: {config.get('description', 'N/A')}")
        print(f"PDF: {config['pdf_path']}")
        print(f"Location: {config['workspace_dir']}")
        print(f"Status: {config.get('status', 'unknown')}")
        print(f"Created: {config.get('created_at', 'N/A')}")
        print(f"Last accessed: {config.get('last_accessed', 'N/A')}")
        
        # Check if checkpoint exists
        checkpoint_file = Path(config['workspace_dir']) / "checkpoint.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                pages = checkpoint.get('pages', [])
                completed = sum(1 for p in pages if p.get('latex_updated', False))
                print(f"Progress: {completed}/{len(pages)} pages completed")
        
        print(f"{'='*60}\n")