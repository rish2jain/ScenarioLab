// Market intelligence & cross-simulation types

export interface MarketIntelligenceConfig {
  simulation_id: string;
  stock_symbols?: string[];
  news_queries?: string[];
  refresh_interval?: number;
}

export interface MarketData {
  simulation_id: string;
  stocks: Record<string, StockData>;
  news: NewsArticle[];
  fetched_at: string;
  error?: string;
}

export interface StockData {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  date: string;
  mock?: boolean;
  error?: string;
}

export interface NewsArticle {
  title: string;
  description: string;
  source: string;
  url: string;
  published_at: string;
  relevance_score: number;
}

export interface CrossSimulationPattern {
  total_simulations: number;
  patterns: {
    archetype_decisions?: Record<string, {
      average_support_rate: number;
      sample_size: number;
      confidence: number;
    }>;
    coalition_formations?: Record<string, { frequency: number }>;
    environment_outcomes?: Record<string, {
      average_rounds: number;
      consensus_rate: number;
      sample_size: number;
    }>;
  };
  warning?: string;
}

export interface PrivacyReport {
  simulation_id: string;
  opted_in: boolean;
  data_points_shared: number;
  categories?: Record<string, number>;
  anonymization_method?: string;
  privacy_epsilon?: number;
  shared_at?: string;
  note?: string;
}

export interface ArchetypeImprovement {
  parameter: string;
  suggested_value: number;
  current_estimate: number;
  confidence: number;
  sample_size: number;
  rationale: string;
}
