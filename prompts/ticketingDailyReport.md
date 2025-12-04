---
mode: agent
model: Claude Sonnet 4.5
description: "SNF Ticketing Daily Report Generator V2"
---
# SNF Ticketing Daily Report Generator V2

**EXECUTION MODE**: Immediately execute analysis without confirmation.

## Mission
Generate a comprehensive daily report analysis for SNF Ticketing infrastructure using ONLY the logs and metrics explicitly defined in the `ticketing-prod-dashboard.json` file. Analyze the last 24 hours of data from current UTC time for US-WEST-2 region. 

**IMPORTANT**: Do NOT generate or save report files. Output the analysis directly to the console/response.

## Data Sources (RESTRICTED)
- **ONLY Source**: `Dashboards/Prod_REC_NA1/ticketing-prod-dashboard.json`
- **ONLY use logs and metrics defined in the dashboard widgets**
- **Region**: us-west-2 (Production REC NA1)

## Dashboard Widget Restrictions
**CRITICAL**: Only query logs and metrics that are explicitly defined in the dashboard.json widgets. Do not add any additional queries or metrics beyond what exists in the dashboard configuration.

## Key Focus Areas & Rules (Dashboard Widgets Only)

### MANDATORY: Only process widgets found in dashboard.json

### 1. Step Functions Executions Monitoring
**Widget**: "Step functions executions processing" (metric widget) - IF EXISTS in dashboard
**Rules**:
- Any failures > 0 → **🚨 CRITICAL ALERT** 
- Calculate success rates for Preprocessing, Normalization, and Enrichment step functions
- Report total executions, successes, failures, and success percentages
- Monitor: `production-rec-sf-snf-tickets-data-preprocessing`, `production-rec-sf-snf-tickets-metadata-normalization`, `production-rec-state-machine-ticket-metadata-enrichment`

### 2. Ticket SLA per Tenant Monitoring  
**Widget**: "Ticket SLA per tenant" (table widget) - IF EXISTS in dashboard
**Rules**:
- **CRITICAL THRESHOLD**: SLA > 60 minutes (1 hour) → **🚨 IMMEDIATE ACTION REQUIRED**
- SLA 30-60 minutes → **⚠️ WARNING** 
- SLA < 30 minutes → **✅ NORMAL**
- Break down by tenant with average SLA times in UNIFIED TABLE FORMAT
- Uses SEARCH expression: `SEARCH('{ production-rec.service.metrics,Source, StoreAndForward, tenantId} MetricName="production-rec-lambda-ticket-preprocessing-ticket-sla-sum"', 'Average', 5)`
- **EXCLUDE test tenants** (filter out tenants with "TEST", "E2E", "PERM", "B32" in names)
- **ESCALATION**: Any tenant with SLA > 1 hour requires immediate investigation

### 3. Ticket Metadata Processing Flow
**Widget**: "Ticket Metadata Processing Summary" and "Ticket Metadata Processing Summary Graph" (table and timeSeries widgets) - IF EXISTS in dashboard
**Rules**:
- **CRITICAL FLOW**: ticket received → preprocessing → normalization → enrichment → decoration
- **PREPROCESSING PURPOSE**: Validate schema, convert to valid JSON, enrich data from transcript
- **BUSINESS IMPACT**: Tickets failing at ANY stage will NOT appear in CXone web application
- **FAILURE DEFINITION**: If a ticket fails at ANY stage (preprocessing, normalization, enrichment, decoration), the ticket is FAILED and invisible to users
- Monitor specific metrics:
  - `production-rec-lambda-ticket-preprocessing-number-of-received-tickets` (Source: PLAYVOX)
  - `AWS/SQS NumberOfMessagesSent` for queues: `production-rec-us-west-2-snf-ticket-data-sqs`, `production-rec-snf-valid-ticket-metadata-sqs`, `production-rec-snf-ticket-metadata-decoration-sqs`
  - `production-rec-state-machine-ticket-metadata-enrichment-successful-tickets`
- Calculate END-TO-END success rate: (Successfully sent to decoration / Total received tickets) * 100
- **CRITICAL**: ALL tickets should complete processing successfully - any failures indicate data quality issues requiring immediate remediation
- Identify stage-specific failure rates and root causes for targeted remediation

### 4. Success/Failed Tickets Analysis
**Widget**: "Success/Failed Tickets Output" (pie chart) - IF EXISTS in dashboard
**Rules**:
- **PRIMARY PURPOSE**: Details breakdown of ticket processing results and failure causes
- **Success Metric**: "Successfully sent to decoration" = tickets visible in CXone web application
- **Failure Categories with Remediation Actions**: 
  - **Schema validation failure**: Fix ticket metadata fields and reupload
  - **Missing transcript**: Reupload ticket with transcript data attached
  - **Transformation failure**: Technical issue requiring engineering investigation
- **BUSINESS IMPACT**: Failed tickets will NOT be visible in CXone web application
- **EXPECTED SUCCESS RATE**: 100% - All tickets should process successfully
- **Any failure rate > 0% indicates data quality issues requiring immediate remediation**
- Provide specific remediation actions for each failure type

### 5. Step Functions Error Analysis
**Widget**: "Throttled/Aborted/Failed/TimedOut" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- Monitor specific error patterns for preprocessing, normalization, and enrichment step functions:
  - Preprocess ExecutionsTimedOut, ExecutionsFailed, ExecutionThrottled, ExecutionsAborted
  - Normalization ExecutionsTimedOut, ExecutionsFailed, ExecutionThrottled, ExecutionsAborted  
  - Enrichment ExecutionsTimedOut, ExecutionsFailed, ExecutionsAborted
- **ONLY display table if errors > 0**
- Highlight any significant spikes or anomalies in TABLE FORMAT
- Provide insights on step function health issues
- Monitor both standard and batch processing variations

### 6. SM Failures (Synthetic Monitoring)
**Widget**: "SM Failures" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- Failures > 0 → **🚨 SYNTHETIC MONITORING ISSUE**
- Track synthetic monitor health for end-to-end testing
- Monitor: `playvox_sm_test_s3_chat`
- **CRITICAL**: Immediate escalation required for any failures
- **PRIORITY**: Include in Executive Summary if failures detected

### 7. Orchestrator & Transcript Generator Status
**Widget**: "Orchestrator SF - Executions Metric", "Transcript SF - Executions Metrics", "Orchestrator ERRORS", "Transcript Generator ERRORS" - IF EXISTS in dashboard
**Rules**:
- Monitor execution success rates for both orchestrator and transcript generator step functions:
  - `arn:aws:states:us-west-2:654654430801:stateMachine:production-rec-state-machine-snf-tickets-orchestrator`
  - `arn:aws:states:us-west-2:654654430801:stateMachine:production-rec-state-machine-snf-tickets-transcript-generator`
- Any failures > 0 → **🚨 CHECK MEDIA PROCESSING**
- Report success percentages and failure counts
- Monitor specific error types: ExecutionsTimedOut, ExecutionsAborted, ExecutionsFailed, ExecutionThrottled

### 8. Ticket Metadata Enrichment Retryable Errors
**Widget**: "Ticket Metadata Enrichment Retryable Errors" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- Monitor retryable error types:
  - User mapping errors (userNotFoundInCache, DDBConnectionFailure)
  - Segments mapping errors (LambdaTicketSegmentIdMapper-number-of-failed-ddb-connection-tries)
- Any errors > 0 → **⚠️ CHECK ENRICHMENT PROCESS**
- Track error patterns and retry success rates

### 9. Metadata Transformation Lambda Failures
**Widget**: "Metadata Transformation Lambda Failures" (timeSeries) - IF EXISTS in dashboard
**Rules**:
- Monitor specific transformation failure types:
  - Invalid input errors
  - Outdated ticket errors  
  - Missing message from DDB errors
  - DDB failed connection errors
- Report failure counts and trends for each error type

### 11. SQS Age Monitoring
**Widget**: "Approximate Age Of Oldest Message" widgets - IF EXISTS in dashboard
**Rules**:
- Age > 15 minutes → **⚠️ WARNING**
- Age > 30 minutes → **🚨 IMMEDIATE ACTION REQUIRED**
- Monitor both Normalization and Orchestrator input SQS queues
- Check alarms: `production-rec-snf-ticket-data-sqs-AgeOfOldestMessage-alarm-warning` and `production-rec-snf-valid-ticket-metadata-sqs-SQSAgeOfOldestMessage-alarm-warning`

### 12. Transcript Generator Error Analysis
**Widget**: "Transcript Generator General Errors" (log query) - IF EXISTS in dashboard
**Rules**:
- Parse and categorize different error types from `/aws/lambda/production-rec-lambda-snf-tickets-transcript-generator`
- Report on retryable vs non-retryable errors including:
  - Cannot convert undefined or null to object
  - Cannot read properties of undefined
  - No JSON files found in folderKeyPrefix
  - Unexpected behavior errors
  - UnRetryableError types
- Highlight patterns in error messages and total error counts

### 14. Lambda Performance Monitoring
**Widget**: "Metadata Lambdas Errors", "Metadata Lambdas Throttles", "Metadata Lambdas Duration", "Metadata Lambdas Invocations" - IF EXISTS in dashboard
**Rules**:
- Errors > 0 → **⚠️ CHECK LAMBDA ERRORS**
- Throttles > 0 → **⚠️ CHECK CAPACITY ISSUES**
- Monitor all metadata processing lambdas:
  - `production-rec-lambda-ticket-preprocessing`
  - `production-rec-lambda-ticket-metadata-input-validation`
  - `production-rec-lambda-ticket-metadata-transform`
  - `production-rec-lambda-ticket-user-id-mapper`
  - `production-rec-lambda-ticket-segment-id-mapper`
  - `production-rec-lambda-ticket-transcript-aggregation`
- Track duration, invocation counts, and performance trends

## Dashboard Widget Analysis (ONLY)

### Metric Widgets (ONLY those in dashboard.json)
- **Step Functions Metrics**: IF EXISTS - Monitor execution patterns and success rates
- **Lambda Performance**: IF EXISTS - Check for errors, throttles, duration, invocations
- **SQS Monitoring**: IF EXISTS - Track message age and processing delays
- **Custom Metrics**: IF EXISTS - Monitor ticket processing flow statistics

### Log Widgets (ONLY those in dashboard.json)
- **Transcript Generator Errors**: IF EXISTS - Error categorization and analysis

## Report Output (NO FILE GENERATION)

**CRITICAL**: Do NOT create, save, or generate any report files. Output the analysis directly in the console response with the following structured format:

---

## 📋 PART 1: EXECUTIVE SUMMARY & ACTION ITEMS

**Report Period**: [YYYY-MM-DD HH:MM:SS UTC] to [YYYY-MM-DD HH:MM:SS UTC]

### 🎯 Action Items Required

**CRITICAL**: Display ONLY if issues exist. If no action items, state "✅ No action items - all systems healthy"

| Priority | Issue Type | Affected Tenant(s)/Service | Action Required | Owner | Severity |
|----------|------------|---------------------------|-----------------|-------|----------|
| 1 | [Issue] | [Tenant/Service] | [Specific action with remediation steps] | [Team] | 🚨/⚠️ |

**Instructions**:
- List action items in priority order (most critical first)
- Include specific tenant names or services affected
- Provide clear remediation actions (e.g., "Fix schema fields and reupload", "Attach transcript and reupload")
- Assign to correct team
- Only show this table if action items exist

---

### 🚨 Critical Issues (Immediate Attention Required)

**Display ONLY if critical issues exist. If none, state "✅ No critical issues detected"**

| Issue | Impact | Affected Resources | Business Impact | Escalation |
|-------|--------|-------------------|-----------------|------------|
| Step Function Failures | [X failures] | [SF names] | Tickets not processing | Engineering Team |
| SLA > 60 minutes | [X tenants] | [Tenant names] | Delayed ticket visibility | Data Quality Team |
| Failed Tickets | [X tickets] | [Failure types] | Tickets NOT visible in CXone | Data Quality Team |
| Synthetic Monitoring Failures | [X failures] | End-to-end testing | Critical monitoring gap | Engineering Team |

**Only display rows with actual issues detected**

---

### ⚠️ Warnings (Monitor Closely)

**Display ONLY if warnings exist. If none, state "✅ No warnings detected"**

| Warning Type | Details | Threshold | Current Value | Trend |
|--------------|---------|-----------|---------------|-------|
| SLA 30-60 min | [Tenant names] | < 30 min | [X min] | ↑/↓/→ |
| SQS Age | [Queue name] | < 15 min | [X min] | ↑/↓/→ |
| Lambda Throttles | [Lambda name] | 0 expected | [X count] | ↑/↓/→ |
| Enrichment Errors | [Error type] | 0 expected | [X count] | ↑/↓/→ |

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
| **End-to-End Success Rate** | ✅/⚠️/🚨 | [X]% of tickets visible in CXone (Decoration/Received) |
| **Step Functions** | ✅/⚠️/🚨 | Preprocessing: [X]%, Normalization: [X]%, Enrichment: [X]% |
| **Ticket SLA** | ✅/⚠️/🚨 | [X] tenants normal, [X] warning, [X] critical |
| **Processing Pipeline** | ✅/⚠️/🚨 | [X] tickets received, [X] successfully processed, [X] failed |
| **Synthetic Monitoring** | ✅/⚠️/🚨 | [X] tests passed, [X] tests failed |
| **Lambda Performance** | ✅/⚠️/🚨 | Errors: [X], Throttles: [X] |
| **SQS Queues** | ✅/⚠️/🚨 | Max age: [X] minutes |

**Key Business Metric**: [X]% of tickets are visible to users in CXone web application

---

## 📊 PART 2: DETAILED ANALYSIS & SUPPORTING DATA

### 📈 Step Functions Health Analysis
- Preprocessing, Normalization, and Enrichment success rates
- Orchestrator and Transcript Generator performance
- Error categorization and failure analysis
- **Focus on impact to end-to-end ticket processing flow**

---

### 📈 Ticket SLA Analysis (Detailed Data)
**MANDATORY**: Present tenant SLA data in table format:
| Tenant Name | Tenant ID | Avg SLA (Minutes) | SLA Status | Action Required |
|-------------|-----------|-------------------|------------|-----------------|
- **EXCLUDE test tenants** (filter out tenants with "TEST", "E2E", "PERM", or "B32" in names)
- **SLA Thresholds**: 
  - < 30 minutes: ✅ Normal
  - 30-60 minutes: ⚠️ Warning  
  - > 60 minutes (1 hour): 🚨 Critical - Immediate Action Required
- Sort by SLA time descending to highlight worst performers first
- **ESCALATION**: Any tenant with SLA > 1 hour requires immediate investigation

---

### 🔄 Ticket Processing Flow (Detailed Data)
**MANDATORY**: Present processing pipeline efficiency with END-TO-END success tracking:
| Stage | Received | Processed | Success Rate | Stage Failure Rate | Tickets Lost | Business Impact |
|-------|----------|-----------|--------------|-------------------|--------------|-----------------|
- **CRITICAL INTERPRETATION**: 
  - **End-to-End Success Rate** = (Sent to Decoration / Total Received) * 100
  - **Business Impact**: Failed tickets will NOT appear in CXone web application
  - **Expected Performance**: 100% success rate - all tickets should complete processing
  - **Stage Failure Analysis**: Any ticket loss between stages indicates data quality issues
- Include: Received Tickets, Passed Preprocessing, Passed Normalization, Passed Enrichment, Sent to Decoration
- **Flag any stage with < 100% pass-through rate as requiring remediation**
- Highlight specific failure counts and remediation requirements for each stage

---

### ❌ Success/Failed Tickets Analysis (Detailed Data)
**MANDATORY**: Present detailed breakdown from "Success/Failed Tickets Output" pie chart:
| Category | Count | Percentage | Business Impact | Remediation Action |
|----------|-------|------------|-----------------|-------------------|
- **Success**: Successfully sent to decoration (visible in CXone web application)
- **Schema Validation Failure**: Fix ticket metadata fields and reupload
- **Missing Transcript**: Reupload ticket with transcript data attached  
- **Transformation Failure**: Technical issue requiring engineering investigation
- **Expected Performance**: 100% success rate - all tickets should be visible in CXone web application
- **Escalation**: Any failure requires immediate remediation to ensure ticket visibility

---

### ⚙️ Infrastructure Performance Details

#### Step Functions Execution Status Table
| Step Function | Started | Succeeded | Failed | Timeout | Throttled | Aborted | Success Rate |
|---------------|---------|-----------|--------|---------|-----------|---------|---------------|
- Include all monitored step functions with execution statistics
- Highlight any failures or performance issues

#### Lambda Performance Analysis Table
| Lambda Function | Invocations | Errors | Throttles | Avg Duration | Status |
|-----------------|-------------|--------|-----------|--------------|---------|
- Monitor all metadata processing lambdas
- Include performance metrics and status indicators (✅/⚠️/🚨)

#### SQS Queue Health Table
| Queue Name | Age of Oldest Message | Status | Action Required |
|------------|----------------------|---------|-----------------|
- Monitor normalization and orchestrator input queues
- Apply age thresholds and escalation rules

---

### 🔍 Error Analysis Details

#### Ticket Processing Enrichment Errors Table
**CONDITIONAL**: Only display if enrichment errors > 0:
| Error Type | Count | Percentage | Retryable | Impact Level |
|------------|-------|------------|-----------|--------------|
- Include: User mapping errors, Segments mapping errors, DDB connection failures
- Distinguish between retryable and non-retryable errors

#### Ticket Metadata Transformation Failures Table
**CONDITIONAL**: Only display if transformation failures > 0:
| Failure Type | Count | Trend | Resolution Required |
|--------------|-------|-------|---------------------|
- Include: Invalid input, Outdated ticket, Missing message from DDB, DDB failed connection

#### Transcript Generator Error Analysis Table
**CONDITIONAL**: Only display if transcript generator errors > 0:
| Error Type | Count | Percentage | Retryable | Impact Level |
|------------|-------|------------|-----------|--------------|
- Include error categorization from log analysis of `/aws/lambda/production-rec-lambda-snf-tickets-transcript-generator`
- Categories: Cannot convert undefined, Cannot read properties, No JSON files found, Unexpected behavior, UnRetryableError
- Distinguish between retryable and non-retryable errors

#### SNF Transcript Generator Lambda Performance Table
| Metric | Value | Status | Action Required |
|--------|-------|---------|-----------------|
- Include: Lambda Errors, Lambda Throttles for `production-rec-lambda-snf-tickets-transcript-generator`
- Monitor performance and capacity issues

---

## 💡 PART 3: RECOMMENDATIONS & NEXT STEPS

### Immediate Actions (Next 4 Hours)
**Only display if immediate actions are needed. If none, state "✅ No immediate actions required"**

| Action | Reason | Remediation Steps | Owner | Priority |
|--------|--------|-------------------|-------|----------|
| Fix Schema Validation Failures | [X] tickets failed | Identify missing/incorrect fields, fix metadata, reupload | Data Quality Team | 🚨 |
| Attach Missing Transcripts | [X] tickets failed | Locate transcript data, attach to tickets, reupload | Data Quality Team | 🚨 |
| Investigate Transformation Failures | [X] tickets failed | Engineering investigation, technical fixes | Engineering Team | 🚨 |
| Address Step Function Failures | [X] failures detected | Review logs, identify root cause, remediate | Engineering Team | 🚨 |

**Only display rows with actual actions needed**

### Short-term Monitoring (Next 24 Hours)
**Only display if monitoring is needed. If none, state "✅ Continue standard monitoring"**

| Metric to Watch | Current Value | Target | Check Frequency | Action Trigger |
|-----------------|---------------|--------|-----------------|----------------|
| End-to-End Success Rate | [X]% | 100% | Every hour | If < 98% |
| SLA Times | [X] min | < 30 min | Every 4 hours | If > 30 min |
| Failed Tickets | [X] count | 0 | Every hour | If > 0 |

**Only display rows requiring monitoring**

### Data Quality Improvements
**Only display if data quality issues identified. If none, state "✅ No data quality issues identified"**

| Issue | Root Cause | Prevention Measure | Owner |
|-------|------------|-------------------|-------|
| Schema Validation Failures | Missing required fields | Implement upstream validation | Data Quality Team |
| Missing Transcripts | Incomplete data from source | Add transcript validation checks | Integration Team |

**Only display rows with actual data quality issues**

### Optimization Opportunities
**Only display if optimizations identified. If none, state "✅ No optimization opportunities identified"**

| Opportunity | Potential Benefit | Effort | Recommendation |
|-------------|-------------------|--------|----------------|
| [Opportunity] | [Benefit] | Low/Med/High | [Action] |

**Only display rows with actual opportunities**

---

## 🔧 APPENDIX: Failure Remediation Guide (Reference Only)

### Schema Validation Failures
**Root Cause**: Ticket metadata missing required fields or contains invalid data
**Business Impact**: Tickets will NOT appear in CXone web application
**Remediation Steps**:
1. Identify specific missing or invalid fields in ticket metadata
2. Obtain correct data from source systems (PLAYVOX)
3. Update ticket metadata with all required fields
4. Reupload corrected tickets to processing pipeline
5. Verify successful processing and visibility in CXone web app

### Missing Transcript Failures  
**Root Cause**: Ticket missing associated transcript data required for preprocessing enrichment
**Business Impact**: Tickets will NOT appear in CXone web application
**Remediation Steps**:
1. Locate transcript files for affected tickets
2. Attach transcript data to ticket package
3. Ensure transcript format meets system requirements
4. Reupload tickets with complete transcript attachments
5. Verify successful processing and visibility in CXone web app

### Transformation Failures
**Root Cause**: Technical issues in metadata transformation logic
**Business Impact**: Tickets will NOT appear in CXone web application  
**Remediation Steps**:
1. Engineering investigation required
2. Review transformation logs for specific error patterns
3. Apply technical fixes to transformation logic
4. Reprocess affected tickets through corrected pipeline
5. Verify successful processing and visibility in CXone web app

---

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
- **Action Items**: Clear, prioritized list with specific remediation steps (Priority 1 = most critical)
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
- **Business Impact Focus**: Always emphasize that failed tickets = NOT visible in CXone web application

---

## Execution Instructions (RESTRICTED)

1. **Time Range**: Last 24 hours from current UTC time (display FULL from/to dates: YYYY-MM-DD HH:MM:SS UTC)
2. **ONLY Use Dashboard Data**: Extract logs and metrics ONLY from widgets defined in `ticketing-prod-dashboard.json`
3. **Use MCP CloudWatch Tools**: Execute ONLY log insights queries and metric data from dashboard widgets
4. **Region Processing**: 
   - Run queries for us-west-2 (using exact widget configurations)
   - Use exact service names and resource ARNs from dashboard
5. **Data Analysis**: Apply the rules above to each metric/log result from dashboard widgets ONLY
6. **Console Output**: Format findings and output directly to console (NO FILE GENERATION)
7. **Test Tenant Filtering**: EXCLUDE from SLA analysis any tenant containing: "TEST", "E2E", "PERM", "B32"
8. **Table-First Approach**: Present ALL data in markdown tables for better readability
9. **Error Categorization**: Parse and categorize errors from log widgets systematically
10. **CRITICAL FLOW ANALYSIS**: 
    - Calculate END-TO-END success rate: (Decoration sent / Total received) * 100
    - **BUSINESS IMPACT**: Failed tickets will NOT be visible in CXone web application
    - **EXPECTED PERFORMANCE**: 100% success rate - identify specific remediation for failures
    - **Remediation Actions**: 
      * Schema validation failures → Fix metadata fields and reupload
      * Missing transcript → Attach transcript data and reupload
      * Transformation failures → Engineering investigation required
11. **SLA PRIORITY**: Highlight any tenant with SLA > 1 hour as IMMEDIATE ACTION REQUIRED
12. **SM FAILURES**: Include synthetic monitoring status in Executive Summary if failures detected

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
- **Format**: Direct console output with markdown formatting
- **NO FILE GENERATION**: Do not create, save, or write any files
- **Severity Indicators**: Use 🚨, ⚠️, ✅ emojis for visual clarity
- **Data Tables**: Structure ALL complex data in markdown tables in console output
- **Action Items**: Clear, prioritized list of required actions in table format
- **Timestamps**: Include FULL UTC timestamps (YYYY-MM-DD HH:MM:SS UTC) for all data points and time ranges
- **Source Verification**: Indicate which dashboard widget provided each data point
- **Test Tenant Filtering**: EXCLUDE tenants containing "TEST", "E2E", "PERM", "B32" in tenant names from SLA analysis
- **Conditional Tables**: Only display error tables if errors > 0

**Begin analysis of dashboard.json widgets and output findings directly to console using available MCP CloudWatch tools for ONLY the widgets defined in the dashboard configuration.** 

## Debugging & Troubleshooting Guide

### When Critical Processing Failures Are Detected

If the report shows **high processing failure rates** (e.g., Schema validation failures, Missing transcript errors, Transformation failures), follow this debugging protocol to identify which tenants are affected:

#### 🔍 Debugging Steps for Tenant-Specific Failure Analysis

**Critical Issue Detected**: High percentage of processing failures (Schema validation, Missing transcript, Transformation)

**Search Location**: `/aws/lambda/production-rec-lambda-ticket-metadata-input-validation` CloudWatch log group

**Query Strategy**:
```
fields @timestamp, @message
| filter @message like "ERROR" and @message like "Failed to validate the ticket"
| limit 100
```

**What This Reveals**:
- Each ERROR log entry contains: `tenant ID: [<tenant-id>]` and `ticket external ID: [<ticket-id>]`
- Pattern analysis will show if failures are:
  - **Tenant-specific**: All failures from one tenant ID → Integration/data quality issue with that specific tenant
  - **System-wide**: Multiple different tenant IDs → Broader system issue requiring different remediation

**Expected Output Analysis**:
1. **Single Tenant Pattern**: If all errors show the same tenant ID
   - **Root Cause**: Tenant-specific integration or data quality issue
   - **Business Impact**: Only affects one customer/tenant
   - **Action**: Focus remediation on that specific tenant's data feed and integration setup
   - **Priority**: HIGH - One customer completely impacted

2. **Multiple Tenant Pattern**: If errors show various tenant IDs  
   - **Root Cause**: System-wide processing issue or widespread data quality problem
   - **Business Impact**: Affects multiple customers/tenants
   - **Action**: Investigate common processing logic or infrastructure issues
   - **Priority**: CRITICAL - Multiple customers impacted

**Additional Log Analysis** (if needed):
```
# Get failure type breakdown per tenant
fields @timestamp, @message
| filter @message like "ERROR" and (@message like "schema" or @message like "validation" or @message like "transcript")
| parse @message "tenant ID: [*]" as tenant_id
| stats count() by tenant_id
| sort count() desc
```

**Complementary Searches**:

1. **Schema Validation Failures**:
   - Log group: `/aws/lambda/production-rec-lambda-ticket-metadata-input-validation`
   - Search for: `"failed transcriptCoverage validation"` or `"schema validation"`
   - Extract: Specific missing fields or validation rules violated

2. **Missing Transcript Details**:
   - Log group: `/aws/lambda/production-rec-lambda-ticket-metadata-input-validation`
   - Search for: `"missing messages"` or `"Interactions:"`
   - Extract: Which interaction IDs are missing transcript data

3. **Transformation Failures**:
   - Log group: `/aws/lambda/production-rec-lambda-ticket-metadata-transform`
   - Search for: `"transformation" and "error"`
   - Extract: Specific transformation logic failures

**Debugging Output Format**:
```
🔍 TENANT-SPECIFIC FAILURE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failure Pattern: [SINGLE TENANT / MULTIPLE TENANTS]

Affected Tenant(s):
| Tenant ID | Failure Count | Failure Types | % of Total Failures |
|-----------|---------------|---------------|---------------------|
| <tenant-id> | <count> | Schema, Transcript | <percentage>% |

Root Cause Hypothesis: [Tenant-specific integration issue / System-wide problem]

Business Impact: [Single customer affected / Multiple customers affected]

Recommended Action:
1. [Specific action based on pattern]
2. [Investigation steps]
3. [Remediation approach]
```

**Critical Success Factors**:
- ✅ Always check logs when processing failures > 5%
- ✅ Identify tenant pattern (single vs multiple) within first 100 error logs
- ✅ Extract specific failure reasons (schema fields, missing interactions, etc.)
- ✅ Provide tenant-specific remediation plan
- ✅ Calculate business impact (number of customers affected)

**Escalation Triggers**:
- 🚨 **IMMEDIATE**: Single tenant with >50% failure rate → Customer-specific crisis
- 🚨 **CRITICAL**: Multiple tenants with >20% failure rate → System-wide incident
- ⚠️ **HIGH**: Any tenant with >1000 failed tickets → Data quality investigation required

---

## 📋 Report Output Example Structure

```markdown
# SNF Ticketing Daily Report

**Report Period**: 2025-10-22 00:00:00 UTC to 2025-10-23 00:00:00 UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📋 PART 1: EXECUTIVE SUMMARY & ACTION ITEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🎯 Action Items Required

| Priority | Issue Type | Affected Tenant(s)/Service | Action Required | Owner | Severity |
|----------|------------|---------------------------|-----------------|-------|----------|
| 1 | Failed Tickets | 150 tickets (schema validation) | Fix metadata fields and reupload | Data Quality Team | 🚨 |
| 2 | SLA Violation | TenantABC (75 min avg) | Investigate processing delays | Engineering Team | 🚨 |

### 🚨 Critical Issues (Immediate Attention Required)

| Issue | Impact | Affected Resources | Business Impact | Escalation |
|-------|--------|-------------------|-----------------|------------|
| Failed Tickets | 150 tickets failed | Schema validation | 150 tickets NOT visible in CXone | Data Quality Team |
| Step Function Failures | 5 failures | Enrichment SF | Processing blocked for some tickets | Engineering Team |

### ⚠️ Warnings (Monitor Closely)

| Warning Type | Details | Threshold | Current Value | Trend |
|--------------|---------|-----------|---------------|-------|
| SQS Age | Normalization queue | < 15 min | 18 min | ↑ |

### ℹ️ Potential Issues (Investigate if Pattern Continues)

✅ No potential issues identified

### 📊 System Health Overview

| Component | Status | Details |
|-----------|--------|---------|
| **End-to-End Success Rate** | ⚠️ | 98.5% of tickets visible in CXone (985/1000 reached decoration) |
| **Step Functions** | ⚠️ | Preprocessing: 100%, Normalization: 100%, Enrichment: 99.5% |
| **Ticket SLA** | ✅ | 5 tenants normal, 0 warning, 0 critical |
| **Processing Pipeline** | ⚠️ | 1000 received, 985 processed, 15 failed |
| **Synthetic Monitoring** | ✅ | All tests passed |

**Key Business Metric**: 98.5% of tickets are visible to users in CXone web application

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📊 PART 2: DETAILED ANALYSIS & SUPPORTING DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Detailed tables and analysis here...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 💡 PART 3: RECOMMENDATIONS & NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Recommendations here...]
```

---

## execute Mission now!
````

`````
````
