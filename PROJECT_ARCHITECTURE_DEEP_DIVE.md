# 🚀 Executive RFQ Assistant: Architecture Deep Dive

This document provides a comprehensive breakdown of the project's structure, explaining the purpose and function of every directory and critical file. This is designed for developers to understand how the Multi-Agent system, Backend API, and Frontend UI interact.

---

## 📂 1. `agents/` - The Intelligence Hub
This is the "Brain" of the system. It contains the logic for AI agents that process RFQs (Request for Quotations) and analyze writing styles.

*   **`rfq_agent/`**: The core multi-agent system.
    *   **`orchestrator.py`**: The "Manager" agent. It receives a task and decides which sub-agent (Researcher, Auditor, etc.) should handle it.
    *   **`researcher_agent.py`**: Extracts data from emails and documents. It finds technical specifications and deadlines.
    *   **`auditor_agent.py`**: Checks extracted data for accuracy. It ensures no wrong information is sent to the client.
    *   **`style_agent.py`**: Analyzes the user's past emails to learn their "Voice" (professional, friendly, concise) so the AI can mimic it.
*   **`executive/`**: Higher-level agents.
    *   **`style_analyzer.py`**: A specialized agent that looks at thousands of words to create a "Writing Style Guide" for the user.

---

## 📂 2. `api/` - The Communication Engine
This folder contains the FastAPI backend. It serves as the bridge between the AI agents and the Web UI.

*   **`main.py`**: The **Entry Point**. This file starts the server, connects all the "Routes" (endpoints), and handles system startup/shutdown logic.
*   **`routes/`**: Each file here handles a specific feature:
    *   **`auth.py`**: Login, Registration, and Session management.
    *   **`emails.py`**: Gmail and Outlook integration logic. Handles OAuth connections and fetching messages.
    *   **`threads.py`**: Groups related emails into "Conversations" or "Threads".
    *   **`drafts.py`**: Manages the AI-generated email drafts before they are sent.
    *   **`admin.py`**: Provides stats and user management for the Admin Portal.
*   **`tasks.py`**: Handles **Background Jobs**. For example, syncing 500 emails happens here so the UI doesn't freeze.

---

## 📂 3. `auth/` - The Security Gate
Handles everything related to safety and permissions.

*   **`security.py`**: Contains the logic for hashing passwords (using `bcrypt`) and creating JWT tokens (the digital keys used for login).
*   **`dependencies.py`**: Functions that check "Is this user logged in?" before allowing access to a page.
*   **`audit.py`**: Logs every important action (who logged in, when, from which IP) for security tracking.

---

## 📂 4. `config/` - The Settings Room
Stores global settings and connection details.

*   **`database.py`**: Connects the Python code to the PostgreSQL database.
*   **`oauth_config.py`** & **`gmail_oauth_config.py`**: Stores the "Client IDs" and "Secrets" for Google and Microsoft login.

---

## 📂 5. `database/` - The Data Foundation
*   **`models.py`**: Defines how data is stored. For example, a `User` has an email, a password, and a role. An `Email` has a subject, a sender, and a body.
*   **`setup_database.py`**: A script that creates the tables in PostgreSQL automatically.

---

## 📂 6. `ui/` - The User Interface (Frontend)
What the user sees in their browser.

*   **`css/`**: Styling (Colors, Fonts, Layouts).
*   **`js/`**: The logic that runs in the browser.
    *   **`api.js`**: The main script that talks to the Backend. Every time a button is clicked, this file sends a request to the server.
    *   **`auth.js`**: Handles the login/logout flow on the screen.
    *   **`dashboard.js`**: Manages the complex charts and lists on the main page.
*   **HTML Files**: The actual pages (Login, Dashboard, Settings, etc.).

---

## 📂 7. `storage/` & `temp/`
*   **`storage/`**: Persistent data like uploaded PDF files, extracted text, and AI-generated reports.
*   **`temp/`**: Temporary files used during processing (deleted after use).

---

## 📄 Key Root Files
*   **`.env`**: The most important file for deployment. It contains "Secret Keys", Database passwords, and Port numbers. **Never share this file!**
*   **`requirements.txt`**: A list of all Python libraries (FastAPI, SQLAlchemy, OpenAI, etc.) needed to run the project.
*   **`venv/`**: The "Virtual Environment". It's a private box that holds all the libraries so they don't mess up the rest of the computer.

---

## 🔄 How it all works together (The Flow)
1.  **User Logins**: `ui/login.html` sends data to `api/routes/auth.py`.
2.  **Auth Check**: `auth/security.py` verifies the password against the database.
3.  **Fetch Emails**: User clicks "Sync". `api/routes/emails.py` talks to Google/Microsoft.
4.  **AI Analysis**: `api/tasks.py` triggers `agents/rfq_agent/researcher_agent.py` to read the emails.
5.  **Display**: The data is saved in the DB, and `ui/js/dashboard.js` shows it on the screen.

---
*Created for: Executive RFQ Assistant Team*
