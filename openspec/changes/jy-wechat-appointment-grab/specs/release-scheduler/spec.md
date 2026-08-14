## ADDED Requirements

### Requirement: Schedule runs for the daily release window
The system SHALL start the grab attempt according to a configured daily release time, defaulting to 07:30 Asia/Shanghai.

#### Scenario: Wake before release
- **WHEN** a scheduled grab is enabled
- **THEN** the system begins warm-up (session check and navigation to the pre-release booking context) at a configured lead time before 07:30

#### Scenario: Enter polling at release time
- **WHEN** the local clock reaches the configured release time
- **THEN** the system begins polling for newly released bookable dates/slots

### Requirement: Poll until success or stop condition
The system SHALL retry slot discovery within the release window until booking succeeds, the window ends, or max attempts are reached.

#### Scenario: Successful grab within window
- **WHEN** a matching bookable slot appears during polling
- **THEN** the system proceeds through the booking flow using selection-priority rules

#### Scenario: Window timeout
- **WHEN** no matching slot is obtained before the configured window end or attempt limit
- **THEN** the system stops polling and reports a timed-out failure

### Requirement: Respect polling rate limits
The system SHALL use a configurable polling interval and MUST avoid unbounded request storms from a single run.

#### Scenario: Interval honored
- **WHEN** polling is active
- **THEN** consecutive refresh/discovery attempts are separated by at least the configured interval

### Requirement: Manual one-shot mode
The system SHALL support a non-scheduled one-shot run for debugging the booking flow outside the 07:30 window.

#### Scenario: Immediate run
- **WHEN** the operator launches one-shot mode
- **THEN** the system executes the booking flow immediately without waiting for the release clock
