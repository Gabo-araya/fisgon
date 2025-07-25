// JavaScript específico para el módulo crawler

class CrawlerDashboard {
    constructor() {
        this.updateInterval = 5000; // 5 segundos
        this.timers = new Map();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoUpdate();
        this.initializeWebSocket();
    }

    setupEventListeners() {
        // Botones de control de sesión
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-start-session')) {
                this.startSession(e.target.dataset.sessionId);
            }
            if (e.target.matches('.btn-stop-session')) {
                this.stopSession(e.target.dataset.sessionId);
            }
            if (e.target.matches('.btn-pause-session')) {
                this.pauseSession(e.target.dataset.sessionId);
            }
        });

        // Formulario de configuración rápida
        const quickConfigForm = document.getElementById('quickConfigForm');
        if (quickConfigForm) {
            quickConfigForm.addEventListener('submit', this.handleQuickConfig.bind(this));
        }

        // Actualización automática toggle
        const autoUpdateToggle = document.getElementById('autoUpdateToggle');
        if (autoUpdateToggle) {
            autoUpdateToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoUpdate();
                } else {
                    this.stopAutoUpdate();
                }
            });
        }
    }

    async startSession(sessionId) {
        try {
            const response = await fetch(`/crawler/sesiones/${sessionId}/iniciar/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.showNotification('Sesión iniciada exitosamente', 'success');
                this.updateSessionStatus(sessionId);
            } else {
                throw new Error('Error al iniciar sesión');
            }
        } catch (error) {
            this.showNotification('Error al iniciar sesión', 'error');
            console.error('Error:', error);
        }
    }

    async stopSession(sessionId) {
        if (!confirm('¿Estás seguro de que quieres detener esta sesión?')) {
            return;
        }

        try {
            const response = await fetch(`/crawler/sesiones/${sessionId}/detener/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.showNotification('Sesión detenida', 'success');
                this.updateSessionStatus(sessionId);
            } else {
                throw new Error('Error al detener sesión');
            }
        } catch (error) {
            this.showNotification('Error al detener sesión', 'error');
            console.error('Error:', error);
        }
    }

    async updateSessionStatus(sessionId) {
        try {
            const response = await fetch(`/crawler/api/sesiones/${sessionId}/status/`);
            if (response.ok) {
                const data = await response.json();
                this.updateSessionUI(sessionId, data);
            }
        } catch (error) {
            console.error('Error actualizando estado:', error);
        }
    }

    updateSessionUI(sessionId, data) {
        // Actualizar badge de estado
        const statusBadge = document.querySelector(`[data-session-id="${sessionId}"] .status-badge`);
        if (statusBadge) {
            statusBadge.textContent = data.status_display;
            statusBadge.className = `badge status-badge ${this.getStatusBadgeClass(data.status)}`;
        }

        // Actualizar barra de progreso
        const progressBar = document.querySelector(`[data-session-id="${sessionId}"] .progress-bar`);
        if (progressBar) {
            progressBar.style.width = `${data.progress_percentage}%`;
            progressBar.textContent = `${data.progress_percentage.toFixed(1)}%`;
        }

        // Actualizar estadísticas
        const statsContainer = document.querySelector(`[data-session-id="${sessionId}"] .session-stats`);
        if (statsContainer) {
            statsContainer.innerHTML = `
                <small class="text-muted">
                    URLs: ${data.total_urls_processed}/${data.total_urls_discovered} |
                    Archivos: ${data.total_files_found}
                </small>
            `;
        }

        // Actualizar botones según estado
        this.updateActionButtons(sessionId, data.status);
    }

    updateActionButtons(sessionId, status) {
        const container = document.querySelector(`[data-session-id="${sessionId}"] .action-buttons`);
        if (!container) return;

        let buttonsHTML = '';
        switch (status) {
            case 'pending':
                buttonsHTML = `<button class="btn btn-sm btn-start btn-start-session" data-session-id="${sessionId}">
                    <i class="bi bi-play"></i> Iniciar
                </button>`;
                break;
            case 'running':
                buttonsHTML = `
                    <button class="btn btn-sm btn-pause btn-pause-session" data-session-id="${sessionId}">
                        <i class="bi bi-pause"></i> Pausar
                    </button>
                    <button class="btn btn-sm btn-stop btn-stop-session" data-session-id="${sessionId}">
                        <i class="bi bi-stop"></i> Detener
                    </button>`;
                break;
            case 'completed':
            case 'failed':
            case 'cancelled':
                buttonsHTML = `<a href="/crawler/sesiones/${sessionId}/resultados/" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-file-text"></i> Ver Resultados
                </a>`;
                break;
        }
        container.innerHTML = buttonsHTML;
    }

    getStatusBadgeClass(status) {
        const classes = {
            'pending': 'bg-warning',
            'running': 'bg-primary',
            'paused': 'bg-info',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'cancelled': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    async handleQuickConfig(e) {
        e.preventDefault();
        const formData = new FormData(e.target);

        try {
            const response = await fetch('/crawler/sesiones/nuevo/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                this.showNotification('Sesión creada exitosamente', 'success');
                // Redirigir o actualizar la página
                window.location.reload();
            } else {
                throw new Error('Error al crear sesión');
            }
        } catch (error) {
            this.showNotification('Error al crear sesión', 'error');
            console.error('Error:', error);
        }
    }

    startAutoUpdate() {
        this.stopAutoUpdate(); // Limpiar timer existente

        this.updateTimer = setInterval(() => {
            this.updateDashboardStats();
            this.updateActiveSessions();
        }, this.updateInterval);
    }

    stopAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    async updateDashboardStats() {
        try {
            const response = await fetch('/crawler/api/dashboard/estadisticas/');
            if (response.ok) {
                const data = await response.json();
                this.updateStatsUI(data);
            }
        } catch (error) {
            console.error('Error actualizando estadísticas:', error);
        }
    }

    updateStatsUI(data) {
        // Actualizar cards de estadísticas
        const elements = {
            'totalSessions': data.total_sessions,
            'activeSessions': data.active_sessions,
            'completedSessions': data.completed_sessions,
            'totalFiles': data.total_files_found
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    async updateActiveSessions() {
        const activeSessionElements = document.querySelectorAll('[data-session-status="running"], [data-session-status="pending"]');

        for (const element of activeSessionElements) {
            const sessionId = element.dataset.sessionId;
            if (sessionId) {
                await this.updateSessionStatus(sessionId);
            }
        }
    }

    initializeWebSocket() {
        // WebSocket para actualizaciones en tiempo real
        if (window.WebSocket) {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/crawler/`;

                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket conectado');
                    this.showConnectionStatus(true);
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket desconectado');
                    this.showConnectionStatus(false);
                    // Intentar reconectar después de 5 segundos
