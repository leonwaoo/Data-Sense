export type CellValue = string | number | boolean | null;

export type Profile = {
  dataset_id: string;
  file_name: string;
  ingest_report?: {
    header_row_number?: number | null;
    metadata_rows_skipped?: number;
    parsed_rows?: number;
    raw_rows_estimate?: number;
    expected_data_rows?: number | null;
    warnings?: string[];
  };
  rows: number;
  columns: number;
  column_names: string[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  date_conversion_suggestions?: {
    column: string;
    suggested_type: string;
    confidence: number;
    message: string;
  }[];
  date_candidates?: {
    column: string;
    kind: string;
    confidence: number;
  }[];
  missing_values: Record<string, number>;
};

export type ScoreBreakdownItem = {
  label: string;
  weight: number;
  lost_points: number;
  detail: string;
};

export type NumericOutlierDetail = {
  column: string;
  row_index: number | string;
  value: number;
  mean: number;
  deviation_ratio: number;
  lower_bound: number;
  upper_bound: number;
};

export type Quality = {
  score: number;
  score_breakdown?: ScoreBreakdownItem[];
  missing_total: number;
  duplicate_rows: number;
  empty_columns: string[];
  numeric_outliers?: Record<string, number>;
  numeric_outlier_details?: NumericOutlierDetail[];
  recommendations: string[];
};

export type ChartPayload = {
  type: string;
  x: string;
  y: string;
  data: Record<string, string | number>[];
};

export type Answer = {
  answer: string;
  calculation: string | null;
  table: Record<string, string | number>[];
  chart: ChartPayload | null;
};

export type ManagerialInsight = {
  id: string;
  title: string;
  severity: "danger" | "warning" | "info" | "neutral";
  metric: string | null;
  period: string | null;
  what_changed: string;
  how_much: string;
  where: string;
  possible_causes: string[];
  managerial_impact: string;
  recommendation: string;
  confidence: "alta" | "media" | "baixa" | string;
  evidence: string[];
};

export type ManagerialDriver = {
  driver: string;
  column: string;
  current_value: number | null;
  previous_value: number | null;
  variation: number | null;
  variation_pct: number | null;
  reading: string;
};

export type ManagerialMonthlyComparison = {
  period: string;
  value: number | null;
  previous_value: number | null;
  variation: number | null;
  variation_pct: number | null;
  historical_mean: number | null;
  z_score: number | null;
  status: string;
  severity: "danger" | "warning" | "info" | "neutral";
  managerial_reading: string;
  main_driver: ManagerialDriver | null;
  drivers: ManagerialDriver[];
};

export type ManagerialComparativeSummary = {
  cards: {
    label: string;
    value: string;
    detail: string;
    tone?: "neutral" | "good" | "warning" | "danger" | string;
  }[];
  readings: string[];
};

export type RootCauseContributor = {
  name: string;
  current_value: number | null;
  previous_value: number | null;
  variation: number | null;
  variation_pct_vs_previous?: number | null;
  share_of_abs_change: number | null;
  share_of_total_change: number | null;
  historical_mean?: number | null;
  historical_delta?: number | null;
  concentration_level?: "alta" | "media" | "baixa" | string;
  recurrence_flag?: "recorrente" | "pontual" | string;
};

export type RootCauseDimensionDriver = {
  dimension: string;
  label: string;
  contributors: RootCauseContributor[];
  coverage: number | null;
};

export type RootCauseImpactRank = RootCauseContributor & {
  dimension: string;
  label: string;
  reading: string;
};

export type DimensionNarrative = {
  dimension: string;
  label: string;
  top_movers: RootCauseContributor[];
  share_concentration: {
    top_1: number | null;
    top_3: number | null;
    level: "alta" | "media" | "baixa" | string;
  };
  historical_comparison: {
    historical_mean: number | null;
    historical_delta: number | null;
    historical_delta_pct: number | null;
  };
  narrative: string;
  managerial_impact: string;
  possible_causes?: string[];
  recommendation?: string;
};

export type RootCauseWaterfallStep = {
  label: string;
  kind: "baseline" | "increase" | "decrease" | "current" | string;
  value: number | null;
  delta: number | null;
  running_total: number | null;
};

export type RootCauseAnalysis = {
  title: string;
  metric: string;
  period: string;
  previous_period: string | null;
  movement: {
    current_value: number | null;
    previous_value: number | null;
    variation: number | null;
    variation_pct: number | null;
    direction: string;
  };
  responsible_month: {
    period: string;
    label: string;
    historical_mean: number | null;
    historical_delta: number | null;
    historical_delta_pct: number | null;
    z_score: number | null;
  };
  primary_contributor: RootCauseContributor | null;
  dimension_drivers: RootCauseDimensionDriver[];
  dimension_impact_ranking?: RootCauseImpactRank[];
  dimension_narratives?: DimensionNarrative[];
  concentration_alerts?: string[];
  supporting_metrics: ManagerialDriver[];
  waterfall: {
    dimension?: string | null;
    top_contributor?: RootCauseContributor | null;
    steps: RootCauseWaterfallStep[];
  };
  summary: string[];
  confidence: "alta" | "media" | "baixa" | string;
  recommendation: string;
};

export type ManagerialAnalysis = {
  mode: string;
  title: string;
  summary: string[];
  context: {
    domain: {
      type: string;
      label: string;
      confidence: number;
      reasons: string[];
    };
    metric_map: {
      primary_metric: string | null;
      support_metrics: Record<string, string>;
      mapped_columns: Record<string, string | null>;
    };
    time: {
      available: boolean;
      label?: string | null;
      columns: string[];
    };
    dimensions: { label: string; column: string }[];
    limitations: string[];
  };
  kpis: { label: string; value: string; detail: string }[];
  insights: ManagerialInsight[];
  root_cause_analysis?: RootCauseAnalysis | null;
  dimension_narratives?: DimensionNarrative[];
  monthly_comparisons?: ManagerialMonthlyComparison[];
  comparative_summary?: ManagerialComparativeSummary;
  alerts: string[];
  recommendations: string[];
  suggested_questions: string[];
};

export type ManagerialAiCause = {
  title: string;
  detail: string;
  confidence: string;
  evidence: string[];
};

export type ManagerialAiReview = {
  mode: string;
  ai_enabled: boolean;
  ai_status: "not_configured" | "disabled" | "failed" | "completed" | string;
  ai_error?: string;
  model: string | null;
  executive_summary: string;
  what_changed: string;
  likely_causes: ManagerialAiCause[];
  managerial_impact: string;
  recommendations: string[];
  investigation_questions: string[];
  confidence: string;
};

export type SuggestedQuestion = {
  question: string;
  category: string;
};

export type UploadResponse = {
  dataset_id: string;
  file_name: string;
  profile: Profile;
  preview: Record<string, CellValue>[];
  quality: Quality;
  managerial_analysis?: ManagerialAnalysis;
  suggested_questions?: SuggestedQuestion[];
  supported_formats?: string[];
};

export type DashboardKpi = {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "accent" | "good" | "warning" | "danger";
};

export type DashboardChart = ChartPayload & {
  id: string;
  title: string;
  subtitle: string;
  insight: string;
  available_types?: string[];
};

export type DashboardPayload = {
  title: string;
  subtitle: string;
  domain: {
    type: string;
    label: string;
    confidence: number;
    reasons: string[];
  };
  kpis: DashboardKpi[];
  charts: DashboardChart[];
  insights: string[];
  filters: DashboardFilterControls;
  quality: {
    score: number;
    score_breakdown?: ScoreBreakdownItem[];
    missing_total: number;
    duplicate_rows: number;
    empty_columns: string[];
    numeric_outliers?: Record<string, number>;
    numeric_outlier_details?: NumericOutlierDetail[];
  };
};

export type DashboardFilters = {
  date_from?: string;
  date_to?: string;
  categories: Record<string, string[]>;
};

export type DashboardFilterControls = {
  date: {
    column: string;
    min: string;
    max: string;
    selected_from: string | null;
    selected_to: string | null;
  } | null;
  categories: {
    label: string;
    column: string;
    values: { value: string; count: number }[];
    selected: string[];
  }[];
  applied_count: number;
  rows_before_filter: number;
  rows_after_filter: number;
};

export type DashboardTheme = "teal" | "blue" | "violet" | "graphite";

export type DashboardSettings = {
  title: string;
  theme: DashboardTheme;
  logoDataUrl: string | null;
};

export type HistoryItem = {
  datasetId: string;
  fileName: string;
  rows: number;
  columns: number;
  qualityScore: number;
  domainLabel: string;
  createdAt: string;
};

export type SectionKey = "overview" | "diagnostic" | "dashboard" | "chat" | "reports";
