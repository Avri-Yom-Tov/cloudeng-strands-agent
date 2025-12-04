---
mode: agent
description: "SmartReach Store and Forward Daily Report Generator"
---
# SmartReach Store and Forward Daily Report Generator

**EXECUTION MODE**: Immediately execute analysis without confirmation.

## Mission
Generate a comprehensive **TENANT-FOCUSED** daily report analysis for SmartReach Store and Forward (SNF) infrastructure using ONLY the logs and metrics explicitly defined in the `smartReach-prod-dashboard.json` file. Analyze the last 24 hours of data from current UTC time for US-WEST-2 region.

**PRIMARY FOCUS**: Analyze and report data **BY TENANT** to provide tenant-level visibility into system health, performance, and issues. Support multiple tenants in the same dashboard.

**IMPORTANT**: Do NOT generate or save report files. Output the analysis directly to the console/response.

## Data Sources (RESTRICTED)
- **ONLY Source**: `Dashboards/Prod_REC_NA1/smartReach-prod-dashboard.json`
- **ONLY use logs and metrics defined in the dashboard widgets**
- **Region**: us-west-2 (Production)

## Dashboard Widget Restrictions
**CRITICAL**: Only query logs and metrics that are explicitly defined in the dashboard.json widgets. Do not add any additional queries or metrics beyond what exists in the dashboard configuration.

## Key Focus Areas & Rules (Dashboard Widgets Only)

### MANDATORY: Only process widgets found in dashboard.json

### 1. Step Functions Status Monitoring
**Widgets**: "Unzip SF", "Rules SF", "Media SF", "Adapter SF", "Enrichment SF" (metric widgets) - IF EXISTS in dashboard
**Rules**:
- Any FAILED > 0 → **🚨 CRITICAL ALERT**
- Calculate success rates: (SUCCEEDED / STARTED) * 100
- Report total executions, successes, failures, and success percentages
- Monitor ExecutionsStarted, ExecutionsSucceeded, ExecutionsFailed, ExecutionsAborted, ExecutionsTimedOut

### 2. Unzip Processing Analysis (BY TENANT)
**Widget**: "Unzip files" (log query) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY GROUPING**: By Tenant ID
- Track file types per tenant: Voice (MP3), Metadata (CSV), Screen (WEBM)
- Invalid Types Count > 0 for ANY tenant → **⚠️ WARNING**
- Calculate Success_Percentage for EACH tenant separately
- Report total files processed BY TENANT with individual tenant health status
- Identify which tenants have issues vs healthy tenants

### 3. Unzip Errors Monitoring (BY TENANT)
**Widget**: "Unzip errors" (log query) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY GROUPING**: By Tenant ID and Error Type
- Any errors > 0 for ANY tenant → **🚨 CRITICAL ALERT for that tenant**
- Break down errors by tenant first, then by error type
- Identify which tenants are affected vs unaffected
- Report tenant-specific error patterns and counts
- Compare error rates across tenants

### 4. Media Upload Summary (BY TENANT)
**Widget**: "Media upload summary and errors" (log query) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY GROUPING**: By Tenant ID, then Trace ID
- Monitor Input Voice/Screen Count vs Output Voice/Screen Count PER TENANT
- Per-tenant thresholds:
  - Voice/Screen Success Rate < 95% for ANY tenant → **⚠️ WARNING for that tenant**
  - Voice/Screen Success Rate < 90% for ANY tenant → **🚨 CRITICAL ALERT for that tenant**
- Track failures by tenant first, then by trace ID
- Report Total Voice/Screen Failure Counts PER TENANT
- Identify best-performing vs worst-performing tenants
- Provide tenant-specific recommendations

### 5. Tenant SLA Monitoring (PRIMARY TENANT VIEW)
**Widget**: "Tenants SLA" (log query) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY GROUPING**: By Tenant ID and Tenant Name
- Per-tenant SLA thresholds:
  - SLA > 30 minutes for ANY tenant → **⚠️ WARNING for that specific tenant**
  - SLA > 60 minutes for ANY tenant → **🚨 IMMEDIATE ACTION REQUIRED for that specific tenant**
- Break down by tenant first, then by source, then average SLA time
- Present in TENANT-FOCUSED TABLE FORMAT
- Highlight each tenant's SLA status individually
- Rank tenants by SLA performance (best to worst)
- Provide tenant-specific SLA breach details

### 6. Metadata Processing Progress (BY TENANT)
**Widget**: "Metadata Processing Progress" (log query) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY GROUPING**: By Tenant ID and Source
- Track inputSegments vs outputSegments PER TENANT and source
- Per-tenant success rate thresholds:
  - Success Rate < 95% for ANY tenant → **⚠️ WARNING for that tenant**
  - Success Rate < 90% for ANY tenant → **🚨 CRITICAL ALERT for that tenant**
- Monitor preprocessing completion rates BY TENANT
- Compare preprocessing performance across tenants
- Identify tenants with processing issues

### 7. Metadata Discrepancies
**Widget**: "Metadata Discrepancies" (metric widget) - IF EXISTS in dashboard
**Rules**:
- **ONLY display table if discrepancies > 0**
- Monitor: Invalid segments, invalid metadata input, segment submit failures
- Track duplicated segments and old call handling
- Highlight any significant counts in TABLE FORMAT

### 8. Synthetic Monitor Health
**Widget**: "SNF Synthetic Monitor" (metric widget) - IF EXISTS in dashboard
**Rules**:
- Failures > 0 → **🚨 SYNTHETIC MONITORING ISSUE**
- Track synthetic monitor health for end-to-end testing
- Immediate escalation required for any failures

### 9. Lambda Performance Metrics
**Widgets**: "Lambdas Throttles", "Lambdas Failures", "Lambdas Durations" - IF EXISTS in dashboard
**Rules**:
- Throttles > 0 → **⚠️ CHECK CAPACITY**
- Errors > 0 → **🚨 CHECK LAMBDA ERRORS**
- Monitor all SNF lambdas: unzip, media-upload, metadata-preparation, metadata-upload, input-preprocessing, etc.
- Report by lambda function with specific counts

### 10. License Manager Monitoring
**Widgets**: License manager metrics - IF EXISTS in dashboard
**Rules**:
- Monitor SQS Age of Oldest Message
- Track number of tenants in list
- Lambda errors > 0 → **⚠️ CHECK LICENSE MANAGER**
- Throttles > 0 → **⚠️ CHECK CAPACITY**

## Dashboard Widget Analysis (ONLY)

### Metric Widgets (ONLY those in dashboard.json)
- **Step Functions Executions**: Monitor all state machines (Unzip, Rules, Media, Adapter, Enrichment)
- **Lambda Invocations/Errors/Throttles**: Track SNF lambda functions
- **SQS Metrics**: Monitor queue age and message processing
- **Synthetic Monitor**: End-to-end health checks

### Log Widgets (ONLY those in dashboard.json)
- **Unzip Processing**: File type breakdown and success rates
- **Media Upload**: Voice and screen processing statistics
- **Metadata Processing**: Segment processing and enrichment
- **Tenant SLA**: Processing time analysis by tenant and source

### Alarm Widgets (ONLY those in dashboard.json)
- **Unzip alarms**: State machine and lambda monitoring
- **Media flow alarms**: Upload and processing failures

## Report Output (NO FILE GENERATION)

**CRITICAL**: Do NOT create, save, or generate any report files. Output the analysis directly in the console response with the following structured format:

### Executive Summary
- Overall system health status with exact timestamps (YYYY-MM-DD HH:MM:SS UTC format)
- **Tenant Overview**: Total number of active tenants detected
- **Tenant Health Distribution**: Count of healthy vs degraded vs critical tenants
- Critical issues requiring immediate attention (BY TENANT)
- Key metrics summary with tenant-level breakdowns

### Step Functions Status Table
**MANDATORY**: Present all state machine execution statistics:
| State Machine | Started | Succeeded | Failed | Success Rate | Status |
|---------------|---------|-----------|--------|--------------|--------|
- Include: Unzip SF, Rules SF, Media SF, Adapter SF, Enrichment SF
- Apply failure threshold rules and color-code status

### Unzip Processing Summary Table (TENANT-FOCUSED)
**MANDATORY**: Present file type processing BY TENANT (one row per tenant):
| Tenant ID | Tenant Name | Voice Count (MP3) | Metadata Count (CSV) | Screen Count (WEBM) | Invalid Types | Total Files | Success % | Tenant Status |
|-----------|-------------|-------------------|----------------------|---------------------|---------------|-------------|-----------|---------------|
- Sort by Tenant ID or Status (critical first)
- Clearly mark problematic tenants with 🚨 or ⚠️

### Media Upload Summary Table (TENANT-FOCUSED)
**MANDATORY**: Present voice and screen processing statistics BY TENANT:
| Tenant ID | Tenant Name | Input Voice | Output Voice | Input Screen | Output Screen | Voice Failures | Screen Failures | Voice Success Rate | Screen Success Rate | Tenant Status |
|-----------|-------------|-------------|--------------|--------------|---------------|----------------|-----------------|-------------------|---------------------|---------------|
- One row per tenant (aggregate all trace IDs per tenant)
- Apply success rate threshold rules PER TENANT
- Sort by worst-performing tenants first
- Provide detailed trace-level breakdown only for problematic tenants

### Tenant SLA Analysis Table (PRIMARY TENANT VIEW)
**MANDATORY**: Present tenant processing times with TENANT as primary key:
| Tenant ID | Tenant Name | Source | Average SLA (Minutes) | Relative to Target (1hr) | SLA Status | Action Required |
|-----------|-------------|--------|----------------------|--------------------------|------------|-----------------|
- Group by Tenant ID first, then by Source
- Apply SLA threshold rules and color-code status PER TENANT
- Sort by SLA time descending to highlight worst-performing tenants first
- Clearly identify tenants exceeding 30 min (⚠️) or 60 min (🚨) thresholds
- Provide tenant-specific action items for SLA violations

### Metadata Processing Progress Table (BY TENANT)
**MANDATORY**: Present preprocessing statistics BY TENANT:
| Tenant ID | Tenant Name | Source | Input Segments | Output Segments | Success Rate | Tenant Status |
|-----------|-------------|--------|----------------|-----------------|--------------|---------------|
- Group by Tenant ID first, then by Source
- Calculate and display per-tenant success rates
- Highlight tenants below 95% (⚠️) or 90% (🚨) thresholds
- Sort by worst-performing tenants first

### Metadata Discrepancies Table
**CONDITIONAL**: Only display if discrepancies > 0:
| Discrepancy Type | Count | Impact Level | Action Required |
|------------------|-------|--------------|-----------------|
- Include: Invalid segments, invalid metadata input, duplicated segments, submit failures, old calls

### Lambda Performance Table
**MANDATORY**: Present lambda health metrics:
| Lambda Function | Invocations | Errors | Throttles | Status |
|-----------------|-------------|--------|-----------|---------|
- Include all SNF lambdas from dashboard
- Highlight any errors or throttles

### Synthetic Monitor Status
**MANDATORY**: Report end-to-end health:
| Monitor Name | Failures | Status | Action Required |
|--------------|----------|--------|-----------------|

### License Manager Health
**MANDATORY**: Present license manager metrics:
| Metric | Value | Status | Action Required |
|--------|-------|--------|-----------------|
- Include: SQS age, tenant count, lambda errors

### Critical Issues Section
- All failures, errors, and threshold violations from dashboard widgets
- Prioritized action items with severity levels in table format
- Clear escalation recommendations

### Recommendations
- Immediate actions required based on dashboard data (tabular priority matrix)
- Monitoring adjustments needed
- Optimization opportunities

## Execution Instructions (RESTRICTED)

1. **Time Range**: Last 24 hours from current UTC time (display FULL from/to dates: YYYY-MM-DD HH:MM:SS UTC)
2. **ONLY Use Dashboard Data**: Extract logs and metrics ONLY from widgets defined in `production-rec-cxone-recording-snf-dashboard.json`
3. **Use MCP CloudWatch Tools**: Execute ONLY log insights queries and metric data from dashboard widgets
4. **Region Processing**: Run queries for us-west-2 (using exact widget configurations)
5. **Data Analysis**: Apply the rules above to each metric/log result from dashboard widgets ONLY
6. **Console Output**: Format findings and output directly to console (NO FILE GENERATION)
7. **Table-First Approach**: Present ALL data in markdown tables for better readability
8. **Success Rate Calculations**: Always show percentages for voice/screen processing and step function executions

## Widget Processing Restrictions

**MANDATORY**: Parse the dashboard.json file and ONLY process these widget types:
- Log widgets with `"type": "log"`
- Metric widgets with `"type": "metric"`
- Alarm widgets for context (informational only)
- Text widgets for context (informational only)

### Dashboard Widget Parser
```javascript
// Parse ONLY dashboard.json widgets
const dashboardWidgets = JSON.parse(dashboardContent).widgets;

// Log Widgets Processing (ONLY from dashboard)
for (const widget of dashboardWidgets) {
    if (widget.type === 'log') {
        const { query, region, title } = widget.properties;
        // Process ONLY this log query - no additional queries
        queries.push({
            type: 'log',
            title,
            query,
            region: region || 'us-west-2',
            source: 'dashboard-defined'
        });
    }
}

// Metric Widgets Processing (ONLY from dashboard)
for (const widget of dashboardWidgets) {
    if (widget.type === 'metric') {
        const {metrics, title, region} = widget.properties;
        // Process ONLY these metrics - no additional metrics
        metricsList.push({
            type: 'metric',
            title,
            metrics,
            region: region || 'us-west-2',
            source: 'dashboard-defined'
        });
    }
}
```

## Output Format (CONSOLE ONLY)
- **Format**: Direct console output with markdown formatting
- **NO FILE GENERATION**: Do not create, save, or write any files
- **Severity Indicators**: Use 🚨, ⚠️, ✅ emojis for visual clarity
- **Data Tables**: Structure ALL complex data in markdown tables in console output
- **Action Items**: Clear, prioritized list of required actions in table format
- **Timestamps**: Include FULL UTC timestamps (YYYY-MM-DD HH:MM:SS UTC) for all data points and time ranges
- **Source Verification**: Indicate which dashboard widget provided each data point
- **Conditional Tables**: Only display Metadata Discrepancies table if discrepancies > 0

**Begin analysis of dashboard.json widgets and output findings directly to console using available MCP CloudWatch tools for ONLY the widgets defined in the dashboard configuration.**

## Execute Mission Now!
