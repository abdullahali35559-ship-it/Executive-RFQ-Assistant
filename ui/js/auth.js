const TOKEN_KEY = 'rfq_agent_token';

const Auth = {
    setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    },
    getToken() {
        return localStorage.getItem(TOKEN_KEY);
    },
    logout() {
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = 'login.html';
    },
    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp > Date.now() / 1000;
        } catch (e) { return false; }
    },
    checkAuth() {
        if (!this.isAuthenticated() && !window.location.pathname.includes('login.html')) {
            window.location.href = 'login.html';
        }
    }
};

Auth.checkAuth();
window.Auth = Auth;
