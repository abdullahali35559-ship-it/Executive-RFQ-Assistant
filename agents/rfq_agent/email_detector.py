from models.pixtral_client import PixtralClient
from config.prompts import RFQ_AGENT_SYSTEM_PROMPT, EMAIL_DETECTION_PROMPT_TEMPLATE
from typing import Dict

class EmailDetector:
    """Detect if emails are tender-related using Pixtral"""
    
    def __init__(self):
        self.llm = PixtralClient()
        self.system_prompt = RFQ_AGENT_SYSTEM_PROMPT
    
    def detect_tender_email(self, 
                            email_id: str,
                            subject: str, 
                            sender: str, 
                            body: str,
                            attachments: list = None) -> Dict:
        """
        Detect if email is tender-related using Pixtral
        """
        
        attachment_names = [a.get('filename', '') for a in attachments] if attachments else []
        attachments_str = ", ".join(attachment_names) if attachment_names else "None"
        
        # Prepare user prompt
        user_prompt = EMAIL_DETECTION_PROMPT_TEMPLATE.format(
            subject=subject,
            sender=sender,
            attachments=attachments_str,
            body_preview=body[:3000]  # First 3000 chars for full context
        )
        
        # Few-shot examples
        examples = [
            {
                "input": {
                    "subject": "RFQ-NEOM-2026-001 - MEP Package",
                    "sender": "tenders@neom.com",
                    "attachments": "ITT_Instructions.pdf, BOQ_MEP.xlsx",
                    "body": "Please submit your quote..."
                },
                "output": {
                    "is_tender": True,
                    "confidence": 0.98,
                    "keywords_found": ["RFQ", "NEOM", "quote"],
                    "reasoning": "Subject contains RFQ reference, known client sender",
                    "action": "PROCEED"
                }
            },
            {
                "input": {
                    "subject": "For calculation",
                    "sender": "zohaibafzal8687@gmail.com",
                    "attachments": "Project_Specs.pdf",
                    "body": "Dear Tender, Please find attached the document..."
                },
                "output": {
                    "is_tender": True,
                    "confidence": 0.95,
                    "keywords_found": ["calculation", "specification"],
                    "reasoning": "Subject indicates takeoff request, includes technical documents",
                    "action": "PROCEED"
                }
            },
            {
                "input": {
                    "subject": "Your Zoho CRM Trial Has Ended",
                    "sender": "shehbaz@zoho.com",
                    "attachments": "None",
                    "body": "Maximize your experience now..."
                },
                "output": {
                    "is_tender": False,
                    "confidence": 0.99,
                    "keywords_found": [],
                    "reasoning": "Marketing/CRM notification, not construction related",
                    "action": "IGNORE"
                }
            }
        ]
        
        # Call LLM
        result = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            examples=examples,
            temperature=0.1
        )
        
        # Validate result
        if not isinstance(result, dict):
            print(f"Warning: LLM did not return a dict. Got: {type(result)}")
            return {"is_tender": False, "confidence": 0.0, "error": "Invalid response format"}
        
        if 'is_tender' not in result:
            print(f"Warning: 'is_tender' not in response. Keys: {result.keys()}")
            # Try to infer from response text or subject/attachments
            if 'response' in result or subject:
                text = (result.get('response', '') + " " + subject + " " + attachments_str).lower()
                is_tender = any(kw in text for kw in ['rfq', 'tender', 'quotation', 'itt', 'calculation', 'boq', 'mep', 'bid'])
                return {
                    "is_tender": is_tender,
                    "confidence": 0.6,
                    "keywords_found": [],
                    "reasoning": "Inferred from text/keywords fallback",
                    "action": "PROCEED" if is_tender else "IGNORE"
                }
            return {"is_tender": False, "confidence": 0.0, "error": "Missing 'is_tender' field"}
        
        return result
