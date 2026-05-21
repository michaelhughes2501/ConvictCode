/* ================================================================
   SecondChance Connect — Main JS (vanilla, no jQuery)
   ================================================================ */

/* ── 1. Theme (runs before DOMContentLoaded to avoid flash) ───── */
(function () {
  const saved = localStorage.getItem('scc-theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', saved);
})();

/* ── Helpers ───────────────────────────────────────────────────── */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content ?? '';

/* ================================================================
   Main init
   ================================================================ */
document.addEventListener('DOMContentLoaded', () => {

  /* 2. Dark-mode toggle ─────────────────────────────────────── */
  const themeBtn = $('#theme-toggle');
  if (themeBtn) {
    const updateIcon = (theme) => {
      themeBtn.innerHTML = theme === 'dark'
        ? '<i class="fas fa-sun" aria-hidden="true"></i>'
        : '<i class="fas fa-moon" aria-hidden="true"></i>';
      themeBtn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    };
    updateIcon(document.documentElement.getAttribute('data-bs-theme'));
    themeBtn.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', next);
      localStorage.setItem('scc-theme', next);
      updateIcon(next);
    });
  }

  /* 3. Auto-dismiss alerts ──────────────────────────────────── */
  $$('.alert.alert-dismissible').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert?.close();
    }, 5500);
  });

  /* 4. Bootstrap tooltips ───────────────────────────────────── */
  $$('[data-bs-toggle="tooltip"]').forEach(el =>
    new bootstrap.Tooltip(el)
  );

  /* 5. Scroll-to-top button ─────────────────────────────────── */
  const scrollBtn = $('#scroll-top');
  if (scrollBtn) {
    window.addEventListener('scroll', () => {
      scrollBtn.classList.toggle('visible', window.scrollY > 280);
    }, { passive: true });
    scrollBtn.addEventListener('click', () =>
      window.scrollTo({ top: 0, behavior: 'smooth' })
    );
  }

  /* 6. IntersectionObserver animations ─────────────────────── */
  const animateEls = $$('.animate-on-scroll');
  if (animateEls.length && 'IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in-view');
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    animateEls.forEach(el => obs.observe(el));
  } else {
    animateEls.forEach(el => el.classList.add('in-view'));
  }

  /* 7. Character counters for textareas ─────────────────────── */
  $$('textarea[maxlength]').forEach(ta => {
    const max = parseInt(ta.getAttribute('maxlength'), 10);
    const counter = document.createElement('small');
    counter.className = 'char-counter text-muted d-block mt-1';
    ta.insertAdjacentElement('afterend', counter);
    const update = () => {
      const rem = max - ta.value.length;
      counter.textContent = `${rem} characters remaining`;
      counter.className = `char-counter d-block mt-1 ${rem < 20 ? (rem < 0 ? 'text-danger' : 'text-warning') : 'text-muted'}`;
    };
    ta.addEventListener('input', update);
    update();
  });

  /* 8. Like buttons (AJAX) ──────────────────────────────────── */
  $$('.like-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const userId = btn.dataset.userId;
      if (!userId) return;
      btn.disabled = true;
      try {
        const res = await fetch(`/like/${userId}`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken() },
        });
        const data = await res.json();
        if (data.mutual) {
          btn.className = 'btn btn-success btn-sm';
          btn.innerHTML = '<i class="fas fa-check me-1"></i>Matched!';
          showToast('🎉 It\'s a match! You can now message each other.', 'success');
        } else if (data.success) {
          btn.className = 'btn btn-primary btn-sm disabled';
          btn.innerHTML = '<i class="fas fa-heart me-1"></i>Liked';
        } else {
          btn.disabled = false;
          showToast(data.error || 'Something went wrong.', 'danger');
        }
      } catch {
        btn.disabled = false;
        showToast('Network error. Please try again.', 'danger');
      }
    });
  });

  /* 9. Live user search (search.html) ───────────────────────── */
  const liveSearchInput = $('#live-search-input');
  const userCards = $$('.user-result-card');
  if (liveSearchInput && userCards.length) {
    liveSearchInput.addEventListener('input', () => {
      const q = liveSearchInput.value.toLowerCase();
      userCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.closest('.user-result-col')?.classList.toggle('d-none', q.length > 0 && !text.includes(q));
      });
      const visible = userCards.filter(c => !c.closest('.user-result-col')?.classList.contains('d-none'));
      const noResults = $('#no-results-msg');
      if (noResults) noResults.classList.toggle('d-none', visible.length > 0);
    });
  }

  /* 10. Live resource filter (resources.html) ───────────────── */
  const resourceSearch = $('#resource-search');
  const resourceCards = $$('.resource-result-item');
  const categoryPills = $$('.category-pill');
  if (resourceSearch || categoryPills.length) {
    let activeCategory = 'all';
    const filterResources = () => {
      const q = (resourceSearch?.value ?? '').toLowerCase();
      resourceCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        const cat = card.dataset.category?.toLowerCase() ?? '';
        const matchQ = !q || text.includes(q);
        const matchC = activeCategory === 'all' || cat === activeCategory;
        card.classList.toggle('resource-hidden', !(matchQ && matchC));
      });
    };
    resourceSearch?.addEventListener('input', filterResources);
    categoryPills.forEach(pill => {
      pill.addEventListener('click', () => {
        categoryPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeCategory = pill.dataset.category?.toLowerCase() ?? 'all';
        filterResources();
      });
    });
  }

  /* 11. Forum category filter ───────────────────────────────── */
  const forumSearch = $('#forum-live-search');
  const forumItems = $$('.forum-item');
  if (forumSearch && forumItems.length) {
    forumSearch.addEventListener('input', () => {
      const q = forumSearch.value.toLowerCase();
      forumItems.forEach(item => {
        item.classList.toggle('d-none', q.length > 0 && !item.textContent.toLowerCase().includes(q));
      });
    });
  }

  /* 12. Chatbot widget ──────────────────────────────────────── */
  initChatbot();

  /* 13. Dashboard analytics charts ─────────────────────────── */
  if ($('#analytics-chart') || $('#activity-chart')) {
    loadAnalytics();
  }

  /* 14. Animated stat counters ──────────────────────────────── */
  $$('[data-counter]').forEach(el => animateCounter(el));

  /* 15. Messages auto-scroll ────────────────────────────────── */
  const msgContainer = $('.message-container');
  if (msgContainer) {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }
});

/* ================================================================
   Chatbot
   ================================================================ */
function initChatbot() {
  const fab = $('#chatbot-fab');
  const panel = $('#chatbot-panel');
  const closeBtn = $('#chatbot-close');
  const messagesEl = $('#chatbot-messages');
  const input = $('#chatbot-input');
  const sendBtn = $('#chatbot-send');
  const quickBtns = $$('.chatbot-quick-btn');

  if (!fab || !panel) return;

  const toggle = () => panel.classList.toggle('open');
  fab.addEventListener('click', () => {
    toggle();
    if (panel.classList.contains('open') && messagesEl.children.length === 0) {
      appendBotMsg('Hi! I\'m your SecondChance Connect assistant. I can help with housing, jobs, legal aid, mental health resources, and navigating this platform. What do you need?');
    }
    input?.focus();
  });
  closeBtn?.addEventListener('click', () => panel.classList.remove('open'));

  const sendMessage = async () => {
    const text = input?.value.trim();
    if (!text) return;
    appendUserMsg(text);
    input.value = '';
    const typing = appendTyping();
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
        },
        body: JSON.stringify({ message: text }),
      });
      typing.remove();
      if (res.ok) {
        const data = await res.json();
        appendBotMsg(data.reply || 'Sorry, I didn\'t get a response.');
      } else {
        appendBotMsg('I\'m having trouble connecting right now. Please try again.');
      }
    } catch {
      typing.remove();
      appendBotMsg('Network error. Please check your connection and try again.');
    }
  };

  sendBtn?.addEventListener('click', sendMessage);
  input?.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

  quickBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (input) input.value = btn.textContent.trim();
      sendMessage();
    });
  });

  function appendUserMsg(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg user fade-in-up';
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollChat();
  }
  function appendBotMsg(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg bot fade-in-up';
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollChat();
  }
  function appendTyping() {
    const div = document.createElement('div');
    div.className = 'chat-msg bot chat-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(div);
    scrollChat();
    return div;
  }
  function scrollChat() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

/* ================================================================
   Analytics
   ================================================================ */
async function loadAnalytics() {
  try {
    const res = await fetch('/api/analytics');
    if (!res.ok) return;
    const data = await res.json();

    // Populate counter elements
    const mapping = {
      'stat-users':    data.total_users,
      'stat-messages': data.total_messages,
      'stat-posts':    data.total_posts,
      'stat-matches':  data.total_matches,
    };
    Object.entries(mapping).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) { el.dataset.counter = val; animateCounter(el); }
    });

    // Main analytics bar chart
    const ctx = document.getElementById('analytics-chart');
    if (ctx && window.Chart) {
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['Members', 'Messages', 'Posts', 'Matches'],
          datasets: [{
            label: 'Platform Stats',
            data: [data.total_users, data.total_messages, data.total_posts, data.total_matches],
            backgroundColor: [
              'rgba(37,99,235,.75)',
              'rgba(124,58,237,.75)',
              'rgba(16,185,129,.75)',
              'rgba(245,158,11,.75)',
            ],
            borderRadius: 8,
            borderSkipped: false,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y.toLocaleString()}` } },
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(128,128,128,.12)' },
              ticks: { precision: 0 },
            },
            x: { grid: { display: false } },
          },
        },
      });
    }

    // Activity this week doughnut
    const ctx2 = document.getElementById('activity-chart');
    if (ctx2 && window.Chart) {
      new Chart(ctx2, {
        type: 'doughnut',
        data: {
          labels: ['New Members', 'Messages', 'Posts'],
          datasets: [{
            data: [data.new_users_week, data.messages_week, data.posts_week],
            backgroundColor: ['rgba(37,99,235,.8)', 'rgba(124,58,237,.8)', 'rgba(16,185,129,.8)'],
            borderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          plugins: {
            legend: { position: 'bottom', labels: { padding: 16 } },
          },
        },
      });
    }
  } catch { /* silent */ }
}

/* ================================================================
   Utilities
   ================================================================ */
function animateCounter(el) {
  const target = parseInt(el.dataset.counter ?? el.textContent, 10);
  if (isNaN(target)) return;
  const duration = 1200;
  const start = performance.now();
  const tick = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(eased * target).toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container') || (() => {
    const div = document.createElement('div');
    div.id = 'toast-container';
    div.className = 'toast-container position-fixed bottom-0 start-50 translate-middle-x p-3';
    div.style.zIndex = '9999';
    document.body.appendChild(div);
    return div;
  })();

  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${type} border-0 show`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay: 4000 });
  bsToast.show();
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}
