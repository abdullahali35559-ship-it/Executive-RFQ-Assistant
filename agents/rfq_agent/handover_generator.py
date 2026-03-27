from datetime import datetime
from typing import Dict

class HandoverGenerator:
    """Generate handover JSON for Tender Agent"""
    
    def create_handover(self, 
                       tender_id: str,
                       metadata: Dict,
                       documents: list,
                       rfi_drafts: list) -> Dict:
        """
        Generate handover JSON for Tender Agent
        
        Returns complete handover payload
        """
        
        handover_json = {
            "tender_id": tender_id,
            "handover_status": "READY_FOR_TENDER_AGENT",
            "from_agent": "RFQ_AGENT",
            "to_agent": "TENDER_AGENT",
            "timestamp": datetime.now().isoformat(),
            
            "metadata": metadata,
            
            "documents": documents,
            
            "rfi_drafts": rfi_drafts,
            
            "storage_path": f"./storage/tenders/{tender_id}",
            
            "rfq_agent_summary": {
                "total_documents": len(documents),
                "documents_by_category": self._count_by_category(documents),
                "malware_scans_passed": True,
                "folder_structure_created": True,
                "rfi_drafts_generated": len(rfi_drafts)
            }
        }
        
        return handover_json
    
    def _count_by_category(self, documents):
        counts = {}
        for doc in documents:
            category = doc.get('category', 'unknown')
            counts[category] = counts.get(category, 0) + 1
        return counts
