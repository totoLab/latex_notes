"""
Checkpoint Manager with Version Tracking
Manages conversion checkpoints for resume capability
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class CheckpointManager:
    """Manages conversion checkpoints with version tracking for images and LaTeX"""
    
    def __init__(self, checkpoint_file: str = "output/checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        Path(os.path.dirname(checkpoint_file)).mkdir(parents=True, exist_ok=True)
    
    def create_page_entry(self, page_num: int, image_version: int = 0, latex_version: int = 0) -> Dict:
        """Create a new page entry"""
        return {
            'page': page_num,
            'image_version': image_version,
            'latex_version': latex_version,
            'image_updated': False,
            'latex_updated': False
        }
    
    def save_checkpoint(self, data: Dict):
        """Save checkpoint data"""
        data['timestamp'] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Checkpoint saved to {self.checkpoint_file}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint data if exists"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
            print(f"📂 Loaded checkpoint from {self.checkpoint_file}")
            print(f"   Last updated: {data.get('timestamp', 'Unknown')}")
            return data
        return None
    
    def clear_checkpoint(self):
        """Remove checkpoint file"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            print(f"🗑️ Checkpoint cleared")
    
    def get_page_entry(self, checkpoint: Dict, page_num: int) -> Optional[Dict]:
        """Get page entry from checkpoint"""
        if not checkpoint or 'pages' not in checkpoint:
            return None
        
        for page_entry in checkpoint['pages']:
            if page_entry['page'] == page_num:
                return page_entry
        return None
    
    def update_page_entry(
        self, 
        checkpoint: Dict, 
        page_num: int, 
        image_version: Optional[int] = None,
        latex_version: Optional[int] = None,
        image_updated: Optional[bool] = None,
        latex_updated: Optional[bool] = None
    ) -> Dict:
        """Update or create a page entry in checkpoint"""
        if 'pages' not in checkpoint:
            checkpoint['pages'] = []
        
        # Find existing entry
        page_entry = None
        for entry in checkpoint['pages']:
            if entry['page'] == page_num:
                page_entry = entry
                break
        
        # Create new entry if doesn't exist
        if page_entry is None:
            page_entry = self.create_page_entry(page_num)
            checkpoint['pages'].append(page_entry)
        
        # Update fields
        if image_version is not None:
            page_entry['image_version'] = image_version
        if latex_version is not None:
            page_entry['latex_version'] = latex_version
        if image_updated is not None:
            page_entry['image_updated'] = image_updated
        if latex_updated is not None:
            page_entry['latex_updated'] = latex_updated
        
        return checkpoint
