from models.pixtral_client import PixtralClient
from config.prompts import GENERAL_EMAIL_ASSISTANT_PROMPT, ATTACHMENT_SUMMARY_PROMPT
import fitz  # PyMuPDF
from typing import Dict

class DocumentClassifier:
    """Classify and summarize attachments/documents for the general assistant"""
    
    def __init__(self):
        self.llm = PixtralClient()
        self.system_prompt = GENERAL_EMAIL_ASSISTANT_PROMPT
    
    def classify_document(self, filename: str, file_path: str) -> Dict:
        """
        Summarize and categorize attachment content using LLM
        """
        
        # Read file preview
        content_preview = self._read_file_preview(file_path)
        
        # Build prompt
        user_prompt = ATTACHMENT_SUMMARY_PROMPT.format(
            filename=filename,
            content_preview=content_preview
        )
        
        # Call LLM
        result = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.0
        )
        
        # Fallback category if LLM doesn't return one
        if 'file_type' not in result:
            result['file_type'] = "Document"
            
        # Simplified category for the flat structure (all go into "General")
        result['category'] = "General"
        result['confidence'] = 1.0
        
        return result
    
    def _read_file_preview(self, file_path: str, max_chars: int = 1500) -> str:
        """Read first 1500 chars of file for context"""
        
        if file_path.endswith('.pdf'):
            try:
                doc = fitz.open(file_path)
                text = ""
                for page in doc[:3]: # check first 3 pages
                    text += page.get_text()
                doc.close()
                return text[:max_chars]
            except:
                return f"[Could not read PDF: {file_path}]"
        
        elif file_path.endswith(('.txt', '.md', '.json', '.xml')):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read(max_chars)
            except:
                return f"[Could not read text file: {file_path}]"
        
        # For Excel, images, etc., return filename
        return f"[Binary file: {file_path}]"
