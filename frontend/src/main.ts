import './style.css';
import {
  fetchDashboard,
  fetchArticles,
  fetchArticleComparisons,
  fetchSupplierProducts,
  runComparisons,
  fetchComparison,
  fetchQuestions,
  submitAnswer,
  resetDatabase,
} from './api';
import type {
  HospitalArticle,
  SupplierProduct,
  ComparisonResult,
  ComparisonSummary,
  DashboardStats,
  InformationRequest,
} from './types';

// App State
type Tab = 'dashboard' | 'articles' | 'suppliers' | 'questions';

let currentTab: Tab = 'dashboard';
let stats: DashboardStats | null = null;
let articles: HospitalArticle[] = [];
let supplierProducts: SupplierProduct[] = [];
let questions: InformationRequest[] = [];
let isRunningMatch = false;

// Toast Helper
function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

// Initial Data Load
async function loadData() {
  try {
    const [d, a, s, q] = await Promise.all([
      fetchDashboard(),
      fetchArticles(),
      fetchSupplierProducts(),
      fetchQuestions(),
    ]);
    stats = d;
    articles = a;
    supplierProducts = s;
    questions = q;
    render();
  } catch (err: any) {
    console.error('Failed to load data:', err);
    showToast(`Connection error: ${err.message || err}`, 'error');
    render();
  }
}

// Global Actions
async function handleRunComparisons() {
  if (isRunningMatch) return;
  isRunningMatch = true;
  render();
  try {
    showToast('Running product candidate generation & comparisons...', 'info');
    const res = await runComparisons();
    showToast(`Comparisons complete! Processed ${res.articles_processed} articles with ${res.total_comparisons} comparisons.`, 'success');
    await loadData();
  } catch (err: any) {
    showToast(`Error running comparisons: ${err.message}`, 'error');
  } finally {
    isRunningMatch = false;
    render();
  }
}

async function handleResetData() {
  if (!confirm('Are you sure you want to reset and re-seed the demo database?')) return;
  try {
    showToast('Resetting database to initial state...', 'info');
    await resetDatabase();
    showToast('Database reset successfully!', 'success');
    await loadData();
  } catch (err: any) {
    showToast(`Error resetting database: ${err.message}`, 'error');
  }
}

// Modal Viewers
async function openComparisonModal(comparisonId: number) {
  try {
    showToast('Loading comparison details...', 'info');
    const comp: ComparisonResult = await fetchComparison(comparisonId);
    renderComparisonModal(comp);
  } catch (err: any) {
    showToast(`Failed to open comparison: ${err.message}`, 'error');
  }
}

async function openArticleComparisonsModal(article: HospitalArticle) {
  try {
    showToast(`Loading matches for ${article.raw_name}...`, 'info');
    const comparisons: ComparisonSummary[] = await fetchArticleComparisons(article.id);
    renderArticleComparisonsModal(article, comparisons);
  } catch (err: any) {
    showToast(`Failed to load matches: ${err.message}`, 'error');
  }
}

function openAnswerModal(question: InformationRequest) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.id = 'answer-modal';

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 560px;">
      <div class="modal-header">
        <h3 class="card-title">💬 Answer Information Request</h3>
        <button class="close-btn" id="close-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div style="margin-bottom: 1rem;">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Hospital Article:</div>
          <div style="font-weight: 600;">${question.hospital_article_name || 'Hospital Item'}</div>
        </div>
        <div style="margin-bottom: 1rem;">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Supplier Product:</div>
          <div style="font-weight: 600;">${question.supplier_product_name || 'Supplier Item'}</div>
        </div>
        <div style="margin-bottom: 1.25rem; padding: 0.75rem; background: #fffbeb; border-radius: var(--radius-sm); border: 1px solid #fde68a;">
          <div style="font-size: 0.75rem; font-weight: 600; color: #92400e; text-transform: uppercase;">Missing / Ambiguous Attribute:</div>
          <div style="font-weight: 700; color: #b45309;">${question.attribute_name}</div>
          <div style="font-size: 0.875rem; color: #78350f; margin-top: 0.25rem;">${question.question_text}</div>
        </div>

        <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">
          Your Answer / Specification Data:
        </label>
        <textarea id="answer-input" rows="3" class="search-input" style="width: 100%; font-family: inherit; resize: vertical;" placeholder="e.g. EO-sterilisiert, DIN EN ISO 7886-1 zertifiziert, etc."></textarea>
        
        <div style="margin-top: 0.75rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.35rem;">Quick Templates:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
            <button type="button" class="btn btn-secondary btn-sm quick-fill" data-val="EO-sterilisiert">EO-sterilisiert</button>
            <button type="button" class="btn btn-secondary btn-sm quick-fill" data-val="DIN EN ISO 7886-1 konform">DIN EN ISO 7886-1</button>
            <button type="button" class="btn btn-secondary btn-sm quick-fill" data-val="Polypropylen (Latexfrei)">Polypropylen</button>
            <button type="button" class="btn btn-secondary btn-sm quick-fill" data-val="Luer-Lock Ansatz">Luer-Lock</button>
          </div>
        </div>

        <div style="margin-top: 1rem;">
          <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.35rem;">Answered By:</label>
          <input type="text" id="answered-by-input" class="search-input" style="width: 100%;" value="Supplier QA Team" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
        <button class="btn btn-primary" id="submit-answer-btn">Submit & Re-evaluate</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector('#close-modal')?.addEventListener('click', close);
  modal.querySelector('#cancel-btn')?.addEventListener('click', close);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) close();
  });

  modal.querySelectorAll('.quick-fill').forEach((btn) => {
    btn.addEventListener('click', () => {
      const val = btn.getAttribute('data-val') || '';
      const input = modal.querySelector('#answer-input') as HTMLTextAreaElement;
      input.value = val;
    });
  });

  modal.querySelector('#submit-answer-btn')?.addEventListener('click', async () => {
    const answerText = (modal.querySelector('#answer-input') as HTMLTextAreaElement).value.trim();
    const answeredBy = (modal.querySelector('#answered-by-input') as HTMLInputElement).value.trim();

    if (!answerText) {
      alert('Please enter an answer to proceed.');
      return;
    }

    try {
      showToast('Submitting answer and re-evaluating compatibility...', 'info');
      await submitAnswer(question.id, answerText, answeredBy);
      showToast('Answer processed! Product enriched and match re-evaluated.', 'success');
      close();
      await loadData();
    } catch (err: any) {
      showToast(`Submission failed: ${err.message}`, 'error');
    }
  });
}

function renderArticleComparisonsModal(article: HospitalArticle, comparisons: ComparisonSummary[]) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.id = 'article-matches-modal';

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 960px;">
      <div class="modal-header">
        <div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">HOSPITAL ARTICLE MATCHES</div>
          <h3 class="card-title" style="margin-top: 0.2rem;">${article.raw_name}</h3>
          <div style="font-size: 0.8rem; color: var(--text-muted);">
            ID: <code>${article.internal_id}</code> | Category: <strong>${article.product_category || 'N/A'}</strong> | Size: <strong>${article.size_label || 'N/A'}</strong>
          </div>
        </div>
        <button class="close-btn" id="close-modal">&times;</button>
      </div>
      <div class="modal-body">
        ${comparisons.length === 0 ? `
          <div style="text-align: center; padding: 3rem 1rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
            <h4>No comparisons generated yet</h4>
            <p style="color: var(--text-muted); margin-top: 0.25rem;">Click "Run Matching" in the header to run candidate generation and decision engine.</p>
          </div>
        ` : `
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                  <th>Supplier Product Candidate</th>
                  <th>Supplier</th>
                  <th>Open Qs</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${comparisons.map((c) => `
                  <tr>
                    <td><strong>#${c.candidate_rank ?? '-'}</strong></td>
                    <td>
                      <span class="badge badge-${c.decision}">
                        ${c.decision === 'compatible' ? '✓ Compatible' : c.decision === 'uncertain' ? '? Uncertain' : '✕ Incompatible'}
                      </span>
                    </td>
                    <td>
                      <span class="score-pill">${Math.round(c.confidence * 100)}%</span>
                    </td>
                    <td>
                      <strong>${c.supplier_product_name}</strong>
                      <div style="font-size: 0.75rem; color: var(--text-muted);">${c.summary || ''}</div>
                    </td>
                    <td>${c.supplier_name || 'Generic Supplier'}</td>
                    <td>
                      ${c.open_questions > 0 ? `<span class="badge badge-uncertain">⚠️ ${c.open_questions} Open</span>` : `<span style="color: var(--text-muted); font-size: 0.8rem;">None</span>`}
                    </td>
                    <td>
                      <button class="btn btn-secondary btn-sm view-detail-btn" data-id="${c.id}">
                        Full Diff & Specs
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="close-btn">Close</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector('#close-modal')?.addEventListener('click', close);
  modal.querySelector('#close-btn')?.addEventListener('click', close);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) close();
  });

  modal.querySelectorAll('.view-detail-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cid = Number(btn.getAttribute('data-id'));
      close();
      openComparisonModal(cid);
    });
  });
}

function renderComparisonModal(comp: ComparisonResult) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.id = 'comparison-detail-modal';

  const hospital = comp.hospital_article;
  const supplier = comp.supplier_product;

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 1050px;">
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span class="badge badge-${comp.decision}" style="font-size: 0.85rem; padding: 0.35rem 0.75rem;">
              ${comp.decision === 'compatible' ? '✓ COMPATIBLE REPLACEMENT' : comp.decision === 'uncertain' ? '? UNCERTAIN (REQUIRES QA)' : '✕ INCOMPATIBLE'}
            </span>
            <span class="score-pill">Confidence: ${Math.round(comp.confidence * 100)}%</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Rank #${comp.candidate_rank} (Score: ${comp.candidate_score?.toFixed(2) || 'N/A'})</span>
          </div>
          <h3 class="card-title" style="margin-top: 0.5rem; font-size: 1.25rem;">
            ${hospital?.raw_name || 'Hospital Article'} ➔ ${supplier?.raw_name || 'Supplier Product'}
          </h3>
        </div>
        <button class="close-btn" id="close-modal">&times;</button>
      </div>

      <div class="modal-body">
        <!-- Summary Alert -->
        ${comp.summary || comp.reasoning_summary ? `
          <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1.5rem;">
            <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Decision Rationale</div>
            <div style="font-size: 0.95rem; margin-top: 0.25rem; line-height: 1.5;">${comp.summary || comp.reasoning_summary}</div>
          </div>
        ` : ''}

        <!-- Side-by-Side Spec Comparison -->
        <div class="spec-grid">
          <div class="spec-card">
            <div class="spec-card-title">🏥 Hospital Requirement</div>
            <div style="font-weight: 700; margin-bottom: 0.75rem;">${hospital?.raw_name || 'N/A'}</div>
            <div class="spec-row"><span class="spec-key">Internal ID</span><span class="spec-val"><code>${hospital?.internal_id || '-'}</code></span></div>
            <div class="spec-row"><span class="spec-key">Category</span><span class="spec-val">${hospital?.product_category || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Subcategory</span><span class="spec-val">${hospital?.product_subcategory || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Material</span><span class="spec-val">${hospital?.material || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Sterility</span><span class="spec-val">${hospital?.sterility || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Size / Gauge</span><span class="spec-val">${hospital?.size_label || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Target Price</span><span class="spec-val">${hospital?.net_target_price != null ? `${hospital.net_target_price} ${hospital.currency || 'EUR'}` : '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Annual Quantity</span><span class="spec-val">${hospital?.annual_quantity?.toLocaleString() || '-'}</span></div>
          </div>

          <div class="spec-card">
            <div class="spec-card-title">🏢 Supplier Alternative (${supplier?.supplier_name || 'Supplier'})</div>
            <div style="font-weight: 700; margin-bottom: 0.75rem;">${supplier?.raw_name || 'N/A'}</div>
            <div class="spec-row"><span class="spec-key">Article No.</span><span class="spec-val"><code>${supplier?.article_number || '-'}</code></span></div>
            <div class="spec-row"><span class="spec-key">Category</span><span class="spec-val">${supplier?.product_category || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Brand / Mfr</span><span class="spec-val">${supplier?.brand || supplier?.manufacturer || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Material</span><span class="spec-val">${supplier?.material || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Sterility</span><span class="spec-val">${supplier?.sterility || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Size / Gauge</span><span class="spec-val">${supplier?.size_label || '-'}</span></div>
            <div class="spec-row"><span class="spec-key">Packaging Unit</span><span class="spec-val">${supplier?.packaging_unit || '-'} (${supplier?.units_per_package || 1} pcs)</span></div>
            <div class="spec-row"><span class="spec-key">DIN/ISO Norms</span><span class="spec-val">${supplier?.din_iso_norms?.join(', ') || '-'}</span></div>
          </div>
        </div>

        <!-- Evidence & Attribute Comparison Matrix -->
        <h4 style="margin-bottom: 0.75rem; font-size: 1rem;">Detailed Attribute Compatibility Matrix</h4>
        <div class="table-responsive">
          <table class="diff-table">
            <thead>
              <tr>
                <th style="width: 20%;">Attribute</th>
                <th style="width: 25%;">Hospital Requirement</th>
                <th style="width: 25%;">Supplier Alternative</th>
                <th style="width: 15%;">Status</th>
                <th style="width: 15%;">Criticality</th>
              </tr>
            </thead>
            <tbody>
              ${comp.all_evidence.map((ev) => `
                <tr class="${ev.status === 'match' ? 'diff-row-match' : ev.status === 'conflict' ? 'diff-row-conflict' : 'diff-row-missing'}">
                  <td><strong>${ev.attribute_name}</strong></td>
                  <td>${ev.hospital_value ?? '<span style="color: var(--text-light);">None</span>'}</td>
                  <td>${ev.supplier_value ?? '<span style="color: var(--text-light);">Missing</span>'}</td>
                  <td>
                    <span class="badge ${ev.status === 'match' ? 'badge-compatible' : ev.status === 'conflict' ? 'badge-incompatible' : 'badge-uncertain'}">
                      ${ev.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span style="font-size: 0.75rem; text-transform: capitalize; color: ${ev.criticality === 'hard_blocker' ? 'var(--danger-text)' : 'var(--text-muted)'}; font-weight: ${ev.criticality === 'hard_blocker' ? '700' : '500'};">
                      ${ev.criticality.replace('_', ' ')}
                    </span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Supplier Questions Section -->
        ${comp.supplier_questions.length > 0 ? `
          <div style="margin-top: 2rem;">
            <h4 style="margin-bottom: 0.75rem; font-size: 1rem; color: #92400e;">⚠️ Information Requests for Supplier (${comp.supplier_questions.length})</h4>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${comp.supplier_questions.map((q) => `
                <div style="border: 1px solid #fde68a; background: #fffbeb; border-radius: var(--radius-md); padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <div style="font-size: 0.75rem; font-weight: 700; color: #b45309;">MISSING SPECIFICATION: ${q.attribute_name.toUpperCase()}</div>
                    <div style="font-size: 0.9rem; color: #78350f; margin-top: 0.25rem;">${q.question_text}</div>
                    ${q.response ? `
                      <div style="margin-top: 0.5rem; padding: 0.5rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: var(--radius-sm); font-size: 0.85rem; color: #166534;">
                        <strong>Answered by ${q.response.answered_by}:</strong> "${q.response.answer_text}"
                      </div>
                    ` : ''}
                  </div>
                  <div>
                    ${q.status === 'open' ? `
                      <button class="btn btn-primary btn-sm answer-q-btn" data-qid="${q.id}">
                        Answer Request
                      </button>
                    ` : `
                      <span class="badge badge-compatible">Answered</span>
                    `}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="close-btn">Close</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => modal.remove();
  modal.querySelector('#close-modal')?.addEventListener('click', close);
  modal.querySelector('#close-btn')?.addEventListener('click', close);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) close();
  });

  modal.querySelectorAll('.answer-q-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const qid = Number(btn.getAttribute('data-qid'));
      const q = comp.supplier_questions.find((x) => x.id === qid);
      if (q) {
        close();
        openAnswerModal(q);
      }
    });
  });
}

// Main Render Function
function render() {
  const app = document.querySelector<HTMLDivElement>('#app')!;

  app.innerHTML = `
    <div class="app-container">
      <!-- Top Navigation -->
      <header class="app-header">
        <div class="brand">
          <div class="brand-icon">🩺</div>
          <div>
            <div class="brand-title">SANOVIO</div>
            <div class="brand-subtitle">Product Match & Replacement Intelligence</div>
          </div>
        </div>

        <nav class="nav-tabs">
          <button class="nav-tab ${currentTab === 'dashboard' ? 'active' : ''}" data-tab="dashboard">
            📊 Dashboard
          </button>
          <button class="nav-tab ${currentTab === 'articles' ? 'active' : ''}" data-tab="articles">
            🏥 Hospital Articles (${articles.length})
          </button>
          <button class="nav-tab ${currentTab === 'suppliers' ? 'active' : ''}" data-tab="suppliers">
            🏢 Supplier Catalog (${supplierProducts.length})
          </button>
          <button class="nav-tab ${currentTab === 'questions' ? 'active' : ''}" data-tab="questions">
            💬 Supplier Q&A ${stats?.open_questions ? `<span class="badge badge-uncertain" style="padding: 0.1rem 0.4rem; font-size: 0.7rem;">${stats.open_questions}</span>` : ''}
          </button>
        </nav>

        <div class="header-actions">
          <button class="btn btn-primary" id="run-match-btn" ${isRunningMatch ? 'disabled' : ''}>
            ${isRunningMatch ? '<span class="spinner"></span> Matching...' : '🚀 Run All Comparisons'}
          </button>
          <button class="btn btn-outline-danger btn-sm" id="reset-btn" title="Reset and re-seed database">
            🔄 Reset Demo
          </button>
        </div>
      </header>

      <!-- Main Body -->
      <main class="main-content">
        ${renderCurrentTab()}
      </main>
    </div>
  `;

  // Attach Event Listeners
  app.querySelectorAll('.nav-tab').forEach((tabBtn) => {
    tabBtn.addEventListener('click', () => {
      const tab = tabBtn.getAttribute('data-tab') as Tab;
      if (tab) {
        currentTab = tab;
        render();
      }
    });
  });

  app.querySelector('#run-match-btn')?.addEventListener('click', handleRunComparisons);
  app.querySelector('#reset-btn')?.addEventListener('click', handleResetData);

  // Tab specific listeners
  attachTabListeners();
}

function renderCurrentTab(): string {
  switch (currentTab) {
    case 'dashboard':
      return renderDashboardTab();
    case 'articles':
      return renderArticlesTab();
    case 'suppliers':
      return renderSuppliersTab();
    case 'questions':
      return renderQuestionsTab();
    default:
      return '';
  }
}

// ---------------- Tab Renders ----------------

function renderDashboardTab(): string {
  if (!stats) {
    return `<div style="text-align: center; padding: 4rem;"><div class="spinner spinner-dark" style="width: 2rem; height: 2rem;"></div><p style="margin-top: 1rem; color: var(--text-muted);">Connecting to SANOVIO backend...</p></div>`;
  }

  return `
    <div class="hero-banner">
      <div class="hero-text">
        <h1>AI-Assisted Medical Product Replacement</h1>
        <p>
          Match hospital article requirements with supplier catalogs using deterministic clinical & physical attribute rules + LLM reasoning for ambiguous specs.
        </p>
        <div style="margin-top: 1.25rem; display: flex; gap: 0.75rem;">
          <button class="btn btn-primary btn-lg" id="dash-run-match-btn" ${isRunningMatch ? 'disabled' : ''}>
            ${isRunningMatch ? '<span class="spinner"></span> Processing Matches...' : '🚀 Run Full Product Matching'}
          </button>
          <button class="btn btn-secondary btn-lg" id="dash-view-articles-btn">
            Browse Hospital Catalog
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Hospital Articles</span>
          <span class="stat-icon" style="background: #eff6ff;">🏥</span>
        </div>
        <div class="stat-value" style="color: var(--primary);">${stats.total_hospital_articles}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Supplier Products</span>
          <span class="stat-icon" style="background: #f0fdf4;">🏢</span>
        </div>
        <div class="stat-value" style="color: #059669;">${stats.total_supplier_products}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Comparisons</span>
          <span class="stat-icon" style="background: #f8fafc;">⚖️</span>
        </div>
        <div class="stat-value">${stats.total_comparisons}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Compatible Matches</span>
          <span class="stat-icon" style="background: var(--success-bg);">✓</span>
        </div>
        <div class="stat-value" style="color: var(--success-text);">${stats.compatible_count}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Uncertain (Need Info)</span>
          <span class="stat-icon" style="background: var(--warning-bg);">?</span>
        </div>
        <div class="stat-value" style="color: var(--warning-text);">${stats.uncertain_count}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Incompatible</span>
          <span class="stat-icon" style="background: var(--danger-bg);">✕</span>
        </div>
        <div class="stat-value" style="color: var(--danger-text);">${stats.incompatible_count}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Open Supplier Requests</span>
          <span class="stat-icon" style="background: #fffbeb;">💬</span>
        </div>
        <div class="stat-value" style="color: #b45309;">${stats.open_questions}</div>
      </div>
    </div>

    <!-- Quick Article Preview -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">🏥 Hospital Articles & Alternative Status</h3>
        <button class="btn btn-secondary btn-sm" id="dash-see-all-btn">View All (${articles.length})</button>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Article Description</th>
              <th>Category</th>
              <th>Size / Dimensions</th>
              <th>Matches Breakdown</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${articles.slice(0, 6).map((a) => `
              <tr>
                <td><code>${a.internal_id}</code></td>
                <td>
                  <strong>${a.raw_name}</strong>
                  ${a.brand ? `<div style="font-size: 0.75rem; color: var(--text-muted);">Brand: ${a.brand}</div>` : ''}
                </td>
                <td>${a.product_category || 'N/A'}</td>
                <td>${a.size_label || '-'}</td>
                <td>
                  <div style="display: flex; gap: 0.4rem; align-items: center;">
                    ${a.compatible_count > 0 ? `<span class="badge badge-compatible">${a.compatible_count} Match</span>` : ''}
                    ${a.uncertain_count > 0 ? `<span class="badge badge-uncertain">${a.uncertain_count} Uncertain</span>` : ''}
                    ${a.incompatible_count > 0 ? `<span class="badge badge-incompatible">${a.incompatible_count} Incompat</span>` : ''}
                    ${a.compatible_count === 0 && a.uncertain_count === 0 && a.incompatible_count === 0 ? `<span class="badge badge-neutral">Not Run</span>` : ''}
                  </div>
                </td>
                <td>
                  <button class="btn btn-secondary btn-sm match-detail-btn" data-id="${a.id}">
                    View Alternatives
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderArticlesTab(): string {
  return `
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">🏥 Hospital Catalog & Replacement Matrix</h3>
        <div style="color: var(--text-muted); font-size: 0.875rem;">Total items: ${articles.length}</div>
      </div>
      <div class="card-body">
        <div class="toolbar">
          <input type="text" id="article-search" class="search-input" placeholder="Search by name, ID, brand, material, category..." />
          <select id="article-filter-category" class="select-filter">
            <option value="">All Categories</option>
            ${Array.from(new Set(articles.map((a) => a.product_category).filter(Boolean))).map((c) => `<option value="${c}">${c}</option>`).join('')}
          </select>
        </div>

        <div class="table-responsive">
          <table class="data-table" id="articles-table">
            <thead>
              <tr>
                <th>Internal ID</th>
                <th>Product Description</th>
                <th>Category / Subcategory</th>
                <th>Material & Sterility</th>
                <th>Size / Dimensions</th>
                <th>Target Price</th>
                <th>Replacement Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${articles.map((a) => `
                <tr data-name="${a.raw_name.toLowerCase()}" data-id="${a.internal_id.toLowerCase()}" data-cat="${(a.product_category || '').toLowerCase()}">
                  <td><code>${a.internal_id}</code></td>
                  <td>
                    <strong>${a.raw_name}</strong>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                      ${a.brand ? `Brand: ${a.brand}` : ''} ${a.article_number ? `| Art: ${a.article_number}` : ''}
                    </div>
                  </td>
                  <td>
                    <div>${a.product_category || 'N/A'}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${a.product_subcategory || ''}</div>
                  </td>
                  <td>
                    <div>${a.material || '-'}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${a.sterility || '-'}</div>
                  </td>
                  <td>${a.size_label || '-'}</td>
                  <td>
                    ${a.net_target_price != null ? `<strong>${a.net_target_price} ${a.currency || 'EUR'}</strong>` : '-'}
                  </td>
                  <td>
                    <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                      ${a.compatible_count > 0 ? `<span class="badge badge-compatible">✓ ${a.compatible_count} Compatible</span>` : ''}
                      ${a.uncertain_count > 0 ? `<span class="badge badge-uncertain">? ${a.uncertain_count} Uncertain</span>` : ''}
                      ${a.incompatible_count > 0 ? `<span class="badge badge-incompatible">✕ ${a.incompatible_count} Incompatible</span>` : ''}
                      ${a.compatible_count === 0 && a.uncertain_count === 0 && a.incompatible_count === 0 ? `<span class="badge badge-neutral">Not Run</span>` : ''}
                    </div>
                  </td>
                  <td>
                    <button class="btn btn-primary btn-sm match-detail-btn" data-id="${a.id}">
                      View Alternatives
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderSuppliersTab(): string {
  return `
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">🏢 Supplier Catalog & Specifications</h3>
        <div style="color: var(--text-muted); font-size: 0.875rem;">Total items: ${supplierProducts.length}</div>
      </div>
      <div class="card-body">
        <div class="toolbar">
          <input type="text" id="supplier-search" class="search-input" placeholder="Search supplier products, norm, material, size..." />
        </div>

        <div class="table-responsive">
          <table class="data-table" id="suppliers-table">
            <thead>
              <tr>
                <th>Article No.</th>
                <th>Supplier / Brand</th>
                <th>Product Description</th>
                <th>Category</th>
                <th>Material & Specs</th>
                <th>Packaging Unit</th>
                <th>DIN / ISO Norms</th>
              </tr>
            </thead>
            <tbody>
              ${supplierProducts.map((p) => `
                <tr data-text="${p.raw_name.toLowerCase()} ${(p.supplier_name || '').toLowerCase()} ${(p.article_number || '').toLowerCase()}">
                  <td><code>${p.article_number || `SP-${p.id}`}</code></td>
                  <td>
                    <strong>${p.supplier_name || 'Generic Supplier'}</strong>
                    ${p.brand ? `<div style="font-size: 0.75rem; color: var(--text-muted);">${p.brand}</div>` : ''}
                  </td>
                  <td><strong>${p.raw_name}</strong></td>
                  <td>${p.product_category || 'N/A'}</td>
                  <td>
                    <div>${p.material || '-'} | ${p.sterility || '-'}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${p.size_label || '-'} ${p.connector_type ? `(${p.connector_type})` : ''}</div>
                  </td>
                  <td>${p.packaging_unit || '-'} (${p.units_per_package || 1} pcs)</td>
                  <td>
                    ${p.din_iso_norms && p.din_iso_norms.length > 0 ? p.din_iso_norms.map((n) => `<span class="badge badge-info" style="font-size: 0.7rem; margin-right: 0.2rem;">${n}</span>`).join('') : '<span style="color: var(--text-light);">-</span>'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderQuestionsTab(): string {
  const openCount = questions.filter((q) => q.status === 'open').length;
  const answeredCount = questions.filter((q) => q.status === 'answered').length;

  return `
    <div class="card">
      <div class="card-header">
        <div>
          <h3 class="card-title">💬 Supplier Q&A & Enrichment Hub</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
            When product specifications are missing or ambiguous, the engine creates targeted questions. Answering them enriches supplier data and re-runs comparison in real-time.
          </p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <span class="badge badge-uncertain">⚠️ ${openCount} Open</span>
          <span class="badge badge-compatible">✓ ${answeredCount} Answered</span>
        </div>
      </div>
      <div class="card-body">
        ${questions.length === 0 ? `
          <div style="text-align: center; padding: 4rem 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🎉</div>
            <h4>No Information Requests</h4>
            <p style="color: var(--text-muted); margin-top: 0.25rem;">
              Run comparison matching to automatically identify missing critical specifications.
            </p>
          </div>
        ` : `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1.25rem;">
            ${questions.map((q) => `
              <div style="background: ${q.status === 'open' ? '#fffbeb' : '#ffffff'}; border: 1px solid ${q.status === 'open' ? '#fde68a' : 'var(--border)'}; border-radius: var(--radius-md); padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                    <span class="badge ${q.status === 'open' ? 'badge-uncertain' : 'badge-compatible'}">
                      ${q.status === 'open' ? '⚠️ Open Request' : '✓ Answered'}
                    </span>
                    <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted);">REQ #${q.id}</span>
                  </div>

                  <div style="margin-bottom: 0.75rem;">
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Target Hospital Item:</div>
                    <strong style="font-size: 0.875rem;">${q.hospital_article_name || 'Hospital Article'}</strong>
                  </div>

                  <div style="margin-bottom: 0.75rem;">
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Supplier Alternative:</div>
                    <strong style="font-size: 0.875rem;">${q.supplier_product_name || 'Supplier Product'}</strong>
                  </div>

                  <div style="background: rgba(0,0,0,0.03); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.75rem;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #b45309; text-transform: uppercase;">
                      Missing Spec: ${q.attribute_name}
                    </div>
                    <div style="font-size: 0.875rem; color: var(--text-main); margin-top: 0.25rem;">
                      ${q.question_text}
                    </div>
                  </div>

                  ${q.response ? `
                    <div style="padding: 0.65rem; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: var(--radius-sm); font-size: 0.825rem; color: #065f46;">
                      <div><strong>Answer:</strong> "${q.response.answer_text}"</div>
                      <div style="font-size: 0.7rem; color: #047857; margin-top: 0.2rem;">By: ${q.response.answered_by || 'Supplier'} (${q.response.answered_at || 'Just now'})</div>
                    </div>
                  ` : ''}
                </div>

                <div style="margin-top: 1rem; display: flex; justify-content: flex-end; gap: 0.5rem;">
                  <button class="btn btn-secondary btn-sm view-comp-link-btn" data-cid="${q.comparison_id}">
                    View Comparison
                  </button>
                  ${q.status === 'open' ? `
                    <button class="btn btn-primary btn-sm answer-q-hub-btn" data-qid="${q.id}">
                      💬 Submit Answer
                    </button>
                  ` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    </div>
  `;
}

// Attach Event Listeners to rendered tabs
function attachTabListeners() {
  // Dashboard listeners
  document.querySelector('#dash-run-match-btn')?.addEventListener('click', handleRunComparisons);
  document.querySelector('#dash-view-articles-btn')?.addEventListener('click', () => {
    currentTab = 'articles';
    render();
  });
  document.querySelector('#dash-see-all-btn')?.addEventListener('click', () => {
    currentTab = 'articles';
    render();
  });

  // Articles Match Alternatives buttons
  document.querySelectorAll('.match-detail-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = Number(btn.getAttribute('data-id'));
      const article = articles.find((a) => a.id === id);
      if (article) {
        openArticleComparisonsModal(article);
      }
    });
  });

  // Filter in articles tab
  const articleSearch = document.querySelector<HTMLInputElement>('#article-search');
  const articleCat = document.querySelector<HTMLSelectElement>('#article-filter-category');
  if (articleSearch && articleCat) {
    const filterFn = () => {
      const q = articleSearch.value.toLowerCase();
      const cat = articleCat.value.toLowerCase();
      const rows = document.querySelectorAll('#articles-table tbody tr');
      rows.forEach((row) => {
        const name = row.getAttribute('data-name') || '';
        const id = row.getAttribute('data-id') || '';
        const rcat = row.getAttribute('data-cat') || '';
        const matchesQ = !q || name.includes(q) || id.includes(q);
        const matchesCat = !cat || rcat.includes(cat);
        (row as HTMLElement).style.display = matchesQ && matchesCat ? '' : 'none';
      });
    };
    articleSearch.addEventListener('input', filterFn);
    articleCat.addEventListener('change', filterFn);
  }

  // Filter in suppliers tab
  const supplierSearch = document.querySelector<HTMLInputElement>('#supplier-search');
  if (supplierSearch) {
    supplierSearch.addEventListener('input', () => {
      const q = supplierSearch.value.toLowerCase();
      const rows = document.querySelectorAll('#suppliers-table tbody tr');
      rows.forEach((row) => {
        const text = row.getAttribute('data-text') || '';
        (row as HTMLElement).style.display = !q || text.includes(q) ? '' : 'none';
      });
    });
  }

  // Q&A Hub buttons
  document.querySelectorAll('.answer-q-hub-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const qid = Number(btn.getAttribute('data-qid'));
      const q = questions.find((x) => x.id === qid);
      if (q) openAnswerModal(q);
    });
  });

  document.querySelectorAll('.view-comp-link-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cid = Number(btn.getAttribute('data-cid'));
      openComparisonModal(cid);
    });
  });
}

// Start app
loadData();
