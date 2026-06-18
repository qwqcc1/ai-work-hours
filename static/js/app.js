// ===== Dark Mode =====
const THEME_KEY = 'ai-workhours-theme';
function getTheme() { return localStorage.getItem(THEME_KEY) || 'light'; }
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.innerHTML = theme === 'dark'
            ? '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 2v-.5M7 12.5V12M2 7h-.5M12.5 7H12M3.4 3.4l-.3-.3M10.9 10.9l.3.3M3.4 10.6l-.3.3M10.9 3.1l.3-.3"/><path d="M10.2 7A3.2 3.2 0 117 3.8a3.5 3.5 0 003.2 3.2z"/></svg>'
            : '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><circle cx="7" cy="7" r="3.5"/><line x1="7" y1="1" x2="7" y2="2"/><line x1="7" y1="12" x2="7" y2="13"/><line x1="1" y1="7" x2="2" y2="7"/><line x1="12" y1="7" x2="13" y2="7"/></svg>';
    }
}
function toggleTheme() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
}
setTheme(getTheme());

// ===== Toast =====
function showToast(msg, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    var icons = {success: '✓', error: '✕', info: 'ℹ', warning: '⚠'};
    toast.innerHTML = '<span>' + (icons[type] || '') + '</span> ' + msg;
    toast.onclick = function() { removeToast(toast); };
    container.appendChild(toast);
    setTimeout(function() { removeToast(toast); }, 3500);
}
function removeToast(toast) {
    toast.classList.add('toast-out');
    setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 260);
}

// ===== API Helpers =====
function getToken() { return localStorage.getItem('token'); }

function authHeaders() {
    return { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' };
}

async function apiFetch(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign(authHeaders(), opts.headers || {});
    var res = await fetch(url, opts);
    if (res.status === 401) { localStorage.clear(); window.location.href = '/'; return res; }
    return res;
}

async function apiGet(url) {
    var res = await apiFetch(url, {});
    return await res.json();
}

async function apiPost(url, data) {
    var res = await apiFetch(url, { method: 'POST', body: JSON.stringify(data) });
    if (res.status >= 400) { var err = await res.json(); throw new Error(err.detail || '请求失败'); }
    return await res.json();
}

async function apiPostDownload(url, data) {
    return await apiFetch(url, { method: 'POST', body: JSON.stringify(data) });
}

async function apiPut(url, data) {
    var res = await apiFetch(url, { method: 'PUT', body: JSON.stringify(data) });
    if (res.status >= 400) { var err = await res.json(); throw new Error(err.detail || '请求失败'); }
    return await res.json();
}

async function apiDelete(url) {
    var res = await apiFetch(url, { method: 'DELETE' });
    if (res.status >= 400) { var err = await res.json(); throw new Error(err.detail || '请求失败'); }
    return await res.json();
}

// ===== Modal =====
var _activeModalOverlay = null;

function showModal(title, bodyHtml, footerHtml) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', title);
    overlay.innerHTML = '<div class="modal"><h3>' + title + '</h3><div class="modal-body">' + bodyHtml + '</div>' + (footerHtml ? '<div class="modal-footer">' + footerHtml + '</div>' : '') + '</div>';
    overlay.onclick = function(e) { if (e.target === overlay) closeModal(overlay); };
    document.body.appendChild(overlay);
    _activeModalOverlay = overlay;
    // Focus first input
    var firstInput = overlay.querySelector('input:not([disabled]), select, textarea');
    if (firstInput) setTimeout(function() { firstInput.focus(); }, 100);
    return overlay;
}
function closeModal(overlay) {
    if (!overlay) overlay = _activeModalOverlay;
    if (!overlay) return;
    overlay.style.opacity = '0';
    _activeModalOverlay = null;
    setTimeout(function() { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }, 200);
}

// Escape key to close modal
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && _activeModalOverlay) {
        closeModal();
    }
});

// ===== Nav =====
function initNav() {
    var token = getToken();
    var isAuthPage = window.location.pathname === '/' || window.location.pathname === '/register';

    // 未登录用户访问需认证页面 → 跳转登录页
    if (!token && !isAuthPage) { window.location.href = '/'; return; }
    // 登录/注册页始终不显示侧边栏
    if (isAuthPage) { return; }

    if (token) {
        var sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.style.display = 'flex';
        document.body.classList.add('has-sidebar');

        var u = JSON.parse(localStorage.getItem('user') || '{}');
        var displayName = u.real_name || u.username || '';
        var nameEl = document.getElementById('sidebar-user-name');
        if (nameEl) nameEl.textContent = displayName;
        var roleEl = document.getElementById('sidebar-user-role');
        if (roleEl) roleEl.textContent = u.role === 'admin' ? '管理员' : '成员';
        var avatarEl = document.getElementById('sidebar-user-avatar');
        if (avatarEl && displayName) avatarEl.textContent = displayName.charAt(0).toUpperCase();

        // Update theme icon
        setTheme(getTheme());

        if (u.role === 'admin') {
            var usersLink = document.getElementById('sidebar-link-users');
            if (usersLink) usersLink.style.display = 'flex';
            var projectsLink = document.getElementById('sidebar-link-projects');
            if (projectsLink) projectsLink.style.display = 'flex';
        }

        highlightCurrentNav();
        autoExpandCurrentSection();
    }
}

function highlightCurrentNav() {
    var path = window.location.pathname;
    var hash = window.location.hash;
    // Direct sidebar links
    var links = document.querySelectorAll('.sidebar-link');
    links.forEach(function(a) { a.classList.remove('active'); a.removeAttribute('aria-current'); });

    // 优先精准匹配：路径 + hash 完全一致
    var matched = false;
    links.forEach(function(a) {
        var href = a.getAttribute('href');
        if (!href) return;
        var parts = href.split('#');
        var linkPath = parts[0];
        var linkHash = parts[1] ? '#' + parts[1] : '';
        if (path.startsWith(linkPath) && linkHash === hash) {
            a.classList.add('active');
            a.setAttribute('aria-current', 'page');
            matched = true;
        }
    });
    // 无精准匹配时回退到路径匹配（仅匹配无 hash 的链接）
    if (!matched) {
        links.forEach(function(a) {
            var href = a.getAttribute('href');
            if (!href || href.indexOf('#') >= 0) return;
            if (path.startsWith(href)) { a.classList.add('active'); a.setAttribute('aria-current', 'page'); }
        });
    }
    // /admin 无 hash 时默认高亮用户管理
    if (!matched && path === '/admin') {
        var defaultLink = document.querySelector('.sidebar-link[href="/admin#users"]');
        if (defaultLink) { defaultLink.classList.add('active'); defaultLink.setAttribute('aria-current', 'page'); }
    }
    // Sub-items
    var subItems = document.querySelectorAll('.sidebar-subitem');
    subItems.forEach(function(a) {
        a.classList.remove('active');
        var href = a.getAttribute('href');
        if (href && path.startsWith(href.split('#')[0])) {
            a.classList.add('active');
        }
    });
}

function autoExpandCurrentSection() {
    var path = window.location.pathname;
    var sections = document.querySelectorAll('.sidebar-section');
    sections.forEach(function(section) {
        var activeSub = section.querySelector('.sidebar-subitem.active');
        if (activeSub) section.classList.add('open');
    });
}

function logout() {
    var token = getToken();
    if (token) { fetch('/api/logout', { method: 'POST', headers: { 'Authorization': 'Bearer ' + token } }).catch(function(){}); }
    localStorage.clear(); window.location.href = '/';
}

// ===== Settings =====
function openSettings() {
    var u = JSON.parse(localStorage.getItem('user') || '{}');
    var bodyHtml =
        '<div class="form-group" style="margin-bottom:14px;">' +
        '<label>用户名</label><input type="text" value="' + (u.username || '') + '" disabled>' +
        '</div>' +
        '<div class="form-group" style="margin-bottom:14px;">' +
        '<label>真实姓名</label><input type="text" id="set-real-name" value="' + (u.real_name || '') + '">' +
        '</div>' +
        '<div class="form-group" style="margin-bottom:14px;">' +
        '<label>手机号</label><input type="text" id="set-phone" value="' + (u.phone || '') + '">' +
        '</div>' +
        '<div class="form-group" style="margin-bottom:14px;">' +
        '<label>新密码 <span style="font-weight:400;color:var(--text-tertiary);">(留空不修改)</span></label>' +
        '<input type="password" id="set-password" placeholder="至少6位">' +
        '</div>';
    showModal('个人设置', bodyHtml,
        '<button class="btn btn-ghost" onclick="closeModal()">取消</button>' +
        '<button class="btn btn-primary" onclick="saveSettings()">保存</button>'
    );
}

async function saveSettings() {
    var data = {
        real_name: document.getElementById('set-real-name').value,
        phone: document.getElementById('set-phone').value
    };
    var pwd = document.getElementById('set-password').value;
    if (pwd) data.password = pwd;
    try {
        var res = await apiPut('/api/profile', data);
        var u = JSON.parse(localStorage.getItem('user') || '{}');
        u.real_name = res.real_name; u.phone = res.phone;
        localStorage.setItem('user', JSON.stringify(u));
        document.getElementById('sidebar-user-name').textContent = u.real_name || u.username || '';
        var avEl = document.getElementById('sidebar-user-avatar');
        if (avEl && (u.real_name || u.username)) avEl.textContent = (u.real_name || u.username).charAt(0).toUpperCase();
        closeModal();
        showToast('设置已保存', 'success');
    } catch(e) {
        showToast('保存失败: ' + e.message, 'error');
    }
}

// ===== Keyboard Shortcuts =====
document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); toggleTheme(); }
    if ((e.metaKey || e.ctrlKey) && e.key === '1') { e.preventDefault(); window.location.href = '/dashboard'; }
    if ((e.metaKey || e.ctrlKey) && e.key === '2') { e.preventDefault(); window.location.href = '/entry'; }
    if ((e.metaKey || e.ctrlKey) && e.key === '3') { e.preventDefault(); window.location.href = '/summary'; }
});

// ===== Date Helpers =====
function fmtDate(d) { return d.toISOString().split('T')[0]; }
function todayStr() { return fmtDate(new Date()); }
function weekStartStr() { var d = new Date(); d.setDate(d.getDate() - d.getDay() + 1); return fmtDate(d); }
function monthStartStr() { return fmtDate(new Date(new Date().getFullYear(), new Date().getMonth(), 1)); }

// ===== Sidebar =====
function initSidebar() {
    // Accordion toggle for sidebar sections
    document.querySelectorAll('.sidebar-section-header').forEach(function(header) {
        header.setAttribute('role', 'button');
        header.setAttribute('tabindex', '0');
        var section = header.closest('.sidebar-section');
        if (section) header.setAttribute('aria-expanded', section.classList.contains('open') ? 'true' : 'false');

        header.addEventListener('click', function() {
            var section = header.closest('.sidebar-section');
            if (!section) return;
            // Accordion: close other open sections
            document.querySelectorAll('.sidebar-section.open').forEach(function(other) {
                if (other !== section) { other.classList.remove('open'); other.querySelector('.sidebar-section-header').setAttribute('aria-expanded', 'false'); }
            });
            var isOpen = section.classList.toggle('open');
            header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
        header.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); header.click(); }
        });
    });

    // User dropdown toggle (click-based)
    var userSection = document.getElementById('sidebar-user');
    if (userSection) {
        userSection.addEventListener('click', function(e) {
            e.stopPropagation();
            userSection.classList.toggle('active');
        });
        document.addEventListener('click', function(e) {
            if (!userSection.contains(e.target)) {
                userSection.classList.remove('active');
            }
        });
    }

    // Mobile sidebar toggle
    var toggleBtn = document.getElementById('sidebar-toggle');
    var sidebarEl = document.getElementById('sidebar');
    var backdrop = document.getElementById('sidebar-backdrop');

    function openSidebar() {
        if (sidebarEl) sidebarEl.classList.add('open');
        if (backdrop) backdrop.classList.add('show');
    }
    function closeSidebar() {
        if (sidebarEl) sidebarEl.classList.remove('open');
        if (backdrop) backdrop.classList.remove('show');
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (sidebarEl && sidebarEl.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }
    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }
    // Escape to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebarEl && sidebarEl.classList.contains('open')) {
            closeSidebar();
        }
    });
    // Close sidebar when clicking a link on mobile
    if (sidebarEl) {
        sidebarEl.querySelectorAll('a[href]').forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    setTimeout(closeSidebar, 150);
                }
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initNav();
    initSidebar();
});

// hash 变化时重新高亮菜单（同页 hash 切换）
window.addEventListener('hashchange', function() {
    highlightCurrentNav();
});
