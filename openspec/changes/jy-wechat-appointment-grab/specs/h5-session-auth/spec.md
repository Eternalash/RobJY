## ADDED Requirements

### Requirement: Persist WeChat H5 session after manual auth
The system SHALL support completing WeChat/H5 authorization once in a browser context and persisting the resulting session state to a local file for later reuse.

#### Scenario: Export session after successful auth
- **WHEN** the user finishes authorization and the hospital H5 home (or equivalent logged-in shell) is reachable
- **THEN** the system saves a reusable session state file (cookies and web storage as supported by the automation runtime)

#### Scenario: Reuse session on subsequent runs
- **WHEN** a grab run starts with a valid session state file
- **THEN** the system loads that state into the browser context before navigating to the hospital H5 entry URL

### Requirement: Detect session validity
The system SHALL verify whether the loaded session is still authenticated before entering the booking flow.

#### Scenario: Session still valid
- **WHEN** the home/menu page shows authenticated user signals (for example patient name or insurance-card area)
- **THEN** the system marks auth as ready and continues

#### Scenario: Session expired
- **WHEN** the page redirects to an auth/login challenge or authenticated signals are absent after timeout
- **THEN** the system stops the automated booking attempt and instructs the operator to re-run manual authorization

### Requirement: Configurable H5 entry
The system SHALL read the H5 base entry parameters (including customer/site identifiers needed for 九院/齐脉) from configuration rather than hard-coding them only in source.

#### Scenario: Launch with configured entry
- **WHEN** the operator starts a run with a valid config that includes the H5 entry URL or equivalent site parameters
- **THEN** the system navigates using those configured values
