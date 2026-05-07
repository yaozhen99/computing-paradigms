# StateKanban Test Case Matrix — R3

> Round 3 端到端验证。所有 R1/R2 测试用例保留，R3 新增标记 (R3)。

---

## TC-E2E: End-to-End Scenarios (R3 — P0)

| TC ID     | Category              | Test Case                                    | Input / Setup                                 | Expected Outcome                                         | Priority |
|-----------|-----------------------|----------------------------------------------|-----------------------------------------------|----------------------------------------------------------|----------|
| TC-E2E-01 | Happy Path            | Coder->Reviewer->crystal->valve write        | ALWAYS_APPROVE + GENERATE_SIMPLE              | Converges in 1+ round, artifact in CrystalZone           | P0       |
| TC-E2E-02 | Collision Convergence | Coder->Reviewer veto->Coder fix->Reviewer ok | REJECT_THEN_APPROVE + GENERATE_SIMPLE         | Converges in 2+ rounds                                  | P0       |
| TC-E2E-03 | Circuit Breaker       | Persistent rejection exceeds max rounds       | ALWAYS_REJECT + GENERATE_WITH_BUG, max=3      | forced_terminate=True, zero artifacts in CrystalZone     | P0       |
| TC-E2E-04 | Viewport Isolation    | Coder viewport excludes reviewer veto signals | Coder spec = [INTENT, ERROR] only             | No VETO signals in coder slice                          | P0       |
| TC-E2E-05 | Snapshot Round-Trip   | Save mid-run, load, verify state matches     | GENERATE_SIMPLE, save after seeding intent    | Loaded kanban has same signal/artifact counts            | P0       |
| TC-E2E-06 | Rework Loop Error     | 3 consecutive valve failures                 | Valve always rejects artifact                 | ValveReworkLoopError(SK_EN_004) raised                  | P0       |

## TC-MCK: MockLLMAdapter (R3 — P1)

| TC ID     | Category         | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|------------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-MCK-01 | structured_mode  | set_structured_response returns JSON string   | role="coder", type=ARTIFACT                 | LLMResponse.content is valid JSON with type/artifact_*   | P0       |
| TC-MCK-02 | structured_mode  | structured_mode property toggle              | adapter.structured_mode = True               | complete() returns JSON strings                          | P0       |
| TC-MCK-03 | behavior_mode    | ALWAYS_APPROVE auto-configures structured    | set_behavior_mode(ALWAYS_APPROVE)            | structured_mode=True, reviewer returns intent            | P0       |
| TC-MCK-04 | behavior_mode    | ALWAYS_REJECT returns veto                   | set_behavior_mode(ALWAYS_REJECT)             | reviewer returns veto on every call                     | P0       |
| TC-MCK-05 | behavior_mode    | REJECT_THEN_APPROVE: first veto then approve | set_behavior_mode(REJECT_THEN_APPROVE)       | Call 1: veto, Call 2+: intent                           | P0       |
| TC-MCK-06 | behavior_mode    | GENERATE_SIMPLE returns artifact             | set_behavior_mode(GENERATE_SIMPLE)           | coder returns artifact with simple content              | P0       |
| TC-MCK-07 | behavior_mode    | GENERATE_WITH_BUG returns buggy artifact     | set_behavior_mode(GENERATE_WITH_BUG)         | coder returns artifact with buggy content               | P0       |
| TC-MCK-08 | priority_chain   | behavior_mode overrides structured_mode      | Set both behavior and structured responses   | Behavior-driven response takes priority                 | P0       |
| TC-MCK-09 | legacy_mode      | Default mode returns legacy LLMResponse      | No structured/behavior mode set              | Returns LLMResponse with plain text content             | P1       |
| TC-MCK-10 | reset            | reset() clears all state                     | Set modes, call reset()                      | All call counts and behavior state cleared              | P1       |

## TC-SNP: Snapshot Module (R3 — P0)

| TC ID     | Category   | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-SNP-01 | save       | Save to valid path                           | kanban + writable dir                       | File written with valid JSON + checksum                  | P0       |
| TC-SNP-02 | save       | Creates parent directories                   | Nested subdirectory path                    | Directories created, file written                       | P0       |
| TC-SNP-03 | save       | Atomic write (tempfile + os.replace)         | Save, verify no partial files               | No .tmp files left, target file complete                | P1       |
| TC-SNP-04 | load       | Load valid snapshot                          | Previously saved file                       | StateKanban fully reconstructed                          | P0       |
| TC-SNP-05 | load       | FileNotFoundError on missing path            | Nonexistent path                            | FileNotFoundError raised                                 | P0       |
| TC-SNP-06 | load       | Invalid JSON raises SnapshotIntegrityError   | Malformed JSON file                         | SnapshotIntegrityError(SK_SN_001)                       | P0       |
| TC-SNP-07 | load       | Checksum mismatch raises SnapshotIntegrityError | Tampered snapshot content                | SnapshotIntegrityError(SK_SN_001)                       | P0       |
| TC-SNP-08 | round-trip | Full save->load round-trip                    | Kanban with signals, artifacts, viewports   | All zones preserved identically                         | P0       |
| TC-SNP-09 | list       | list_snapshots returns sorted filenames      | Multiple .json files in dir                 | Sorted list of .json filenames                          | P0       |
| TC-SNP-10 | list       | list_snapshots on missing dir returns empty  | Nonexistent directory                       | Empty list                                              | P1       |
| TC-SNP-11 | delete     | delete_snapshot removes file                 | Existing snapshot file                      | File no longer exists                                   | P0       |
| TC-SNP-12 | delete     | delete_snapshot on missing file raises       | Nonexistent file path                       | FileNotFoundError raised                                | P0       |
| TC-SNP-13 | manager    | SnapshotManager.save_snapshot/load_snapshot round-trip | Manager with base_dir, explicit path | Save+load produces identical state                      | P0       |
| TC-SNP-14 | write_error| Write to readonly dir raises SnapshotWriteError | Permission-denowned directory             | SnapshotWriteError(SK_SN_002)                           | P1       |

## TC-ENG: Engine via ToolRegistry (R3 — P0)

| TC ID     | Category          | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|-------------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-ENG-01 | registry_dispatch | _call_llm_for_role uses registry.dispatch     | Engine with registry, call_llm registered   | Dispatch logged in AuditZone                            | P0       |
| TC-ENG-02 | registry_dispatch | Direct adapter fallback when _use_registry=False | engine.set_use_registry_for_llm(False)   | No registry dispatch, direct adapter.complete() call    | P0       |
| TC-ENG-03 | build_context     | _build_context formats slice correctly       | ViewportSlice with signals + artifacts      | Formatted context string with Role/Signals/Artifacts    | P0       |
| TC-ENG-04 | rework_loop       | 3 consecutive valve failures -> ValveReworkLoopError | Valve always fails                      | ValveReworkLoopError(SK_EN_004) raised after 3 failures | P0       |
| TC-ENG-05 | rework_loop       | Valve success resets consecutive counter     | 2 failures then 1 success                  | Counter reset to 0, no ValveReworkLoopError            | P0       |

## TC-CLL: call_llm Tool (R3 — P0)

| TC ID     | Category        | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|-----------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-CLL-01 | success         | Valid call returns structured result          | Valid messages + adapter                    | {"success": True, "output": {"content": ..., "finish_reason": ...}} | P0 |
| TC-CLL-02 | error           | Adapter exception returns error dict          | Adapter that raises                         | {"success": False, "error": ..., "error_code": "SK_LLM_001"} | P0 |
| TC-CLL-03 | null_bytes      | Null bytes in message content rejected        | messages with \x00 in content              | ToolRegistryError(SK_TR_004) raised                     | P0       |
| TC-CLL-04 | null_bytes_deep | Null bytes in nested dict/list rejected       | params with nested \x00                    | ToolRegistryError(SK_TR_004) raised                     | P0       |
| TC-CLL-05 | audit           | Each invocation produces audit log entry      | Valid call_llm invocation                   | AuditZone has tool_call entry                           | P1       |
| TC-CLL-06 | message_convert | Raw dict messages converted to LLMMessage     | params with {"role":"user","content":"hi"}  | LLMMessage objects passed to adapter                    | P0       |
| TC-CLL-07 | factory         | create_call_llm_tool returns callable         | Valid adapter                               | Returned callable is awaitable                           | P0       |

## TC-CCX: call_codex Tool (R3 — P1)

| TC ID     | Category        | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|-----------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-CCX-01 | null_bytes      | Null bytes in prompt returns SK_TR_004 error  | prompt with \x00                           | {"success": False, "error_code": "SK_TR_004"}            | P0       |
| TC-CCX-02 | error_handling  | Codex not available returns error             | Codex CLI not on PATH                      | {"success": False, "error": ...}                         | P1       |
| TC-CCX-03 | factory         | create_call_codex_tool returns callable       | Valid CodexAdapter                          | Returned callable is awaitable                           | P0       |
| TC-CCX-04 | async           | Tool call returns coroutine                   | Valid adapter                               | asyncio.iscoroutine(result) is True                      | P0       |
| TC-CCX-05 | graceful_fail   | Clean prompt doesn't trigger SK_TR_004        | Valid prompt, codex not available           | error_code != SK_TR_004                                 | P1       |

## TC-ERR: New Error Codes (R3 — P0)

| TC ID     | Category   | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-ERR-01 | SK_CX_003  | CodexTimeoutError error_code and http_analogy | CodexTimeoutError instance                 | error_code="SK_CX_003", http_analogy=408               | P0       |
| TC-ERR-02 | SK_CX_003  | CodexTimeoutError hierarchy                  | isinstance check                            | CodexAdapterError -> StateKanbanError                   | P0       |
| TC-ERR-03 | SK_EN_004  | ValveReworkLoopError error_code and http_analogy | ValveReworkLoopError instance           | error_code="SK_EN_004", http_analogy=500               | P0       |
| TC-ERR-04 | SK_EN_004  | ValveReworkLoopError hierarchy               | isinstance check                            | EngineError -> StateKanbanError                         | P0       |
| TC-ERR-05 | SK_TR_004  | ToolRegistryError with SK_TR_004 for null bytes | ToolRegistryError(error_code="SK_TR_004") | error_code="SK_TR_004"                                  | P0       |
| TC-ERR-06 | codex_null | CodexAdapter.complete raises SK_TR_004       | Messages with null byte content             | ToolRegistryError(error_code="SK_TR_004")              | P0       |
| TC-ERR-07 | call_codex_null | call_codex returns SK_TR_004 error dict  | Prompt with null bytes                      | {"success":False, "error_code":"SK_TR_004"}             | P0       |

## TC-CLI: CLI Snapshot Subcommands (R3 — P1)

| TC ID     | Category | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|----------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-CLI-01 | save     | `sk snapshot save` creates file               | snapshot save path.json                     | File exists with valid JSON                              | P0       |
| TC-CLI-02 | load     | `sk snapshot load` restores and prints info   | snapshot load path.json                     | stdout shows signal/artifact counts                     | P0       |
| TC-CLI-03 | list     | `sk snapshot list` shows snapshots            | snapshot list                               | Lists .json files or "No snapshots found"              | P1       |
| TC-CLI-04 | delete   | `sk snapshot delete` removes file             | snapshot delete path.json                   | File removed                                             | P0       |
| TC-CLI-05 | drive+snapshot | --snapshot-save after drive              | drive "test" --snapshot-save out.json       | Snapshot file created after drive                       | P1       |
| TC-CLI-06 | no-registry | --no-registry bypasses ToolRegistry        | drive "test" --no-registry                  | Engine uses direct adapter call                         | P1       |

## TC-PAP: Paper Criteria (R3 — P0)

| TC ID     | Category        | Test Case                                    | Input                                       | Expected Outcome                                         | Priority |
|-----------|-----------------|----------------------------------------------|---------------------------------------------|----------------------------------------------------------|----------|
| TC-PAP-01 | convergence_rate| Convergence rate >= 80% across scenarios      | 10 e2e runs with happy path                | converged_count / total >= 0.8                          | P0       |
| TC-PAP-02 | interception    | Interception rate = 100%                     | Invalid artifact writes                     | All invalid writes blocked by Valve                     | P0       |
| TC-PAP-03 | lossless_handoff| Snapshot restore produces identical state     | Save, load snapshot                         | Loaded state matches original                           | P0       |

## TC-REG: Regression — R1/R2 Retained (P0)

All TC IDs from R1/R2 matrix are retained. Key regression areas:

| TC ID         | Category           | Test Case                                    | Priority |
|---------------|--------------------|----------------------------------------------|----------|
| TC-FZ-001..020| FluidZone          | All R1 FluidZone tests                       | P0       |
| TC-CZ-001..011| CrystalZone        | All R1 CrystalZone tests                     | P0       |
| TC-AZ-001..007| AuditZone          | All R1 AuditZone tests                       | P0       |
| TC-SK-001..009| StateKanban        | All R1 facade tests                          | P0       |
| TC-MB-001..012| MessageBus         | All R1 bus tests                             | P0       |
| TC-VS-001..012| ViewportSlicer     | All R1/R2 viewport tests                     | P0       |
| TC-OV-001..011| OutputValve        | All R1 valve tests                           | P0       |
| TC-TR-001..015| ToolRegistry       | All R1/R2 registry tests                     | P0       |
| TC-PM-001..008| ProcessManager     | All R1 process tests                         | P0       |
| TC-EN-001..008| Engine             | All R2 engine tests                          | P0       |
| TC-RP-001..011| ResponseParser     | All R2 parser tests                          | P0       |
| TC-CD-001..006| Convergence        | All R2 convergence tests                     | P0       |
| TC-RR-001..005| Review Fixes       | All R2 review fix tests                      | P0       |
