// JavaScript для Telegram Mini App

class BeerTapsApp {
    constructor() {
        this.user = null;
        this.isAdmin = false;
        this.tg = window.Telegram.WebApp;
        
        this.init();
    }

    async init() {
        // Инициализация Telegram WebApp
        this.tg.ready();
        this.tg.expand();
        
        // Аутентификация
        await this.authenticate();
        
        // Настройка интерфейса
        this.setupUI();
        
        // Загрузка данных
        await this.loadTaps();
        
        // Настройка обработчиков событий
        this.setupEventHandlers();
    }

    async authenticate() {
        try {
            const response = await fetch('/api/auth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.tg.initDataUnsafe)
            });

            if (response.ok) {
                const data = await response.json();
                this.user = data.user;
                this.isAdmin = data.user.is_admin;
                
                this.updateUserInfo();
                this.updatePermissions();
            } else {
                this.showNotification('Ошибка аутентификации', 'error');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            this.showNotification('Ошибка подключения', 'error');
        }
    }

    updateUserInfo() {
        const userInfo = document.getElementById('user-info');
        if (this.user && userInfo) {
            userInfo.textContent = `${this.user.first_name} ${this.user.last_name || ''}`.trim();
        }
    }

    updatePermissions() {
        const userRole = document.getElementById('user-role');
        const adminActions = document.getElementById('admin-actions');
        const addTab = document.getElementById('add-tab');
        const settingsTab = document.getElementById('settings-tab');

        if (this.isAdmin) {
            if (userRole) userRole.textContent = 'Администратор';
            if (adminActions) adminActions.style.display = 'block';
            if (addTab) addTab.style.display = 'block';
            if (settingsTab) settingsTab.style.display = 'block';
        } else {
            if (userRole) userRole.textContent = 'Пользователь';
            if (adminActions) adminActions.style.display = 'none';
            if (addTab) addTab.style.display = 'none';
            if (settingsTab) settingsTab.style.display = 'none';
        }
    }

    setupUI() {
        // Настройка темы Telegram
        document.body.style.backgroundColor = this.tg.themeParams.bg_color || '#ffffff';
        document.body.style.color = this.tg.themeParams.text_color || '#000000';
    }

    setupEventHandlers() {
        // Навигация по вкладкам
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Форма добавления пива
        const addForm = document.getElementById('add-beer-form');
        if (addForm) {
            addForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addBeer();
            });
        }
    }

    switchTab(tabName) {
        // Обновляем активную вкладку
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Показываем соответствующее содержимое
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // Загружаем данные при необходимости
        if (tabName === 'taps') {
            this.loadTaps();
        }
    }

    async loadTaps() {
        const tapsList = document.getElementById('taps-list');
        if (!tapsList) return;

        tapsList.innerHTML = '<div class="loading">Загрузка кранов...</div>';

        try {
            const response = await fetch('/api/taps');
            const data = await response.json();

            if (data.success) {
                this.renderTaps(data.taps);
            } else {
                this.showNotification('Ошибка загрузки кранов', 'error');
                tapsList.innerHTML = '<div class="empty-state"><h3>Ошибка загрузки</h3><p>Не удалось загрузить список кранов</p></div>';
            }
        } catch (error) {
            console.error('Error loading taps:', error);
            this.showNotification('Ошибка подключения', 'error');
            tapsList.innerHTML = '<div class="empty-state"><h3>Ошибка подключения</h3><p>Проверьте подключение к интернету</p></div>';
        }
    }

    renderTaps(taps) {
        const tapsList = document.getElementById('taps-list');
        
        if (taps.length === 0) {
            tapsList.innerHTML = '<div class="empty-state"><h3>Краны пусты</h3><p>Добавьте пиво в краны для начала работы</p></div>';
            return;
        }

        tapsList.innerHTML = taps.map(tap => `
            <div class="tap-card">
                <div class="tap-header">
                    <div class="tap-number">Кран ${tap.tap_position}</div>
                    ${this.isAdmin ? `
                        <div class="tap-actions">
                            <button class="btn btn-sm btn-secondary" onclick="app.editBeer(${tap.tap_position})">Редактировать</button>
                        </div>
                    ` : ''}
                </div>
                <div class="tap-info">
                    <div class="info-row">
                        <span class="info-label">Пивоварня:</span>
                        <span class="info-value">${tap.brewery}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Название:</span>
                        <span class="info-value">${tap.beer_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Стиль:</span>
                        <span class="info-value">${tap.beer_style}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Цена:</span>
                        <span class="info-value price">${tap.price_per_liter.toFixed(2)} руб/л</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async addBeer() {
        const form = document.getElementById('add-beer-form');
        const formData = new FormData(form);
        
        const data = {
            tap_position: parseInt(formData.get('tap_position')),
            brewery: formData.get('brewery'),
            beer_name: formData.get('beer_name'),
            beer_style: formData.get('beer_style'),
            price_per_liter: parseFloat(formData.get('price_per_liter')),
            user_id: this.user.id
        };

        try {
            const response = await fetch('/api/tap', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                form.reset();
                await this.loadTaps();
                this.switchTab('taps');
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            console.error('Error adding beer:', error);
            this.showNotification('Ошибка при добавлении пива', 'error');
        }
    }

    async editBeer(tapPosition) {
        try {
            const response = await fetch(`/api/tap/${tapPosition}`);
            const data = await response.json();

            if (data.success) {
                const tap = data.tap;
                
                // Заполняем форму редактирования
                document.getElementById('edit-tap-position').value = tap.tap_position;
                document.getElementById('edit-brewery').value = tap.brewery;
                document.getElementById('edit-beer-name').value = tap.beer_name;
                document.getElementById('edit-beer-style').value = tap.beer_style;
                document.getElementById('edit-price-per-liter').value = tap.price_per_liter;

                // Показываем модальное окно
                const modal = new bootstrap.Modal(document.getElementById('editModal'));
                modal.show();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading tap:', error);
            this.showNotification('Ошибка загрузки данных крана', 'error');
        }
    }

    async updateBeer() {
        const tapPosition = document.getElementById('edit-tap-position').value;
        
        const data = {
            brewery: document.getElementById('edit-brewery').value,
            beer_name: document.getElementById('edit-beer-name').value,
            beer_style: document.getElementById('edit-beer-style').value,
            price_per_liter: parseFloat(document.getElementById('edit-price-per-liter').value),
            user_id: this.user.id
        };

        try {
            const response = await fetch(`/api/tap/${tapPosition}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
                await this.loadTaps();
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            console.error('Error updating beer:', error);
            this.showNotification('Ошибка при обновлении пива', 'error');
        }
    }

    async deleteBeer() {
        const tapPosition = document.getElementById('edit-tap-position').value;
        
        if (!confirm('Вы уверены, что хотите удалить пиво из этого крана?')) {
            return;
        }

        const data = {
            user_id: this.user.id
        };

        try {
            const response = await fetch(`/api/tap/${tapPosition}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
                await this.loadTaps();
            } else {
                this.showNotification(result.error, 'error');
            }
        } catch (error) {
            console.error('Error deleting beer:', error);
            this.showNotification('Ошибка при удалении пива', 'error');
        }
    }

    async refreshData() {
        await this.loadTaps();
        this.showNotification('Данные обновлены', 'success');
    }

    async clearAllTaps() {
        if (!confirm('Вы уверены, что хотите очистить все краны? Это действие нельзя отменить.')) {
            return;
        }

        // Здесь можно добавить API для очистки всех кранов
        this.showNotification('Функция очистки всех кранов в разработке', 'info');
    }

    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        notifications.appendChild(notification);

        // Удаляем уведомление через 3 секунды
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
}

// Глобальные функции для вызова из HTML
let app;

function refreshData() {
    if (app) app.refreshData();
}

function clearAllTaps() {
    if (app) app.clearAllTaps();
}

function updateBeer() {
    if (app) app.updateBeer();
}

function deleteBeer() {
    if (app) app.deleteBeer();
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    app = new BeerTapsApp();
});
