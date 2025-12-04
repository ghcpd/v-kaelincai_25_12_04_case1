# MNIST Classifier v2 - Directory Structure

## Overview
```
Claude-haiku-4.5/
├── src/                          # Source code
│   ├── __init__.py
│   └── mnist_classifier_v2.py    # Main v2 implementation (600+ LOC)
│
├── mocks/                        # Mock implementations
│   ├── __init__.py
│   └── mock_api_v2.py           # Mock REST API (300+ LOC)
│
├── data/                         # Test data and fixtures
│   ├── __init__.py
│   └── test_fixtures.json       # 8 test cases with observability assertions
│
├── tests/                        # Integration tests
│   └── __init__.py
│
├── scripts/                      # Executable scripts
│   └── run_integration_tests.sh  # One-click test runner (15 KB)
│
├── docs/                         # Documentation index
│   └── README_DOCS.txt          # Documentation guide
│
└── [Root Documentation Files]
    ├── README.md                          # Project README (quick start)
    ├── EXECUTIVE_SUMMARY.md               # One-page overview
    ├── 01_CURRENT_STATE_ANALYSIS.md       # Root cause analysis (10 KB)
    ├── 02_GREENFIELD_ARCHITECTURE.md      # v2 architecture design (15 KB)
    ├── 03_INTEGRATION_TEST_SUITE.md       # 8+ tests specification (12 KB)
    ├── 04_LOGGING_SCHEMA.md               # Observability design (14 KB)
    ├── 05_COMPARISON_REPORT.md            # v1.1 vs v2 analysis (20 KB)
    ├── ROLLOUT_PLAN.md                    # 4-phase deployment (12 KB)
    ├── DELIVERABLES_INDEX.md              # Complete deliverables index (10 KB)
    └── [Legacy files - to be archived]
        ├── data_test_fixtures.json        # Copy in data/test_fixtures.json
        ├── mocks_mock_api_v2.py           # Copy in mocks/mock_api_v2.py
        ├── src_v2_mnist_classifier_v2.py  # Copy in src/mnist_classifier_v2.py
        └── run_integration_tests.sh       # Copy in scripts/run_integration_tests.sh
```

## Key Locations

### Implementation Code
- **v2 Runtime**: `src/mnist_classifier_v2.py`
  - Classes: MNISTClassifierV2, StructuredLogger, CircuitBreaker, IdempotencyStore, AuditStore
  - Features: Explicit normalization (fixes v1.1 bug), idempotency, retry, timeout, circuit breaker, logging, audit trail

- **Mock API**: `mocks/mock_api_v2.py`
  - Endpoints: POST /api/v2/predict, GET /api/v2/health, GET /api/v2/metrics
  - Status codes: 200 (success), 4xx (client errors), 5xx (server errors)

### Test Fixtures
- **Test Data**: `data/test_fixtures.json`
  - 8 canonical test cases
  - Test fixtures (model_path, image_paths, default parameters)
  - Observability assertions

### Test Runner
- **Script**: `scripts/run_integration_tests.sh`
  - One-click execution
  - 5 v2 implementation tests
  - 3 mock API tests
  - Generates results summary

### Documentation
- **Analysis**: `01_CURRENT_STATE_ANALYSIS.md`
  - Root cause: Missing normalization at line 47 of v1.1
  - Evidence: Code inspection, test failures, activation analysis
  - Crash points: File I/O, preprocessing, forward pass

- **Architecture**: `02_GREENFIELD_ARCHITECTURE.md`
  - 12-state unified state machine
  - 5-layer service decomposition
  - API contracts with JSON schemas
  - Idempotency, retry, timeout, circuit breaker design

- **Testing**: `03_INTEGRATION_TEST_SUITE.md`
  - 8 repeatable tests
  - Preprocessing, idempotency, retry, timeout, consistency, performance, confidence, error handling

- **Logging**: `04_LOGGING_SCHEMA.md`
  - Structured JSON logging
  - Request tracing (trace_id, span_id)
  - Sensitive field masking (image_path → hash)
  - Metrics collection and alert rules

- **Comparison**: `05_COMPARISON_REPORT.md`
  - v1.1 vs v2: 7 dimensions (correctness, reliability, performance, idempotency, observability, migration, cost)
  - Cost analysis: $37K annual savings
  - Migration path: 4 phases with gates and rollback

- **Rollout**: `ROLLOUT_PLAN.md`
  - 4-phase deployment strategy
  - Phase 1: Shadow Mode (Week 1)
  - Phase 2: Canary (Week 2)
  - Phase 3: Ramp-Up (Week 3-4)
  - Phase 4: Full Cutover (Week 5+)
  - Emergency rollback: < 5 min

## File Organization Rationale

### `src/` - Source Code
- **Purpose**: Production-ready implementation
- **Contents**: MNISTClassifierV2 main class + supporting classes
- **Build**: Python 3.8+, imports: numpy, PIL
- **Deploy**: Copy to production environment

### `mocks/` - Mock Implementations
- **Purpose**: Integration testing without production infrastructure
- **Contents**: MockMNISTAPI, MockAPIResponse
- **Use**: Simulate REST endpoints for testing

### `data/` - Test Data
- **Purpose**: Provide reproducible test scenarios
- **Contents**: Test fixtures (JSON) with 8 canonical test cases
- **Scope**: Model paths, image paths, expected results, observability assertions

### `scripts/` - Automation
- **Purpose**: Executable test and deployment scripts
- **Contents**: Test runner with prerequisite checks
- **Execute**: `bash scripts/run_integration_tests.sh`

### `docs/` - Documentation Index
- **Purpose**: Guide readers to documentation
- **Contents**: README pointing to all analysis and architecture docs

### Root - Documentation
- **Purpose**: Easy access to analysis and deployment guidance
- **Audience**: Stakeholders, engineers, DevOps teams
- **Scope**: Analysis, architecture, testing, logging, comparison, rollout

## Quick Navigation

**For Project Managers**:
- Start: `EXECUTIVE_SUMMARY.md`
- Details: `05_COMPARISON_REPORT.md`, `ROLLOUT_PLAN.md`

**For Engineers**:
- Analysis: `01_CURRENT_STATE_ANALYSIS.md`
- Design: `02_GREENFIELD_ARCHITECTURE.md`
- Code: `src/mnist_classifier_v2.py`
- Tests: `03_INTEGRATION_TEST_SUITE.md`, `scripts/run_integration_tests.sh`

**For DevOps/SREs**:
- Deployment: `ROLLOUT_PLAN.md`, `EXECUTIVE_SUMMARY.md`
- Observability: `04_LOGGING_SCHEMA.md`
- Monitoring: Alert rules in `04_LOGGING_SCHEMA.md`

**For QA/Testers**:
- Test Coverage: `03_INTEGRATION_TEST_SUITE.md`
- Test Fixtures: `data/test_fixtures.json`
- Test Runner: `scripts/run_integration_tests.sh`

## Dependencies

### Python Packages
- `numpy>=1.26.0` - Numerical computing
- `Pillow>=10.0.0` - Image I/O
- `pytest>=7.4.0` - Test framework (optional, for pytest compatibility)

### Files Required for Execution
- `models/mnist_model.npy` - Pre-trained model weights
- `data/test_digit_7.png` - Test image for digit 7
- `data/test_digit_3.png` - Test image for digit 3

## Status: ✅ Complete

All files organized according to specifications:
- ✅ Source code in `src/`
- ✅ Mock API in `mocks/`
- ✅ Test fixtures in `data/`
- ✅ Test runner in `scripts/`
- ✅ Documentation in root + `docs/`
- ✅ All supporting files in place

Ready for Phase 1 (Shadow Mode) deployment.
