# Project Deep Analysis

Yeh README poore repo ka deep analysis hai: har page ka kaam, har Python/JS file ke functions aur classes, aur system flow ka overview.

## System Overview
- Multi-agent RFQ pipeline: emails/documents ingest -> data extraction -> draft generation
- FastAPI backend (API routes, auth, background tasks)
- UI dashboard (HTML pages + JS clients)
- PostgreSQL models + migrations

## Entry Points
- api/main.py - FastAPI app boot + routes + DB init
- scripts/run_rfq_agent.py - background agent runner

## UI Pages
- ui/admin-login.html - Admin Portal - RFI - UI page: Admin Portal - RFI.
- ui/admin.html - FYXER — Executive Command Center - UI page: FYXER — Executive Command Center.
- ui/assistant.html - RFI Assistant - UI page: RFI Assistant.
- ui/attachments.html - Documents - RFI - UI page: Documents - RFI.
- ui/bulk-actions.html - Bulk Action Center - RFI - UI page: Bulk Action Center - RFI.
- ui/calendar.html - Calendar - RFI - UI page: Calendar - RFI.
- ui/contacts.html - Contacts - RFI - UI page: Contacts - RFI.
- ui/drafts.html - Draft Replies - RFI - UI page: Draft Replies - RFI.
- ui/emails.html - Emails - RFI - UI page: Emails - RFI.
- ui/index.html - RFI Dashboard - UI page: RFI Dashboard.
- ui/login.html - Login - RFI - UI page: Login - RFI.
- ui/settings.html - Settings - RFI - UI page: Settings - RFI.
- ui/tenders.html - Tender Report - RFI Assistant - UI page: Tender Report - RFI Assistant.
- ui/threads.html - Business Threads - RFI - UI page: Business Threads - RFI.

## API Routes
- api/routes/__init__.py - Package initializer.
- api/routes/admin.py - API route handlers for admin features. (prefix: /api/admin)
- api/routes/assistant.py - API route handlers for assistant features.
- api/routes/attachments.py - API route handlers for attachments features.
- api/routes/auth.py - API route handlers for auth features. (prefix: /api/auth)
- api/routes/contacts.py - API route handlers for contacts features.
- api/routes/dashboard.py - API route handlers for dashboard features.
- api/routes/drafts.py - API route handlers for drafts features.
- api/routes/emails.py - API route handlers for emails features.
- api/routes/threads.py - API route handlers for threads features.
- api/routes/user.py - API route handlers for user features.

## Folder Responsibilities
- agents/ - AI agents (research, analysis, drafting).
- api/ - Backend routes and async tasks.
- auth/ - Authentication, sessions, audit logging.
- config/ - App settings, OAuth, DB config.
- database/ - SQLAlchemy models and migrations.
- integrations/ - External integrations (email/file).
- models/ - LLM / model clients.
- scripts/ - Maintenance utilities and one-off tools.
- tests/ - Test suite and validation scripts.
- ui/ - Frontend HTML/JS/CSS.
- root/ - Root utilities and docs.

## File-by-File Summary

### root/
- AZURE_PERMISSION_UPDATE.md - # Azure API Permissions Update Guide
- PROJECT_ARCHITECTURE_DEEP_DIVE.md - # 🚀 Executive RFQ Assistant: Architecture Deep Dive
- README.md - # Project Deep Analysis
- brain/3507dcba-e680-4f6c-a059-b133bfee0267/scratch/cleanup_main.py - No summary available.
- brain/3507dcba-e680-4f6c-a059-b133bfee0267/scratch/test_style.py - Test script for style.
- check_audit_logs.py - Diagnostic check for audit logs.
- check_db.py - Diagnostic check for db.
- check_db_attachments.py - Diagnostic check for db attachments.
- check_db_detailed.py - Diagnostic check for db detailed.
- check_llm_final.py - Diagnostic check for llm final.
- check_ollama.py - Diagnostic check for ollama.
- check_pwd.py - Diagnostic check for pwd.
- check_remote.py - Diagnostic check for remote.
- check_roles.py - Diagnostic check for roles.
- create_test_docs.py - No summary available.
- dash.html - No summary available.
- debug_idx.py - Debug helper for idx.
- deep_analyze_tnd1.py - No summary available.
- diagnose_missing_emails.py - Diagnostics for missing emails.
- diagnose_missing_emails_v2.py - Diagnostics for missing emails v2.
- fix_db_data.py - Fix or repair routine for db data.
- fix_duplicate.py - Fix or repair routine for duplicate.
- get_doc_details.py - Fetch helper for doc details.
- get_tender_details.py - Fetch helper for tender details.
- implementation_status.md - # Project Progress and Multi Agent Architecture Report
- init_followup_db.py - Initialization helper for followup db.
- list_emails_by_date.py - List or report utility for emails by date.
- list_emails_full.py - List or report utility for emails full.
- list_users.py - List or report utility for users.
- project_analysis.json - JSON object keys: generated_at, root, overview, files
- refresh_outlook_token.py - Outlook OAuth2 Token Refresh Script
- reset_superadmin.py - Reset utility for superadmin.
- reset_users.py - Reset utility for users.
- run_gmail_oauth.py - Run utility for gmail oauth.
- run_outlook_oauth.py - Run utility for outlook oauth.
- scratch/analysis_indexer.py - No summary available.
- scratch/generate_project_docs.py - No summary available.
- scratch/migrate_db.py - No summary available.
- scratch/update_versions.py - No summary available.
- scratch/verify_endpoints.py - Verification script for endpoints.
- seed_users.py - No summary available.
- simulate_api_logic.py - Simulation helper for api logic.
- simulate_style_sync.py - Simulation helper for style sync.
- storage/emails/TND-2026-00001/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00002/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00003/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00004/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00005/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00006/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00007/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00008/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00009/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00010/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00011/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00012/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- storage/emails/TND-2026-00013/handover_packet.json - JSON object keys: tender_id, handover_status, from_agent, to_agent, timestamp, metadata, documents, rfi_drafts, storage_path, rfq_agent_summary
- temp_script.js - Temporary or experimental helper.
- temp_script_fixed.js - Temporary or experimental helper.
- tender_details.json - JSON data file
- test_backend_api.py - Test script for backend api.
- test_emails_api.py - Test script for emails api.
- test_graph_api_debug.py - Test script for graph api debug.
- test_llm.py - Test script for llm.
- test_llm_chat.py - Test script for llm chat.
- test_rfi_consolidation.py - Test script for rfi consolidation.
- test_rfi_physical_check.py - Test script for rfi physical check.
- test_smart_agent.py - Test script for smart agent.
- test_style_manual.py - Test script for style manual.
- tmp_create_db.py - Temporary or experimental helper.
- tmp_debug_assistant.py - Temporary or experimental helper.
- update_pwd.py - No summary available.
- verify_data_final.py - Verification script for data final.
- verify_email_filter.py - Verification script for email filter.
- verify_full_system.py - Verification script for full system.
- verify_llm_config.py - Verification script for llm config.
- verify_pages.py - Verification script for pages.
- verify_sanitization.py - Verification script for sanitization.
- verify_search_fix.py - Verification script for search fix.
- verify_stabilization.py - Verification script for stabilization.
- verify_system.py - Verification script for system.
- verify_thread_tags.py - Verification script for thread tags.

### agents/
- agents/__init__.py - Package initializer.
- agents/executive/assistant.py - Agent component for assistant.
- agents/executive/followup_manager.py - Agent component for followup manager.
- agents/executive/scheduler.py - Agent component for scheduler.
- agents/executive/style_analyzer.py - Agent component for style analyzer.
- agents/rfq_agent/__init__.py - Package initializer.
- agents/rfq_agent/agent.py - Agent component for agent.
- agents/rfq_agent/auditor_agent.py - Agent component for auditor agent.
- agents/rfq_agent/client_matcher.py - Agent component for client matcher.
- agents/rfq_agent/cloud_file_downloader.py - Agent component for cloud file downloader.
- agents/rfq_agent/cloud_link_detector.py - Agent component for cloud link detector.
- agents/rfq_agent/document_classifier.py - Agent component for document classifier.
- agents/rfq_agent/document_versioner.py - Agent component for document versioner.
- agents/rfq_agent/draft_manager.py - Agent component for draft manager.
- agents/rfq_agent/email_detector.py - Agent component for email detector.
- agents/rfq_agent/email_fetcher.py - Agent component for email fetcher.
- agents/rfq_agent/file_manager.py - Agent component for file manager.
- agents/rfq_agent/gmail_api_client.py - Agent component for gmail api client.
- agents/rfq_agent/handover_generator.py - Agent component for handover generator.
- agents/rfq_agent/malware_scanner.py - Agent component for malware scanner.
- agents/rfq_agent/manager_agent.py - Agent component for manager agent.
- agents/rfq_agent/metadata_extractor.py - Agent component for metadata extractor.
- agents/rfq_agent/orchestrator.py - Agent component for orchestrator.
- agents/rfq_agent/outlook_graph.py - Agent component for outlook graph.
- agents/rfq_agent/outlook_oauth.py - Agent component for outlook oauth.
- agents/rfq_agent/project_matcher.py - Agent component for project matcher.
- agents/rfq_agent/reply_generator.py - Agent component for reply generator.
- agents/rfq_agent/researcher_agent.py - Agent component for researcher agent.
- agents/rfq_agent/rfi_generator.py - Agent component for rfi generator.
- agents/rfq_agent/style_agent.py - Agent component for style agent.
- agents/rfq_agent/writer_agent.py - Agent component for writer agent.

### api/
- api/__init__.py - Package initializer.
- api/main.py - FastAPI app entry point, startup tasks, routing, and DB initialization.
- api/routes/__init__.py - Package initializer.
- api/routes/admin.py - API route handlers for admin features.
- api/routes/assistant.py - API route handlers for assistant features.
- api/routes/attachments.py - API route handlers for attachments features.
- api/routes/auth.py - API route handlers for auth features.
- api/routes/contacts.py - API route handlers for contacts features.
- api/routes/dashboard.py - API route handlers for dashboard features.
- api/routes/drafts.py - API route handlers for drafts features.
- api/routes/emails.py - API route handlers for emails features.
- api/routes/threads.py - API route handlers for threads features.
- api/routes/user.py - API route handlers for user features.
- api/tasks.py - Background task helpers and async processing.
- api/utils/security.py - No summary available.

### auth/
- auth/audit.py - Authentication and authorization utilities for audit.
- auth/dependencies.py - Authentication and authorization utilities for dependencies.
- auth/security.py - Authentication and authorization utilities for security.
- auth/session_manager.py - Authentication and authorization utilities for session_manager.
- auth/sessions.json - Session data store (redacted)
- auth/user_manager.py - Authentication and authorization utilities for user_manager.
- auth/users.json - User data store (redacted)

### config/
- config/__init__.py - Package initializer.
- config/auth_settings.py - Configuration and settings for auth_settings.
- config/database.py - Configuration and settings for database.
- config/gmail_oauth_config.py - Configuration and settings for gmail_oauth_config.
- config/oauth_config.py - Configuration and settings for oauth_config.
- config/prompts.py - Configuration and settings for prompts.
- config/settings.py - Configuration and settings for settings.

### database/
- database/__init__.py - Package initializer.
- database/complete_setup.py - Database models, migrations, and setup for complete_setup.
- database/connection.py - Database models, migrations, and setup for connection.
- database/migrations/create_draft_emails.py - Database models, migrations, and setup for create_draft_emails.
- database/migrations/fix_tenders_columns.py - Database models, migrations, and setup for fix_tenders_columns.
- database/models.py - Database models, migrations, and setup for models.
- database/setup_database.py - Database models, migrations, and setup for setup_database.

### integrations/
- integrations/__init__.py - Package initializer.
- integrations/email_listeners/__init__.py - Package initializer.
- integrations/file_fetchers/__init__.py - Package initializer.

### models/
- models/__init__.py - Package initializer.
- models/pixtral_client.py - Model or client implementation for pixtral client.

### scripts/
- scripts/__init__.py - Package initializer.
- scripts/backfill_attachment_metadata.py - Utility script to backfill attachment metadata.
- scripts/backfill_links.py - Utility script to backfill links.
- scripts/check_mappings.py - Utility script to check mappings.
- scripts/check_ollama.py - Utility script to check ollama.
- scripts/check_rfi_status.py - Utility script to check rfi status.
- scripts/check_status.py - Utility script to check status.
- scripts/clean_tender_15.py - Utility script to clean tender 15.
- scripts/clean_test_data.py - Utility script to clean test data.
- scripts/cleanup_attachment_duplicates.py - Utility script to cleanup attachment duplicates.
- scripts/cleanup_junk.py - Utility script to cleanup junk.
- scripts/debug_emails.py - Utility script to debug emails.
- scripts/deep_cleanup.py - Utility script to deep cleanup.
- scripts/dump_mappings.py - Utility script to dump mappings.
- scripts/elevate_user.py - Utility script to elevate user.
- scripts/enrich_threads.py - Utility script to enrich threads.
- scripts/fix_db.py - Utility script to fix db.
- scripts/fix_db_schema.py - Utility script to fix db schema.
- scripts/global_deduplicate_links.py - Utility script to global deduplicate links.
- scripts/init_database.py - Utility script to init database.
- scripts/init_tags.py - Utility script to init tags.
- scripts/investigate_dupes.py - Utility script to investigate dupes.
- scripts/migrate_add_clients_projects.py - Utility script to migrate add clients projects.
- scripts/migrate_add_version_columns.py - Utility script to migrate add version columns.
- scripts/migrate_assistant.py - Utility script to migrate assistant.
- scripts/migrate_meta.py - Utility script to migrate meta.
- scripts/migrate_sync_col.py - Utility script to migrate sync col.
- scripts/monitor_followups.py - Utility script to monitor followups.
- scripts/process_emails.py - Utility script to process emails.
- scripts/reprocess_tenders.py - Utility script to reprocess tenders.
- scripts/run_db_migration.py - Utility script to run db migration.
- scripts/run_rfq_agent.py - Utility script to run rfq agent.
- scripts/seed_tags.py - Utility script to seed tags.
- scripts/sync_storage_db.py - Utility script to sync storage db.
- scripts/test_links_integration.py - Utility script to test links integration.
- scripts/test_malware_scan.py - Utility script to test malware scan.
- scripts/test_outlook.py - Utility script to test outlook.
- scripts/test_pixtral.py - Utility script to test pixtral.
- scripts/test_pixtral_connection.py - Utility script to test pixtral connection.
- scripts/test_repro.py - Utility script to test repro.
- scripts/troubleshoot_outlook.py - Utility script to troubleshoot outlook.
- scripts/verify_deep_fix.py - Utility script to verify deep fix.
- scripts/verify_final_fixed.py - Utility script to verify final fixed.
- scripts/verify_new_llm.py - Utility script to verify new llm.
- scripts/verify_tokens.py - Utility script to verify tokens.

### tests/
- tests/health_check.py - Test cases for health check.
- tests/run_all_tests.py - Test cases for run all tests.
- tests/test_assistant_deep_intel.py - Test cases for test assistant deep intel.
- tests/test_auth_flow.py - Test cases for test auth flow.
- tests/test_calendar_fix.py - Test cases for test calendar fix.
- tests/test_document_classifier.py - Test cases for test document classifier.
- tests/test_draft_management.py - Test cases for test draft management.
- tests/test_email_detection.py - Test cases for test email detection.
- tests/test_file_manager.py - Test cases for test file manager.
- tests/test_metadata_extractor.py - Test cases for test metadata extractor.
- tests/test_rfi_generator.py - Test cases for test rfi generator.
- tests/test_specialist_features.py - Test cases for test specialist features.
- tests/test_specialist_features_v2.py - Test cases for test specialist features v2.

### ui/
- ui/README.md - # 🚀 RFQ Agent UI - Quick Start Guide
- ui/admin-login.html - UI page: Admin Portal - RFI.
- ui/admin.html - UI page: FYXER — Executive Command Center.
- ui/assistant.html - UI page: RFI Assistant.
- ui/attachments.html - UI page: Documents - RFI.
- ui/bulk-actions.html - UI page: Bulk Action Center - RFI.
- ui/calendar.html - UI page: Calendar - RFI.
- ui/contacts.html - UI page: Contacts - RFI.
- ui/drafts.html - UI page: Draft Replies - RFI.
- ui/emails.html - UI page: Emails - RFI.
- ui/index.html - UI page: RFI Dashboard.
- ui/js/admin.js - Frontend logic for admin.
- ui/js/api.js - Frontend logic for api.
- ui/js/auth.js - Frontend logic for auth.
- ui/js/calendar_app.js - Frontend logic for calendar app.
- ui/js/dashboard.js - Frontend logic for dashboard.
- ui/js/drafts.js - Frontend logic for drafts.
- ui/login.html - UI page: Login - RFI.
- ui/settings.html - UI page: Settings - RFI.
- ui/tenders.html - UI page: Tender Report - RFI Assistant.
- ui/threads.html - UI page: Business Threads - RFI.

## Functions and Classes Index

### agents/__init__.py
Functions: none
Classes: none

### agents/executive/assistant.py
Functions: none
Classes:
- ExecutiveAssistant - Answers context-aware questions about the user's data (Emails, Threads, Docs)
Methods: __init__(self, db), answer_query(self, query, conversation_id, mode, external_context) - Main entry point for assistant chat with multi-mode support, _retrieve_context(self, query) - Deep Context Search: Emails, Sent Follow-ups, Financials, Documents, and Calendar

### agents/executive/followup_manager.py
Functions: none
Classes:
- FollowupManager - Analyze sent emails and suggest follow-ups for stale threads
Methods: __init__(self, db_session), find_stale_threads(self) - Find threads where the last message was SENT by us and is older than threshold, generate_suggestions(self) - Main loop to identify and generate follow-up tasks

### agents/executive/scheduler.py
Functions: none
Classes:
- GoogleCalendarClient - Interface to Google Calendar for Free/Busy lookups
Methods: __init__(self), connect(self), get_upcoming_events(self, days) - Get busy slots for the next X days, create_event(self, summary, start_time, end_time, description, attendees, send_updates) - Create a new event on Google Calendar, delete_event(self, event_id) - Delete an event from Google Calendar
- OutlookCalendarClient - Interface to Microsoft Graph for Calendar lookups
Methods: __init__(self), connect(self), get_upcoming_events(self, days), create_event(self, subject, start_time, end_time, body_preview, attendees, send_updates) - Create a new event on Outlook Calendar, delete_event(self, event_id) - Delete an event from Outlook Calendar
- ExecutiveScheduler - Orchestrates availability lookups and suggests slots
Methods: __init__(self, provider), find_free_slots(self, days) - Fetch busy events and return a summary for the LLM

### agents/executive/style_analyzer.py
Functions: none
Classes:
- StyleAnalyzer - Analyzes historical sent emails to derive the user's unique writing style
Methods: __init__(self, db), sync_user_voice(self, user_id) - Fetch last 50 sent emails and build a style guide

### agents/rfq_agent/__init__.py
Functions: none
Classes: none

### agents/rfq_agent/agent.py
Functions: none
Classes:
- RFQAgent - Main Agent class for processing incoming emails
Methods: __init__(self), process_incoming_email(self, email_data) - Process an incoming email using the centralized workflow

### agents/rfq_agent/auditor_agent.py
Functions: none
Classes:
- AuditorAgent - The final quality controller in the Multi-Agent system. It compares the drafted response against Management Strategy and Researcher Findings to ensure absolute accuracy, professional tone, and compliance.
Methods: __init__(self), review_draft(self, subject, draft_body, strategy, findings) - Produce a compliance and quality audit of the drafted response.

### agents/rfq_agent/client_matcher.py
Functions: none
Classes:
- ClientMatcher - Identify and track clients from email sender information
Methods: __init__(self), find_or_create_client(self, email_sender, email_body, session) - Find existing client or create new one  Args:     email_sender: Email sender address     email_body: Email body for context     session: Database session (optional)      Returns:     Client object, extract_client_name(self, email_sender, email_body) - Extract client/company name from email using LLM  Args:     email_sender: Email address     email_body: Email body text      Returns:     Client name string, match_by_email_domain(self, email, session) - Match client by email domain, but skip for public providers (Gmail, etc.), update_client_contact(self, client_id, email, session) - Add new contact email to client  Args:     client_id: Client ID     email: Email address to add     session: Database session (optional), _extract_domain(self, email) - Extract domain from email address

### agents/rfq_agent/cloud_file_downloader.py
Functions: none
Classes:
- CloudFileDownloader - Download files from cloud storage services
Methods: __init__(self) - Initialize downloader, download_from_onedrive(self, share_url, save_dir) - Download files from OneDrive shared link  Args:     share_url: OneDrive sharing URL     save_dir: Directory to save downloaded files      Returns:     List of downloaded file paths, download_from_google_drive(self, drive_url, file_id, save_dir) - Download files from Google Drive  Args:     drive_url: Google Drive URL     file_id: Extracted file/folder ID     save_dir: Directory to save downloaded files      Returns:     List of downloaded file paths, _get_share_id(self, share_url) - Convert OneDrive sharing URL to shareId for Graph API  Args:     share_url: OneDrive sharing URL      Returns:     Encoded shareId, _get_folder_children(self, share_id, headers) - Get children of a OneDrive folder, _download_onedrive_file(self, item, save_dir, headers) - Download a single file from OneDrive, _download_google_drive_file(self, service, file_metadata, save_dir) - Download a single file from Google Drive, _get_export_mime_type(self, google_mime_type) - Get export MIME type for Google Docs files, _update_filename_for_export(self, filename, export_mime_type) - Add proper extension to exported Google Docs files

### agents/rfq_agent/cloud_link_detector.py
Functions: none
Classes:
- CloudProvider - Supported cloud storage providers
- CloudLinkDetector - Detect and classify cloud storage links in email bodies
Methods: __init__(self) - Initialize detector, detect_links(self, email_body) - Detect all cloud storage links in email body  Args:     email_body: Email body text      Returns:     List of dictionaries with link info:     {         'url': 'https://...',         'provider': CloudProvider.ONEDRIVE,         'type': 'shared_link',         'file_id': '...' (for Google Drive)     }, _detect_onedrive_links(self, email_body) - Detect OneDrive links, _detect_sharepoint_links(self, email_body) - Detect SharePoint links, _detect_google_drive_links(self, email_body) - Detect Google Drive links, _detect_dropbox_links(self, email_body) - Detect Dropbox links, has_cloud_links(self, email_body) - Check if email body contains any cloud storage links, classify_link_safety(self, url) - Classify link safety: TRUSTED, VERIFIED, SUSPICIOUS

### agents/rfq_agent/document_classifier.py
Functions: none
Classes:
- DocumentClassifier - Classify and summarize attachments/documents for the general assistant
Methods: __init__(self), classify_document(self, filename, file_path) - Summarize and categorize attachment content using LLM, _read_file_preview(self, file_path, max_chars) - Read up to 15000 chars of file for deep analysis

### agents/rfq_agent/document_versioner.py
Functions: none
Classes:
- DocumentVersioner - Handle document version tracking
Methods: get_latest_version(self, tender_id, filename, session) - Get the latest version number for a document  Args:     tender_id: Tender ID     filename: Original filename     session: Database session (optional)      Returns:     Latest version number (0 if no previous versions), create_versioned_filename(self, original, version) - Create versioned filename  Args:     original: Original filename     version: Version number      Returns:     Versioned filename (e.g., "Document_v2.pdf"), check_if_duplicate(self, file_hash, tender_id, session) - Check if document with same hash already exists  Args:     file_hash: SHA256 hash of file     tender_id: Tender ID     session: Database session (optional)      Returns:     Document object if duplicate found, None otherwise, link_versions(self, new_doc_id, old_doc_id, reason, session) - Link new document version to previous version  Args:     new_doc_id: ID of new document     old_doc_id: ID of previous document     reason: Reason for new version     session: Database session (optional), get_version_history(self, tender_id, filename, session) - Get complete version history for a document  Args:     tender_id: Tender ID     filename: Original filename     session: Database session (optional)      Returns:     List of Document objects ordered by version, _get_base_filename(self, filename) - Remove version suffix from filename

### agents/rfq_agent/draft_manager.py
Functions: none
Classes:
- DraftManager - Manage draft email creation in Gmail and Outlook
Methods: __init__(self), create_gmail_draft(self, to, subject, body, cc, attachments) - Create draft email in Gmail with attachments, create_outlook_draft(self, to, subject, body, cc, attachments) - Create draft email in Outlook with attachments, create_draft(self, provider, to, subject, body, cc, attachments) - Create draft email in specified provider

### agents/rfq_agent/email_detector.py
Functions: none
Classes:
- EmailDetector - Detect if emails are actionable business correspondence or junk using LLM
Methods: __init__(self), detect_actionable_email(self, email_id, subject, sender, body, attachments) - Detect if email is actionable business correspondence using LLM, detect_tender_email(self) - Legacy wrapper for backward compatibility

### agents/rfq_agent/email_fetcher.py
Functions: none
Classes:
- EmailFetcher - Fetch emails from Gmail or Outlook
Methods: __init__(self, provider), connect(self), disconnect(self), fetch_emails(self, limit) - Fetch unread emails (generic), fetch_tender_emails(self, limit) - Legacy wrapper, fetch_sent_emails(self, limit) - Fetch recently sent emails (API only), _parse_email(self, msg_id), _decode_header(self, header), _extract_body(self, msg), _extract_attachments(self, msg), mark_as_read(self, email_id) - Mark an email as read across providers, move_to_processed(self, email_data)

### agents/rfq_agent/file_manager.py
Functions:
- generate_tender_id() - Generate unique ID: TND-YYYY-NNNNN
Classes:
- FileManager - Manage file storage with flat structure and malware protection
Methods: __init__(self, storage_base), create_thread_folder(self, thread_id) - Create a single flat folder for the thread, create_tender_folder(self) - Legacy alias, create_folder_structure(self) - Legacy alias, save_file(self, file_data, tender_id, category, original_filename, version, source) - Save file to flat directory structure, get_or_create_tender_folder(self, project_id, tender_id, existing_folder) - Get existing folder path or create new flat folder

### agents/rfq_agent/gmail_api_client.py
Functions: none
Classes:
- GmailAPIFetcher - Fetch Gmail emails using Gmail API
Methods: __init__(self), _load_credentials(self) - Load OAuth2 credentials from file, connect(self, verify) - Connect to Gmail API, fetch_tender_emails(self, limit) - Fetch tender-related emails from Gmail  Returns list of email dictionaries compatible with EmailFetcher interface, mark_as_read(self, email_id) - Mark an email as read by removing the UNREAD label, fetch_sent_emails(self, limit) - Fetch recently sent emails to learn writing style, _fetch_email_details(self, message_id) - Fetch full email details, move_to_processed(self, email_data) - Move email to processed label and mark as read, _get_or_create_label(self, label_name) - Get label ID or create if doesn't exist, mark_as_read(self, message_id) - Mark email as read by removing UNREAD label, _extract_body(self, payload) - Extract email body from payload recursively, _extract_attachments(self, message_id, payload) - Extract attachments from email recursively, create_draft(self, to, subject, body, in_reply_to, attachments) - Create a draft email in Gmail with optional attachments, add_attachment_to_draft(self, draft_id, filename, content) - Add an attachment to an existing Gmail draft by recreating it, update_draft(self, draft_id, subject, body) - Update an existing Gmail draft, send_draft(self, draft_id) - Send a Gmail draft, send_immediate_email(self, to, subject, body) - Send a high-end professional HTML email, delete_draft(self, draft_id) - Delete a Gmail draft, fetch_calendar_events(self, days) - Fetch calendar events for the next X days, create_calendar_event(self, title, start_iso, end_iso, attendees, description, notify_guests) - Create a new calendar event with triple-layered fallback for Meet generation, disconnect(self) - Cleanup (no persistent connection for API)

### agents/rfq_agent/handover_generator.py
Functions: none
Classes:
- HandoverGenerator - Generate handover JSON for Tender Agent
Methods: create_handover(self, tender_id, metadata, documents, rfi_drafts) - Generate handover JSON for Tender Agent  Returns complete handover payload, _count_by_category(self, documents)

### agents/rfq_agent/malware_scanner.py
Functions: none
Classes:
- MalwareScanner - Scan files for viruses and malware using ClamAV
Methods: __init__(self, quarantine_dir), _find_clamscan(self) - Find the clamscan binary, scan_file(self, file_path) - Scan a file for malware.  If infected, move it to quarantine.  Returns:     {         'status': 'CLEAN' | 'INFECTED' | 'ERROR',         'detail': str,         'quarantined': bool,         'quarantined_path': Optional[str]     }, _is_eicar_test_file(self, file_path) - Check if file contains the EICAR test string or our safe test string, _quarantine(self, file_path, reason) - Move file to quarantine directory

### agents/rfq_agent/manager_agent.py
Functions: none
Classes:
- ManagerAgent - The orchestrator that analyzes incoming inquiries and directs specialized agents. It determines the professional context and provides 'Inquiry Directives' for researchers.
Methods: __init__(self), analyze_inquiry(self, sender, subject, body, attachment_names) - Analyze the intent and provide directives.

### agents/rfq_agent/metadata_extractor.py
Functions: none
Classes:
- MetadataExtractor - Extract tender metadata from email and documents
Methods: __init__(self), extract_metadata(self, tender_id, email_data, documents) - Extract metadata from email and documents  Returns:     {         "client_name": str,         "project_name": str,         "tender_reference": str,         "submission_deadline": str (ISO 8601 with +03:00),         "rfi_deadline": str,         "contact_person": str,         "contact_email": str,         "location": str,         "trade": str,         "confidence": float     }

### agents/rfq_agent/orchestrator.py
Functions: none
Classes:
- AgentOrchestrator - Coordinates the collaboration between the Manager, Researcher, and Writer agents. It manages the data flow and ensures each agent has the context needed to succeed.
Methods: __init__(self), process_inquiry(self, email_data, documents, writing_style_guide, custom_instructions) - Run the complete multi-agent workflow for a single inquiry.

### agents/rfq_agent/outlook_graph.py
Functions: none
Classes:
- OutlookGraphFetcher - Fetch Outlook emails using Microsoft Graph API
Methods: __init__(self), _load_token(self) - Load and refresh OAuth2 access token, _get_headers(self) - Get HTTP headers with auth token, connect(self) - Verify connection to Graph API, fetch_tender_emails(self, limit) - Fetch tender-related emails from inbox  Returns list of email dictionaries compatible with EmailFetcher interface, fetch_sent_emails(self, limit) - Fetch recently sent emails to learn writing style, _convert_to_email_format(self, graph_message) - Convert Graph API message to EmailFetcher format, _fetch_attachments(self, message_id) - Fetch attachments for a message, _parse_date(self, date_str) - Parse Graph API date format, move_to_processed(self, email_data) - Move email to processed folder, _get_or_create_folder(self, folder_name) - Get folder ID or create if doesn't exist, mark_as_read(self, message_id) - Mark message as read, create_draft(self, to, subject, body, in_reply_to) - Create a draft email in Outlook  Args:     to: Recipient email address     subject: Email subject     body: Email body (plain text or HTML)     in_reply_to: Optional message ID to reply to      Returns:     Dict with 'success', 'draft_id', and optional 'error', update_draft(self, draft_id, subject, body) - Update an existing draft email  Args:     draft_id: Draft message ID     subject: New subject (optional)     body: New body content (optional)      Returns:     Dict with 'success' and optional 'error', add_attachment_to_draft(self, draft_id, filename, content) - Add an attachment to an existing Outlook draft, send_draft(self, draft_id) - Send a draft email  Args:     draft_id: Draft message ID to send      Returns:     Dict with 'success' and optional 'error', send_immediate_email(self, to, subject, body) - Send a high-end professional HTML email, delete_draft(self, draft_id) - Delete a draft email  Args:     draft_id: Draft message ID to delete      Returns:     Dict with 'success' and optional 'error', get_drafts(self, limit) - Get all draft emails from Drafts folder  Args:     limit: Maximum number of drafts to retrieve      Returns:     List of draft dictionaries, fetch_calendar_events(self, days) - Fetch calendar events for the next X days, create_calendar_event(self, title, start_iso, end_iso, attendees, description) - Create a new calendar event in Outlook, disconnect(self) - Cleanup (no persistent connection for REST API)

### agents/rfq_agent/outlook_oauth.py
Functions: none
Classes:
- OutlookOAuthFetcher - Fetch Outlook emails using OAuth2 token from FastAPI
Methods: __init__(self), get_access_token(self) - Load access token from file, connect_imap(self) - Connect to Outlook IMAP using OAuth2, disconnect(self) - Disconnect from IMAP

### agents/rfq_agent/project_matcher.py
Functions: none
Classes:
- ProjectMatcher - Match emails to existing or new projects
Methods: __init__(self), find_matching_project(self, client_id, project_data, session) - Find matching project using a multi-layer strategy: Layer 1: Metadata Matching (100% Confidence) - Threading headers Layer 2: Reference Matching (95% Confidence) - Unique IDs in text Layer 3: Semantic Matching (85% Confidence) - LLM similarity, extract_project_reference(self, project_data) - Extract project reference number from email  Args:     project_data: Dict with email data, calculate_similarity(self, project1, project2) - Calculate similarity between two project names using LLM, create_new_project(self, client_id, tender_id, project_name, project_reference, session) - Create new project for a client, _detect_intent_shift(self, new_email, old_subject) - Detect if a client is using an old thread for a completely NEW project. Returns True if a new project intent is detected., _extract_project_name(self, project_data) - Extract project name from email data

### agents/rfq_agent/reply_generator.py
Functions: none
Classes:
- ReplyGenerator - Generate high-quality business email drafts and category suggestions
Methods: __init__(self), generate_draft(self, sender, subject, body, attachments, smart_instructions) - Produce a professional email draft based on history and attachments, suggest_categories(self, subject, body, attachment_names, current_date) - Suggest categories (tags) and extract meeting details if present

### agents/rfq_agent/researcher_agent.py
Functions: none
Classes:
- ResearcherAgent - The investigator specialized in deep document analysis. It resolves the directives issued by the Manager by scanning technical data and finding verified facts.
Methods: __init__(self), investigate(self, directives, email_context, document_contexts) - Execute directives using available contexts with Deep Intelligence.

### agents/rfq_agent/rfi_generator.py
Functions: none
Classes:
- RFIGenerator - Generate RFI draft emails for missing documents
Methods: __init__(self), check_completeness(self, tender_id, documents) - Check for missing or incorrect documents, considering all documents in DB for this tender  Args:     tender_id: Tender ID     documents: Optional list of documents currently being processed  Returns:     Dict with 'missing', 'incorrect', and 'irrelevant' lists, generate_rfi_draft(self, tender_id, missing_category, tender_metadata) - Generate RFI draft email for missing document  Returns:     {         "rfi_id": str,         "subject": str,         "body": str,         "priority": str,         "deadline_request": str,         "status": "DRAFT"     }, generate_consolidated_rfi_draft(self, tender_id, missing_categories, incorrect_categories, irrelevant_files, tender_metadata) - Generate ONE consolidated RFI draft for all missing and incorrect categories, _generate_rfi_id(self, tender_id) - Generate RFI ID

### agents/rfq_agent/style_agent.py
Functions: none
Classes:
- StyleAgent - Analyzes user-provided samples and historical emails to extract  linguistic patterns, tone, and formatting preferences.
Methods: __init__(self), analyze_samples(self, samples) - Analyze raw email samples and return a structured Style Guide., extract_style_from_emails(self, emails) - Takes a list of email objects (subject/body) and analyzes them for tone.

### agents/rfq_agent/writer_agent.py
Functions: none
Classes:
- WriterAgent - The communicator specialized in professional correspondence. It synthesizes business strategy and technical facts into high-end executive drafts.
Methods: __init__(self), draft_response(self, sender, subject, strategy, tone, findings, writing_style_guide, custom_instructions, previous_draft, revision_feedback) - Produce a professional response draft, mirroring the user's authentic style.

### api/__init__.py
Functions: none
Classes: none

### api/main.py
Functions:
- run_migrations() - Ensure database schema is up to date with Self-Healing logic
- init_admin() - Seed initial admin users
- lifespan(app)
- executive_guardian_middleware(request, call_next)
- root()
- dashboard_page()
- dashboard_all_fallback(current_user)
- admin_portal()
- serve_page(page_name)
Classes: none

### api/routes/__init__.py
Functions: none
Classes: none

### api/routes/admin.py
Functions:
- get_db()
- get_admin_stats(current_admin, db) - Get platform-wide statistics including chart data for widgets.
- list_users(current_admin, db) - List all registered users. SuperAdmin Only.
- create_user(user_data, request, current_admin, db) - Create a new user. SuperAdmin Only.
- get_user_detail(user_id, current_admin, db) - Get detailed info about a specific user. SuperAdmin Only.
- update_user(user_id, update_data, request, current_admin, db) - Update user role or status. SuperAdmin Only.
- get_audit_logs(limit, current_admin, db) - Get latest audit logs. SuperAdmin Only.
Classes:
- AdminStats
- UserCreate
- UserUpdate

### api/routes/assistant.py
Functions:
- get_conversations(mode, current_user, db)
- create_conversation(request, current_user, db)
- delete_conversation(conv_id, current_user, db)
- get_assistant_history(conversation_id, current_user, db)
- assistant_chat(request, current_user, db)
- assistant_extract_text(file, current_user)
Classes:
- CreateConversationRequest

### api/routes/attachments.py
Functions:
- get_all_attachments(current_user, db)
- get_attachment(att_id, current_user, db)
- download_attachment(att_id, current_user, db)
Classes: none

### api/routes/auth.py
Functions:
- register(user_data, request, db) - Register a new user in PostgreSQL
- login(request, response, db) - Login and set HTTP-only session cookie with Brute-Force Shielding
- logout(response) - Professional Logout: Wipes the session cookie
- get_me(current_user) - Return the current user's profile info
Classes:
- UserLogin
- UserRegister

### api/routes/contacts.py
Functions:
- get_contacts(current_user, db)
- get_contact(contact_id, current_user, db)
- add_contact(contact_data, current_user, db)
- get_contact_intelligence(contact_id, current_user, db) - Fetch intelligence data for a specific contact
Classes: none

### api/routes/dashboard.py
Functions:
- get_dashboard_stats(current_user, db) - Get aggregate statistics for the dashboard with caching
- get_system_status(current_user, db) - Check connectivity to various system components with caching
- get_agent_status(current_user, db) - Return the current processing status of the agent with live logs
- get_session_summary(from_time, to_time, current_user, db) - Get a summary of tender activities within a specific time range
- trigger_email_processing(background_tasks, current_user) - Trigger the email processing agent in the background
- run_sync_intelligence(user_id) - Background task to fetch and process emails
- get_morning_brief(current_user, db)
- get_tasks(current_user, db)
- get_followups(current_user, db)
- get_calendar_events(days, refresh, current_user) - Fetch events from both Google and Outlook with simple caching
- get_session_summary(from_time, to_time, current_user, db) - Get construction pulse summary for a specific time range
- create_calendar_event(data, current_user) - Create an event in either Google or Outlook
Classes: none

### api/routes/drafts.py
Functions:
- get_drafts(thread_id, db, current_user)
- get_draft_detail(draft_id, db, current_user)
- update_draft(draft_id, draft_data, db, current_user)
- send_draft(draft_id, db, current_user)
- delete_draft(draft_id, db, current_user)
Classes:
- DraftUpdate
- DraftEnhance

### api/routes/emails.py
Functions:
- get_msal_app()
- outlook_oauth_login()
- outlook_oauth_callback(request, background_tasks, db)
- get_gmail_flow()
- gmail_oauth_login()
- gmail_oauth_callback(request, background_tasks, db)
- get_emails(thread_id, current_user, db)
- get_single_email(id, current_user, db)
- get_oauth_status(request)
- gmail_logout()
- outlook_logout()
Classes: none

### api/routes/threads.py
Functions:
- get_threads(status, current_user, db) - Get all threads with optional status filter
- get_single_thread(thread_id, current_user, db)
- get_thread_attachments(thread_id, current_user, db)
- get_tags(current_user, db)
- reprocess_thread(thread_id, current_user, db) - Manually trigger re-analysis of a thread
- download_handover(thread_id, current_user, db) - Download the handover packet for an active project
- get_thread_emails(thread_id, current_user, db) - Get all emails associated with a thread
Classes: none

### api/routes/user.py
Functions:
- get_user_settings(current_user)
- update_user_settings(settings, current_user, db)
- sync_voice(current_user, db)
- get_me(current_user)
Classes:
- UserSettingsUpdate

### api/tasks.py
Functions:
- sync_user_writing_style(user_id, provider) - Background task to fetch last 50 sent emails and analyze writing style.
Classes: none

### api/utils/security.py
Functions: none
Classes:
- ResponseGuard - Scans AI responses for sensitive patterns and masks them
Methods: sanitize(text) - Main method to clean text before sending to UI, is_suspicious(query) - Detect potential prompt injection attempts

### auth/audit.py
Functions:
- log_action(db, user_id, action, details, thread_id, ip_address) - Log an action to the audit_log table.
Classes: none

### auth/dependencies.py
Functions:
- get_current_user(request) - ELITE SECURITY: Strictly relies on HttpOnly Cookies. JS-Readable Tokens are DISALLOWED.
- get_current_admin(current_user) - Dependency to enforce admin/superadmin role.
- get_optional_current_user(request) - Optional version of the current user dependency (Cookie Based).
Classes: none

### auth/security.py
Functions:
- verify_password(plain_password, hashed_password) - Verify a password against a hash
- get_password_hash(password) - Generate a password hash
- create_access_token(data, expires_delta) - Create a new JWT access token
- decode_access_token(token) - Decode a JWT access token and return the payload
Classes: none

### auth/session_manager.py
Functions: none
Classes:
- SessionManager
Methods: __init__(self), _ensure_sessions_file(self) - Ensure the sessions JSON file exists., get_all_sessions(self) - Load all active sessions from the JSON file., add_session(self, username, token, expires_at) - Add a new active session., is_token_valid(self, token) - Check if a token exists in the active sessions., revoke_session(self, token) - Remove a session (logout).

### auth/user_manager.py
Functions: none
Classes:
- UserManager
Methods: __init__(self), _ensure_users_file(self) - Ensure the users JSON file exists., get_all_users(self) - Load all users from the JSON file., get_user_by_username(self, username) - Find a user by their username., add_user(self, user_data) - Add a new user to the JSON file., delete_user(self, username) - Remove a user from the JSON file.

### brain/3507dcba-e680-4f6c-a059-b133bfee0267/scratch/cleanup_main.py
Functions: none
Classes: none

### brain/3507dcba-e680-4f6c-a059-b133bfee0267/scratch/test_style.py
Functions:
- test_style_mirroring_manual()
Classes: none

### check_audit_logs.py
Functions: none
Classes: none

### check_db.py
Functions: none
Classes: none

### check_db_attachments.py
Functions:
- check_attachments()
Classes: none

### check_db_detailed.py
Functions: none
Classes: none

### check_llm_final.py
Functions:
- check_cloud()
- check_local()
Classes: none

### check_ollama.py
Functions:
- check_ollama()
Classes: none

### check_pwd.py
Functions:
- check()
Classes: none

### check_remote.py
Functions:
- check_remote()
Classes: none

### check_roles.py
Functions:
- check_users()
Classes: none

### config/__init__.py
Functions: none
Classes: none

### config/auth_settings.py
Functions: none
Classes: none

### config/database.py
Functions:
- get_db() - Get database session
- init_db() - Initialize database tables
Classes: none

### config/gmail_oauth_config.py
Functions: none
Classes: none

### config/oauth_config.py
Functions: none
Classes: none

### config/prompts.py
Functions: none
Classes: none

### config/settings.py
Functions: none
Classes: none

### create_test_docs.py
Functions:
- create_dummy_files() - Create dummy text files that can be renamed to PDF for testing classification
Classes: none

### database/__init__.py
Functions: none
Classes: none

### database/complete_setup.py
Functions:
- create_database() - Create the database if it doesn't exist
Classes: none

### database/connection.py
Functions: none
Classes: none

### database/migrations/create_draft_emails.py
Functions: none
Classes: none

### database/migrations/fix_tenders_columns.py
Functions:
- migrate()
Classes: none

### database/models.py
Functions: none
Classes:
- Contact - Formerly Client
- Topic - Formerly Project
- Tag - New Category/Tag Model
- Thread - Formerly Tender
- Email
- Attachment - Formerly Document
- DraftReply - Formerly DraftEmail / RFIDraft
- FollowupTask - New: Track threads that need following up
- User
- AuditLog
- AssistantConversation
- AssistantChat

### database/setup_database.py
Functions:
- create_database() - Create all database tables
Classes: none

### debug_idx.py
Functions: none
Classes: none

### deep_analyze_tnd1.py
Functions:
- analyze_tnd_00001()
Classes: none

### diagnose_missing_emails.py
Functions:
- check_missing_emails()
Classes: none

### diagnose_missing_emails_v2.py
Functions:
- diagnose_tenders(tender_ids)
Classes: none

### fix_db_data.py
Functions: none
Classes: none

### fix_duplicate.py
Functions: none
Classes: none

### get_doc_details.py
Functions:
- get_document_details()
Classes: none

### get_tender_details.py
Functions:
- get_tender_details()
Classes: none

### init_followup_db.py
Functions:
- init_followup_schema()
Classes: none

### integrations/__init__.py
Functions: none
Classes: none

### integrations/email_listeners/__init__.py
Functions: none
Classes: none

### integrations/file_fetchers/__init__.py
Functions: none
Classes: none

### list_emails_by_date.py
Functions:
- list_emails_by_date()
Classes: none

### list_emails_full.py
Functions:
- list_emails()
Classes: none

### list_users.py
Functions: none
Classes: none

### models/__init__.py
Functions: none
Classes: none

### models/pixtral_client.py
Functions: none
Classes:
- PixtralClient - Client for interacting with LLMs (Pixtral via Ollama or Claude via OpenRouter)
Methods: __init__(self), generate(self, system_prompt, user_prompt, temperature, examples) - Generate response from configured LLM, chat(self, system_prompt, user_prompt, temperature) - Simple chat interface, test_connection(self) - Test if LLM is responding

### refresh_outlook_token.py
Functions:
- load_token() - Load existing token from file
- save_token(token_data) - Save token to file
- is_token_expired(token_data) - Check if access token is expired or will expire soon
- refresh_token() - Refresh the Outlook access token using refresh token
- get_valid_token() - Get a valid access token (refresh if needed)
Classes: none

### reset_superadmin.py
Functions: none
Classes: none

### reset_users.py
Functions:
- reset_users()
Classes: none

### run_gmail_oauth.py
Functions:
- authenticate_gmail() - Authenticate with Gmail and save token
Classes: none

### run_outlook_oauth.py
Functions:
- main() - Main OAuth2 flow
Classes:
- CallbackHandler - Handle OAuth2 callback
Methods: do_GET(self), log_message(self, format)

### scratch/analysis_indexer.py
Functions:
- read_text(path)
- iter_files(root)
- summarize_python(source)
- summarize_js(source)
- summarize_html(source)
- summarize_json(path, source)
- main()
Classes: none

### scratch/generate_project_docs.py
Functions:
- read_text(path)
- infer_summary(path, entry)
- extract_route_prefix(path)
- make_markdown(data)
- main()
Classes: none

### scratch/migrate_db.py
Functions:
- fix_database()
Classes: none

### scratch/update_versions.py
Functions: none
Classes: none

### scratch/verify_endpoints.py
Functions:
- test_auth()
- test_endpoint(name, path, method)
Classes: none

### scripts/__init__.py
Functions: none
Classes: none

### scripts/backfill_attachment_metadata.py
Functions:
- backfill()
Classes: none

### scripts/backfill_links.py
Functions:
- backfill_links()
Classes: none

### scripts/check_mappings.py
Functions: none
Classes: none

### scripts/check_ollama.py
Functions:
- test_url(url, name)
Classes: none

### scripts/check_rfi_status.py
Functions: none
Classes: none

### scripts/check_status.py
Functions: none
Classes: none

### scripts/clean_tender_15.py
Functions:
- remove_readonly(func, path, excinfo)
Classes: none

### scripts/clean_test_data.py
Functions:
- clean_test_data() - Remove test tender data
Classes: none

### scripts/cleanup_attachment_duplicates.py
Functions:
- cleanup_duplicates()
Classes: none

### scripts/cleanup_junk.py
Functions:
- cleanup_junk()
Classes: none

### scripts/debug_emails.py
Functions:
- debug_emails() - Debug email fetching
Classes: none

### scripts/deep_cleanup.py
Functions:
- deep_cleanup()
Classes: none

### scripts/dump_mappings.py
Functions: none
Classes: none

### scripts/elevate_user.py
Functions:
- elevate_user(email)
Classes: none

### scripts/enrich_threads.py
Functions:
- universal_enrich()
Classes: none

### scripts/fix_db.py
Functions: none
Classes: none

### scripts/fix_db_schema.py
Functions:
- check_columns()
Classes: none

### scripts/global_deduplicate_links.py
Functions:
- global_deduplicate()
Classes: none

### scripts/init_database.py
Functions:
- create_schema() - Create database schema
Classes: none

### scripts/init_tags.py
Functions:
- init_default_tags()
Classes: none

### scripts/investigate_dupes.py
Functions: none
Classes: none

### scripts/migrate_add_clients_projects.py
Functions:
- migrate_database() - Add new tables and update existing schema
- verify_migration() - Verify migration was successful
Classes: none

### scripts/migrate_add_version_columns.py
Functions:
- add_version_columns() - Add version tracking columns to documents table
Classes: none

### scripts/migrate_assistant.py
Functions:
- migrate()
Classes: none

### scripts/migrate_meta.py
Functions:
- migrate()
Classes: none

### scripts/migrate_sync_col.py
Functions:
- migrate()
Classes: none

### scripts/monitor_followups.py
Functions:
- sync_sent_emails() - Fetch and store recently sent emails
- run_analysis() - Run the FollowupManager logic
Classes: none

### scripts/process_emails.py
Functions:
- apply_tag_inheritance(db, sender_email, current_email_obj) - If this sender has tags from previous emails, apply them to the current email.
- process_email_batch() - Fetch and process emails (General Assistant)
Classes: none

### scripts/reprocess_tenders.py
Functions:
- reprocess_tender(tender_id, email_id, keyword, reset_all_failed) - Reset processed status for emails to allow RFQ Agent to re-run
Classes: none

### scripts/run_db_migration.py
Functions:
- run_migration()
Classes: none

### scripts/run_rfq_agent.py
Functions:
- sanitize_filename(filename) - Sanitize filename to be safe for filesystem
- apply_tag_inheritance(db, email_record, contact_id, thread_id) - Apply tags from: 1. The same thread (if it exists) 2. The same contact (if they have history)
- log_progress(db, thread_id, action, details)
- process_incoming_email(email_data) - Main workflow for General Email Assistant
Classes: none

### scripts/seed_tags.py
Functions:
- seed_tags()
Classes: none

### scripts/sync_storage_db.py
Functions:
- sync_storage_to_db() - Scans STORAGE_PATH and ensures every file and folder has a  corresponding record in the database.
Classes: none

### scripts/test_links_integration.py
Functions:
- test_links(target_url)
Classes: none

### scripts/test_malware_scan.py
Functions:
- test_malware_scanning()
Classes: none

### scripts/test_outlook.py
Functions:
- test_outlook() - Test Outlook IMAP connection
Classes: none

### scripts/test_pixtral.py
Functions:
- test_pixtral() - Test Pixtral connection and basic functionality
Classes: none

### scripts/test_pixtral_connection.py
Functions:
- test_connection(url) - Test if Pixtral server is accessible
Classes: none

### scripts/test_repro.py
Functions:
- test_full_repro_hardened()
Classes: none

### scripts/troubleshoot_outlook.py
Functions:
- test_outlook_connection() - Test Outlook IMAP with different methods
Classes: none

### scripts/verify_deep_fix.py
Functions: none
Classes: none

### scripts/verify_final_fixed.py
Functions:
- verify_final()
Classes: none

### scripts/verify_new_llm.py
Functions:
- test_new_llm()
Classes: none

### scripts/verify_tokens.py
Functions:
- check_outlook_token()
- check_google_token()
Classes: none

### seed_users.py
Functions: none
Classes: none

### simulate_api_logic.py
Functions:
- simulate_get_emails(tender_id, status, include_all)
Classes: none

### simulate_style_sync.py
Functions:
- simulate_background_sync(provider)
Classes: none

### test_backend_api.py
Functions:
- root()
- get_system_status() - System status for dashboard
- get_dashboard_stats() - Dashboard statistics
- get_recent_activity() - Recent activity feed
- get_tenders() - Get all tenders
- process_emails() - Process new emails
- get_oauth_status() - OAuth provider status
- get_clients() - Get all clients
- health_check() - Health check endpoint
Classes: none

### test_emails_api.py
Functions:
- check_api_for_emails()
Classes: none

### test_graph_api_debug.py
Functions:
- load_token() - Load OAuth2 token
- test_endpoint(url, token, description) - Test a Graph API endpoint
Classes: none

### test_llm.py
Functions:
- test()
Classes: none

### test_llm_chat.py
Functions:
- test_chat()
Classes: none

### test_rfi_consolidation.py
Functions:
- test_consolidation()
Classes: none

### test_rfi_physical_check.py
Functions:
- test_physical_check()
Classes: none

### test_smart_agent.py
Functions:
- test_missing_attachment_detection()
Classes: none

### test_style_manual.py
Functions:
- test_style_mirroring_manual()
Classes: none

### tests/health_check.py
Functions:
- check_endpoints()
Classes: none

### tests/run_all_tests.py
Functions: none
Classes: none

### tests/test_assistant_deep_intel.py
Functions:
- test_deep_intelligence()
Classes: none

### tests/test_auth_flow.py
Functions:
- test_auth_flow()
Classes: none

### tests/test_calendar_fix.py
Functions:
- test_payload_simulation()
Classes: none

### tests/test_document_classifier.py
Functions:
- test_classification() - Test document classification
Classes: none

### tests/test_draft_management.py
Functions:
- test_draft_creation() - Create a test draft in Outlook and database
Classes: none

### tests/test_email_detection.py
Functions:
- test_tender_email() - Test with tender email
- test_non_tender_email() - Test with non-tender email
Classes: none

### tests/test_file_manager.py
Functions:
- test_file_manager() - Test file manager functionality
Classes: none

### tests/test_metadata_extractor.py
Functions:
- test_metadata_extraction() - Test metadata extraction from email
Classes: none

### tests/test_rfi_generator.py
Functions:
- test_rfi_generator() - Test RFI draft generation
Classes: none

### tests/test_specialist_features.py
Functions:
- setup_test_environment() - Cleanup old test data
- run_specialist_test()
Classes: none

### tests/test_specialist_features_v2.py
Functions: none
Classes:
- TestSpecialistFeatures
Methods: setUp(self), tearDown(self), test_end_to_end_construction_workflow(self)

### tmp_create_db.py
Functions:
- create_database()
Classes: none

### tmp_debug_assistant.py
Functions: none
Classes: none

### update_pwd.py
Functions:
- update_user()
Classes: none

### verify_data_final.py
Functions:
- get_token()
- verify_data(token)
Classes: none

### verify_email_filter.py
Functions:
- test_email_filtering()
Classes: none

### verify_full_system.py
Functions:
- verify_pages()
- verify_apis()
- test_cache_performance()
Classes: none

### verify_llm_config.py
Functions:
- test_config()
Classes: none

### verify_pages.py
Functions:
- test_pages()
Classes: none

### verify_sanitization.py
Functions:
- sanitize_filename(filename)
Classes: none

### verify_search_fix.py
Functions:
- mock_frontend_search(emails, search_term)
Classes: none

### verify_stabilization.py
Functions:
- get_token()
- test_endpoint(path, method, data)
Classes: none

### verify_system.py
Functions:
- test_endpoint(name, path, params)
- run_suite()
Classes: none

### verify_thread_tags.py
Functions: none
Classes: none

## Frontend JS Index

### temp_script.js
Functions: initAssistant, loadConversations, selectConversation, startNewChat, deleteConversation, loadHistory, sendMessage, appendMessage, showTypingStatus, removeTypingStatus, handleFile, clearUpload, exportChat
Classes: none

### temp_script_fixed.js
Functions: initAssistant, loadConversations, selectConversation, startNewChat, deleteConversation, loadHistory, sendMessage, appendMessage, showTypingStatus, removeTypingStatus, handleFile, clearUpload, exportChat
Classes: none

### ui/js/admin.js
Functions: initNavigation, loadDashboardStats, fetchUsers, fetchAuditLogs, viewUserDetail, closeDetails, toggleUserStatus, logout
Classes: none

### ui/js/api.js
Functions: none
Classes: RFQAgentAPI

### ui/js/auth.js
Functions: none
Classes: none

### ui/js/calendar_app.js
Functions: initCalendar, renderUpcomingSidebar, openEventModal, copyCurrentMeetingLink, closeEventModal, deleteCurrentEvent, openBookingModal, closeBookingModal, handleBookingSubmit
Classes: none

### ui/js/dashboard.js
Functions: initDashboard, loadDashboardData, loadMorningBrief, triggerSync, checkAgentStatus, loadPulseStats, toLocalISOString, applySessionPreset, loadSessionSummary, showNotice, loadTasks, loadPriorityList, loadPendingDrafts, loadAgendaWidget, loadHoldQueue, confirmHold, loadPulseStats, renderMissingCategories, loadProjectPulse, loadFollowups, approveFollowup, bookMeeting, openBookingModal, closeBookingModal, handleBookingSubmit, loadRecentActivity, processEmails, viewThreads, checkSystem, openSettings, showSystemStatus, showLoading, hideLoading, showSuccess, showError, showToast, closeModal, setVal, outsideClickListener
Classes: removal, from

### ui/js/drafts.js
Functions: initDrafts, loadDrafts, displayDrafts, uploadAttachment, saveDraft, sendDraft, deleteDraft, toggleAI, setAIPrompt, enhanceDraft, addEditListeners, formatDate, showLoading, hideLoading, showToast
Classes: none
