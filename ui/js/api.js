// RFQ Agent - API Client
// Handles all communication with FastAPI backend

const API_BASE_URL = 'http://localhost:8000';  // FastAPI server

class RFQAgentAPI {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    // Generic request handler
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Get system status
    async getSystemStatus() {
        return await this.request('/api/status');
    }

    // Get dashboard stats
    async getDashboardStats() {
        return await this.request('/api/dashboard/stats');
    }

    // Get all tenders
    async getTenders(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`/api/tenders?${params}`);
    }

    // Get single tender
    async getTender(tenderId) {
        return await this.request(`/api/tenders/${tenderId}`);
    }

    // Trigger email processing
    async processEmails() {
        return await this.request('/api/process-emails', {
            method: 'POST'
        });
    }

    // Get processing status
    async getAgentStatus() {
        return await this.request('/api/agent/status');
    }

    // Get recent activity
    async getRecentActivity(limit = 10) {
        return await this.request(`/api/activity?limit=${limit}`);
    }

    // Get clients
    async getClients() {
        return await this.request('/api/clients');
    }

    // Get RFI drafts
    async getRFIDrafts(tenderId = null) {
        const endpoint = tenderId
            ? `/api/rfis?tender_id=${tenderId}`
            : '/api/rfis';
        return await this.request(endpoint);
    }

    // Get documents for a tender
    async getDocuments(tenderId) {
        return await this.request(`/api/tenders/${tenderId}/documents`);
    }

    // ===== DRAFT EMAIL METHODS =====

    // Get all drafts
    async getDrafts(tenderId = null) {
        const endpoint = tenderId
            ? `/api/drafts?tender_id=${tenderId}`
            : '/api/drafts';
        return await this.request(endpoint);
    }

    // Get single draft
    async getDraft(draftId) {
        return await this.request(`/api/drafts/${draftId}`);
    }

    // Update draft
    async updateDraft(draftId, { subject, body }) {
        return await this.request(`/api/drafts/${draftId}`, {
            method: 'PUT',
            body: JSON.stringify({ subject, body })
        });
    }

    async toggleDocumentCorrect(docId) {
        return await this.request(`/api/documents/${docId}/toggle-correct`, {
            method: 'POST'
        });
    }

    async uploadDraftAttachment(draftId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseURL}/api/drafts/${draftId}/attachments`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    // Send draft
    async sendDraft(draftId) {
        return await this.request(`/api/drafts/${draftId}/send`, {
            method: 'POST'
        });
    }

    // Delete draft
    async deleteDraft(draftId) {
        return await this.request(`/api/drafts/${draftId}`, {
            method: 'DELETE'
        });
    }

    // Get emails
    async getEmails(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`/api/emails?${params}`);
    }

    // Get single email
    async getEmail(emailId) {
        return await this.request(`/api/emails/${emailId}`);
    }

    // Archive email
    async archiveEmail(emailId) {
        return await this.request(`/api/emails/${emailId}/archive`, {
            method: 'POST'
        });
    }

    // Get single document
    async getDocument(docId) {
        return await this.request(`/api/documents/${docId}`);
    }

    // Delete document
    async deleteDocument(docId) {
        return await this.request(`/api/documents/${docId}`, {
            method: 'DELETE'
        });
    }

    // Get single client
    async getClient(clientId) {
        return await this.request(`/api/clients/${clientId}`);
    }

    // AI Assistant
    async getConversations() {
        return await this.request('/api/assistant/conversations');
    }

    async createConversation(title = "New Conversation") {
        return await this.request('/api/assistant/conversations', {
            method: 'POST',
            body: JSON.stringify({ title })
        });
    }

    async deleteConversation(convId) {
        return await this.request(`/api/assistant/conversations/${convId}`, {
            method: 'DELETE'
        });
    }

    async getChatHistory(conversationId = null) {
        const endpoint = conversationId
            ? `/api/assistant/history?conversation_id=${conversationId}`
            : '/api/assistant/history';
        return await this.request(endpoint);
    }

    async askAssistant(message, context = null, conversationId = null) {
        return await this.request('/api/assistant/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                context,
                conversation_id: conversationId
            })
        });
    }

    async extractTextAssistant(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseURL}/api/assistant/extract-text`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    // OAuth status
    async getOAuthStatus() {
        return await this.request('/api/oauth/status');
    }
}

// Create singleton instance
const api = new RFQAgentAPI();

// Export for use in other files
window.RFQAgentAPI = api;
