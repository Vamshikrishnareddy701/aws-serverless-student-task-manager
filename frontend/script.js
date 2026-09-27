/**
 * AWS Serverless Student Task Manager - Frontend Controller
 * Pure Vanilla JavaScript ES6+
 */

document.addEventListener('DOMContentLoaded', () => {

  // Local Flask API endpoint vs Amazon API Gateway production endpoint
  // Replace AWS_API_GATEWAY_URL with your deployed API Gateway Invoke URL when hosting on S3
  // Example: 'https://abc123xyz.execute-api.us-east-1.amazonaws.com/api'
  const AWS_API_GATEWAY_URL = ''; 

  const API_BASE_URL = AWS_API_GATEWAY_URL || (
    (window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1'))
      ? '/api'
      : 'http://localhost:5000/api'
  );


  const state = {
    tasks: [],
    stats: {
      total_tasks: 0,
      pending_tasks: 0,
      completed_tasks: 0,
      high_priority_tasks: 0,
      completion_rate: 0
    },
    activeTab: 'all',
    searchQuery: '',
    priorityFilter: 'all',
    sortBy: 'default',
    theme: localStorage.getItem('task_manager_theme') || 'dark',
    taskToDelete: null,
    taskToEdit: null
  };

  // ---------------------------------------------------------------------------
  // 2. DOM Elements Selection
  // ---------------------------------------------------------------------------
  const elements = {
    // Theme & Health
    themeToggleBtn: document.getElementById('theme-toggle'),
    serverStatusDot: document.querySelector('.status-dot'),
    statusText: document.getElementById('status-text'),

    // Statistics
    statTotal: document.getElementById('stat-total'),
    statPending: document.getElementById('stat-pending'),
    statCompleted: document.getElementById('stat-completed'),
    statHigh: document.getElementById('stat-high'),
    statPct: document.getElementById('stat-pct'),
    progressFill: document.getElementById('progress-fill'),

    // Task Creation Form
    taskForm: document.getElementById('task-form'),
    taskTitle: document.getElementById('task-title'),
    taskDesc: document.getElementById('task-desc'),
    taskPriority: document.getElementById('task-priority'),
    taskCategory: document.getElementById('task-category'),
    taskDueDate: document.getElementById('task-duedate'),
    titleError: document.getElementById('title-error'),
    resetFormBtn: document.getElementById('reset-form-btn'),

    // Search & Filters
    searchInput: document.getElementById('search-input'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    priorityFilter: document.getElementById('priority-filter'),
    sortSelect: document.getElementById('sort-select'),

    // Container & States
    tasksContainer: document.getElementById('tasks-container'),
    loadingSpinner: document.getElementById('loading-spinner'),
    emptyState: document.getElementById('empty-state'),
    seedBtn: document.getElementById('seed-btn'),

    // Edit Modal
    editModalOverlay: document.getElementById('edit-modal-overlay'),
    editTaskForm: document.getElementById('edit-task-form'),
    editTaskId: document.getElementById('edit-task-id'),
    editTaskTitle: document.getElementById('edit-task-title'),
    editTaskDesc: document.getElementById('edit-task-desc'),
    editTaskPriority: document.getElementById('edit-task-priority'),
    editTaskCategory: document.getElementById('edit-task-category'),
    editTaskDueDate: document.getElementById('edit-task-duedate'),
    editTaskCompleted: document.getElementById('edit-task-completed'),
    closeEditModalBtn: document.getElementById('close-edit-modal'),
    cancelEditBtn: document.getElementById('cancel-edit-btn'),

    // Delete Modal
    deleteModalOverlay: document.getElementById('delete-modal-overlay'),
    deleteTaskTitleText: document.getElementById('delete-task-title-text'),
    closeDeleteModalBtn: document.getElementById('close-delete-modal'),
    cancelDeleteBtn: document.getElementById('cancel-delete-btn'),
    confirmDeleteBtn: document.getElementById('confirm-delete-btn'),

    // Toast Container
    toastContainer: document.getElementById('toast-container')
  };

  // Initialize Theme
  document.documentElement.setAttribute('data-theme', state.theme);
  updateThemeIcon();

  // ---------------------------------------------------------------------------
  // 3. API Communication Layer
  // ---------------------------------------------------------------------------
  
  /** Check Backend Health */
  async function checkServerHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (response.ok) {
        elements.serverStatusDot.classList.add('online');
        elements.serverStatusDot.classList.remove('pulsing');
        elements.statusText.textContent = 'API Gateway Connected';
      } else {
        throw new Error('Server non-OK response');
      }
    } catch (err) {
      elements.serverStatusDot.classList.remove('online');
      elements.serverStatusDot.classList.add('pulsing');
      elements.statusText.textContent = 'Local Standalone Mode';
    }
  }

  /** Load All Tasks & Stats */
  async function fetchTasks() {
    showSpinner(true);
    try {
      const queryParams = new URLSearchParams();
      if (state.activeTab !== 'all') queryParams.append('status', state.activeTab);
      if (state.searchQuery.trim()) queryParams.append('search', state.searchQuery.trim());
      if (state.priorityFilter !== 'all') queryParams.append('priority', state.priorityFilter);

      const response = await fetch(`${API_BASE_URL}/tasks?${queryParams.toString()}`);
      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
      
      const result = await response.json();
      if (result.success) {
        state.tasks = result.data || [];
        if (result.stats) state.stats = result.stats;
        renderApp();
      } else {
        showToast(result.error || 'Failed to fetch tasks', 'error');
      }
    } catch (error) {
      console.error('Fetch Tasks Error:', error);
      showToast('Could not connect to Flask API backend.', 'error');
    } finally {
      showSpinner(false);
    }
  }

  /** Create Task */
  async function apiCreateTask(taskData) {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
      });
      const result = await response.json();
      if (response.ok && result.success) {
        showToast('Task created successfully!', 'success');
        elements.taskForm.reset();
        fetchTasks();
      } else {
        showToast(result.error || 'Validation error while creating task', 'error');
      }
    } catch (err) {
      showToast('Error sending request to server.', 'error');
    }
  }

  /** Update Task */
  async function apiUpdateTask(taskId, updateData) {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });
      const result = await response.json();
      if (response.ok && result.success) {
        showToast('Task updated successfully!', 'success');
        fetchTasks();
      } else {
        showToast(result.error || 'Failed to update task', 'error');
      }
    } catch (err) {
      showToast('Error updating task on server.', 'error');
    }
  }

  /** Delete Task */
  async function apiDeleteTask(taskId) {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'DELETE'
      });
      const result = await response.json();
      if (response.ok && result.success) {
        showToast('Task deleted successfully', 'info');
        fetchTasks();
      } else {
        showToast(result.error || 'Failed to delete task', 'error');
      }
    } catch (err) {
      showToast('Error deleting task on server.', 'error');
    }
  }

  /** Reset / Seed Defaults */
  async function apiSeedTasks() {
    try {
      const response = await fetch(`${API_BASE_URL}/seed`, { method: 'POST' });
      const result = await response.json();
      if (result.success) {
        showToast('Reset default sample tasks!', 'success');
        fetchTasks();
      }
    } catch (err) {
      showToast('Could not reset sample data.', 'error');
    }
  }

  // ---------------------------------------------------------------------------
  // 4. UI Rendering Functions
  // ---------------------------------------------------------------------------

  function renderApp() {
    renderStats();
    renderTasksList();
  }

  function renderStats() {
    elements.statTotal.textContent = state.stats.total_tasks || 0;
    elements.statPending.textContent = state.stats.pending_tasks || 0;
    elements.statCompleted.textContent = state.stats.completed_tasks || 0;
    elements.statHigh.textContent = state.stats.high_priority_tasks || 0;

    const rate = state.stats.completion_rate || 0;
    elements.statPct.textContent = `${rate}%`;
    elements.progressFill.style.width = `${rate}%`;
  }

  function renderTasksList() {
    // Process local sorting
    let displayTasks = [...state.tasks];

    if (state.sortBy === 'duedate') {
      displayTasks.sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'));
    } else if (state.sortBy === 'priority') {
      const weight = { 'High': 1, 'Medium': 2, 'Low': 3 };
      displayTasks.sort((a, b) => (weight[a.priority] || 4) - (weight[b.priority] || 4));
    } else if (state.sortBy === 'title') {
      displayTasks.sort((a, b) => a.title.localeCompare(b.title));
    }

    // Clear Container
    elements.tasksContainer.innerHTML = '';

    if (displayTasks.length === 0) {
      elements.emptyState.classList.remove('hidden');
      return;
    }

    elements.emptyState.classList.add('hidden');

    displayTasks.forEach((task) => {
      const card = createTaskCardElement(task);
      elements.tasksContainer.appendChild(card);
    });
  }

  function createTaskCardElement(task) {
    const card = document.createElement('div');
    card.className = `task-card ${task.completed ? 'completed' : ''}`;
    card.dataset.id = task.id;

    // Due date formatting & urgency check
    let dueHtml = '';
    if (task.due_date) {
      const today = new Date().toISOString().split('T')[0];
      let dateStatusClass = '';
      let dateIcon = 'fa-regular fa-calendar';

      if (!task.completed) {
        if (task.due_date < today) {
          dateStatusClass = 'overdue';
          dateIcon = 'fa-solid fa-triangle-exclamation';
        } else if (task.due_date === today) {
          dateStatusClass = 'due-today';
          dateIcon = 'fa-solid fa-clock';
        }
      }

      dueHtml = `
        <span class="due-badge ${dateStatusClass}">
          <i class="${dateIcon}"></i> Due: ${escapeHtml(task.due_date)}
        </span>
      `;
    }

    const priorityClass = `priority-${(task.priority || 'medium').toLowerCase()}`;

    card.innerHTML = `
      <div class="checkbox-box">
        <button class="custom-checkbox ${task.completed ? 'checked' : ''}" 
                aria-label="Toggle Complete" 
                data-action="toggle-complete">
          <i class="fa-solid fa-check"></i>
        </button>
      </div>

      <div class="task-main-content">
        <div class="task-header-meta">
          <span class="priority-pill ${priorityClass}">${escapeHtml(task.priority || 'Medium')}</span>
          <span class="category-pill">${escapeHtml(task.category || 'General')}</span>
          ${dueHtml}
        </div>
        <h4 class="task-title">${escapeHtml(task.title)}</h4>
        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
      </div>

      <div class="task-actions">
        <button class="action-icon-btn edit-btn" data-action="edit" title="Edit Task">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="action-icon-btn delete-btn" data-action="delete" title="Delete Task">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    `;

    // Card Level Event Listeners
    card.addEventListener('click', (e) => {
      const target = e.target.closest('[data-action]');
      if (!target) return;

      const action = target.dataset.action;
      if (action === 'toggle-complete') {
        apiUpdateTask(task.id, { completed: !task.completed });
      } else if (action === 'edit') {
        openEditModal(task);
      } else if (action === 'delete') {
        openDeleteModal(task);
      }
    });

    return card;
  }

  // ---------------------------------------------------------------------------
  // 5. Event Listeners & Modals
  // ---------------------------------------------------------------------------

  // Form Submit (Create Task)
  elements.taskForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const title = elements.taskTitle.value.trim();

    if (!title) {
      elements.titleError.classList.add('visible');
      elements.taskTitle.focus();
      return;
    }
    elements.titleError.classList.remove('visible');

    const newTask = {
      title: title,
      description: elements.taskDesc.value.trim(),
      priority: elements.taskPriority.value,
      category: elements.taskCategory.value,
      due_date: elements.taskDueDate.value
    };

    apiCreateTask(newTask);
  });

  // Title input clears error on type
  elements.taskTitle.addEventListener('input', () => {
    if (elements.taskTitle.value.trim()) {
      elements.titleError.classList.remove('visible');
    }
  });

  // Reset form
  elements.resetFormBtn.addEventListener('click', () => {
    elements.taskForm.reset();
    elements.titleError.classList.remove('visible');
  });

  // Search input live filter
  let searchTimeout;
  elements.searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value;
    if (state.searchQuery) {
      elements.clearSearchBtn.classList.remove('hidden');
    } else {
      elements.clearSearchBtn.classList.add('hidden');
    }

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      fetchTasks();
    }, 250);
  });

  // Clear search button
  elements.clearSearchBtn.addEventListener('click', () => {
    elements.searchInput.value = '';
    state.searchQuery = '';
    elements.clearSearchBtn.classList.add('hidden');
    fetchTasks();
  });

  // Status Filter Tabs
  elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeTab = btn.dataset.filter;
      fetchTasks();
    });
  });

  // Priority Filter
  elements.priorityFilter.addEventListener('change', (e) => {
    state.priorityFilter = e.target.value;
    fetchTasks();
  });

  // Sort Filter
  elements.sortSelect.addEventListener('change', (e) => {
    state.sortBy = e.target.value;
    renderTasksList();
  });

  // Seed Button
  elements.seedBtn.addEventListener('click', () => {
    apiSeedTasks();
  });

  // Theme Toggle
  elements.themeToggleBtn.addEventListener('click', () => {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('task_manager_theme', state.theme);
    updateThemeIcon();
  });

  function updateThemeIcon() {
    const icon = elements.themeToggleBtn.querySelector('i');
    if (state.theme === 'dark') {
      icon.className = 'fa-solid fa-sun';
    } else {
      icon.className = 'fa-solid fa-moon';
    }
  }

  // --- Edit Modal Controls ---
  function openEditModal(task) {
    state.taskToEdit = task;
    elements.editTaskId.value = task.id;
    elements.editTaskTitle.value = task.title;
    elements.editTaskDesc.value = task.description || '';
    elements.editTaskPriority.value = task.priority || 'Medium';
    elements.editTaskCategory.value = task.category || 'General';
    elements.editTaskDueDate.value = task.due_date || '';
    elements.editTaskCompleted.value = task.completed ? 'true' : 'false';

    elements.editModalOverlay.classList.remove('hidden');
  }

  function closeEditModal() {
    elements.editModalOverlay.classList.add('hidden');
    state.taskToEdit = null;
  }

  elements.closeEditModalBtn.addEventListener('click', closeEditModal);
  elements.cancelEditBtn.addEventListener('click', closeEditModal);

  elements.editTaskForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!state.taskToEdit) return;

    const updatedData = {
      title: elements.editTaskTitle.value.trim(),
      description: elements.editTaskDesc.value.trim(),
      priority: elements.editTaskPriority.value,
      category: elements.editTaskCategory.value,
      due_date: elements.editTaskDueDate.value,
      completed: elements.editTaskCompleted.value === 'true'
    };

    apiUpdateTask(state.taskToEdit.id, updatedData);
    closeEditModal();
  });

  // --- Delete Modal Controls ---
  function openDeleteModal(task) {
    state.taskToDelete = task;
    elements.deleteTaskTitleText.textContent = `"${task.title}"`;
    elements.deleteModalOverlay.classList.remove('hidden');
  }

  function closeDeleteModal() {
    elements.deleteModalOverlay.classList.add('hidden');
    state.taskToDelete = null;
  }

  elements.closeDeleteModalBtn.addEventListener('click', closeDeleteModal);
  elements.cancelDeleteBtn.addEventListener('click', closeDeleteModal);
  
  elements.confirmDeleteBtn.addEventListener('click', () => {
    if (state.taskToDelete) {
      apiDeleteTask(state.taskToDelete.id);
      closeDeleteModal();
    }
  });

  // ---------------------------------------------------------------------------
  // 6. Helpers & Utilities
  // ---------------------------------------------------------------------------

  function showSpinner(show) {
    if (show) {
      elements.loadingSpinner.classList.remove('hidden');
    } else {
      elements.loadingSpinner.classList.add('hidden');
    }
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-solid fa-info-circle';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    if (type === 'error') iconClass = 'fa-solid fa-circle-exclamation';

    toast.innerHTML = `
      <i class="${iconClass}"></i>
      <span>${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ---------------------------------------------------------------------------
  // 7. Initialization
  // ---------------------------------------------------------------------------
  checkServerHealth();
  fetchTasks();
});
