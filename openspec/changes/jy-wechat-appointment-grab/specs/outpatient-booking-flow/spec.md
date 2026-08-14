## ADDED Requirements

### Requirement: Enter outpatient appointment from home
The system SHALL navigate from the authenticated H5 home into the outpatient appointment（门诊预约）flow.

#### Scenario: Open outpatient appointment
- **WHEN** auth is ready and the operator/run requests outpatient booking
- **THEN** the system activates the outpatient appointment entry and reaches the appointment notice or department selection stage

### Requirement: Accept appointment notice
The system SHALL complete the appointment notice acknowledgements required before booking：agree（「是」）then dismiss（「我知道了」）.

#### Scenario: Notice agreement sequence
- **WHEN** the appointment notice dialog is shown
- **THEN** the system selects agreement「是」and subsequently confirms「我知道了」，proceeding only after both are completed

### Requirement: Book by date then time slot
The system SHALL, after a doctor/schedule candidate is chosen, select an available date, click预约, select a time slot, and click确认.

#### Scenario: Date and slot confirmation
- **WHEN** an available date exists for the selected doctor and campus
- **THEN** the system selects that date, clicks预约, chooses a configured or earliest acceptable time slot, and clicks确认

### Requirement: Confirm patient then submit with captcha
The system SHALL confirm the target patient（就诊人）and submit the reservation only after a captcha value is provided.

#### Scenario: Patient confirmation
- **WHEN** the patient confirmation step is shown
- **THEN** the system selects or affirms the configured patient identity

#### Scenario: Captcha then final reserve
- **WHEN** the captcha challenge is presented
- **THEN** the system waits for an operator-supplied captcha value, fills it, and clicks预约 to submit

#### Scenario: Optional final submit gate
- **WHEN** config enables submit confirmation
- **THEN** the system MUST NOT click the final预约 until the operator explicitly confirms

### Requirement: Emit step-level outcomes
The system SHALL record success or failure for each booking step with enough detail to diagnose UI or data mismatches.

#### Scenario: Step failure logging
- **WHEN** any booking step fails or times out
- **THEN** the system logs the step name, failure reason, and a page screenshot or equivalent artifact when available
