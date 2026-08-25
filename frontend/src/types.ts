export interface HospitalArticle {
  id: number;
  internal_id: string;
  raw_name: string;
  brand: string | null;
  article_number: string | null;
  annual_quantity: number | null;
  order_unit: string | null;
  base_units_per_order_unit: number | null;
  base_unit: string | null;
  gtin: string | null;
  ean: string | null;
  mdr_class: string | null;
  net_target_price: number | null;
  currency: string | null;
  product_category: string | null;
  product_subcategory: string | null;
  manufacturer: string | null;
  material: string | null;
  sterility: string | null;
  size_label: string | null;
  dimensions: Record<string, number> | null;
  connector_type: string | null;
  graduation_ml: number | null;
  compatible_count: number;
  uncertain_count: number;
  incompatible_count: number;
}

export interface SupplierProduct {
  id: number;
  supplier_id: number;
  supplier_name: string | null;
  raw_name: string;
  article_number: string | null;
  brand: string | null;
  gtin: string | null;
  pzn: string | null;
  product_category: string | null;
  manufacturer: string | null;
  material: string | null;
  sterility: string | null;
  size_label: string | null;
  dimensions: Record<string, number> | null;
  connector_type: string | null;
  graduation_ml: number | null;
  mdr_class: string | null;
  packaging_unit: string | null;
  units_per_package: number | null;
  din_iso_norms: string[] | null;
}

export interface AttributeComparison {
  attribute_name: string;
  hospital_value: string | null;
  supplier_value: string | null;
  status: "match" | "conflict" | "missing" | "not_applicable";
  criticality: "hard_blocker" | "critical" | "important" | "informational";
  note: string | null;
}

export interface InformationResponse {
  id: number;
  request_id: number;
  answer_text: string;
  answered_by: string | null;
  answered_at: string | null;
}

export interface InformationRequest {
  id: number;
  comparison_id: number;
  supplier_product_id: number;
  attribute_name: string;
  question_text: string;
  status: string;
  hospital_article_name: string | null;
  supplier_product_name: string | null;
  response: InformationResponse | null;
}

export interface ComparisonResult {
  id: number;
  hospital_article_id: number;
  supplier_product_id: number;
  decision: "compatible" | "incompatible" | "uncertain";
  confidence: number;
  summary: string | null;
  reasoning_summary: string | null;
  candidate_rank: number | null;
  candidate_score: number | null;
  version: number;
  matching_attributes: AttributeComparison[];
  conflicting_attributes: AttributeComparison[];
  missing_critical_attributes: AttributeComparison[];
  all_evidence: AttributeComparison[];
  supplier_questions: InformationRequest[];
  hospital_article: HospitalArticle | null;
  supplier_product: SupplierProduct | null;
}

export interface ComparisonSummary {
  id: number;
  supplier_product_id: number;
  supplier_name: string | null;
  supplier_product_name: string;
  decision: "compatible" | "incompatible" | "uncertain";
  confidence: number;
  candidate_rank: number | null;
  summary: string | null;
  open_questions: number;
}

export interface DashboardStats {
  total_hospital_articles: number;
  total_supplier_products: number;
  total_comparisons: number;
  compatible_count: number;
  incompatible_count: number;
  uncertain_count: number;
  open_questions: number;
  answered_questions: number;
}
