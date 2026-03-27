from models.pixtral_client import PixtralClient
from config.prompts import RFQ_AGENT_SYSTEM_PROMPT, DOCUMENT_CLASSIFICATION_PROMPT_TEMPLATE
from config.settings import VALID_CATEGORIES
import fitz  # PyMuPDF
from typing import Dict

class DocumentClassifier:
    """Classify documents into 01-08 categories using Pixtral"""
    
    def __init__(self):
        self.llm = PixtralClient()
        self.system_prompt = RFQ_AGENT_SYSTEM_PROMPT
    
    def classify_document(self, filename: str, file_path: str) -> Dict:
        """
        Classify document using Pixtral
        
        Returns:
            {
                "category": str,  # e.g. "01_Instructions"
                "confidence": float,
                "reasoning": str,
                "keywords_matched": list,
                "manual_review_needed": bool
            }
        """
        
        # Read file preview
        content_preview = self._read_file_preview(file_path)
        
        # Build prompt
        user_prompt = DOCUMENT_CLASSIFICATION_PROMPT_TEMPLATE.format(
            filename=filename,
            content_preview=content_preview
        )
        
        # Few-shot examples
        examples = [
            {
                "input": {
                    "filename": "BOQ_Package_A_Rev2.xlsx",
                    "content": "Item | Description | Quantity | Unit | Rate..."
                },
                "output": {
                    "category": "05_BOQ",
                    "confidence": 0.99,
                    "reasoning": "Filename explicitly 'BOQ', content shows pricing table",
                    "keywords_matched": ["BOQ", "Quantity", "Rate"],
                    "manual_review_needed": False
                }
            },
            {
                "input": {
                    "filename": "Tender_Instructions_Rev0.pdf",
                    "content": "Instructions to Contractors: 1. Submission deadline..."
                },
                "output": {
                    "category": "01_Instructions",
                    "confidence": 0.97,
                    "reasoning": "Filename and content clearly indicate instructions",
                    "keywords_matched": ["Instructions", "deadline"],
                    "manual_review_needed": False
                }
            }
        ]
        
        # Call LLM
        result = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            examples=examples
        )
        
        # Validate category
        if result.get('category') not in VALID_CATEGORIES:
            result['category'] = "08_Output"  # Fallback
            result['confidence'] = 0.5
            result['manual_review_needed'] = True
        
        # Metadata based on category
        result['manual_review_needed'] = result.get('confidence', 0) < 0.7
        
        # STRICT IRRELEVANT FILTERING:
        # Check for academic or non-tender academic content (IT courses, syllabus, books)
        irrelevant_keywords = ['syllabus', 'it project management', 'course material', 'curriculum', 'assignment', 'exam', 'lecture']
        filename_lower = filename.lower()
        if any(kw in filename_lower for kw in irrelevant_keywords):
            print(f"  🚩 Auto-flagged irrelevant document: {filename}")
            result['category'] = "08_Output"
            result['confidence'] = 1.0
            result['reasoning'] = "Irrelevant academic/IT content detected."

        # If it's an output/irrelevant doc, mark as incorrect
        if result['category'] == "08_Output":
            result['is_correct'] = False
        else:
            result['is_correct'] = True
            
        return result
    
    def _read_file_preview(self, file_path: str, max_chars: int = 1500) -> str:
        """Read first 1500 chars of file"""
        
        if file_path.endswith('.pdf'):
            try:
                doc = fitz.open(file_path)
                text = doc[0].get_text()[:max_chars]
                doc.close()
                return text
            except:
                return ""
        
        elif file_path.endswith(('.txt', '.md')):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read(max_chars)
            except:
                return ""
        
        # For Excel, images, etc., return filename only
        return f"[Binary file: {file_path}]"
