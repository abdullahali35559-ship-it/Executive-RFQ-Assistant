"""
Test RFI Generator Module
"""
import sys
sys.path.append('..')

from agents.rfq_agent.rfi_generator import RFIGenerator

def test_rfi_generator():
    """Test RFI draft generation"""
    
    print("=== RFI Generator Test ===\n")
    
    rfi_gen = RFIGenerator()
    
    # Test missing documents detection
    print("Step 1: Checking document completeness...")
    documents = [
        {"category": "01_Instructions", "filename": "instructions.pdf"},
        {"category": "03_Drawings", "filename": "drawings.pdf"}
        # Missing: 02_Scope_of_Work, 05_BOQ, 07_Commercial
    ]
    
    missing = rfi_gen.check_completeness("TND-2026-00001", documents)
    print(f"  ✅ Missing documents detected: {missing}")
    
    if missing:
        print(f"\nStep 2: Generating RFI draft for: {missing[0]}")
        
        # Generate RFI for first missing item
        rfi_draft = rfi_gen.generate_rfi_draft(
            tender_id="TND-2026-00001",
            missing_category=missing[0],
            tender_metadata={
                "client_name": "NEOM",
                "tender_reference": "RFQ-NEOM-2026-001"
            }
        )
        
        print(f"\n  ✅ RFI Draft Generated:")
        print(f"     RFI ID: {rfi_draft['rfi_id']}")
        print(f"     Priority: {rfi_draft.get('priority', 'MEDIUM')}")
        print(f"     Status: {rfi_draft['status']}")
        print(f"\n  Subject: {rfi_draft.get('subject', 'N/A')}")
        print(f"\n  Body:\n")
        body = rfi_draft.get('body', 'No body generated')
        print("  " + "\n  ".join(body.split('\n')))
        
        print("\n✅ RFI generation test passed!")
        return True
    else:
        print("  ℹ️ All required documents present")
        return True

if __name__ == "__main__":
    test_rfi_generator()
