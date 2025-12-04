---
mode: agent
model: Claude Sonnet 4.5
description: "AppLink Daily Report"
---
# AppLink Daily Report Generator V2

**EXECUTION MODE**: Immediately execute analysis without confirmation.

## Mission
Generate a comprehensive daily report analysis for AppLink infrastructure using ONLY the logs and metrics explicitly defined in the `applink-prod-dashboard.json` file. Analyze the last 24 hours of data from current UTC time for both US-WEST-2 and EU-WEST-2 regions. 

**IMPORTANT**: Do NOT generate or save report files. Output the analysis directly to the console/response.

## Data Sources (RESTRICTED)
- **ONLY Source**: `Dasboards/Prod_NA1/WFO/applink-prod-dashboard.json`
- **ONLY use logs and metrics defined in the dashboard widgets**
- **Regions**: 
  - us-west-2 (Production NA)
  - eu-west-2 (Production UK - replace "production-" with "production-uk-")

## Dashboard Widget Restrictions
**CRITICAL**: Only query logs and metrics that are explicitly defined in the dashboard.json widgets. Do not add any additional queries or metrics beyond what exists in the dashboard configuration.

## Key Focus Areas & Rules (Dashboard Widgets Only)

### MANDATORY: Only process widgets found in dashboard.json

### 1. Media State Machine Statistics
**Widget**: "Media State Machine Statistics" (log query) - IF EXISTS in dashboard
**Rules**:
- Any failures > 0 → **🚨 CRITICAL ALERT - ESCALATE TO AMIGOS TEAM**
- Calculate success rates for both audio and screen state machines
- Report total executions, successes, failures, and success percentages
- **ESCALATION**: ALL media-related issues (audio/voice and screen state machine failures) → Contact Amigos Team: WCXPTUCXoneHybridRDAmigos@nice.com

### 2. Input / Success SLA Monitoring  
**Widget**: "Input / Success" (log query) - IF EXISTS in dashboard
**Rules**:
- SLA < 30 minutes → **✅ HEALTHY**
- SLA 30-60 minutes → **⚠️ WARNING** - Monitor closely
- SLA > 60 minutes → **🚨 CRITICAL - ESCALATE TO DEF TEAM**
- Break down by tenant with average processing times in UNIFIED TABLE FORMAT
- **MANDATORY**: Query BOTH US-WEST-2 AND EU-WEST-2 regions
- **EXCLUDE test tenants** (filter out tenants with "TEST", "E2E", "PERM", "B32" in names)
- Present both regions in single table with Region column
- Highlight any tenant exceeding thresholds
- **SLA RESPONSIBILITY**: SLA violations are primarily caused by DEF (Data Exchange Framework) delays in file delivery (99% of cases). Escalate to DEF team first, not Rockets team.
- **MISSED CALLS FLOW IMPACT**: Monitor for old call segments (>7 days) being processed through the missed calls flow, which can significantly inflate SLA metrics. Check missed calls flow metrics and investigate extreme SLA outliers (>1000 minutes) as potential historical backlog processing.

### 3. Interactions Processing Distribution
**Widget**: "Interactions processing distribution diagram" (pie chart) - IF EXISTS in dashboard
**Rules**:
- Analyze the flow: DEF → Valid Segments → SQS → Kinesis
- Report on duplicate segments, invalid segments, filtering
- Calculate processing efficiency percentages
- Identify bottlenecks or anomalies in the processing pipeline

### 4. Old Calls vs New Calls Analysis
**Widget**: "Old calls vs new calls" (pie chart) - IF EXISTS in dashboard
**Rules**:
- Compare ratio of old vs new segments from DEF
- Analyze trends and provide insights on call patterns
- Flag unusual ratios that might indicate issues
- **MISSED CALLS FLOW**: Monitor metrics for old segments redirected to missed calls flow
  - Check: `production-uk-missed-calls-lambda-batch-size-information`
  - Check: `production-uk-missed-calls-lambda-number-of-valid-segments-received-from-DEF`
  - Check: `production-uk-missed-calls-lambda-number-of-segments-received-from-metadata-producer` (sent to SQS)
  - Check: `production-uk-missed-calls-lambda-number-of-duplicate-segments-received-from-DEF`
- **FLOW ARCHITECTURE**: Main flow detects old calls (>168 hours) → redirects to missed calls flow → checks tenant permissions → validates time range → filters duplicates → sends to SQS
- Report on duplicate filtering efficiency and permission-based filtering

### 5. Interactions Processing Discrepancies
**Widget**: "Interactions processing discrepancies" (timeSeries) - MANDATORY in dashboard
**Rules**:
- Monitor duplicated segments, missing audio segments, user resolution failures
- **ONLY display table if discrepancies > 0**
- Highlight any significant spikes or anomalies in TABLE FORMAT
- Provide insights on data quality issues
- **If widget is missing or data cannot be retrieved**: 🚨 Contact Rockets Team - Critical monitoring widget unavailable

### 6. SM Failures (Synthetic Monitoring)
**Widget**: "SM Failures" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- Failures > 0 → **🚨 SYNTHETIC MONITORING ISSUE**
- Track synthetic monitor health for end-to-end testing
- Immediate escalation required for any failures

### 7. SAP HTTP Response Codes
**Widget**: "SAP - 3XX/4XX/5XX HTTP codes" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- 3XX > 0 → **⚠️ CHECK REDIRECTS**
- 4XX > 0 → **⚠️ CHECK CLIENT ERRORS** 
- 5XX > 0 → **🚨 CHECK SERVER ERRORS**
- Report by error type with specific counts

## Dashboard Widget Analysis (ONLY)

### Metric Widgets (ONLY those in dashboard.json)
- **ONLY analyze metrics explicitly defined in dashboard widget configurations**
- **Main Lambdas Invocations**: IF EXISTS - Monitor traffic patterns
- **Main Lambdas Throttles**: IF EXISTS - Check for capacity issues  
- **Main Errors**: IF EXISTS - Track error rates across services
- **Metadata flow errors**: IF EXISTS - Detailed error breakdown

### Infrastructure Widgets (ONLY those in dashboard.json)
- **SAP Memory/CPU**: IF EXISTS - Resource utilization monitoring
- **Contact ID Ranges**: IF EXISTS - Availability and consumption tracking
- **Load Balancer Health**: IF EXISTS - Request counts and response codes

### Log Widgets (ONLY those in dashboard.json)
- **Metadata Lambdas statistics**: IF EXISTS - Processing flow analysis
- **Contact ID Producer**: IF EXISTS - Allocation success/failure rates

## Report Output (NO FILE GENERATION)

**CRITICAL**: Do NOT create, save, or generate any report files. Output the analysis directly in the console response with the following structured format:

---

## 📋 PART 1: EXECUTIVE SUMMARY & ACTION ITEMS

**Report Period**: [YYYY-MM-DD HH:MM:SS UTC] to [YYYY-MM-DD HH:MM:SS UTC]

### 🎯 Action Items Required

**CRITICAL**: Display ONLY if issues exist. If no action items, state "✅ No action items - all systems healthy"

| Priority | Issue Type | Affected Tenant(s)/Service | Action Required | Owner | Severity |
|----------|------------|---------------------------|-----------------|-------|----------|
| 1 | [Issue] | [Tenant/Service] | [Specific action] | [Team] | 🚨/⚠️ |

**Instructions**:
- List action items in priority order (most critical first)
- Include specific tenant names or services affected
- Provide clear, actionable next steps
- Assign to correct team (Amigos/DEF/Rockets)
- Only show this table if action items exist

---

### 🚨 Critical Issues (Immediate Attention Required)

**Display ONLY if critical issues exist. If none, state "✅ No critical issues detected"**

| Issue | Impact | Affected Resources | Escalation Contact |
|-------|--------|-------------------|-------------------|
| Media State Machine Failures | [X failures detected] | [Region/Type] | Amigos Team: WCXPTUCXoneHybridRDAmigos@nice.com |
| SLA > 60 minutes | [X tenants affected] | [Tenant names] | DEF Team (PRIMARY) |
| Missing Expected Tenants | [X tenants missing] | [Tenant names] | Rockets Team: WCXPTUCXoneRecordingRDRockets@nice.com |

**Only display rows with actual issues detected**

---

### ⚠️ Warnings (Monitor Closely)

**Display ONLY if warnings exist. If none, state "✅ No warnings detected"**

| Warning Type | Details | Threshold | Current Value | Trend |
|--------------|---------|-----------|---------------|-------|
| SLA 30-60 min | [Tenant names] | < 30 min | [X min] | ↑/↓/→ |
| Processing Discrepancies | [Type] | 0 expected | [X count] | ↑/↓/→ |

**Only display rows with actual warnings detected**

---

### ℹ️ Potential Issues (Investigate if Pattern Continues)

**Display ONLY if potential issues exist. If none, state "✅ No potential issues identified"**

| Observation | Details | Recommendation |
|-------------|---------|----------------|
| [Pattern observed] | [Specific details] | [Monitor/Investigate action] |

**Only display rows with actual observations**

---

### 📊 System Health Overview

| Component | Status | Details |
|-----------|--------|---------|
| **Media State Machines** | ✅/⚠️/🚨 | Audio: [X]% success, Screen: [X]% success |
| **SLA Performance** | ✅/⚠️/🚨 | [X] tenants healthy, [X] warning, [X] critical |
| **Processing Pipeline** | ✅/⚠️/🚨 | [X]% end-to-end success rate |
| **Expected Tenants** | ✅/⚠️/🚨 | [X]/[Total] tenants active |
| **Regional Health** | ✅/⚠️/🚨 | US-WEST-2: [Status], EU-WEST-2: [Status] |

---

## 📊 PART 2: DETAILED ANALYSIS & SUPPORTING DATA

### Regional Comparison (US-WEST-2 vs EU-WEST-2)
- Side-by-side metrics comparison table for dashboard widgets only
- Regional performance differences in tabular format
- Cross-region consistency analysis

---

### 📈 Input / Success SLA Analysis (Detailed Data)
**MANDATORY**: Present unified tenant SLA data from BOTH regions in single table format:
| Region | Tenant Name | Tenant ID | Input Segments | Success Segments | Avg SLA (Minutes) | SLA Status | Action Required |
|--------|-------------|-----------|----------------|------------------|-------------------|------------|-----------------|
- **INCLUDE BOTH REGIONS**: US-WEST-2 AND EU-WEST-2 in single unified table
- **EXCLUDE test tenants** (filter out tenants with "TEST", "E2E", or "PERM" in names)
- Apply SLA threshold rules:
  - SLA < 30 minutes → ✅ HEALTHY
  - SLA 30-60 minutes → ⚠️ WARNING
  - SLA > 60 minutes → 🚨 CRITICAL
- Sort by SLA time descending to highlight worst performers first
- **SLA ESCALATION**: For SLA > 60 minutes, escalate to DEF team (Data Exchange Framework) as root cause is typically DEF file delivery delays (99% of cases)

---

### 🔍 Expected Tenants Validation (Detailed Data)
**MANDATORY**: Verify presence of critical production tenants in each region:

**US-WEST-2 Expected Tenants**:
- ✅ LOWES COMPANIES, INC. (11ee324f-8cf5-8590-bcb1-0242ac110002)
- ✅ L.A. CARE HEALTH PLAN - ENTERPRISE (11ee99ce-6424-5740-a605-0242ac110006)
- ✅ MUTUAL OF OMAHA INSURANCE COMPANY (11efad0d-b533-ddb0-badf-0242ac110002)
- ✅ JEA (11eed003-bc7c-d140-810e-0242ac110004)
- ✅ AMERITAS GROUP (11efefba-6ea9-9de0-9014-0242ac110003)


**EU-WEST-2 Expected Tenants**:
- ✅ AGEAS UK - UK - ENTERPRISE (11ee047d-f96e-90e0-9d30-0242ac110002)

**Validation Rules**:
- Check if each expected tenant appears in the SLA analysis data
- Mark as ✅ if tenant found with activity, ⚠️ if found with no activity, 🚨 if missing
- Report any expected tenants that are missing from the data
- Flag tenants with zero segments processed as potential issues

---

### 🔧 Investigation Protocols (Reference Only - Use When Issues Detected)

#### Missing Tenant Investigation Protocol
**🚨 CRITICAL**: Any missing expected tenant requires immediate investigation using these debugging steps:

**Step 1: Metadata Producer Analysis**
- Query metadata producer logs for tenant ID: `filter strcontains(@message, "TENANT_ID")`
- Look for: User token failures, processing errors, DynamoDB issues, S3 errors
- Check error patterns: `ErrorMetadataProducerUserTokenFetchFailure`, `DynamoDBException`, `S3Exception`

**Step 2: Processing Flow Analysis** 
- Verify tenant data reaches each stage: DEF → Metadata → SQS → Media State Machine
- Check for: Filtering issues, validation failures, pipeline bottlenecks
- Analyze: Segment counts, processing times, error classifications

**Step 3: Infrastructure Health Check**
- Review: Lambda errors, throttling, memory issues, timeouts
- Validate: Network connectivity, service dependencies, resource limits
- Monitor: CloudWatch alarms, service health indicators

**Step 4: Data Source Verification**
- Confirm: DEF file delivery, S3 bucket accessibility, data format validity
- Check: File timestamps, size variations, corruption indicators

**ESCALATION**: Document all findings and contact Rockets Team with investigation results

#### SLA Violation Investigation Protocol
**⚠️ IMPORTANT**: SLA violations (> 60 minutes) are typically caused by DEF (Data Exchange Framework) file delivery delays in 99% of cases.

**Primary Escalation Path for SLA Violations:**
1. **DEF Team** (PRIMARY) - Investigate file delivery timing and delays
   - Check DEF file generation timestamps
   - Verify file delivery to S3 timing
   - Review DEF processing queue and backlog
   - Analyze file size and delivery patterns

**Missed Calls Flow Investigation (for extreme SLA outliers > 1000 minutes):**
1. **Check Missed Calls Flow Metrics**
   - Query: `production-uk-missed-calls-lambda-batch-size-information` metric
   - Query: `production-uk-missed-calls-lambda-number-of-valid-segments-received-from-DEF` metric
   - Query: `production-uk-missed-calls-lambda-number-of-segments-received-from-metadata-producer` metric (sent to SQS)
   - Compare: Received count vs. Sent to SQS count (difference indicates duplicate filtering)

2. **Analyze Old Call Segments**
   - Query metadata producer logs for missed calls flow lambda executions
   - Filter: `filter @message like /Missed calls contacts filter/`
   - Look for: Time range validation results ("IN TIME RANGE COUNT" vs "OUT OF TIME RANGE COUNT")
   - Check: Duplication detection messages showing filtered segments
   - Identify: Segment IDs, ages, and tenant permissions

3. **Root Cause Analysis**
   - **Historical Backlog Processing**: Old segments (>7 days) from missed calls flow can inflate SLA metrics
   - **Expected Behavior**: Main flow redirects old calls → Missed calls flow checks permissions → Validates time range → Filters duplicates → Sends to SQS
   - **Key Indicators**: 
     - Extreme SLA values (>1000 min = >16 hours, >10000 min = >1 week)
     - Segments with startTime significantly older than processing timestamp
     - Discrepancy between received segments and sent to SQS (duplicate filtering)
   - **Duplication Filtering**: Redis/cache lookup prevents reprocessing previously handled segments

4. **Validation Steps**
   - Query top segments by SLA time: `stats max(sla_time) by segment_id, tenant_name | sort max desc | limit 50`
   - Retrieve segment metadata: Check `startTime`, `updateTime`, `updateType` fields
   - Calculate actual age: Time difference between segment creation and processing
   - Verify tenant permissions: Confirm tenant enabled for missed calls flow processing

**Secondary Investigation (Only if DEF confirms timely delivery and no missed calls flow activity):**
2. **Metadata Producer Analysis**
   - Query metadata producer logs for tenant ID
   - Check processing start time vs. file arrival time
   - Look for: Processing delays, queue backlogs, resource constraints

3. **Infrastructure Review**
   - Lambda execution times and cold starts
   - SQS queue depths and message delays
   - State machine execution timing

**ESCALATION CONTACT**:
- **DEF Team** (PRIMARY for SLA > 60 min): Investigate file delivery delays
- **Amigos Team**: For DEF-related issues and file delivery investigations
- **Rockets Team** (SECONDARY): WCXPTUCXoneRecordingRDRockets@nice.com - Only after DEF confirms timely delivery and no missed calls flow anomalies detected

**CRITICAL**: For extreme SLA outliers (>1000 minutes), always investigate missed calls flow metrics and log entries before escalating to DEF team.

---

### 📊 Processing Pipeline Details

#### Missed Calls Flow Analysis (EU-WEST-2)
**CONDITIONAL**: Display if missed calls flow activity detected:
| Metric | Value | Status | Notes |
|--------|-------|--------|-------|
| Batch Size (Files Received) | X | ✅/⚠️/🚨 | New metadata files from DEF |
| Valid Segments Received | X | ✅/⚠️/🚨 | Segments passing time range validation |
| Segments Sent to SQS | X | ✅/⚠️/🚨 | Non-duplicate segments injected |
| Duplicate Segments Filtered | X | ℹ️ | Previously processed segments |
| Processing Efficiency | X% | ✅/⚠️ | (Sent to SQS / Valid Segments) * 100 |

**ANALYSIS**:
- **Flow Architecture**: Main flow → Detects old calls (>168 hours) → Redirects to missed calls flow → Checks tenant permissions → Validates time range → Filters duplicates (Redis) → Sends to SQS
- **Discrepancy Analysis**: If (Valid Segments - Sent to SQS) > 0, segments were filtered as duplicates
- **SLA Impact**: Old segments from missed calls flow can significantly inflate tenant SLA metrics
- **Investigation Trigger**: If extreme SLA outliers (>1000 min) detected, check missed calls flow for historical backlog processing

#### Interactions Processing Discrepancies Table
**CONDITIONAL**: Only display if discrepancies > 0:
| Discrepancy Type | Count | Percentage | Trend | Impact Level |
|------------------|-------|------------|-------|--------------|
- Include: Duplicated segments, missing audio, user resolution failures
- Only show table if any discrepancies detected

#### Metadata Lambdas Statistics Table
**MANDATORY**: Present unified regional comparison:
| Region | Received Files | Segments Sent to SQS | Decoration Received from SQS | Successfully Uploaded to Kinesis | Participant Validation Errors | Recording Validation Errors | SQS Send Errors |
|--------|----------------|---------------------|------------------------------|----------------------------------|------------------------------|----------------------------|-----------------|

#### Media State Machine Statistics Table
| Region | Audio Success | Audio Failures | Audio Rate | Screen Success | Screen Failures | Screen Rate | Status |
|--------|---------------|----------------|------------|----------------|-----------------|-------------|---------|

**ESCALATION**: If ANY failures detected (audio or screen) → 🚨 Contact Amigos Team (WCXPTUCXoneHybridRDAmigos@nice.com) - All media processing issues

---

### 📉 Additional Processing Metrics

#### Metadata Flow Details
**MANDATORY**: Present metadata flow data in unified regional comparison table:
| Region | Received Files | Segments Sent to SQS | Decoration Received from SQS | Successfully Uploaded to Kinesis | Participant Validation Errors | Recording Validation Errors | SQS Send Errors |
|--------|----------------|---------------------|------------------------------|----------------------------------|------------------------------|----------------------------|-----------------|
- Rows: US-WEST-2 and EU-WEST-2 regions
- Columns: Each process stage with counts and status indicators
- Include variance analysis and status indicators (✅/⚠️/🚨)

#### Dashboard Widget Analysis Tables
- Traffic patterns and trends from dashboard metrics in tabular format
- Processing efficiency metrics from dashboard logs in tables
- Resource utilization analysis from dashboard data in structured tables
- Lambda performance metrics table

---

## 💡 PART 3: RECOMMENDATIONS & NEXT STEPS

### Immediate Actions (Next 4 Hours)
**Only display if immediate actions are needed. If none, state "✅ No immediate actions required"**

| Action | Reason | Owner | Priority |
|--------|--------|-------|----------|
| [Specific action] | [Why needed] | [Team] | 🚨/⚠️ |

### Short-term Monitoring (Next 24 Hours)
**Only display if monitoring is needed. If none, state "✅ Continue standard monitoring"**

| Metric to Watch | Current Value | Target | Check Frequency |
|-----------------|---------------|--------|-----------------|
| [Metric] | [Value] | [Target] | [Frequency] |

### Optimization Opportunities
**Only display if optimizations identified. If none, state "✅ No optimization opportunities identified"**

| Opportunity | Potential Benefit | Effort | Recommendation |
|-------------|-------------------|--------|----------------|
| [Opportunity] | [Benefit] | Low/Med/High | [Action] |

## Widget Missing or Data Issues
**ESCALATION PROTOCOL**: If any of the following critical widgets are missing or fail to return data:
- "Interactions processing discrepancies" 
- "Media State Machine Statistics"
- "Input / Success" (SLA monitoring)
- "Metadata Lambdas statistics"

**ACTION**: 🚨 **Contact Rockets Team** - Report widget name and error details for immediate investigation
**Email**: WCXPTUCXoneRecordingRDRockets@nice.com

## Media State Machine Issues
**ESCALATION PROTOCOL**: If any critical issues are detected with Audio or Screen State Machines:
- Any failures > 0 (audio state machine or screen state machine)
- State machine execution errors
- Media processing failures
- Audio/Screen segment processing issues
- Media file processing timeouts or errors

**ACTION**: 🚨 **Contact Amigos Team** - ALL media-related issues (voice/audio and screen)
**Email**: WCXPTUCXoneHybridRDAmigos@nice.com

**Note**: Amigos team is responsible for all media processing pipeline issues including both audio/voice and screen recording state machines.

## Metadata Producer Issues
**ESCALATION PROTOCOL**: If any critical issues are detected with the Metadata Producer Lambda:
- Error rate > 5%
- Processing failures or timeouts
- SQS send failures
- User token fetch failures
- DynamoDB failures
- S3 put errors
- General service failures

**ACTION**: 🚨 **Contact Rockets Team** - Report error type, count, and affected tenants for immediate investigation
**Email**: WCXPTUCXoneRecordingRDRockets@nice.com

## Execution Instructions (RESTRICTED)

1. **Time Range**: Last 24 hours from current UTC time (display FULL from/to dates: YYYY-MM-DD HH:MM:SS UTC)
2. **ONLY Use Dashboard Data**: Extract logs and metrics ONLY from widgets defined in `applink-prod-dashboard.json`
3. **Use MCP CloudWatch Tools**: Execute ONLY log insights queries and metric data from dashboard widgets
4. **Region Processing**: 
   - Run queries for us-west-2 first (using exact widget configurations)
   - Run queries for eu-west-2 (replace region and service prefixes as defined in dashboard)
   - **MANDATORY**: Combine SLA data from BOTH regions into unified tables
   - Present regional comparison data side-by-side where applicable
5. **Data Analysis**: Apply the rules above to each metric/log result from dashboard widgets ONLY
6. **Console Output**: Format findings and output directly to console (NO FILE GENERATION)
7. **Test Tenant Filtering**: EXCLUDE from SLA analysis any tenant containing: "TEST", "E2E", "PERM", "B32"
8. **Table-First Approach**: Present ALL data in markdown tables for better readability
9. **Unified Metadata Table**: Combine US-WEST-2 and EU-WEST-2 metadata statistics in single comparison table

## Widget Processing Restrictions

**MANDATORY**: Parse the dashboard.json file and ONLY process these widget types:
- Log widgets with `"type": "log"` 
- Metric widgets with `"type": "metric"`
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

### Report Structure Principles
1. **Priority-First Design**: Most critical information at the top (Part 1)
2. **Actionable Focus**: Every section should lead to clear actions or "no action needed"
3. **Conditional Display**: Only show warnings/issues tables if problems exist
4. **Clear Separation**: Use visual separators (---) between major sections
5. **Three-Part Structure**:
   - **PART 1**: Action Items & Critical Issues (What needs attention NOW)
   - **PART 2**: Detailed Analysis (Supporting data and evidence)
   - **PART 3**: Recommendations (What to do next)

### Formatting Rules
- **Format**: Direct console output with markdown formatting
- **NO FILE GENERATION**: Do not create, save, or write any files
- **Severity Indicators**: Use 🚨 (Critical), ⚠️ (Warning), ✅ (Healthy), ℹ️ (Info) emojis for visual clarity
- **Data Tables**: Structure ALL complex data in markdown tables in console output
- **Action Items**: Clear, prioritized list of required actions in table format (Priority 1 = most critical)
- **Timestamps**: Include FULL UTC timestamps (YYYY-MM-DD HH:MM:SS UTC) for all data points and time ranges
- **Conditional Display**: 
  - If NO issues: State "✅ No [issues/warnings/actions] detected" instead of empty tables
  - Only show tables when there is actual data to display
  - This applies to: Action Items, Critical Issues, Warnings, Potential Issues, Recommendations
- **Test Tenant Filtering**: EXCLUDE tenants containing "TEST", "E2E", "PERM", "B32" in tenant names from SLA analysis
- **Visual Hierarchy**: 
  - Use ## for main parts (PART 1, 2, 3)
  - Use ### for major sections within parts
  - Use #### for subsections
  - Use --- horizontal rules between major sections

---

## 📋 Report Output Example Structure

```markdown
# AppLink Daily Report

**Report Period**: 2025-10-22 00:00:00 UTC to 2025-10-23 00:00:00 UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📋 PART 1: EXECUTIVE SUMMARY & ACTION ITEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🎯 Action Items Required

| Priority | Issue Type | Affected Tenant(s)/Service | Action Required | Owner | Severity |
|----------|------------|---------------------------|-----------------|-------|----------|
| 1 | Media State Machine Failures | Audio State Machine (US-WEST-2) | Investigate 3 failures in last 24h | Amigos Team | 🚨 |
| 2 | SLA Violation | LOWES (75 min avg) | Contact DEF team for file delivery delays | DEF Team | 🚨 |

### 🚨 Critical Issues (Immediate Attention Required)

| Issue | Impact | Affected Resources | Escalation Contact |
|-------|--------|-------------------|-------------------|
| Media State Machine Failures | 3 failures in 24h | Audio (US-WEST-2) | Amigos: WCXPTUCXoneHybridRDAmigos@nice.com |
| SLA > 60 minutes | 1 tenant affected | LOWES | DEF Team (PRIMARY) |

### ⚠️ Warnings (Monitor Closely)

| Warning Type | Details | Threshold | Current Value | Trend |
|--------------|---------|-----------|---------------|-------|
| SLA 30-60 min | JEA | < 30 min | 45 min | ↑ |

### ℹ️ Potential Issues (Investigate if Pattern Continues)

✅ No potential issues identified

### 📊 System Health Overview

| Component | Status | Details |
|-----------|--------|---------|
| **Media State Machines** | ⚠️ | Audio: 99.7% success (3 failures), Screen: 100% success |
| **SLA Performance** | ⚠️ | 4 tenants healthy, 1 warning, 1 critical |
| **Processing Pipeline** | ✅ | 99.9% end-to-end success rate |
| **Expected Tenants** | ✅ | 6/6 tenants active |
| **Regional Health** | ✅ | US-WEST-2: Healthy, EU-WEST-2: Healthy |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📊 PART 2: DETAILED ANALYSIS & SUPPORTING DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Detailed tables and analysis here...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 💡 PART 3: RECOMMENDATIONS & NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Recommendations here...]
```

**Begin analysis of dashboard.json widgets and output findings directly to console using available MCP CloudWatch tools for ONLY the widgets defined in the dashboard configuration.** 

---

## Escalation Contacts Quick Reference

| Issue Type | Team | Email | When to Contact |
|------------|------|-------|-----------------|
| **Media State Machine Failures** | Amigos Team | WCXPTUCXoneHybridRDAmigos@nice.com | ANY audio/voice or screen state machine failures (>0) |
| **SLA Violations (> 60 min)** | DEF Team | (PRIMARY) | File delivery delays - 99% of SLA issues |
| **SLA Violations (> 60 min)** | Amigos Team | WCXPTUCXoneHybridRDAmigos@nice.com | DEF-related file delivery investigations |
| **Metadata Producer Issues** | Rockets Team | WCXPTUCXoneRecordingRDRockets@nice.com | Lambda errors, processing failures, timeouts |
| **Missing Critical Widgets** | Rockets Team | WCXPTUCXoneRecordingRDRockets@nice.com | Dashboard widget failures or missing data |
| **Infrastructure Issues** | Rockets Team | WCXPTUCXoneRecordingRDRockets@nice.com | After DEF confirms timely delivery |

**Critical Rule**: ALL media-related issues (audio/voice and screen state machines) → Amigos Team

---

## execute Mission now!

