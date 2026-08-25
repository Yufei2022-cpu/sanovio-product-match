import type {
  HospitalArticle,
  SupplierProduct,
  ComparisonResult,
  ComparisonSummary,
  DashboardStats,
  InformationRequest
} from './types';

const API_BASE = 'http://127.0.0.1:8000/api';

export async function fetchDashboard(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error(`Failed to load dashboard: ${res.statusText}`);
  return res.json();
}

export async function fetchArticles(): Promise<HospitalArticle[]> {
  const res = await fetch(`${API_BASE}/articles`);
  if (!res.ok) throw new Error(`Failed to load articles: ${res.statusText}`);
  return res.json();
}

export async function fetchArticle(id: number): Promise<HospitalArticle> {
  const res = await fetch(`${API_BASE}/articles/${id}`);
  if (!res.ok) throw new Error(`Failed to load article ${id}: ${res.statusText}`);
  return res.json();
}

export async function fetchArticleComparisons(articleId: number): Promise<ComparisonSummary[]> {
  const res = await fetch(`${API_BASE}/articles/${articleId}/comparisons`);
  if (!res.ok) throw new Error(`Failed to load comparisons: ${res.statusText}`);
  return res.json();
}

export async function fetchSupplierProducts(): Promise<SupplierProduct[]> {
  const res = await fetch(`${API_BASE}/supplier-products`);
  if (!res.ok) throw new Error(`Failed to load supplier products: ${res.statusText}`);
  return res.json();
}

export async function runComparisons(): Promise<{ status: string; total_comparisons: number; articles_processed: number }> {
  const res = await fetch(`${API_BASE}/comparisons/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Failed to run comparisons: ${res.statusText}`);
  return res.json();
}

export async function fetchComparison(id: number): Promise<ComparisonResult> {
  const res = await fetch(`${API_BASE}/comparisons/${id}`);
  if (!res.ok) throw new Error(`Failed to load comparison ${id}: ${res.statusText}`);
  return res.json();
}

export async function fetchQuestions(status?: string): Promise<InformationRequest[]> {
  const url = status ? `${API_BASE}/questions?status=${encodeURIComponent(status)}` : `${API_BASE}/questions`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load questions: ${res.statusText}`);
  return res.json();
}

export async function submitAnswer(questionId: number, answerText: string, answeredBy: string = 'Supplier Representative'): Promise<any> {
  const res = await fetch(`${API_BASE}/questions/${questionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      answer_text: answerText,
      answered_by: answeredBy,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Failed to submit answer: ${res.statusText}`);
  }
  return res.json();
}

export async function resetDatabase(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/reset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to reset data: ${res.statusText}`);
  return res.json();
}
