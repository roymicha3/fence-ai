import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import shutil
import os


class Session:
    
    def __init__(self,
                 name: str = None,
                 parent = None, 
                 data_dir: Path = Path("data"),
                 resources: Optional[List[Path]] = None):
        self._parent = parent
        resources = resources or []
        if name is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = name
        
        self.creation_time = datetime.now()
        self._data_dir_name = data_dir

        os.makedirs(self.data_dir, exist_ok=True)
        
        for path in resources:
            
            if path.is_file():
                dst_file = self.data_dir / path.name
                shutil.copy(path, dst_file)
            
            elif path.is_dir():
                dst_dir = self.data_dir / path.name
                os.makedirs(dst_dir, exist_ok=True)
                
                for file_path in path.iterdir():
                    dst_file = dst_dir / file_path.name
                    shutil.copy(file_path, dst_file)
    
    
    @property
    def parent(self):
        return self._parent
    
    @property
    def prefix(self):
        if self.parent is None:
            return self.id
        else:
            return f"{self.parent.prefix}/{self.id}"
        
    @property
    def data_dir(self):
        return Path(os.path.join(self.prefix, self._data_dir_name))
    
    def __str__(self):
        return f"Session {self.id} created at {self.creation_time}"
        
        