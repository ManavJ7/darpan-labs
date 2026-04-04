export interface ConceptInfo {
  id: number;
  name: string;
  short_name: string;
  color: string;
}

export interface MetricData {
  t2b: number | null;
  mean: number | null;
  n: number;
}

export interface T2BData {
  [conceptName: string]: {
    [metricName: string]: MetricData;
  };
}

export interface FriedmanResult {
  statistic: number | null;
  p_value: number | null;
  n: number;
  significant: boolean;
}

export interface WilcoxonResult {
  pair: [string, string];
  statistic: number | null;
  p_value: number | null;
  p_adjusted: number | null;
  significant: boolean;
  n: number;
}

export interface MixedModelResult {
  concept_var_pct: number;
  position_var_pct: number;
  respondent_var_pct: number;
  verdict: string;
}

export interface TurfResult {
  individual_reach: { [concept: string]: number };
  best_2: { concepts: string[]; reach_pct: number; reach_n: number };
  best_3: { concepts: string[]; reach_pct: number; reach_n: number };
}

export interface BarrierItem {
  name: string;
  count: number;
  pct: number;
}

export interface BarrierData {
  barriers: BarrierItem[];
  total_mentions: number;
}

export interface DirectRankingItem {
  top3_count: number;
  top3_pct: number;
  rank1_count: number;
  rank1_pct: number;
}

export interface ThemeItem {
  theme_name: string;
  frequency: number;
  sentiment: string;
  representative_quote: string;
}

export interface PriceData {
  price_pi: MetricData;
  wtp: {
    mean: number | null;
    median: number | null;
    min: number | null;
    max: number | null;
    n: number;
  };
}

export interface ScreeningContext {
  frequencies: { [key: string]: number };
  satisfaction: { [key: string]: number };
  top_brands: { [key: string]: number };
  n: number;
}

export interface DataBlock {
  n: number;
  t2b: T2BData;
  composites: { [concept: string]: number | null };
  friedman: FriedmanResult;
  wilcoxon: WilcoxonResult[];
  tiers: { [concept: string]: number };
  mixedModel: MixedModelResult;
  turf: TurfResult;
  barriers: { [concept: string]: BarrierData };
  directRanking: { [concept: string]: DirectRankingItem };
  priceData: PriceData;
  screeningContext: ScreeningContext;
  themes: { [concept: string]: { appealing: ThemeItem[]; change: ThemeItem[] } };
}

export interface AgreementData {
  level: "Confirmed" | "Directional" | "Divergent";
  description: string;
  real_tier1: string[];
  twin_tier1: string[];
  real_top: string;
  twin_top: string;
}

export interface DashboardData {
  metadata: {
    study: string;
    concepts_tested: number;
    real_n: number;
    twin_n: number;
    concept_names: string[];
    concept_short_names: string[];
  };
  concepts: ConceptInfo[];
  real: DataBlock;
  twin: DataBlock;
  agreement: AgreementData;
}

export type DataSource = "real" | "twin" | "both";

export type DashboardTab = "aggregate" | "individual" | "extended-aggregate" | "extended-validation";
