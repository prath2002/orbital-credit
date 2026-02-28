# Requirements Document

## Introduction

Orbital-Credit is an Autonomous Underwriting Agent that uses satellite imagery and AI to remotely verify rural farmers' creditworthiness for nano-loans (₹20k - ₹50k). The system addresses the "credit invisible" problem where farmers lack formal income documents, making traditional lending impossible due to expensive manual verification costs.

## Glossary

- **System**: The Orbital-Credit autonomous underwriting platform
- **Banker**: Rural bank employee who makes final lending decisions
- **Farmer**: Rural farmer applying for nano-loans without formal income documentation
- **NDVI**: Normalized Difference Vegetation Index - satellite-derived measure of vegetation health
- **AA_Framework**: Account Aggregator Framework for debt verification
- **JLG**: Joint Liability Group - social trust mechanism using references
- **Risk_Engine**: Three-layer risk assessment system combining satellite, debt, and social data
- **Traffic_Light_System**: Decision framework categorizing applications as Green (auto-approve), Red (auto-reject), or Yellow (human review)

## Requirements

### Requirement 1: Satellite-Based Farm Analysis

**User Story:** As a banker, I want to automatically assess a farmer's ability to pay using satellite data, so that I can make lending decisions without expensive field visits.

#### Acceptance Criteria

1. WHEN GPS coordinates are provided, THE System SHALL retrieve Sentinel-2 satellite data for the last 3 years
2. WHEN satellite data is processed, THE System SHALL calculate NDVI values for vegetation analysis
3. WHEN NDVI analysis is complete, THE System SHALL detect crop cycles by identifying peaks in the NDVI curve
4. WHEN crop cycles are detected, THE System SHALL classify farms as Single Cropping (1 peak/year) or Double Cropping (2 peaks/year)
5. WHEN yield patterns are analyzed, THE System SHALL calculate volatility scores based on yield variance over time
6. WHEN thermal signatures are detected, THE System SHALL flag farms with stubble burning activity and reduce credit scores accordingly

### Requirement 2: Debt Verification Through Account Aggregator

**User Story:** As a banker, I want to verify a farmer's existing debt obligations, so that I can assess their capacity to take on additional loans.

#### Acceptance Criteria

1. WHEN a mobile number is provided, THE System SHALL integrate with the AA Framework to retrieve debt information
2. WHEN existing loans are identified, THE System SHALL calculate total outstanding debt amounts
3. WHEN new loan amount is specified, THE System SHALL verify that (Existing Debt + New Loan) does not exceed 50% of estimated income
4. IF debt-to-income ratio exceeds 50%, THEN THE System SHALL flag the application as "Over-Leveraged"
5. WHEN debt verification fails or times out, THE System SHALL handle the error gracefully and flag for manual review

### Requirement 3: Social Trust Assessment

**User Story:** As a banker, I want to assess a farmer's intent to pay through social references, so that I can evaluate repayment likelihood.

#### Acceptance Criteria

1. WHEN a farmer application is submitted, THE System SHALL require exactly 2 reference contacts
2. WHEN references are provided, THE System SHALL verify their identity and contact information
3. WHEN reference verification is complete, THE System SHALL establish a Digital Joint Liability Group
4. WHEN a borrower defaults, THE System SHALL automatically reduce the trust scores of their references
5. WHEN calculating social trust, THE System SHALL consider the historical trust scores of provided references

### Requirement 4: Traffic Light Decision Framework

**User Story:** As a banker, I want automated loan decisions with clear categorization, so that I can focus my time on borderline cases requiring human judgment.

#### Acceptance Criteria

1. WHEN all risk layers are processed, THE System SHALL categorize applications into Green, Yellow, or Red zones
2. WHEN satellite history is perfect AND no debt exists AND identity is verified, THE System SHALL assign Green Zone (auto-approve)
3. WHEN no crop history is detected OR fire signatures are found OR high debt exists, THE System SHALL assign Red Zone (auto-reject)
4. WHEN satellite data is cloudy OR scores are borderline, THE System SHALL assign Yellow Zone for human review
5. WHEN Yellow Zone applications are created, THE System SHALL generate summary reports for human bankers

### Requirement 5: Risk Score Calculation and Reporting

**User Story:** As a banker, I want detailed risk assessments with explanations, so that I can understand and validate automated decisions.

#### Acceptance Criteria

1. WHEN farm analysis is complete, THE System SHALL generate a comprehensive risk score from 0-100
2. WHEN risk scores are calculated, THE System SHALL provide detailed explanations for each risk factor
3. WHEN decisions are made, THE System SHALL generate audit trails showing all data sources and calculations
4. WHEN reports are requested, THE System SHALL present findings in banker-friendly format with visual indicators
5. WHEN explanations are generated, THE System SHALL use clear, non-technical language suitable for rural bankers

### Requirement 6: API Interface for Integration

**User Story:** As a system integrator, I want RESTful APIs for farm analysis, so that I can integrate credit decisions into existing banking workflows.

#### Acceptance Criteria

1. WHEN farm analysis is requested, THE System SHALL provide POST /analyze-farm endpoint accepting GPS coordinates and farmer details
2. WHEN risk scores are queried, THE System SHALL provide GET /risk-score endpoint returning current assessment status
3. WHEN API calls are made, THE System SHALL respond within 5 minutes for complete analysis
4. WHEN API errors occur, THE System SHALL return appropriate HTTP status codes with descriptive error messages
5. WHEN API responses are sent, THE System SHALL include all necessary data for decision making in structured JSON format

### Requirement 7: Data Quality and Error Handling

**User Story:** As a banker, I want reliable analysis even with incomplete data, so that I can make decisions despite satellite data limitations.

#### Acceptance Criteria

1. WHEN satellite data is cloudy or incomplete, THE System SHALL flag data quality issues and route to human review
2. WHEN external APIs fail, THE System SHALL implement retry logic with exponential backoff
3. WHEN data processing errors occur, THE System SHALL log detailed error information for debugging
4. WHEN insufficient data exists for analysis, THE System SHALL clearly communicate limitations to the user
5. WHEN system components are unavailable, THE System SHALL gracefully degrade functionality and notify users

### Requirement 8: Performance and Scalability

**User Story:** As a rural banker, I want fast loan processing, so that I can serve more farmers efficiently during peak seasons.

#### Acceptance Criteria

1. WHEN farm analysis is initiated, THE System SHALL complete processing within 5 minutes for 95% of requests
2. WHEN multiple requests are submitted, THE System SHALL handle concurrent processing without performance degradation
3. WHEN system load increases, THE System SHALL scale automatically to maintain response times
4. WHEN data is cached, THE System SHALL serve repeated requests for the same farm within 30 seconds
5. WHEN peak usage occurs, THE System SHALL maintain availability above 99% during business hours

### Requirement 9: Security and Privacy

**User Story:** As a farmer, I want my personal and farm data protected, so that my privacy is maintained throughout the credit assessment process.

#### Acceptance Criteria

1. WHEN farmer data is collected, THE System SHALL encrypt all personally identifiable information
2. WHEN data is transmitted, THE System SHALL use HTTPS encryption for all API communications
3. WHEN data is stored, THE System SHALL implement access controls limiting data access to authorized personnel only
4. WHEN data retention periods expire, THE System SHALL automatically purge farmer data according to regulatory requirements
5. WHEN audit logs are maintained, THE System SHALL track all data access and modifications for compliance purposes

### Requirement 10: Banker Dashboard Interface

**User Story:** As a rural banker, I want an intuitive web interface, so that I can easily review loan applications and make final decisions.

#### Acceptance Criteria

1. WHEN bankers access the system, THE System SHALL provide a React-based dashboard with clear navigation
2. WHEN applications are displayed, THE System SHALL show traffic light status with color-coded indicators
3. WHEN detailed analysis is requested, THE System SHALL present satellite imagery, risk scores, and explanations in organized sections
4. WHEN decisions are made, THE System SHALL provide approve/reject buttons with confirmation dialogs
5. WHEN application history is needed, THE System SHALL maintain searchable records of all processed applications