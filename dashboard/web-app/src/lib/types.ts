export type TrafficLightStatus = "GREEN" | "YELLOW" | "RED" | string;

export type AnalyzeFarmRequestPayload = {
  gps_coordinates: {
    latitude: number;
    longitude: number;
  };
  farmer_mobile: string;
  loan_amount: number;
  references: [string, string];
  banker_id: string;
};

export type AnalyzeFarmResponse = {
  application_id: string;
  status: "processing" | "completed";
  message: string;
};

export type BankerApplicationItem = {
  application_id: string;
  farmer_mobile: string;
  loan_amount: number;
  status: string;
  created_at: string;
  overall_score: number | null;
  traffic_light_status: TrafficLightStatus | null;
};

export type BankerApplicationsResponse = {
  banker_id: string;
  applications: BankerApplicationItem[];
};

export type LayerScore = {
  score: number | null;
  status: string | null;
  quality?: number | null;
  provider_status?: string | null;
  flags: string[];
};

export type DebtLayerScore = LayerScore & {
  existing_debt?: number | null;
  proposed_debt?: number | null;
  estimated_income?: number | null;
  debt_to_income_ratio?: number | null;
};

export type SocialLayerScore = LayerScore & {
  verified_references?: number | null;
};

export type YellowExplanationBundle = {
  primary_reasons: string[];
  missing_or_low_confidence_data: string[];
  recommended_manual_checks: string[];
  expected_impact_if_approved: string;
  expected_impact_if_rejected: string;
};

export type RiskScoreResponse = {
  application_id: string;
  satellite: LayerScore;
  debt: DebtLayerScore;
  social: SocialLayerScore;
  overall_score: number | null;
  traffic_light_status: TrafficLightStatus | null;
  rationale: string | null;
  yellow_explanation?: YellowExplanationBundle | null;
  metadata: {
    created_at: string;
    processing_time_seconds: number;
    data_quality_flags: string[];
  };
};

export type DecisionRequestPayload = {
  manual_action?: "approve" | "reject" | "escalate";
  satellite_score: number;
  debt_score: number | null;
  social_score: number | null;
  satellite_data_quality: number;
  debt_to_income_ratio: number | null;
  debt_status: string | null;
  social_verified_references: number | null;
  satellite_no_crop_history: boolean;
  satellite_fire_detected: boolean;
  identity_verification_failed: boolean;
  rationale_override: string | null;
  actor_id: string;
};

export type DecisionResponse = {
  application_id: string;
  assessment_id: string;
  overall_score: number;
  traffic_light_status: string;
  status: string;
  rationale: string;
  yellow_explanation: YellowExplanationBundle | null;
  decision_rule_version: string | null;
  decision_rule_id: string | null;
  manual_action?: "approve" | "reject" | "escalate" | null;
};

export type ConnectivityCheckResponse = {
  scene: {
    scene_id: string;
    acquired_at: string;
    cloud_cover: number | null;
    bands: Record<string, string>;
  };
  stac_search_latency_ms: number;
  sas_sign_latency_ms: number;
  download_probes: Array<{
    band: string;
    bytes_downloaded: number;
    latency_ms: number;
  }>;
};

export type AgentRecommendationResponse = {
  application_id: string;
  generated_at: string;
  traffic_light_status: string | null;
  graph_path: string[];
  recommendation: {
    action: "approve" | "reject" | "escalate";
    confidence: number;
    summary: string;
    primary_reasons: string[];
    required_checks: string[];
    expected_impact_if_approved: string;
    expected_impact_if_rejected: string;
  };
};
