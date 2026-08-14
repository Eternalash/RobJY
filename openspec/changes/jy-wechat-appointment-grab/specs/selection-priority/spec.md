## ADDED Requirements

### Requirement: Campus priority order
The system SHALL choose campuses according to a configured priority list, defaulting to 南部院区 first, then 高科园区.

#### Scenario: Prefer southern campus when available
- **WHEN** both 南部院区 and 高科园区 have bookable slots matching other filters
- **THEN** the system selects 南部院区

#### Scenario: Fall back to GaoKe campus
- **WHEN** 南部院区 has no matching bookable slot but 高科园区 does
- **THEN** the system selects 高科园区

#### Scenario: Skip unlisted campuses by default
- **WHEN** only campuses outside the configured priority list have slots
- **THEN** the system does not book those campuses unless the config explicitly includes them

### Requirement: Department targeting
The system SHALL enter the department specified in configuration via the department navigation UI (category list and sub-department list as presented by the H5).

#### Scenario: Select configured department
- **WHEN** the department panel is available and the config specifies a department name
- **THEN** the system locates and opens that department (exact or configured match rule)

#### Scenario: Department not found
- **WHEN** the configured department cannot be found within timeout
- **THEN** the system fails the run with an explicit department-not-found error

### Requirement: Doctor title priority
The system SHALL prefer doctors by professional title order, defaulting to 主任医师 then 副主任医师.

#### Scenario: Prefer chief physician
- **WHEN** bookable schedules exist for both 主任医师 and 副主任医师 under the selected campus/department filters
- **THEN** the system chooses a 主任医师 schedule

#### Scenario: Fall back to associate chief physician
- **WHEN** no 主任医师 schedule is bookable but a 副主任医师 schedule is
- **THEN** the system chooses a 副主任医师 schedule

#### Scenario: No matching title
- **WHEN** no doctor with a configured title priority is bookable
- **THEN** the system does not select lower-priority titles unless the config explicitly allows them

### Requirement: Tie-break among equal-priority candidates
The system SHALL apply a deterministic tie-break when multiple candidates share the same campus and title priority.

#### Scenario: Earliest bookable date wins
- **WHEN** multiple doctors share the same selected campus and title rank and have available dates
- **THEN** the system prefers the candidate with the earliest available bookable date (and earliest slot if dates tie), unless config overrides the tie-break
