# Solution Design Document (SDD)   
### Project: Automated Client Risk Processing Bot  
### Version: 0.1  
#### Author: Thiago Almeida  
#### Date: 20/01/2026

---

# 1. Executive Summary

This document describes the proposed automation solution for processing incoming client data, validating information, assessing risk through external and internal systems, and generating decision outputs automatically.

The purpose of this document is to define the business problem, scope, high-level process flow, business rules, exception handling strategy, and architectural considerations before implementation begins.

This document covers both conceptual and technical architectural considerations required for enterprise-level implementation.

---

## 2. Business Overview

### 2.1 Problem Statement

The organization receives approximately 500 new client records daily in spreadsheet format. These records must be validated, assessed for risk using an external scoring service, cross-checked against the internal database, and classified according to predefined approval criteria.

Currently, the process is performed manually by a business analyst, taking approximately 8 hours per day to complete. The manual workflow introduces risks such as human error, inconsistent decision-making, lack of traceability, and operational inefficiency.

The goal of this automation is to reduce processing time, improve consistency, ensure traceability for audit purposes, and support scalable client onboarding.

---

### 2.2 Business Impact

If not automated:

- Delays in client onboarding may impact revenue flow.
- Manual errors may result in incorrect approval or rejection.
- Lack of audit trail increases compliance risk.
- Operational cost remains high due to manual effort.

With automation:

- Processing time reduced to under 2 hours.
- Standardized decision rules.
- Full traceability of decisions.
- Improved scalability.

---

### 2.3 Process Frequency

The process runs once daily, processing a batch of approximately 500 client records.

Peak scenarios may reach up to 1,500 records per execution.

---

### 2.4 Volume Estimation

- Average daily volume: 500 records
- Peak volume: 1,500 records
- Expected annual growth: 15%

---

### 2.5 SLA (Service Level Agreement)

- Maximum processing time: 2 hours
- Acceptable failure rate: < 2%
- Retry policy: System exceptions retried up to 2 times


---

# 3. Process Overview (Business Level – No Technical Details)

## 3.1 High-Level Process Flow

The automation will execute the following logical steps:

1. Receive input Excel file containing new client records.
2. Validate file structure and mandatory fields.
3. Load client records for processing.
4. For each client:
   - Check if client already exists in internal database.
   - If exists, mark as Ignored.
   - If not, call external Risk Scoring API.
   - Apply business decision rules.
   - Store decision result in database.
5. Generate consolidated processing report.
6. Send notification email with summary results.
7. Log all processing activities for traceability.

---

## 3.2 Process Actors

- Input Provider: Business Operations Team
- Automation Executor: RPA Robot (Unattended)
- Output Consumers:
  - Risk Team
  - Operations Team
- Monitoring Responsible:
  - Automation Support Team

---

# 4. Business Rules

The following business rules will determine client classification:

1. If the client already exists in the internal database:
   - Status = "Ignored"
   - No further processing required.

2. If Risk Score > 700:
   - Status = "Approved"

3. If Risk Score between 500 and 700 (inclusive):
   - Status = "Manual Review"

4. If Risk Score < 500:
   - Status = "Rejected"

5. If mandatory fields (Client ID, Name, Email) are missing:
   - Raise Business Exception
   - Record as "Invalid Data"

---

# 5. Exception Handling Strategy (Business Perspective)

## 5.1 Business Exceptions

Business exceptions are expected logical inconsistencies that do not stop the entire process:

- Duplicate client
- Missing mandatory fields
- Invalid or null score returned by API

These exceptions will be logged and recorded without stopping the automation.

---

## 5.2 System Exceptions

System exceptions are unexpected technical failures:

- API timeout or connection failure
- Database connection error
- Corrupted input file
- Authentication failure

System exceptions will trigger retry mechanisms according to SLA policy.
If retry attempts fail, the transaction will be marked as Failed and logged for investigation.

---

# 6. High-Level Architecture (Conceptual)

The automation solution will be composed of the following conceptual components:

---

### Automation Platform

A Robotic Process Automation (RPA) platform will execute the business workflow in a transaction-based model.  
The automation will process each client record individually, applying validation, decision rules, and integration logic.

---

### Orchestration Mechanism

An orchestration platform will manage:

- Queue-based transaction processing
- Execution triggers (scheduled batch execution)
- Retry mechanisms for system exceptions
- Centralized monitoring and logging

The orchestration model will ensure scalability, fault tolerance, and execution traceability.

---

### Database

A relational database will store:

- Client records
- Risk score results
- Decision outcomes
- Processing history
- Error logs

This ensures data persistence, auditability, and reporting capabilities.

---

### External API

An external risk scoring service will evaluate each client’s risk profile.

The automation will:
- Send client identifiers
- Receive a risk score
- Validate the response
- Handle integration errors according to SLA policy

---

### Notification System

An automated notification mechanism will send execution summaries to stakeholders, including:

- Total processed records
- Approved / Rejected / Manual Review counts
- Failed transactions
- Execution time

This ensures operational transparency and monitoring visibility.

---

### Logging and Monitoring

The solution will implement structured logging to:

- Differentiate business and system exceptions
- Support audit requirements
- Enable operational monitoring
- Facilitate troubleshooting

---

The automation will retrieve input data, process transactions individually, apply business rules, update database records, and generate structured outputs while ensuring compliance, traceability, and scalability.

---

# 7. Technical Architecture

## 7.1 Technical Architecture Overview

This section translates the conceptual architecture into a detailed technical design, defining the technologies, integration layers, execution model, and data structure required for implementation.

---

## 7.2 Technology Stack

The following technologies were selected:

- RPA Platform: UiPath Studio (Community Edition)
- Orchestration: UiPath Orchestrator (Cloud Community)
- Database: PostgreSQL (local instance)
- API Service: Python (Flask REST API)
- Version Control: GitHub
- Development Environment: Local machine

---

## 7.3 Layered Technical Design

### 7.3.1 Input Layer
- Reads Excel file
- Validates structure
- Loads transactions into Orchestrator Queue

### 7.3.2 Orchestration Layer
- Queue-based processing
- Retry mechanism for system exceptions
- REFramework implementation

### 7.3.3 Processing Layer
- Applies business rules
- Coordinates API and database calls
- Determines final decision

### 7.3.4 Integration Layer
- Executes SQL queries (SELECT / INSERT / UPDATE)
- Calls Risk Scoring API
- Validates API responses

### 7.3.5 Output Layer
- Generates processing report
- Updates database status
- Sends notification email

### 7.3.6 Logging Strategy
- Uses Orchestrator logs
- Differentiates business vs system exceptions
- Ensures traceability for audit

---

## 7.4 Database Initial Design

Database: PostgreSQL

The database design separates business data from processing control to ensure auditability and scalability.

---

### 7.4.1 Table: clients

Stores master client data.

Fields:

- id (Primary Key)
- client_id (Unique, Business Identifier)
- name
- email
- created_at (Timestamp)

Index:
- Unique constraint on client_id

---

### 7.4.2 Table: client_risk_processing

Stores processing results and execution history.

Fields:

- id (Primary Key)
- client_id (Foreign Key → clients.client_id)
- risk_score
- decision_status (Approved / Rejected / Manual Review / Ignored)
- processing_status (Success / Failed / Retried)
- processing_attempts
- error_message
- processed_at (Timestamp)

Indexes:
- Index on client_id
- Index on processed_at

---

## 7.5 API Design – Risk Scoring Service

The Risk Scoring Service is a RESTful API responsible for evaluating the risk profile of a given client and returning a numeric risk score.

The service will follow REST standards and include versioning to ensure future scalability.

---

### 7.5.1 Base URL

/api/v1/risk-score

---

### 7.5.2 HTTP Method

POST

---

### 7.5.3 Request Headers

- Content-Type: application/json
- Accept: application/json
- X-Request-ID: Unique transaction identifier (for traceability)

---

### 7.5.4 Request Body

{
  "client_id": "string"
}

Validation Rules:
- client_id is mandatory
- client_id must be a non-empty string
- client_id must match expected format

---

### 7.5.5 Success Response (200 OK)

{
  "client_id": "string",
  "risk_score": integer,
  "status": "success",
  "processed_at": "ISO 8601 timestamp"
}

Constraints:
- risk_score range: 0–1000
- status must always be "success"

---

### 7.5.6 Business Error Response (400 Bad Request)

{
  "client_id": "string",
  "status": "error",
  "error_type": "validation_error",
  "message": "Invalid client_id format"
}

This type of error will be treated as Business Exception in the RPA workflow.

---

### 7.5.7 System Error Response (500 Internal Server Error)

{
  "status": "error",
  "error_type": "system_error",
  "message": "Unexpected internal failure"
}

This type of error will trigger retry according to SLA policy.

---

### 7.5.8 Timeout / Service Unavailable (504 Gateway Timeout / 503 Service Unavailable)

Returned when:
- Service overload
- Dependency failure
- Simulated stress scenario

These responses will be treated as System Exceptions and retried up to 2 times per transaction.

---

### 7.5.9 Failure Simulation Strategy (For Testing)

To validate retry and resilience mechanisms, the API will include:

- Random timeout simulation (5–10% probability)
- Manual toggle for service unavailable state
- Forced internal server error trigger

This ensures proper validation of:
- Retry policy
- Queue reprocessing
- SLA adherence
- Monitoring alerts

---

### 7.5.10 Idempotency Consideration

The API is idempotent at the transaction level:

- Multiple identical requests for the same client_id will return the same risk_score
- No duplicate data will be created
- No state mutation occurs inside the API

This ensures safe retry execution from the RPA platform.

---

## 7.6 Execution Model

Execution Type:
- Unattended automation

Transaction Model:
- One client per Queue item

Retry Strategy:
- System exception: 2 retries
- Business exception: no retry

Environment Setup:
- Development: Local machine
- Orchestrator: Cloud
- Database: Local PostgreSQL
- API: Local Flask service

---

# 8. Non-Functional Requirements

This section defines the quality attributes, operational expectations, and technical performance criteria that the solution must satisfy.

Non-functional requirements ensure that the automation is reliable, scalable, secure, and compliant with business expectations.

---

## 8.1 Performance Requirements

- The automation must process up to 1,500 client records within a maximum of 2 hours.
- Average processing time per transaction should not exceed 3 seconds.
- Database operations must respond within 200ms under normal load.
- API calls must have a timeout threshold of 10 seconds.

---

## 8.2 Scalability Requirements

- The architecture must support annual data growth of at least 15%.
- The system must support horizontal scaling via multi-bot execution if required.
- The database design must support long-term historical storage (minimum 5 years).

---

## 8.3 Reliability Requirements

- System exception retry policy: maximum 2 retries per transaction.
- Business exceptions must not stop the execution.
- The solution must isolate transaction failures without impacting the entire batch.
- Failed transactions must be reprocessable.

---

## 8.4 Availability Requirements

- The automation must be executable on a daily scheduled basis.
- Orchestration platform availability is assumed at > 99%.
- API dependency downtime must not cause total batch failure.

---

## 8.5 Security Requirements

- Database access must be credential-protected.
- API endpoints must validate input parameters.
- Sensitive data must not be logged in plain text.
- Credentials must not be hard-coded in the automation.
- Secure assets must be stored in Orchestrator.

---

## 8.6 Audit and Compliance Requirements

- All processed transactions must be traceable.
- Decision outcomes must be stored historically.
- Error logs must contain sufficient diagnostic information.
- Execution logs must differentiate business and system exceptions.

---

## 8.7 Maintainability Requirements

- The solution must follow REFramework structure.
- Business rules must be modular and easily adjustable.
- Code must be version-controlled via GitHub.
- Documentation must be updated with any architectural changes.

---

## 8.8 Monitoring and Observability

- Execution summary must be sent via email after each run.
- Failed transaction count must be included in notification.
- Logs must be accessible via Orchestrator.
- The system must support future dashboard integration.


# 9. Assumptions

This section defines the environmental, technical, and operational assumptions considered during the solution design.  
These assumptions are critical to ensure architectural decisions remain valid.

---

## 9.1 Environmental Assumptions

- The automation will run in a stable network environment with consistent internet connectivity.
- The RPA platform (UiPath Orchestrator Cloud) will maintain operational availability above 99%.
- The development and execution environment will support PostgreSQL and Python runtime without resource limitations.
- Execution will occur in a controlled environment without concurrent manual interference.

---

## 9.2 Data Consistency Assumptions

- The input Excel file will follow the predefined schema and column structure.
- Client identifiers (client_id) are unique and consistent across executions.
- Mandatory fields (client_id, name, email) will be correctly populated in most cases.
- External API will return risk_score within expected numeric range (0–1000).
- No duplicate client records will be intentionally introduced in the same batch.

---

## 9.3 Infrastructure Availability Assumptions

- PostgreSQL database will be available during execution window.
- API service will be reachable via HTTP endpoint.
- SMTP/email service will be available for notification dispatch.
- Credentials stored in Orchestrator will remain valid and properly configured.
- Local system resources (CPU, memory, disk) will be sufficient to process up to 1,500 records per execution.

---

## 9.4 Operational Assumptions

- The process will run once per day under unattended mode.
- Business rules will not change during execution.
- Stakeholders will review failure reports when provided.
- Manual reprocessing will be performed only when necessary.

---

Failure of any of these assumptions may require architectural revision or operational adjustment.


---

# 10. Constraints

This section defines the known limitations and restrictions that impact the design, implementation, and operation of the solution.

Constraints differ from assumptions as they represent confirmed limitations rather than expected conditions.

---

## 10.1 Time Constraints

- The solution must process up to 1,500 records within a maximum SLA of 2 hours.
- Daily execution window is limited to business-defined operational hours.
- Retry attempts must not cause total execution time to exceed SLA.
- Implementation must be achievable within a limited development timeframe using available resources.

---

## 10.2 Technical Constraints

- The solution will use UiPath Community Edition for development.
- Orchestration is limited to UiPath Cloud Orchestrator (Community version limitations may apply).
- The database will initially run on a local PostgreSQL instance.
- The API service will be locally hosted using Python Flask during development phase.
- Parallel bot execution is not implemented in version 0.1.
- No external paid monitoring or logging tools will be used in this version.

---

## 10.3 Security Constraints

- No enterprise-grade identity provider integration (e.g., SSO) in version 0.1.
- No encryption at rest configured at database level (local environment).
- API authentication mechanism is simplified for development purposes.
- Sensitive production-grade data will not be used in testing environment.

---

## 10.4 Infrastructure Constraints

- Execution environment is limited to a single machine during development.
- Database and API run on the same host during initial version.
- Resource allocation (CPU, RAM) depends on local machine capabilities.
- Internet connectivity is required for Orchestrator communication.

---

## 10.5 Budget Constraints

- Only free/community tools are used in version 0.1.
- No paid cloud infrastructure services are included.
- No enterprise monitoring, scaling, or load-balancing tools are implemented.

---

Future architectural revisions may relax these constraints as the solution evolves.


---

# 11. Risks

This section identifies potential risks that may impact the successful implementation and operation of the automation solution.

Risks are categorized to support mitigation planning and architectural resilience.

---

## 11.1 Operational Risks

### 11.1.1 Input File Format Change
If the Excel input structure changes without prior communication, the automation may fail validation.

Impact:
- Batch interruption
- Increased business exceptions

Mitigation:
- Strict schema validation
- Early file structure verification
- Clear documentation of expected format

---

### 11.1.2 Incorrect Business Rule Configuration
Changes in approval thresholds or logic may cause inconsistent decisions.

Impact:
- Incorrect approvals or rejections
- Compliance exposure

Mitigation:
- Centralized configuration variables
- Version-controlled rule management
- Business validation before deployment

---

## 11.2 Technical Risks

### 11.2.1 API Service Downtime
External risk scoring API may become unavailable during execution.

Impact:
- Increased system exceptions
- SLA breach risk

Mitigation:
- Retry mechanism (2 attempts)
- Transaction isolation via Queue
- Manual reprocessing capability

---

### 11.2.2 Database Connectivity Failure
Loss of database connectivity during execution.

Impact:
- Incomplete transaction persistence
- Execution failure

Mitigation:
- Exception handling and logging
- Transaction-level rollback
- Execution restart capability

---

### 11.2.3 Orchestrator Connectivity Issues
Loss of communication between bot and Orchestrator Cloud.

Impact:
- Execution interruption
- Incomplete logging

Mitigation:
- Stable internet requirement
- Monitoring of bot status
- Manual restart procedures

---

## 11.3 Dependency Risks

### 11.3.1 Third-Party Service Latency
API response time degradation may increase total execution time.

Impact:
- SLA violation risk

Mitigation:
- Timeout configuration (10 seconds)
- Performance monitoring
- Future parallel execution strategy

---

### 11.3.2 Infrastructure Resource Limitation
Insufficient CPU or memory on local execution machine.

Impact:
- Slow execution
- Unexpected failures

Mitigation:
- Resource monitoring
- Controlled batch size
- Future cloud migration planning

---

## 11.4 Data Integrity Risks

### 11.4.1 Duplicate Client Records
Duplicate client_id entries may impact reporting accuracy.

Mitigation:
- Unique constraint at database level
- Pre-processing duplicate validation

---

### 11.4.2 Inconsistent Risk Score Response
API may return null or out-of-range values.

Mitigation:
- Response validation
- Business exception handling
- Logging for audit

---

## 11.5 Compliance and Audit Risks

### 11.5.1 Insufficient Logging
Inadequate logs may prevent root cause analysis.

Mitigation:
- Structured logging strategy
- Differentiation between business and system exceptions
- Persistent processing history

---

Risk monitoring must be reviewed periodically as the system evolves and scales.

---

# 10. Future Considerations

List possible future improvements:
- Scalability adjustments
- Migration to unattended execution
- Enhanced logging
- Monitoring dashboards
