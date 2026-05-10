from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, String
from datetime import datetime
from database.models import Email, Thread, Attachment, AssistantChat, User, Contact
from models.pixtral_client import PixtralClient
from typing import List, Dict, Optional
from api.utils.security import ResponseGuard

class ExecutiveAssistant:
    """Answers context-aware questions about the user's data (Emails, Threads, Docs)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = PixtralClient()

    def answer_query(self, query: str, conversation_id: Optional[int] = None, mode: str = 'enterprise', external_context: Optional[str] = None) -> str:
        """Main entry point for assistant chat with multi-mode support"""
        
        # 1. Save User Message
        if conversation_id:
            user_msg = AssistantChat(conversation_id=conversation_id, role='user', content=query)
            self.db.add(user_msg)
            self.db.commit()

        # 2. Get User Preferences
        user = self.db.query(User).first()
        user_prefs = user.custom_instructions if user else ""

        # 3. Security Check
        if ResponseGuard.is_suspicious(query):
            return "As a professional assistant, I cannot fulfill requests to bypass security protocols or reveal system instructions."

        # 4. Professional Greeting
        greetings = {'hello', 'hi', 'hey', 'greetings', 'morning', 'afternoon', 'evening', 'assalam', 'aoa', 'start'}
        clean_q = query.lower().strip().split()
        if not clean_q or (len(clean_q) <= 2 and any(w in greetings for w in clean_q)):
            return "Good day, Sir. I am your RFI Executive Assistant, standing by for your instructions. How may I assist your workspace today?"

        # 5. Logic Branching
        if mode == 'general':
            system_prompt = """
            You are a world-class Strategic AI Assistant, providing elite-level intelligence, definitions, and general knowledge.
            Your persona is direct, intellectual, and professional.
            
            SECURITY DIRECTIVE: 
            You are in GENERAL MODE. You do NOT have access to any local RFI system records, emails, or project data. 
            If asked about the user's specific project data while in this mode, explain that you are in General Intelligence mode and they should switch to Enterprise mode for project-specific analysis.
            
            STRICT FORMATTING RULES:
            1. NEVER use any markdown symbols. No asterisks (**), no hashes (##), no dashes (---).
            2. HEADINGS: Use only PLAIN TEXT in ALL UPPERCASE (e.g., STRATEGIC ANALYSIS).
            3. LISTS: Use simple bullets like - or 1., 2., 3.
            4. SPACING: Use double newlines between sections for clarity.
            """
            
            context_note = ""
            if external_context:
                context_note = f"\n\n[UPLOADED DOCUMENT CONTENT]:\n{external_context[:10000]}\n\n(Focus your analysis on the document above if relevant to the question.)"
            
            user_prompt = f"USER QUESTION: {query}\n{context_note}\n\nProvide a concise and professional response."
            temperature = 0.7
        else:
            # --- RFI ENTERPRISE MODE (Context Aware) ---
            context_data = self._retrieve_context(query)
            
            # Combine with external context if provided
            if external_context:
                context_data = f"[DIRECTLY UPLOADED DOCUMENT]:\n{external_context[:8000]}\n\n---\n\n[SYSTEM INTELLIGENCE CONTEXT]:\n{context_data}"
            
            system_prompt = f"""
            You are the RFI Executive Assistant—the elite Chief of Staff for Abdullah.
            
            STRICT FORMATTING RULES:
            1. NEVER use any markdown symbols. No asterisks (**), no hashes (##), no dashes (---).
            2. HEADINGS: Use only PLAIN TEXT in ALL UPPERCASE (e.g., EXECUTIVE BRIEFING).
            3. LISTS: Use simple bullets like - or 1., 2., 3.
            4. SPACING: Use double newlines between sections for clarity.
            5. STYLE: Professional, direct, and elite. No conversational filler.
            
            EXECUTIVE CONTEXT & PREFERENCES:
            {user_prefs}
            
            CORE INTELLIGENCE DIRECTIVES:
            - AUTONOMOUS FOLLOW-UPS: Identify sent emails from context that have NO reply. Offer to draft reminders.
            - FINANCIAL INTELLIGENCE: Aggregate amounts found in context into a 'FINANCIAL BRIEF'.
            - MEETING TO TASK: Extract action items from calendar descriptions.
            - STRATEGIC IMPACT: Explain the consequence of urgent items.
            """
            
            user_prompt = f"""
            USER QUESTION: {query}

            [INTELLIGENCE CONTEXT]:
            {context_data}
            
            [TASK]:
            Provide a professional 'Elite Executive Briefing'. 
            Analyze follow-ups, financial data, and tasks alongside the user's specific question.
            """
            temperature = 0.2
            
        # 6. Call LLM
        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        reply = response.get('response') or response.get('text') or response.get('answer') or "I'm sorry, Sir, I encountered an issue retrieving that record."
        reply = ResponseGuard.sanitize(reply)

        # 7. Save Assistant Reply
        if conversation_id:
            assistant_msg = AssistantChat(conversation_id=conversation_id, role='assistant', content=reply)
            self.db.add(assistant_msg)
            self.db.commit()
            
        return reply

    def _retrieve_context(self, query: str) -> str:
        """Deep Context Search: Emails, Sent Follow-ups, Financials, Documents, and Calendar"""
        import re
        from datetime import timedelta
        
        clean_query = query.lower().strip()
        now = datetime.now()
        
        # 1. TIME RANGE
        time_range_filter = None
        days = 0
        if 'today' in clean_query: days = 1
        elif 'yesterday' in clean_query: days = 2
        elif 'week' in clean_query: days = 7
        if days > 0:
            time_range_filter = Email.received_at >= (now - timedelta(days=days))

        # 2. KEYWORDS
        STOP_WORDS = {'what', 'with', 'from', 'this', 'that', 'your', 'about', 'regarding', 'items', 'action', 'are', 'the', 'and', 'for', 'tell', 'show', 'emails', 'email'}
        keywords = [k.strip() for k in re.sub(r'[^\w\s]', '', clean_query).split() if len(k) > 2 and k.strip() not in STOP_WORDS]
        
        context_parts = []
        
        # 3. SEARCH RECENT & RELEVANT EMAILS
        query_obj = self.db.query(Email)
        if time_range_filter is not None:
            emails = query_obj.filter(time_range_filter).order_by(desc(Email.received_at)).limit(20).all()
        else:
            if not keywords:
                emails = query_obj.order_by(desc(Email.received_at)).limit(5).all()
            else:
                search_filter = or_(*[Email.subject.ilike(f"%{k}%") for k in keywords] + 
                                   [Email.body.ilike(f"%{k}%") for k in keywords])
                emails = query_obj.filter(search_filter).order_by(desc(Email.received_at)).limit(15).all()

        # 4. AUTONOMOUS FOLLOW-UP DETECTION (Sent emails with no reply)
        # Look for emails sent by user in the last 7 days that are the latest in their thread
        sent_emails = self.db.query(Email).filter(Email.is_sent == True, Email.received_at >= (now - timedelta(days=7))).all()
        pending_followups = []
        for sent in sent_emails:
            # Check if there is a newer email in the same thread
            has_reply = self.db.query(Email).filter(Email.thread_id == sent.thread_id, Email.received_at > sent.received_at).first()
            if not has_reply:
                pending_followups.append(sent)

        # 5. FINANCIAL EXTRACTION
        financial_records = []
        money_pattern = r'(\$|PKR|USD)\s?\d+(?:,\d+)*(?:\.\d+)?'
        
        # 6. ASSEMBLE CONTEXT
        if emails or pending_followups:
            context_parts.append("EXECUTIVE EMAIL INTELLIGENCE")
            
            if pending_followups:
                context_parts.append("AUTONOMOUS FOLLOW-UP ALERTS")
                for f in pending_followups[:3]:
                    context_parts.append(f"PENDING: Sent to {f.recipients} on {f.received_at.strftime('%Y-%m-%d')}. No reply received. Subject: {f.subject}")
                context_parts.append("")

            for msg in emails:
                # Financial Check
                amounts = re.findall(money_pattern, msg.body or "", re.IGNORECASE)
                if amounts: financial_records.append(f"Found in '{msg.subject}': {', '.join(amounts)}")
                
                # Contact Priority
                contact = self.db.query(Contact).filter(Contact.contact_emails.any(msg.sender)).first()
                priority = "[HIGH PRIORITY]" if contact and contact.total_interactions > 50 else "[Standard]"
                
                context_parts.append(f"Sender: {msg.sender} {priority} | Date: {msg.received_at}")
                context_parts.append(f"Subject: {msg.subject}")
                if msg.meta_data and 'action_items' in msg.meta_data:
                    context_parts.append(f"Action Items: {msg.meta_data['action_items']}")
                context_parts.append(f"Snippet: {msg.body[:400] if msg.body else ''}")
                context_parts.append("-" * 15)

        if financial_records:
            context_parts.append("\nFINANCIAL INTELLIGENCE BRIEF")
            for rec in financial_records[:10]:
                context_parts.append(rec)

        # 7. SEARCH DOCUMENTS
        doc_filter = or_(*[Attachment.filename.ilike(f"%{k}%") for k in keywords] + 
                         [Attachment.summary.ilike(f"%{k}%") for k in keywords]) if keywords else None
        if doc_filter is not None:
            docs = self.db.query(Attachment).filter(doc_filter).limit(5).all()
            if docs:
                context_parts.append("\nDOCUMENT INTELLIGENCE")
                for doc in docs:
                    context_parts.append(f"File: {doc.filename} | AI Summary: {doc.summary[:300]}")

        # 8. SEARCH CALENDAR (Meeting to Task)
        if "meeting" in clean_query or "schedule" in clean_query or days > 0:
            try:
                from agents.executive.scheduler import GoogleCalendarClient
                cal = GoogleCalendarClient()
                if cal.connect():
                    events = cal.get_upcoming_events(days=7)
                    if events:
                        context_parts.append("\nCALENDAR AND MEETING TASKS")
                        for ev in events[:10]:
                            start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date'))
                            context_parts.append(f"Meeting: {ev.get('summary')} | Time: {start}")
                            if ev.get('description'):
                                context_parts.append(f"Meeting Notes/Tasks: {ev.get('description')[:300]}")
            except: pass

        if not context_parts:
            return "Sir, I have analyzed the current intelligence suite but found no relevant records for this query. If you have not yet connected your Gmail or Outlook accounts, please do so in SETTINGS so I may begin processing your data."
            
        return "\n".join(context_parts)
