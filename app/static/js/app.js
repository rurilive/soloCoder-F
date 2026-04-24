const API_BASE = '/api';

let currentUser = null;

async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return;
    }
    
    return response;
}

async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
    });
    
    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify({
            id: data.user_id,
            username: data.username,
            role: data.role,
            real_name: data.real_name
        }));
        return { success: true };
    } else {
        const error = await response.json();
        return { success: false, message: error.detail };
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
        return JSON.parse(userStr);
    }
    return null;
}

function isAdmin() {
    const user = getCurrentUser();
    return user && user.role === 'admin';
}

function isTeacher() {
    const user = getCurrentUser();
    return user && (user.role === 'teacher' || user.role === 'admin');
}

function isStudent() {
    const user = getCurrentUser();
    return user && user.role === 'student';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

function showModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getDifficultyText(difficulty) {
    const map = {
        'easy': '简单',
        'medium': '中等',
        'hard': '困难'
    };
    return map[difficulty] || difficulty;
}

function getDifficultyTag(difficulty) {
    return `tag-${difficulty}`;
}

function getQuestionTypeText(type) {
    const map = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'true_false': '判断题',
        'fill_blank': '填空题',
        'short_answer': '简答题',
        'essay': '论述题'
    };
    return map[type] || type;
}

function getExamStatusText(status) {
    const map = {
        'draft': '草稿',
        'published': '已发布',
        'started': '进行中',
        'ended': '已结束'
    };
    return map[status] || status;
}

function getMonitorEventTypeText(type) {
    const map = {
        'window_blur': '窗口失焦',
        'window_focus': '窗口获得焦点',
        'visibility_hidden': '页面隐藏',
        'visibility_visible': '页面可见',
        'fullscreen_enter': '进入全屏',
        'fullscreen_exit': '退出全屏',
        'copy_detected': '检测到复制',
        'paste_detected': '检测到粘贴',
        'tab_switch': '标签页切换',
        'mouse_leave': '鼠标离开'
    };
    return map[type] || type;
}

function initNavbar() {
    const user = getCurrentUser();
    if (!user) return;
    
    const userInfo = document.getElementById('userInfo');
    if (userInfo) {
        userInfo.innerHTML = `
            <span>${user.real_name || user.username}</span>
            <span class="tag ${isAdmin() ? 'tag-hard' : isTeacher() ? 'tag-medium' : 'tag-easy'}">
                ${isAdmin() ? '管理员' : isTeacher() ? '教师' : '学生'}
            </span>
            <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="logout()">退出</button>
        `;
    }
    
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === window.location.pathname) {
            link.classList.add('active');
        }
    });
    
    const teacherLinks = document.querySelectorAll('[data-role="teacher"]');
    const adminLinks = document.querySelectorAll('[data-role="admin"]');
    const studentLinks = document.querySelectorAll('[data-role="student"]');
    
    teacherLinks.forEach(link => {
        if (!isTeacher()) {
            link.style.display = 'none';
        }
    });
    
    adminLinks.forEach(link => {
        if (!isAdmin()) {
            link.style.display = 'none';
        }
    });
    
    studentLinks.forEach(link => {
        if (!isStudent()) {
            link.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
        checkAuth();
    }
    
    initNavbar();
    
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.remove('show');
            }
        });
    });
    
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('show');
        }
    });
});
