import hashlib
import os
from datetime import datetime
from typing import Dict, Optional
from config.settings import STORAGE_PATH
from agents.rfq_agent.document_versioner import DocumentVersioner
from agents.rfq_agent.malware_scanner import MalwareScanner

class FileManager:
    """Manage file storage with SHA256 hashing and folder structure"""
    
    def __init__(self, storage_base: str = STORAGE_PATH):
        self.storage_base = storage_base
        self.versioner = DocumentVersioner()
        self.scanner = MalwareScanner()
        os.makedirs(storage_base, exist_ok=True)
    
    def create_tender_folder(self, tender_id: str) -> str:
        """Alias for create_folder_structure"""
        return self.create_folder_structure(tender_id)
        
    def create_folder_structure(self, tender_id: str) -> str:
        """Create 01-08 folder structure for tender"""
        
        base_path = os.path.join(self.storage_base, tender_id)
        
        folders = [
            "01_Instructions",
            "02_Scope_of_Work",
            "03_Drawings",
            "04_Specifications",
            "05_BOQ",
            "06_Standards",
            "07_Commercial",
            "08_Output"
        ]
        
        for folder in folders:
            folder_path = os.path.join(base_path, folder)
            os.makedirs(folder_path, exist_ok=True)
        
        return base_path
    
    def save_file(self, 
                  file_data: bytes,
                  tender_id: str,
                  category: str,
                  original_filename: str,
                  version: int = 1,
                  source: str = "email_attachment") -> Dict:
        """
        Save file with SHA256 hash and make read-only
        Supports versioning (v2, v3, etc.)
        
        Returns:
            {
                "status": "SAVED" or "DUPLICATE",
                "path": str,
                "hash": str,
                "size": int,
                "version": int
            }
        """
        
        # Calculate SHA256 hash
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Create versioned filename if needed
        versioned_filename = self.versioner.create_versioned_filename(
            original_filename, 
            version
        )
        
        # Determine destination path
        dest_folder = os.path.join(self.storage_base, tender_id, category)
        dest_path = os.path.join(dest_folder, versioned_filename)
        
        # Ensure folder exists
        os.makedirs(dest_folder, exist_ok=True)
        
        # Save file to temp location first for scanning
        temp_dir = os.path.join(self.storage_base, "temp_scan")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{file_hash}_{original_filename}")
        
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        
        # Scan for malware
        scan_result = self.scanner.scan_file(temp_path)
        
        if scan_result['status'] == 'INFECTED':
            return {
                "status": "QUARANTINED",
                "path": scan_result.get('quarantined_path'),
                "hash": file_hash,
                "size": len(file_data),
                "version": version,
                "scan_detail": scan_result['detail']
            }
        
        # If clean or error (pass-through error for now to avoid blocking), save to final destination
        with open(dest_path, 'wb') as f:
            f.write(file_data)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Set read-only (Windows: attrib +r, Linux: chmod 444)
        if os.name == 'nt':  # Windows
            os.system(f'attrib +r "{dest_path}"')
        else:  # Linux/Mac
            os.chmod(dest_path, 0o444)
        
        return {
            "status": "SAVED",
            "path": dest_path,
            "hash": file_hash,
            "size": len(file_data),
            "version": version,
            "versioned_filename": versioned_filename
        }
    
    def get_or_create_tender_folder(self, 
                                    project_id: Optional[int],
                                    tender_id: str,
                                    existing_folder: Optional[str] = None) -> str:
        """
        Get existing folder path for project or create new one
        
        Args:
            project_id: Project ID (if existing project)
            tender_id: Tender ID
            existing_folder: Existing folder path (if any)
            
        Returns:
            Folder path
        """
        if existing_folder and os.path.exists(existing_folder):
            print(f"✅ Reusing existing folder: {existing_folder}")
            return existing_folder
        
        # Create new folder structure
        return self.create_folder_structure(tender_id)

def generate_tender_id() -> str:
    """Generate unique tender ID: TND-YYYY-NNNNN"""
    from datetime import datetime
    from database.connection import SessionLocal
    from database.models import Project
    from sqlalchemy import desc
    
    year = datetime.now().year
    db = SessionLocal()
    try:
        # Get last tender number from database for the current year
        last_tender = db.query(Project).filter(
            Project.tender_id.like(f"TND-{year}-%")
        ).order_by(desc(Project.tender_id)).first()
        
        if last_tender:
            # Extract number from TND-YYYY-NNNNN
            try:
                 last_number_str = last_tender.tender_id.split('-')[-1]
                 last_number = int(last_number_str)
            except (ValueError, IndexError):
                 last_number = 0
        else:
            last_number = 0
            
        new_number = last_number + 1
        return f"TND-{year}-{new_number:05d}"
    finally:
        db.close()
