# User Stories
Translated from SRS Functional Requirements.
*Source: docs/FULL-SRS.md*

---

## [FR-AUTH] — Authentication & Registration

### US-001 — User Registration
**Priority:** Must Have
**Story:**
> As a fleet owner or driver, I want to register an account by providing my company name, full name, email, password, and role, so that I can access Flotte225 and use the features relevant to my role.

**Acceptance Criteria:**
- [ ] Given I'm on the registration page, when I submit valid details with a unique email, then my account is created and an OTP verification email is sent to me.
- [ ] Given I submit an email that already exists, when I click register, then I see a clear error message and no account is created.
- [ ] Given I complete registration, when my account is created, then my password is stored hashed (bcrypt) and never in plaintext.
- [ ] Given I select a role at registration, when my account is active, then my role cannot be changed by any UI action or API call.

---

### US-002 — Email Verification via OTP
**Priority:** Must Have
**Story:**
> As a newly registered user, I want to verify my email address using an OTP code sent to my inbox, so that my account is activated and my email ownership is confirmed.

**Acceptance Criteria:**
- [ ] Given I've registered, when I enter the correct OTP, then my account is activated and I'm redirected to login.
- [ ] Given I enter an incorrect OTP, when I submit, then I see an error and my account remains inactive.
- [ ] Given 15 minutes have passed, when I try to use the OTP, then it is rejected as expired and I am prompted to request a new one.

---

### US-003 — Login & Role-Based Redirect
**Priority:** Must Have
**Story:**
> As a registered user, I want to log in with my email and password and be automatically redirected to my role-specific dashboard, so that I can access my workspace without extra navigation.

**Acceptance Criteria:**
- [ ] Given valid credentials, when I log in, then I receive a JWT (24h expiry) and am redirected to the correct dashboard (owner / driver / admin).
- [ ] Given an invalid password or unknown email, when I submit, then I see an error and no token is issued.
- [ ] Given my token has expired, when I navigate to a protected page, then I am redirected to login with an appropriate message.
- [ ] Given my account is suspended, when I try to log in, then I see a clear suspension message.

---

### US-004 — Password Reset via OTP
**Priority:** Must Have
**Story:**
> As a user who forgot my password, I want to receive a 6-digit OTP by email to reset my password, so that I can regain access to my account without contacting support.

**Acceptance Criteria:**
- [ ] Given I enter my email on the forgot-password page, when I submit, then the system always responds "If this email is registered, you will receive a reset code" — regardless of whether the email exists.
- [ ] Given a valid OTP is entered within 15 minutes, when I submit a new password, then my password is updated and the OTP is invalidated.
- [ ] Given an OTP that has already been used, when I try to reuse it, then it is rejected.
- [ ] Given 15 minutes have passed, when I try to use the OTP, then it is rejected as expired.

---

## [FR-VEH] — Vehicle Management

### US-005 — Register a Vehicle
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to register a new vehicle with its details (name, brand, model, plate, fuel type, initial mileage), so that I can start tracking it in my fleet.

**Acceptance Criteria:**
- [ ] Given I'm on the vehicles page, when I submit a valid vehicle form with all required fields, then the vehicle is created and appears in my fleet list.
- [ ] Given I enter a license plate that already exists in the system, when I submit, then the form is rejected with a clear duplicate plate error.
- [ ] Given I leave a required field empty (name, brand, model, plate, fuel type, initial mileage), when I submit, then validation blocks submission with a field-level error.
- [ ] Given I create a vehicle, when the form is submitted, then I can optionally assign one or more existing drivers to it at the same time.

---

### US-006 — Edit a Vehicle
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to update any field of an existing vehicle, so that I can keep my fleet records accurate over time.

**Acceptance Criteria:**
- [ ] Given I open a vehicle's edit form, when I change any field and save, then the vehicle record is updated immediately.
- [ ] Given I change the license plate to one that already belongs to another vehicle, when I save, then the update is rejected with a duplicate plate error.

---

### US-007 — Pause and Resume a Vehicle
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to mark a vehicle as Paused (en panne) when it's temporarily unavailable, so that it doesn't generate false anomaly alerts and drivers can't log fuel entries for it.

**Acceptance Criteria:**
- [ ] Given an active vehicle, when I click "Pause", then its status changes to Paused and a distinct badge is shown in all lists.
- [ ] Given a paused vehicle, when a driver attempts to submit a fuel entry for it, then the submission is rejected.
- [ ] Given a paused vehicle, when I click "Resume", then it returns to Active status and all features work again.
- [ ] Given a paused vehicle, when the alert engine runs, then no performance anomaly alerts are generated for it.

---

### US-008 — Archive a Vehicle (Soft Delete)
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to archive a vehicle I no longer use instead of deleting it, so that I preserve all historical data while keeping my active list clean.

**Acceptance Criteria:**
- [ ] Given an active vehicle, when I archive it, then it disappears from all operational views (dashboard, fuel entry, active lists).
- [ ] Given an archived vehicle, when I open the "Archived Vehicles" section, then I can see it with all its historical data intact.
- [ ] Given a driver was active on the archived vehicle, when archiving completes, then that driver's status is automatically reset to Inactive.
- [ ] Given an archived vehicle, when I click "Restore", then it returns to active status and is visible in all operational views again.

---

### US-009 — Assign and Remove Drivers from a Vehicle
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to assign or remove drivers from any of my vehicles at any time, so that I control who can submit fuel entries for each vehicle.

**Acceptance Criteria:**
- [ ] Given a vehicle's details page, when I search for and add a driver, then that driver is assigned and can log fuel for the vehicle.
- [ ] Given I try to assign a user with the OWNER role, when I search, then OWNER-role accounts do not appear in the assignable driver list.
- [ ] Given a driver is currently active (driving status = ON) on a vehicle, when I remove them from that vehicle, then their driving status is automatically reset to Inactive.
- [ ] Given a driver is assigned to Vehicle A and Vehicle B, when I remove them from Vehicle A, then their assignment to Vehicle B is unaffected.

---

## [FR-FUEL] — Fuel Entry Management

### US-010 — Submit a Fuel Entry
**Priority:** Must Have
**Story:**
> As an active driver, I want to submit a fuel entry with the vehicle, date, odometer reading, quantity, and amount paid, so that my fleet owner has accurate refueling data for cost and consumption tracking.

**Acceptance Criteria:**
- [ ] Given I am active (driving status = ON) and assigned to the selected vehicle, when I submit a valid fuel entry, then it is saved and appears in my recent entries list.
- [ ] Given I am inactive (driving status = OFF), when I attempt to submit a fuel entry, then the submission is rejected with a clear message asking me to activate my driving status first.
- [ ] Given I select a vehicle I am not assigned to, when I submit, then the entry is rejected.
- [ ] Given I enter an odometer reading equal to or less than the previous reading for that vehicle, when I submit, then the entry is rejected with an odometer validation error.
- [ ] Given all fields are valid, when the entry is saved, then distance driven and consumption (L/100km) are automatically calculated and stored.

---

### US-011 — View My Fuel Entry History
**Priority:** Must Have
**Story:**
> As a driver, I want to see my last 10 fuel entries on my dashboard, so that I can quickly verify my recent submissions without navigating elsewhere.

**Acceptance Criteria:**
- [ ] Given I am logged in as a driver, when I open my dashboard, then my last 10 fuel entries are displayed (date, vehicle, odometer, litres, amount).
- [ ] Given I have fewer than 10 entries, when I view the dashboard, then all available entries are shown.
- [ ] Given I have no entries, when I view the dashboard, then an empty state message is displayed.

---

### US-012 — Edit a Fuel Entry (within 24h)
**Priority:** Must Have
**Story:**
> As a driver, I want to correct a fuel entry I submitted within the last 24 hours, so that I can fix mistakes before the data becomes permanent.

**Acceptance Criteria:**
- [ ] Given an entry submitted less than 24 hours ago, when I edit and save it, then the record is updated and an activity log entry is created capturing before and after values.
- [ ] Given an entry submitted more than 24 hours ago, when I try to edit it, then the edit option is not available and the entry is shown as locked.
- [ ] Given I edit an entry, when the odometer value I enter is not strictly greater than the previous entry for that vehicle, then the update is rejected.

---

### US-013 — Delete a Fuel Entry (within 24h)
**Priority:** Must Have
**Story:**
> As a driver, I want to delete a fuel entry I submitted within the last 24 hours, so that I can remove accidental or duplicate submissions before they affect fleet analytics.

**Acceptance Criteria:**
- [ ] Given an entry submitted less than 24 hours ago, when I delete it, then the entry is removed and an activity log entry is created with a full data snapshot of the deleted record.
- [ ] Given an entry submitted more than 24 hours ago, when I try to delete it, then the delete option is not available.

---

### US-014 — Owner Views Fleet Fuel Entries
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to view all fuel entries submitted across my fleet, so that I can monitor refueling activity and verify data accuracy.

**Acceptance Criteria:**
- [ ] Given I am logged in as an owner, when I navigate to the fuel entries section, then I see all entries for all my vehicles (not other owners' vehicles).
- [ ] Given I view the fuel entries list, when I look at any entry, then I can see the driver, vehicle, date, odometer, litres, amount, and calculated consumption.
- [ ] Given I am an owner, when I attempt to edit or delete a fuel entry, then no such action is available — the view is read-only.

---

## [FR-MAINT] — Maintenance & Compliance

### US-015 — Manage Maintenance Records
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to record the last oil change odometer reading, insurance expiry date, and technical inspection expiry date for each vehicle, so that I can track compliance and get timely alerts before deadlines are missed.

**Acceptance Criteria:**
- [ ] Given I open the maintenance page for a vehicle, when no record exists yet, then an empty maintenance form is automatically created and displayed.
- [ ] Given I enter one or more maintenance fields and save, then the values are stored and immediately reflected in the alert engine.
- [ ] Given I leave some fields empty, when I save, then only the filled fields are stored — empty fields do not generate alerts.
- [ ] Given a maintenance record exists, when I update any field and save, then the record is updated and alerts are recalculated instantly.

---

### US-016 — Oil Change Tracking by Mileage
**Priority:** Must Have
**Story:**
> As a fleet owner, I want the system to track kilometers driven since the last oil change, so that I am alerted when a vehicle is approaching or has exceeded the 500 km oil change threshold.

**Acceptance Criteria:**
- [ ] Given a vehicle has an oil change odometer reading recorded, when new fuel entries push cumulative km driven to between 400 and 500 km since last oil change, then a Warning alert is generated.
- [ ] Given cumulative km driven since last oil change exceeds 500 km, when the alert engine runs, then a Critical alert is generated for that vehicle.
- [ ] Given I update the oil change odometer reading after a service, when I save, then the km counter resets and previous oil change alerts are cleared.
- [ ] Given no oil change odometer reading is recorded for a vehicle, when the alert engine runs, then no oil change alert is generated.

---

## [FR-DASH-OWN] — Owner Dashboard

### US-017 — View Fleet Financial Summary
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to see total fuel spend, spend per vehicle as a bar chart, and a monthly trend line chart on my dashboard, so that I can quickly understand where my money is going and whether costs are rising.

**Acceptance Criteria:**
- [ ] Given I open my dashboard, when fuel entries exist, then total fleet spend is displayed as a summary figure.
- [ ] Given multiple vehicles exist, when I view the dashboard, then a bar chart shows spend per vehicle with alternating green/gold colors.
- [ ] Given entries span multiple months, when I view the dashboard, then a line chart with gradient shows month-over-month spend evolution.
- [ ] Given no fuel entries exist yet, when I open the dashboard, then charts display an empty state rather than errors.

---

### US-018 — View Fleet Consumption Indicators
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to see average fuel consumption per vehicle (L/100km) in a summary table, so that I can identify which vehicles are consuming more fuel than expected.

**Acceptance Criteria:**
- [ ] Given at least 2 fuel entries with valid distance for a vehicle exist, when I view the dashboard, then that vehicle's average consumption is shown in L/100km.
- [ ] Given a vehicle has only 1 entry or no calculable distance, when I view the table, then its consumption shows as "—" or "Insuffisant" rather than a misleading number.

---

### US-019 — View Driver Status Panel
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to see all my drivers listed with their current status (Active / Inactive) and, for active drivers, which vehicle they are driving, so that I can monitor field operations in real time.

**Acceptance Criteria:**
- [ ] Given drivers are assigned to my vehicles, when I open the dashboard, then all drivers are listed with name and status.
- [ ] Given a driver is active, when I view the panel, then the vehicle they are currently driving is shown alongside their name.
- [ ] Given a driver is inactive, when I view the panel, then no vehicle is shown for them.

---

### US-020 — View Alerts, Anomalies & Compliance Deadlines
**Priority:** Must Have
**Story:**
> As a fleet owner, I want to see active maintenance alerts, performance anomalies, and upcoming compliance deadlines on my dashboard, so that I can take action before problems escalate.

**Acceptance Criteria:**
- [ ] Given a vehicle has a critical maintenance alert, when I open the dashboard, then it appears in red in the alerts section.
- [ ] Given a vehicle has a warning alert, when I open the dashboard, then it appears in orange.
- [ ] Given a vehicle's insurance or inspection expires within 30 days, when I view the compliance section, then it shows with the number of days remaining.
- [ ] Given a vehicle has an anomaly (consumption spike or cost spike), when I view the dashboard, then it appears in the anomalies section with the anomaly type indicated.

---

### US-021 — View Dashboard Visualizations
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to see a donut chart of spend by vehicle, a spend growth gauge, and an operational fleet gauge on my dashboard, so that I can get an at-a-glance health summary of my entire fleet.

**Acceptance Criteria:**
- [ ] Given I open the dashboard, when data exists, then a donut chart shows spend distribution across vehicles.
- [ ] Given month-over-month data exists, when I view the dashboard, then a circular gauge shows the spend growth rate (%).
- [ ] Given my fleet has vehicles, when I view the operational gauge, then it shows the percentage of vehicles with no critical alert, not archived, and not paused.
- [ ] Given all vehicles are healthy, when I view the gauge, then it shows 100%.

---

## [FR-DASH-DRV] — Driver Dashboard

### US-022 — View Assigned Vehicles
**Priority:** Must Have
**Story:**
> As a driver, I want to see the list of vehicles assigned to me on my dashboard, so that I know which vehicles I am authorized to log fuel for.

**Acceptance Criteria:**
- [ ] Given I am logged in as a driver, when I open my dashboard, then I see only the vehicles assigned to me (brand, model, plate).
- [ ] Given a vehicle is unassigned from me, when I refresh my dashboard, then it no longer appears in my list.
- [ ] Given no vehicles are assigned to me yet, when I open my dashboard, then a clear empty state message is shown.

---

### US-023 — Toggle Driving Status
**Priority:** Must Have
**Story:**
> As a driver, I want to activate or deactivate my driving status from my dashboard and select which vehicle I am currently driving, so that the system knows I am on a mission and allows me to submit fuel entries.

**Acceptance Criteria:**
- [ ] Given I am inactive, when I click the activation toggle, then I am prompted to select one of my assigned vehicles before status is set to Active.
- [ ] Given I select a vehicle and confirm, when activation completes, then my status shows Active with the selected vehicle name.
- [ ] Given I am active, when I click the toggle again, then my driving status is set to Inactive and no vehicle is shown.
- [ ] Given I am inactive, when I try to submit a fuel entry, then the submission is blocked with a prompt to activate first.

---

## [FR-LOG] — Activity Log (Audit Trail)

### US-024 — Automatic Activity Logging
**Priority:** Must Have
**Story:**
> As a fleet owner, I want every fuel entry creation, edit, and deletion by my drivers to be automatically recorded in an activity log, so that I have a full audit trail of who changed what and when.

**Acceptance Criteria:**
- [ ] Given a driver submits a new fuel entry, when it is saved, then a CREATE log entry is recorded with all submitted values, the driver's identity, the vehicle, and a server-side timestamp.
- [ ] Given a driver edits a fuel entry, when the update is saved, then an UPDATE log entry is recorded with both the before and after values.
- [ ] Given a driver deletes a fuel entry, when the deletion completes, then a DELETE log entry is recorded with a full snapshot of the deleted data.
- [ ] Given these actions occur, when the owner views the log, then entries are displayed in reverse chronological order (newest first).

---

### US-025 — Filter Activity Log
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to filter the activity log by driver or by vehicle, so that I can quickly investigate the actions of a specific driver or trace changes to a specific vehicle.

**Acceptance Criteria:**
- [ ] Given I am on the activity log page, when I select a driver from the filter, then only log entries created by that driver are displayed.
- [ ] Given I select a vehicle from the filter, when the filter is applied, then only log entries related to that vehicle are displayed.
- [ ] Given I clear the filter, when I view the log, then all entries are shown again.
- [ ] Given no entries match the filter, when I apply it, then an empty state message is shown rather than an error.

---

## [FR-ALERT] — Alerts & Anomaly Detection

### US-026 — Maintenance & Compliance Alerts
**Priority:** Must Have
**Story:**
> As a fleet owner, I want the system to automatically generate critical and warning alerts for overdue or upcoming insurance, technical inspection, and oil change deadlines, so that I never miss a compliance obligation.

**Acceptance Criteria:**
- [ ] Given a vehicle's insurance expiry date has passed, when alerts are evaluated, then a Critical (red) alert is shown for that vehicle.
- [ ] Given a vehicle's insurance expiry is within 30 days, when alerts are evaluated, then a Warning (orange) alert is shown.
- [ ] Given a vehicle's technical inspection expiry date has passed, when alerts are evaluated, then a Critical (red) alert is shown.
- [ ] Given a vehicle's inspection expiry is within 30 days, when alerts are evaluated, then a Warning (orange) alert is shown.
- [ ] Given a maintenance field is empty for a vehicle, when alerts are evaluated, then no alert is generated for that field.
- [ ] Given a vehicle is paused or archived, when alerts are evaluated, then no alerts are generated for it.

---

### US-027 — Abnormal Fuel Consumption Detection
**Priority:** Should Have
**Story:**
> As a fleet owner, I want the system to flag a vehicle when its latest fuel consumption deviates more than 20% from its historical average, so that I can investigate potential fuel theft, mechanical issues, or driver behavior problems.

**Acceptance Criteria:**
- [ ] Given a vehicle has at least 2 fuel entries with valid consumption values, when a new entry is submitted with consumption > 20% above or below the historical average, then the vehicle is flagged as anomalous in the dashboard.
- [ ] Given a vehicle has fewer than 2 valid consumption entries, when alerts are evaluated, then no consumption anomaly is raised for it.
- [ ] Given the anomaly is resolved (subsequent entries return to normal), when alerts are re-evaluated, then the flag is cleared.

---

### US-028 — Monthly Cost Spike Detection
**Priority:** Should Have
**Story:**
> As a fleet owner, I want the system to flag a vehicle when its fuel spend this month is more than 30% above last month's spend, so that I can quickly spot abnormal cost increases before they impact my budget.

**Acceptance Criteria:**
- [ ] Given previous month data exists for a vehicle, when the current month's total spend exceeds it by more than 30%, then a cost spike anomaly is shown on the dashboard for that vehicle.
- [ ] Given no previous month data exists, when alerts are evaluated, then no cost spike alert is raised.
- [ ] Given the anomalous vehicle appears on the dashboard, when I view it, then the anomaly type (cost spike or consumption anomaly) is clearly labeled.

---

## [FR-WEBHOOK] — Webhook Notifications

### US-029 — Automated Webhook Dispatch
**Priority:** Could Have
**Story:**
> As a system administrator, I want the system to automatically send a fleet summary payload to a configured webhook URL every 24 hours, so that external tools (Slack, internal dashboards) receive regular fleet updates without manual intervention.

**Acceptance Criteria:**
- [ ] Given `WEBHOOK_URL` is set in the environment, when 24 hours have elapsed since the last dispatch, then the system sends a POST request to the configured URL with the fleet summary payload.
- [ ] Given `WEBHOOK_URL` is not set, when the scheduler runs, then no request is made and no error is raised.
- [ ] Given the webhook fires, when I check the payload, then it includes the owner identity, period covered, alert summary (total, critical, warning by type), and driver activity delta since last send.
- [ ] Given the interval is configured via `WEBHOOK_INTERVAL_HOURS`, when the variable is changed, then the scheduler respects the new interval on next restart.

---

### US-030 — View Last Webhook Status
**Priority:** Could Have
**Story:**
> As a fleet owner, I want to see the date and HTTP status of the last webhook dispatch from my dashboard, so that I can confirm my external integrations are receiving data correctly.

**Acceptance Criteria:**
- [ ] Given a webhook has been dispatched, when I view the relevant section of my dashboard, then I see the timestamp and HTTP response status of the last send.
- [ ] Given the last webhook failed (non-2xx response), when I view the status, then it is clearly shown as failed.
- [ ] Given no webhook has ever been sent, when I view the section, then a "No dispatch yet" state is shown.

---

## [FR-EXPORT] — Data Export

### US-031 — Export Fleet Data to PDF or Excel
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to export my fuel entries, analytics summary, maintenance records, or activity logs as a PDF or Excel file, so that I can share reports with stakeholders or keep offline records.

**Acceptance Criteria:**
- [ ] Given I am on the export page, when I select a dataset type (fuel entries, analytics, maintenance, activity log), a format (PDF or Excel), and optionally a date range, then the file is generated and downloaded to my device.
- [ ] Given I select PDF, when the file is generated, then it is formatted with Flotte225 brand styling (green/gold palette), headers, and tables.
- [ ] Given I select Excel (.xlsx), when the file is generated, then it contains raw tabular data suitable for further analysis.
- [ ] Given I apply a date range filter, when the export runs, then only entries within that range are included.
- [ ] Given I am on the Starter plan, when I attempt to access the export page, then I see a locked-state UI with an upgrade prompt instead of the export form.

---

## [FR-AI] — AI-Generated Reports

### US-032 — Generate an On-Demand AI Fleet Report
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to trigger an AI-generated fleet report with one click and receive it by email, so that I get a plain-French summary of my fleet's performance without having to interpret raw data myself.

**Acceptance Criteria:**
- [ ] Given I am on the reports page, when I click "Generate Report", then a loading indicator is shown while the report is being prepared.
- [ ] Given the report is generated successfully, when it is ready, then it is sent to my registered email address within 2 minutes and a confirmation message is shown in the UI.
- [ ] Given the report is generated, when I receive the email, then it contains plain-French interpretation of: fleet spend trend, best/worst vehicles, driver behavior summary, upcoming compliance deadlines, and actionable recommendations.
- [ ] Given the OpenRouter API call fails, when the report cannot be generated, then an error message is shown in the UI and no email is sent.
- [ ] Given I am on the Starter plan, when I access the reports page, then the generate button is locked with an upgrade prompt.
- [ ] Given I am on the Pro plan, when I have already generated 5 reports this month, then the button is disabled with a message indicating the monthly limit is reached.

---

### US-033 — Configure Scheduled AI Reports
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to configure a recurring AI report schedule (weekly or monthly) and receive it automatically by email, so that I stay informed about my fleet without having to remember to generate reports manually.

**Acceptance Criteria:**
- [ ] Given I am on the reports page, when I enable the schedule and select Weekly (every Monday) or Monthly (1st of each month), then the schedule is saved and active.
- [ ] Given a schedule is active, when the scheduled time arrives, then the system automatically generates and emails the report to my registered address.
- [ ] Given I toggle the schedule off, when I save, then no further automated reports are sent until re-enabled.
- [ ] Given I am on the Pro plan, when I try to enable a scheduled report, then the schedule option is locked with an upgrade prompt (Business plan required).
- [ ] Given I am on the Business plan, when I view the reports page, then I can see the date and status (Sent / Failed) of the last scheduled report.

---

## [FR-WA] — WhatsApp Integration

### US-034 — Configure WhatsApp Notifications
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to add my WhatsApp-enabled phone number in my profile settings, so that the system can send me fleet notifications and critical alerts directly on WhatsApp.

**Acceptance Criteria:**
- [ ] Given I am on my profile settings page, when I enter a valid WhatsApp-enabled phone number and save, then the number is stored and used for WhatsApp notifications.
- [ ] Given I am on the Starter plan, when I access the WhatsApp settings field, then it is locked with an upgrade prompt (Pro plan required).
- [ ] Given WhatsApp API credentials are not configured in the environment, when I save my number, then the feature is silently disabled and no WhatsApp messages are sent.

---

### US-035 — Receive WhatsApp Fleet Alerts
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to receive WhatsApp messages for critical alerts (expired insurance, inspection) and detected performance anomalies, so that urgent issues reach me instantly even when I'm not logged into the app.

**Acceptance Criteria:**
- [ ] Given a vehicle has a critical alert (insurance expired or inspection expired), when the notification engine runs, then a WhatsApp message is sent to my configured number describing the alert.
- [ ] Given a vehicle is flagged with a performance anomaly (consumption or cost spike), when the notification engine runs, then a WhatsApp message is sent with the anomaly details.
- [ ] Given no critical alerts or anomalies exist, when the notification engine runs, then no WhatsApp message is sent.
- [ ] Given a daily summary is due, when it triggers, then the WhatsApp message contains the same payload structure as the webhook (alert summary + driver activity delta).

---

## [FR-ADMIN] — Super Admin

### US-036 — View & Search All Users
**Priority:** Must Have
**Story:**
> As a super admin, I want to view a paginated, searchable list of all registered users, so that I can find and manage any account on the platform quickly.

**Acceptance Criteria:**
- [ ] Given I am logged in as a super admin, when I open the admin dashboard, then I see a paginated list of all owners and drivers.
- [ ] Given I type a name or email in the search field, when I submit, then only matching users are shown.
- [ ] Given no users match the search, when I submit, then an empty state is shown.

---

### US-037 — Suspend & Reactivate a User Account
**Priority:** Must Have
**Story:**
> As a super admin, I want to suspend or reactivate any user account, so that I can enforce platform rules and handle abuse or non-payment situations.

**Acceptance Criteria:**
- [ ] Given I find a user in the admin list, when I click "Suspend", then their account is immediately suspended.
- [ ] Given a user's account is suspended, when they attempt to log in, then they are blocked and shown a clear suspension message.
- [ ] Given a suspended account, when I click "Reactivate", then the user can log in again normally.

---

### US-038 — Permanently Delete a User Account
**Priority:** Must Have
**Story:**
> As a super admin, I want to permanently delete a user account and all its associated data, so that I can comply with deletion requests or remove abandoned accounts.

**Acceptance Criteria:**
- [ ] Given I select a user account, when I click "Delete", then a confirmation dialog appears warning that this action is irreversible.
- [ ] Given I confirm the deletion, when it completes, then the user and all their associated data (vehicles, fuel entries, maintenance records, logs) are permanently removed.
- [ ] Given I cancel the confirmation dialog, when it closes, then no data is deleted.

---

### US-039 — View Any Owner's Fleet
**Priority:** Must Have
**Story:**
> As a super admin, I want to view any owner's vehicle list and fleet summary, so that I can assist with support requests or audit data without needing to log in as that owner.

**Acceptance Criteria:**
- [ ] Given I find an owner in the admin panel, when I click "View Fleet", then I see their full vehicle list and fleet summary in read-only mode.
- [ ] Given I am viewing an owner's fleet, when I look at the data, then I cannot modify any records from the admin view.

---

### US-040 — Manage Subscription Plans per Owner
**Priority:** Must Have
**Story:**
> As a super admin, I want to view and manually change the subscription plan of any owner, so that I can handle manual payments, trials, and support exceptions without a payment gateway.

**Acceptance Criteria:**
- [ ] Given I open an owner's admin profile, when I view their details, then their current plan (Starter / Pro / Business) is clearly shown.
- [ ] Given I select a new plan and save, when the change is applied, then the owner's feature access updates immediately to match the new plan.
- [ ] Given I activate or deactivate a specific feature flag for an owner, when I save, then that override takes effect regardless of their plan tier.

---

### US-041 — View Platform-Wide Analytics
**Priority:** Should Have
**Story:**
> As a super admin, I want to view platform-wide analytics (total owners, drivers, vehicles, fuel entries, plan distribution, registration trends), so that I can monitor the health and growth of the Flotte225 platform.

**Acceptance Criteria:**
- [ ] Given I open the admin analytics section, when data exists, then I see total counts for owners, drivers, vehicles, and fuel entries.
- [ ] Given multiple plans are in use, when I view the plan distribution section, then I see how many owners are on each plan (Starter / Pro / Business).
- [ ] Given registrations have occurred over time, when I view the trend chart, then new registrations are shown month by month.

---

### US-042 — Super Admin Account Bootstrap
**Priority:** Must Have
**Story:**
> As a system developer, I want the first super admin account to be created via a secure seed script at deployment time, so that no public endpoint can be used to create privileged accounts.

**Acceptance Criteria:**
- [ ] Given the seed script is run at deployment, when it completes, then a SUPER_ADMIN account is created with credentials defined in environment variables.
- [ ] Given the public registration form, when any user submits it, then only OWNER or DRIVER roles are selectable — SUPER_ADMIN is not an option.
- [ ] Given the seed script is run a second time, when it detects the super admin already exists, then it skips creation without error.

---

## [FR-PLAN] — Subscription Plans (SaaS)

### US-043 — Default Starter Plan on Registration
**Priority:** Must Have
**Story:**
> As a newly registered fleet owner, I want to be automatically placed on the Starter (free) plan, so that I can start using Flotte225 immediately without any payment required.

**Acceptance Criteria:**
- [ ] Given a new owner completes registration, when their account is activated, then they are automatically assigned the Starter plan.
- [ ] Given I am on the Starter plan, when I log in, then I can manage up to 2 vehicles and 3 drivers without restriction.

---

### US-044 — Enforce Plan Limits at API Level
**Priority:** Must Have
**Story:**
> As the system, I want to enforce subscription plan limits server-side on every relevant API call, so that users cannot bypass plan restrictions by manipulating the frontend.

**Acceptance Criteria:**
- [ ] Given a Starter owner has 2 vehicles, when they call the create-vehicle API endpoint, then the response is a 403 with an upgrade message — regardless of client-side state.
- [ ] Given a Starter owner has 3 drivers, when they attempt to assign a new driver, then the API rejects the action with an upgrade message.
- [ ] Given a Pro owner calls the scheduled-AI-report API, when the plan check runs, then access is denied with a Business plan required message.

---

### US-045 — Upgrade Prompt for Locked Features
**Priority:** Must Have
**Story:**
> As a fleet owner on a lower plan, I want to see a clear upgrade prompt when I try to access a feature not included in my plan, so that I understand what I'm missing and how to unlock it.

**Acceptance Criteria:**
- [ ] Given I am on the Starter plan, when I navigate to the export, AI reports, anomaly detection, or WhatsApp pages, then the feature area is shown in a locked state with a description of which plan unlocks it.
- [ ] Given I click "Upgrade", when the modal or page opens, then I see a plan comparison table (Starter / Pro / Business) with features and pricing.
- [ ] Given simulation mode is active, when I click upgrade, then I am shown a message to contact the administrator to upgrade my plan.

---

### US-046 — Owner Views Current Plan & Usage
**Priority:** Should Have
**Story:**
> As a fleet owner, I want to see my current subscription plan and usage indicators (vehicles used, drivers used, AI reports generated this month) on my profile page, so that I know where I stand before hitting any limits.

**Acceptance Criteria:**
- [ ] Given I open my profile page, when I view it, then my current plan name is clearly displayed.
- [ ] Given I am on the Pro plan, when I view my usage, then I see how many on-demand AI reports I have used this month out of 5.
- [ ] Given I am approaching a limit (e.g., 2 of 2 vehicles used on Starter), when I view my profile, then a visual indicator highlights I am at the limit.
- [ ] Given simulation mode is active, when I click the "Upgrade" button, then I see a contact-admin message instead of a payment form.

---

*46 stories from 14 modules | 2026-04-06 | Source: Generated from FULL-SRS.md*
