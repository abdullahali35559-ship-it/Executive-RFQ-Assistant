from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, String
from datetime import datetime
from database.models import Email, Thread, Attachment, AssistantChat
from models.pixtral_client import PixtralClient
from typing import List, Dict, Optional

class ExecutiveAssistant:
    """Answers context-aware questions about the user's data (Emails, Threads, Docs)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = PixtralClient()

    def answer_query(self, query: str, conversation_id: Optional[int] = None) -> str:
        """Main entry point for assistant chat"""
        
        # 1. Save User Message
        if conversation_id:
            user_msg = AssistantChat(conversation_id=conversation_id, role='user', content=query)
            self.db.add(user_msg)
            self.db.commit()

        # 2. Retrieve Context (Search-based RAG)
        context_data = self._retrieve_context(query)
        
        # 3. Build Prompt
        system_prompt = """
        You are the 'Executive Knowledge Assistant' for the AI Email & RFQ Portal.
        You have access to the user's email history (Threads), documents, and calendar.
        
        The portal has the following sections that you can guide the user to:
        - Dashboard: Overall summary, stats, and 'Coming Up' agenda.
        - Calendar: View schedules and book new meetings.
        - Business Threads: View all email conversations grouped by business topics (Tenders).
        - Draft Replies: See AI-suggested responses to emails.
        - Documents: Access all extracted PDF/Excel files.
        - Contacts: Manage business contacts and their history.
        
        Answer the user's question based ONLY on the provided context.
        If you don't find the answer in the context, say you don't know yet.
        Be concise, helpful, and professional.
        """
        
        user_prompt = f"""
        USER QUESTION: {query}

        [CURRENT SYSTEM SUMMARY]:
        - User: Abdullah (Executive)
        - Current Page: AI Assistant Page
        
        [RELEVANT CONTEXT FROM DATABASE]:
        {context_data}
        
        ANSWER:
        """
        
        # 4. Call LLM
        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )
        
        reply = response.get('response') or response.get('text') or response.get('answer') or response.get('path')
        if not reply and isinstance(response, dict):
            # Take the first long string or list of strings as the answer
            for val in response.values():
                if isinstance(val, str) and len(val) > 20:
                    reply = val
                    break
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                    reply = "\n".join([f"- {i}" for i in val])
                    break
        
        reply = reply or "I'm sorry, I couldn't find the answer in my records."
        
        # 5. Save Assistant Reply
        if conversation_id:
            assistant_msg = AssistantChat(conversation_id=conversation_id, role='assistant', content=reply)
            self.db.add(assistant_msg)
            self.db.commit()
            
        return reply

    def _retrieve_context(self, query: str) -> str:
        """Search DB for keywords in query to build context string"""
        # Extract potential keywords, cleaning punctuation and stop words
        import re
        STOP_WORDS = {'what', 'with', 'from', 'this', 'that', 'your', 'about', 'regarding', 'items', 'action', 'are', 'the', 'and', 'for'}
        clean_query = re.sub(r'[^\w\s]', '', query).lower()
        keywords = [k.strip() for k in clean_query.split() if len(k) > 2 and k.strip() not in STOP_WORDS]
        
        context_parts = []
        
        # Search Threads/Emails
        search_filter = or_(*[Email.subject.ilike(f"%{k}%") for k in keywords] + 
                           [Email.body.ilike(f"%{k}%") for k in keywords] +
                           [Email.meta_data.cast(String).ilike(f"%{k}%") for k in keywords]) # Search in meta_data too
        
        all_matches = self.db.query(Email).filter(search_filter).all()
        
        # Rank by keyword relevance
        scored_matches = []
        for msg in all_matches:
            score = 0
            subject_low = (msg.subject or "").lower()
            body_low = (msg.body or "").lower()
            meta_low = str(msg.meta_data or "").lower()
            
            for k in keywords:
                if k in subject_low:
                    score += 15 # Boost subject matches
                if k in body_low:
                    score += 2
                if k in meta_low:
                    score += 10 # Boost meta_data (action items/deadlines) matches
            
            if score > 0:
                scored_matches.append((score, msg))
        
        # Sort by score descending, then by date
        scored_matches.sort(key=lambda x: (x[0], x[1].received_at or datetime.min), reverse=True)
        matches = [m for score, m in scored_matches[:20]] # Increase to 20
        
        if matches:
            context_parts.append("--- EMAILS & THREADS ---")
            for msg in matches:
                context_parts.append(f"Date: {msg.received_at} | From: {msg.sender} | Subject: {msg.subject}")
                # Include metadata context if present
                if msg.meta_data:
                    if 'action_items' in msg.meta_data:
                        context_parts.append(f"Action Items: {', '.join(msg.meta_data['action_items'])}")
                    if 'meeting_suggestion' in msg.meta_data:
                        s = msg.meta_data['meeting_suggestion']
                        context_parts.append(f"Suggested Meeting: {s.get('topic')} at {s.get('start_time')}")
                
                context_parts.append(f"Content: {msg.body[:600] if msg.body else '[No Body - Check Meta/Attachments]'}")
                context_parts.append("")

        # Search Attachments (Filename AND Summary)
        doc_filter = or_(*[Attachment.filename.ilike(f"%{k}%") for k in keywords] + 
                           [Attachment.summary.ilike(f"%{k}%") for k in keywords])
        docs = self.db.query(Attachment).filter(doc_filter).limit(10).all()
        
        if docs:
            context_parts.append("--- DOCUMENTS ---")
            for doc in docs:
                context_parts.append(f"Filename: {doc.filename} | Category: {doc.category}")
                context_parts.append(f"AI Summary: {doc.summary}")

        # Search Calendar (NEW)
        try:
            from agents.executive.scheduler import GoogleCalendarClient
            cal = GoogleCalendarClient()
            if cal.connect():
                events = cal.get_upcoming_events(days=30)
                matching_events = []
                for ev in events:
                    title = ev.get('summary', '').lower()
                    desc = ev.get('description', '').lower()
                    if any(k in title or k in desc for k in keywords) or "metting" in clean_query or "meeting" in clean_query:
                        matching_events.append(ev)
                
                if matching_events:
                    context_parts.append("--- CALENDAR EVENTS ---")
                    for ev in matching_events[:10]:
                        start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date'))
                        context_parts.append(f"Meeting: {ev.get('summary')} | Time: {start}")
                        if ev.get('description'):
                            context_parts.append(f"Context: {ev.get('description')[:200]}")
                        context_parts.append("")
        except Exception as e:
            print(f"Calendar search error for assistant: {e}")
        
        if not context_parts:
            # Fallback: if they ask about meetings, just give them the next few
            if "meeting" in clean_query or "metting" in clean_query or "schedule" in clean_query:
                 # Fetch upcoming anyway
                 try:
                    cal = GoogleCalendarClient()
                    if cal.connect():
                        events = cal.get_upcoming_events(days=14)
                        if events:
                            context_parts.append("--- UPCOMING MEETINGS ---")
                            for ev in events[:5]:
                                start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date'))
                                context_parts.append(f"Meeting: {ev.get('summary')} | Time: {start}")
                 except: pass

        if not context_parts:
            return "No specific records found for these keywords. Please try broader terms."
            
        return "\n".join(context_parts)
