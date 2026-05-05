# StateKanban Test Case Matrix

## TC-1: FluidZone

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-FZ-001 | Write | Write valid IntentSignal | Complete IntentSignal | Signal stored, readable | P0 |
| TC-FZ-002 | Write | Write valid VetoSignal with reason | VetoSignal(reason="bug") | Signal stored with reason | P0 |
| TC-FZ-003 | Write | Write valid ErrorSignal | ErrorSignal(error_code="SK_OV_001") | Signal stored with error fields | P0 |
| TC-FZ-004 | Validation | Signal with empty signal_id | signal_id="" | InvalidSignalError raised | P0 |
| TC-FZ-005 | Validation | Signal with empty author_role | author_role="" | InvalidSignalError raised | P0 |
| TC-FZ-006 | Validation | Signal with empty target_id | target_id="" | InvalidSignalError raised | P0 |
| TC-FZ-007 | Validation | Signal with invalid signal_type | signal_type="unknown" | InvalidSignalError raised | P0 |
| TC-FZ-008 | Read | Read all signals | No filters | All signals returned, timestamp-ordered | P0 |
| TC-FZ-009 | Read | Read by target_id | target_id="artifact_A" | Only matching signals | P0 |
| TC-FZ-010 | Read | Read by signal_type | signal_type=VETO | Only VETO signals | P0 |
| TC-FZ-011 | Read | Read by author_role | author_role="coder" | Only coder signals | P0 |
| TC-FZ-012 | Read | Read with combined filters | target_id + signal_type | Intersection of filters | P0 |
| TC-FZ-013 | Read | Read from empty zone | No signals written | Empty list | P0 |
| TC-FZ-014 | Collision | No collision (INTENT only) | Only IntentSignals for target | has_collision=False, is_resolved=True | P0 |
| TC-FZ-015 | Collision | INTENT+VETO collision | Intent + Veto on same target | has_collision=True, is_resolved=False | P0 |
| TC-FZ-016 | Collision | No signals for target | target_id="nonexistent" | has_collision=False, is_resolved=True | P0 |
| TC-FZ-017 | Collision | VETO only (no INTENT) | Only VetoSignal | has_collision=False, is_resolved=True | P0 |
| TC-FZ-018 | Clear | Clear signals at round >= N | Signals at rounds 0,1,2; clear round>=2 | Rounds 0,1 preserved, round 2 removed | P0 |
| TC-FZ-019 | Clear | Clear rebuilds index correctly | Clear then read by target | Index reflects remaining signals | P1 |
| TC-FZ-020 | Overwrite | Same key (target,type,author) overwritten | Two signals with same key | Latest signal wins | P0 |

## TC-2: CrystalZone

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-CZ-001 | Append | Append with seq_no=0 (auto-assign) | Artifact(seq_no=0) | seq_no=1 assigned | P0 |
| TC-CZ-002 | Append | Append multiple, auto-assign | Three artifacts with seq_no=0 | seq_nos 1,2,3 | P0 |
| TC-CZ-003 | Append | Append with explicit seq_no | Artifact(seq_no=5) | seq_no=5 assigned | P0 |
| TC-CZ-004 | Conflict | Duplicate seq_no | Same seq_no twice | ArtifactConflictError | P0 |
| TC-CZ-005 | Read | Read by seq_no | Append then read | Correct artifact returned | P0 |
| TC-CZ-006 | Read | Read non-existent seq_no | seq_no=999 | None returned | P0 |
| TC-CZ-007 | Read | Read all artifacts | No filter | All artifacts, seq_no sorted | P0 |
| TC-CZ-008 | Read | Filter by artifact_type | artifact_type=CODE | Only CODE artifacts | P0 |
| TC-CZ-009 | Read | Filter by author_role | author_role="coder" | Only coder artifacts | P0 |
| TC-CZ-010 | Read | latest_seq_no on empty | No artifacts | 0 | P0 |
| TC-CZ-011 | Read | latest_seq_no after appends | Append 3 artifacts | 3 | P0 |
| TC-CZ-012 | Immutable | No update method exists | Inspection | No update() method | P1 |
| TC-CZ-013 | Immutable | No delete method exists | Inspection | No delete() method | P1 |

## TC-3: AuditZone

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-AZ-001 | Log | Log entry | event_type, actor, action, details | Monotonically increasing entry_id | P0 |
| TC-AZ-002 | Log | Multiple log entries | Three entries | IDs 1, 2, 3 | P0 |
| TC-AZ-003 | Read | Read all entries | No filter | All entries | P0 |
| TC-AZ-004 | Read | Filter by event_type | event_type="tool_call" | Only matching entries | P0 |
| TC-AZ-005 | Read | Filter by actor | actor="ToolRegistry" | Only matching entries | P0 |
| TC-AZ-006 | Read | Filter by since_entry_id | since_entry_id=2 | Entries with id > 2 | P0 |
| TC-AZ-007 | Read | Empty zone | No entries logged | Empty list | P1 |

## TC-4: StateKanban (Facade)

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-SK-001 | Convergence | Immediate agreement (no collision) | Only IntentSignals | converged=True, rounds=1 | P0 |
| TC-SK-002 | Convergence | Collision resolves immediately | INTENT+VETO then VETO cleared | converged=True | P0 |
| TC-SK-003 | Convergence | Forced terminate at 10 rounds | Persistent INTENT+VETO | converged=False, forced_terminate=True, rounds=10 | P0 |
| TC-SK-004 | Convergence | Convergence result fields | Any convergence | All ConvergenceResult fields populated | P0 |
| TC-SK-005 | Viewport | Register and retrieve viewport spec | ViewportSpec for "coder" | get_viewport_spec returns spec | P0 |
| TC-SK-006 | Viewport | Retrieve non-existent viewport | "unknown_role" | None returned | P1 |
| TC-SK-007 | Serialization | to_json -> from_json round-trip | Full kanban state | All zones preserved | P0 |
| TC-SK-008 | Serialization | Checksum validation pass | Valid snapshot | from_json succeeds | P0 |
| TC-SK-009 | Serialization | Checksum validation fail | Tampered snapshot | SnapshotIntegrityError | P0 |

## TC-5: MessageBus

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-MB-001 | Subscribe | Valid subscription | signal_type, async callback | subscription_id returned | P0 |
| TC-MB-002 | Subscribe | Empty signal_type | signal_type="" | SubscriptionError | P0 |
| TC-MB-003 | Subscribe | Non-callable callback | callback=42 | SubscriptionError | P0 |
| TC-MB-004 | Unsubscribe | Valid unsubscribe | Existing subscription_id | Subscription removed | P0 |
| TC-MB-005 | Unsubscribe | Invalid subscription_id | Unknown ID | SubscriptionError | P0 |
| TC-MB-006 | Publish | Publish to matching subscribers | Signal matching type | Callbacks invoked | P0 |
| TC-MB-007 | Publish | Publish with no subscribers | Signal with no matching type | No error, audit logged | P0 |
| TC-MB-008 | Publish | Audit log on publish | Any publish | Audit entry created | P1 |
| TC-MB-009 | Sync call | Successful sync call | Registered handler | Response returned | P0 |
| TC-MB-010 | Sync call | Sync call timeout | Slow handler + short timeout | SyncCallTimeoutError | P0 |
| TC-MB-011 | Sync call | No handler registered | Unknown target_role | SyncCallTimeoutError | P0 |
| TC-MB-012 | Sync call | Audit log on completion | Successful call | Audit entry created | P1 |
| TC-MB-013 | Async notify | Valid notification | Registered notify handler | Handler called | P0 |
| TC-MB-014 | Async notify | No handler registered | Unknown target_role | No error (best-effort) | P0 |
| TC-MB-015 | Async notify | Handler throws exception | Failing handler | Error swallowed, audit logged | P1 |

## TC-6: ViewportSlicer

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-VS-001 | Filter | Filter signals by visible_signal_types | Spec allows INTENT only | Only INTENT signals in slice | P0 |
| TC-VS-002 | Filter | Filter artifacts by visible_artifact_types | Spec allows CODE only | Only CODE artifacts in slice | P0 |
| TC-VS-003 | Filter | Filter by target patterns (glob) | Pattern "artifact_*" | Only matching target_ids | P0 |
| TC-VS-004 | Filter | Empty target patterns (match all) | patterns=[] | All signals pass | P0 |
| TC-VS-005 | Priority | Role-relevant signals first | Signals from own role + others | Own role signals first | P0 |
| TC-VS-006 | Priority | Own artifacts before others | Artifacts by own role + others | Own artifacts first | P0 |
| TC-VS-007 | Budget | Token budget respected | Budget=100, many signals | total_tokens <= budget | P0 |
| TC-VS-008 | Budget | Budget exceeded, items excluded | Small budget, many items | items_excluded > 0 | P0 |
| TC-VS-009 | Budget | SliceOverflowError | Budget too small for any item | SliceOverflowError raised | P0 |
| TC-VS-010 | Error | No spec for role | role="nonexistent" | InvalidViewportSpecError | P0 |
| TC-VS-011 | Token | estimate_tokens heuristic | Known string | len(text)//4 (min 1) | P1 |
| TC-VS-012 | Metadata | Slice log populated | Any slice | slice_log contains budget and counts | P1 |

## TC-7: OutputValve

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-OV-001 | Syntax | Valid Python code | Artifact(path="x.py", content="x=1") | ValidationResult(passed=True) | P0 |
| TC-OV-002 | Syntax | Invalid Python code | Artifact(path="x.py", content="def (") | ValidationResult(passed=False) | P0 |
| TC-OV-003 | Syntax | Valid JSON config | Artifact(path="x.json", content='{"a":1}') | ValidationResult(passed=True) | P0 |
| TC-OV-004 | Syntax | Invalid JSON config | Artifact(path="x.json", content="{invalid}") | ValidationResult(passed=False) | P0 |
| TC-OV-005 | Syntax | Non-.py/.json passes | Artifact(path="x.txt", content="anything") | ValidationResult(passed=True) | P0 |
| TC-OV-006 | Chain | Full chain passes | Valid artifact | ValveResult(success=True) | P0 |
| TC-OV-007 | Chain | Fail-fast on first failure | Invalid syntax | Only SyntaxValidator runs, TypeValidator skipped | P0 |
| TC-OV-008 | Write | Atomic write on success | Valid artifact + writable dir | File exists with correct content | P0 |
| TC-OV-009 | Write | Atomic write creates parent dir | New subdirectory path | Directory created, file written | P0 |
| TC-OV-010 | Error | ErrorSignal injected on failure | Invalid artifact | ErrorSignal in FluidZone | P0 |
| TC-OV-011 | Custom | Add custom validator | Custom validator at position 0 | Runs first in chain | P1 |
| TC-OV-012 | Type | TypeValidator always passes (stub) | Any artifact | passed=True | P1 |
| TC-OV-013 | Test | TestValidator always passes (stub) | Any artifact | passed=True | P1 |

## TC-8: ToolRegistry

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-TR-001 | Register | Register new tool | Valid ToolDef + implementation | Tool registered, list_tools includes it | P0 |
| TC-TR-002 | Register | Duplicate registration | Same name twice | ToolNotFoundError | P0 |
| TC-TR-003 | Dispatch | Allowed role dispatch | role in required_permissions | ToolResult(success=True) | P0 |
| TC-TR-004 | Dispatch | Denied role dispatch | role not in permissions | PermissionDeniedError | P0 |
| TC-TR-005 | Dispatch | Tool not found | Unknown tool_name | ToolNotFoundError | P0 |
| TC-TR-006 | Dispatch | "all_roles" permission | required_permissions={"all_roles"} | Any role passes | P0 |
| TC-TR-007 | Timeout | Tool exceeds timeout | Slow implementation + short timeout | ToolTimeoutError | P0 |
| TC-TR-008 | Timeout | Timeout injects error signal | Timeout scenario | ErrorSignal in FluidZone | P0 |
| TC-TR-009 | Audit | Successful dispatch logged | Valid dispatch | Audit entry with "tool_call" event_type | P0 |
| TC-TR-010 | Audit | Permission denied logged | Denied dispatch | Audit entry with "permission_denied" event_type | P0 |
| TC-TR-011 | Audit | Params hashed | Any dispatch | params_hash in audit details | P1 |
| TC-TR-012 | Audit | Tool error logged | Implementation throws exception | Audit entry with "tool_error" event_type | P0 |

## TC-9: ProcessManager

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-PM-001 | Create | Create process | role, tool_permits, viewport_spec | ProcessInfo(state=CREATED) | P0 |
| TC-PM-002 | Create | Duplicate active process for role | Same role, active existing | InvalidStateTransitionError | P0 |
| TC-PM-003 | Activate | CREATED -> ACTIVE | activate(created_pid) | state=ACTIVE, heartbeat_at set | P0 |
| TC-PM-004 | Activate | SUSPENDED -> ACTIVE | activate(suspended_pid) | state=ACTIVE | P0 |
| TC-PM-005 | Activate | ACTIVE -> ACTIVE (invalid) | activate(active_pid) | InvalidStateTransitionError | P0 |
| TC-PM-006 | Activate | TERMINATED -> ACTIVE (invalid) | activate(terminated_pid) | InvalidStateTransitionError | P0 |
| TC-PM-007 | Suspend | ACTIVE -> SUSPENDED | suspend(active_pid) | state=SUSPENDED | P0 |
| TC-PM-008 | Suspend | CREATED -> SUSPENDED (invalid) | suspend(created_pid) | InvalidStateTransitionError | P0 |
| TC-PM-009 | Terminate | ACTIVE -> TERMINATED | terminate(active_pid, "scheduler") | state=TERMINATED | P0 |
| TC-PM-010 | Terminate | SUSPENDED -> TERMINATED | terminate(suspended_pid, "scheduler") | state=TERMINATED | P0 |
| TC-PM-011 | Terminate | Self-termination | terminate(pid, pid) | SelfTerminationError | P0 |
| TC-PM-012 | Terminate | TERMINATED -> TERMINATED (invalid) | terminate(terminated_pid, "scheduler") | InvalidStateTransitionError | P0 |
| TC-PM-013 | Handoff | claim_primary valid | Old + new process for role | Old terminated, new active, viewport inherited | P0 |
| TC-PM-014 | Handoff | No predecessor | claim_primary with no old process | HandoffError | P0 |
| TC-PM-015 | Handoff | New process not found | Invalid new_process_id | HandoffError | P0 |
| TC-PM-016 | Handoff | Role mismatch | New process with different role | HandoffError | P0 |
| TC-PM-017 | Heartbeat | Record heartbeat | heartbeat(active_pid) | heartbeat_at updated | P0 |
| TC-PM-018 | Heartbeat | Heartbeat on non-ACTIVE | heartbeat(suspended_pid) | InvalidStateTransitionError | P0 |
| TC-PM-019 | Heartbeat | Timeout detection | Manipulate heartbeat_at to be old | Timed out PID returned | P0 |
| TC-PM-020 | List | List all processes | Multiple processes | All returned | P0 |
| TC-PM-021 | List | Filter by state | state=ACTIVE | Only active processes | P0 |
| TC-PM-022 | Audit | State transitions logged | Any transition | Audit entry created | P1 |
| TC-PM-023 | Snapshot | get_state_for_snapshot / load_state_from_snapshot | Full state | Round-trip preserves data | P0 |
| TC-PM-024 | Terminate | Non-existent process | Unknown PID | InvalidStateTransitionError | P0 |

## TC-10: Snapshot

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-SN-001 | Save | Save to valid path | kanban + writable dir | File written with valid JSON | P0 |
| TC-SN-002 | Save | Creates parent directories | New subdirectory | Directory created | P0 |
| TC-SN-003 | Load | Load valid snapshot | Previously saved file | StateKanban reconstructed | P0 |
| TC-SN-004 | Load | File not found | Non-existent path | FileNotFoundError | P0 |
| TC-SN-005 | Load | Invalid JSON | Corrupted file | SnapshotIntegrityError | P0 |
| TC-SN-006 | Load | Checksum mismatch | Tampered content | SnapshotIntegrityError | P0 |
| TC-SN-007 | Round-trip | Full round-trip | Save -> Load | All zones identical | P0 |
| TC-SN-008 | Atomic | Temp file cleaned on failure | Write failure scenario | No partial file at target | P1 |

## TC-11: Error Codes Contract

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-EC-001 | Code | InvalidSignalError.error_code | Instance check | "SK_FZ_001" | P0 |
| TC-EC-002 | Code | SignalCollisionError.error_code | Instance check | "SK_FZ_002" | P0 |
| TC-EC-003 | Code | ConvergenceTimeoutError.error_code | Instance check | "SK_FZ_003" | P0 |
| TC-EC-004 | Code | ArtifactConflictError.error_code | Instance check | "SK_CZ_001" | P0 |
| TC-EC-005 | Code | AppendOnlyViolationError.error_code | Instance check | "SK_CZ_002" | P0 |
| TC-EC-006 | Code | AuditWriteError.error_code | Instance check | "SK_AZ_001" | P0 |
| TC-EC-007 | Code | InvalidViewportSpecError.error_code | Instance check | "SK_VS_001" | P0 |
| TC-EC-008 | Code | SliceOverflowError.error_code | Instance check | "SK_VS_002" | P0 |
| TC-EC-009 | Code | SyntaxCheckError.error_code | Instance check | "SK_OV_001" | P0 |
| TC-EC-010 | Code | TypeCheckError.error_code | Instance check | "SK_OV_002" | P0 |
| TC-EC-011 | Code | TestExecutionError.error_code | Instance check | "SK_OV_003" | P0 |
| TC-EC-012 | Code | AtomicWriteError.error_code | Instance check | "SK_OV_004" | P0 |
| TC-EC-013 | Code | HumanGateRejectedError.error_code | Instance check | "SK_OV_005" | P0 |
| TC-EC-014 | Code | PermissionDeniedError.error_code | Instance check | "SK_TR_001" | P0 |
| TC-EC-015 | Code | ToolNotFoundError.error_code | Instance check | "SK_TR_002" | P0 |
| TC-EC-016 | Code | ToolTimeoutError.error_code | Instance check | "SK_TR_003" | P0 |
| TC-EC-017 | Code | InvalidStateTransitionError.error_code | Instance check | "SK_PM_001" | P0 |
| TC-EC-018 | Code | SelfTerminationError.error_code | Instance check | "SK_PM_002" | P0 |
| TC-EC-019 | Code | HeartbeatTimeoutError.error_code | Instance check | "SK_PM_003" | P0 |
| TC-EC-020 | Code | HandoffError.error_code | Instance check | "SK_PM_004" | P0 |
| TC-EC-021 | Code | SubscriptionError.error_code | Instance check | "SK_MB_001" | P0 |
| TC-EC-022 | Code | SyncCallTimeoutError.error_code | Instance check | "SK_MB_002" | P0 |
| TC-EC-023 | Code | LLMRateLimitError.error_code | Instance check | "SK_LLM_001" | P0 |
| TC-EC-024 | Code | LLMAuthError.error_code | Instance check | "SK_LLM_002" | P0 |
| TC-EC-025 | Code | LLMResponseParseError.error_code | Instance check | "SK_LLM_003" | P0 |
| TC-EC-026 | Code | SnapshotIntegrityError.error_code | Instance check | "SK_SN_001" | P0 |
| TC-EC-027 | Code | SnapshotWriteError.error_code | Instance check | "SK_SN_002" | P0 |
| TC-EC-028 | HTTP | All http_analogy values match contract | Each error class | Matches api_contracts.md table | P0 |
| TC-EC-029 | Hierarchy | Error inheritance chain | isinstance checks | Matches architecture 4.1 tree | P0 |

## TC-12: Integration / Pipeline

| TC ID | Category | Test Case | Input | Expected Output | Priority |
|-------|----------|-----------|-------|-----------------|----------|
| TC-INT-001 | Pipeline | Full write pipeline: ToolRegistry->OutputValve->filesystem | Valid code artifact | File written, ToolResult(success=True) | P0 |
| TC-INT-002 | Pipeline | Write pipeline with syntax failure | Invalid Python code | No file written, ErrorSignal in FluidZone | P0 |
| TC-INT-003 | Pipeline | Permission denied in full pipeline | Unauthorized role + write_file | PermissionDeniedError | P0 |
| TC-INT-004 | Snapshot | PM state in snapshot round-trip | Create/activate processes, snapshot, restore | Process states preserved | P0 |
| TC-INT-005 | Convergence | Collision -> convergence -> CrystalZone | INTENT+VETO on target, resolve | Artifact in CrystalZone | P0 |
| TC-INT-006 | Metrics | Convergence rate measurement | Multiple collisions, some resolve | convergence_rate = resolved / total | P0 |
| TC-INT-007 | Metrics | Interception rate (OutputValve) | Mix of valid/invalid artifacts | interception_rate = blocked / total_attempts | P0 |
| TC-INT-008 | Metrics | Lossless handoff verification | claim_primary, read old viewport | New process has same viewport spec | P0 |
| TC-INT-009 | Bootstrap | Full system bootstrap | _bootstrap_system(config) | All components initialized | P0 |
