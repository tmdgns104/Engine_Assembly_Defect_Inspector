/* A communication trial, not an inspector or a safety controller.
 * State changes use current cyclic evidence, never Explicit attribute reads.
 * Automatic cycles use physical PLC baselines and edges, not software grants.
 * Explicit one-shot policies remain maintenance-only compatibility paths.
 */
#include "engine_commissioning.h"
#include <string.h>

const char *CommPhaseName(CommPhase phase) {
  static const char *names[] = {
    "WAIT_CONNECTION", "SYNC_LOW", "IDLE", "REQUEST_RECEIVED", "TEST_RESULT_READY",
    "RESULT_SENT", "DONE_SENT", "WAIT_REQUEST_OFF", "CLEARING_DONE", "READY_NEXT", "DISARMED"
  };
  return names[phase];
}

static void Event(CommState *state, const char *name, double now) {
  if (state->event != 0) state->event(state, name, now, state->event_context);
}

static void Phase(CommState *state, CommPhase phase, const char *event, double now) {
  state->phase = phase;
  Event(state, event, now);
}

static bool ActiveRequest(const CommState *state) {
  return state->phase >= REQUEST_RECEIVED && state->phase <= CLEARING_DONE;
}

bool CommControlsValid(const CommState *state, double now) {
  return state->connected && state->seen && state->run && state->bool_valid
      && now >= state->last_receive_at
      && now - state->last_receive_at <= state->config.receive_max_age_s;
}

static bool PermissionSignals(const CommState *state) {
  /* This is only the observed PLC software convention. Physical isolation and
   * independent stopping means must be verified separately before field use. */
  return state->words[1] == state->config.estop_ok_value
      && state->words[2] == 1
      && state->words[3] == state->config.stop_released_value;
}

void CommInit(CommState *state, const CommConfig *config, double now,
              CommEvent event, void *context) {
  memset(state, 0, sizeof(*state));
  state->config = *config;
  state->armed = config->mode == COMM_SYNTHETIC_RESULT && config->armed;
  state->phase = WAIT_CONNECTION;
  state->reason = "WAIT_CURRENT_CONNECTION_AND_REQUEST_LOW";
  state->started_at = now;
  state->event = event;
  state->event_context = context;
  Event(state, "TRIAL_INITIALIZED", now);
}

void CommFault(CommState *state, const char *reason, double now) {
  bool changed = state->phase != DISARMED || strcmp(state->reason, reason) != 0;
  state->armed = false;
  if (state->initial_issued) state->initial_revoked = true;
  state->saw_low = false;
  state->ai_stopped_seen = false;
  memset(state->raw100, 0, 4);
  state->phase = DISARMED;
  state->reason = reason;
  if (changed) Event(state, "TRIAL_ABORTED_NO_NEW_DONE", now);
}

void CommOpen(CommState *state, double now) {
  if (ActiveRequest(state) || state->initial_issued) CommFault(state, "NEW_CONNECTION_CANCELS_CONTEXT", now);
  if (state->config.automatic_repeat) state->armed=false;
  state->ai_stopped_seen = false;
  ++state->session_id;
  state->connected = true;
  state->seen = state->run = state->bool_valid = state->saw_low = false;
  memset(state->raw150, 0, 8);
  memset(state->raw100, 0, 4);
  memset(state->words, 0, sizeof(state->words));
  state->reason = "WAIT_FRESH_REQUEST_LOW";
  Phase(state, state->armed ? SYNC_LOW : DISARMED, "CONNECTION_OPENED", now);
}

void CommDisconnect(CommState *state, const char *reason, double now) {
  /* Any lost link consumes permission. Reconnecting cannot restart a trial. */
  state->connected = state->seen = state->run = false;
  CommFault(state, reason, now);
  Event(state, "CONNECTION_LOST", now);
}

bool CommInitialArm(CommState *s, const char *id, double now) {
  if (!id || strlen(id)!=32) return false;
  for (unsigned int i=0;i<32;i++)
    if (!((id[i]>='0' && id[i]<='9') || (id[i]>='a' && id[i]<='f'))) return false;
  if (s->config.mode!=COMM_AI_RUNTIME || s->config.supervised_repeat || s->config.automatic_repeat || s->initial_issued ||
      !CommControlsValid(s,now) || !s->ai_ready ||
      !(now>=s->ai_heartbeat_at && now-s->ai_heartbeat_at<=.5) ||
      s->words[0] || s->words[2] ||
      s->words[1]!=s->config.estop_ok_value ||
      s->words[3]!=s->config.stop_released_value ||
      s->request_id || s->result_count || s->done_count ||
      memcmp(s->raw100,"\0\0\0\0",4) ||
      (s->phase!=DISARMED && s->phase!=SYNC_LOW)) return false;
  memcpy(s->approval_id,id,33);
  s->initial_issued=true; s->armed=true; s->saw_low=false;
  s->reason="FIRST_PRODUCT_WAIT_NEW_START";
  Phase(s,SYNC_LOW,"FIRST_PRODUCT_EXPLICIT_APPROVAL",now);
  return true;
}

bool CommSupervisedArm(CommState *s, const char *id, double now) {
  if (!id || strlen(id)!=32) return false;
  for (unsigned int i=0;i<32;i++)
    if (!((id[i]>='0' && id[i]<='9') || (id[i]>='a' && id[i]<='f'))) return false;
  if (!s->config.supervised_repeat || s->config.automatic_repeat || s->config.mode!=COMM_AI_RUNTIME ||
      s->armed || s->approval_count>=4096 || !CommControlsValid(s,now) ||
      !s->ai_ready || !(now>=s->ai_heartbeat_at && now-s->ai_heartbeat_at<=.5) ||
      s->words[0] || s->words[2] ||
      s->words[1]!=s->config.estop_ok_value || s->words[3]!=s->config.stop_released_value ||
      memcmp(s->raw100,"\0\0\0\0",4) ||
      (s->phase!=READY_NEXT && s->phase!=DISARMED && s->phase!=SYNC_LOW) ||
      s->request_id!=s->completed_count || s->result_count!=s->completed_count ||
      s->done_count!=s->completed_count) return false;
  for (unsigned int i=0;i<s->approval_count;i++)
    if (!strcmp(s->issued_approvals[i],id)) return false;
  memcpy(s->issued_approvals[s->approval_count++],id,33);
  memcpy(s->approval_id,id,33);
  s->initial_issued=true; s->initial_consumed=false; s->initial_revoked=false;
  /* Only the per-grant budget is renewed; cumulative request/result IDs remain. */
  s->armed=true; s->used=false; s->saw_low=false;
  s->reason="SUPERVISED_WAIT_NEW_START";
  Phase(s,SYNC_LOW,"SUPERVISED_PRODUCT_APPROVAL",now);
  return true;
}

/* Automatic operation has no arm command, approval ID or per-product budget.
 * Readiness is current device health; the PLC supplies all request edges. */
static void AutomaticReceive(CommState *s, double now) {
  if (!s->ai_ready || !(now>=s->ai_heartbeat_at && now-s->ai_heartbeat_at<=.5)) {
    if (s->armed || ActiveRequest(s)) {
      Event(s,!s->ai_ready ? "HEALTH_READY_FALSE_RX" : "HEALTH_LEASE_EXPIRED_RX",now);
      CommFault(s,"PYTHON_NOT_READY",now);
    }
    return;
  }
  if (!CommControlsValid(s,now) || s->words[1]!=s->config.estop_ok_value ||
      s->words[3]!=s->config.stop_released_value) return;
  if ((s->phase==DISARMED || s->phase==WAIT_CONNECTION) && !s->words[0] && !s->words[2]) {
    s->armed=true; s->used=false; s->saw_low=false; s->ai_stopped_seen=true;
    s->reason="WAIT_NEW_PHYSICAL_START";
    Phase(s,SYNC_LOW,"PLC_STOPPED_BASELINE",now);
  } else if (s->phase==READY_NEXT && !s->words[0]) {
    /* Result, Done and Done reset were actually sent for this transaction.
     * No application permission is required to observe the next PLC edge. */
    s->armed=true; s->used=false; s->saw_low=false;
    s->reason="WAIT_PLC_REQUEST_LOW";
    Phase(s,SYNC_LOW,"PLC_TRANSACTION_SETTLED",now);
  }
}

static void AiReceive(CommState *s, double now) {
  if (s->config.automatic_repeat) { AutomaticReceive(s,now); return; }
  /* Maintenance commissioning only: real CLEAR never creates first permission.
   * FIRST_PRODUCT_ONLY also refuses repeat permission when CLEAR is true. */
  if (!s->initial_issued || s->initial_revoked) return;
  if (!s->ai_ready || !(now>=s->ai_heartbeat_at && now-s->ai_heartbeat_at<=.5)) {
    if (s->armed || ActiveRequest(s)) {
      Event(s, !s->ai_ready ? "HEALTH_READY_FALSE_RX" : "HEALTH_LEASE_EXPIRED_RX", now);
      CommFault(s,"PYTHON_NOT_READY",now);
    }
    return;
  }
  if (s->phase==READY_NEXT) s->reason=s->config.automatic_repeat ?
    "AUTO_WAIT_DURABLE_TRANSACTION_SETTLEMENT" : s->config.supervised_repeat ?
    "WAIT_SUPERVISOR_PRODUCT_CLEAR_AND_NEW_GRANT" : "FIRST_CYCLE_COMPLETE_NO_AUTOMATIC_REARM";
}

void CommAiHealth(CommState *s, bool ready, bool clear, double now) {
  s->ai_ready=ready; s->ai_clear=clear; s->ai_heartbeat_at=now;
  if (!ready && (s->armed || ActiveRequest(s))) {
    Event(s,"HEALTH_READY_FALSE_IPC",now);
    CommFault(s,"PYTHON_NOT_READY",now);
  }
}

bool CommAiResult(CommState *s, unsigned long session, unsigned long request,
                  unsigned int decision, bool durable, double now) {
  if (s->config.mode!=COMM_AI_RUNTIME || s->phase!=REQUEST_RECEIVED ||
      session!=s->session_id || request!=s->request_id || !durable ||
      !CommControlsValid(s,now) || !PermissionSignals(s) || !s->words[0] ||
      !s->ai_ready || now-s->ai_heartbeat_at>.5) return false;
  /* Operator-selected PLC disposition: preserve the four-way AI decision in
   * Python/Journal; PLC's two-state interface receives every non-PASS as NG.
   * This does not bypass current request/control/health/durability checks. */
  if (decision<1 || decision>4) return false;
  s->reason=decision==3 ? "AI_REVIEW_AS_PLC_NG" :
            decision==4 ? "AI_ERROR_AS_PLC_NG" : "AI_PASS_OR_FAIL";
  s->raw100[0]=(decision!=1); s->raw100[1]=s->raw100[2]=s->raw100[3]=0;
  ++s->result_count; Phase(s,TEST_RESULT_READY,"PYTHON_RESULT_DURABLE",now);
  return true;
}

void CommReceive(CommState *state, const uint8_t bytes[8], uint32_t run_idle,
                 bool sequence_duplicate, double now) {
  if (!state->connected) return;
  ++state->receive_count;
  if (sequence_duplicate) {
    ++state->duplicate_count;
    if (!state->seen || memcmp(state->raw150, bytes, 8) != 0) {
      CommFault(state, "DUPLICATE_SEQUENCE_CHANGED_DATA", now);
      return;
    }
  }
  memcpy(state->raw150, bytes, 8);
  state->last_receive_at = now;
  state->seen = true;
  state->run = run_idle == 1;
  state->bool_valid = true;
  for (unsigned int i = 0; i < 4; ++i) {
    state->words[i] = bytes[2 * i] | ((unsigned int)bytes[2 * i + 1] << 8);
    if (state->words[i] > 1) state->bool_valid = false;
  }
  Event(state, "CYCLIC_RX", now);
  if (!state->bool_valid || run_idle > 1) {
    CommFault(state, !state->bool_valid ? "BOOL_ENCODING_INVALID" : "RUN_IDLE_INVALID", now);
    return;
  }
  if (state->config.mode == COMM_RX_ONLY) {
    memset(state->raw100, 0, 4);
    return;
  }
  if (state->config.mode == COMM_AI_RUNTIME) AiReceive(state, now);
  /* Completed/disarmed one-shot never rearms from an incoming request. */
  if (!state->armed && !ActiveRequest(state)) return;
  /* The operator starts the line after arming the test. A released STOP and
   * valid E-stop convention with Mc_Run=0 / Request=0 is initial standby,
   * not a cancelled active cycle. Require LOW again after Mc_Run becomes 1.
   * A STOP, lost link, or Mc_Run drop after IDLE still permanently disarms. */
  if (state->phase == SYNC_LOW && state->run && state->words[0] == 0
      && state->words[1] == state->config.estop_ok_value
      && state->words[2] == 0 && state->words[3] == state->config.stop_released_value) {
    state->reason = "WAIT_PLC_RUN_AND_REQUEST_LOW";
    return;
  }
  if (!state->run || !PermissionSignals(state)) {
    CommFault(state, !state->run ? "ORIGINATOR_IDLE" : "PLC_CONTROL_INHIBIT", now);
    return;
  }
  bool request = state->words[0] == 1;
  if (!request) {
    if (state->phase == SYNC_LOW && state->armed && !state->used) {
      state->saw_low = true;
      state->reason = "READY_FOR_ONE_RISING_EDGE";
      Phase(state, IDLE, "REQUEST_LOW_BASELINE", now);
    } else if (state->phase == DONE_SENT || state->phase == WAIT_REQUEST_OFF) {
      memset(state->raw100, 0, 4);
      Phase(state, CLEARING_DONE, "REQUEST_OFF_RECEIVED", now);
    } else if (state->phase >= REQUEST_RECEIVED && state->phase <= RESULT_SENT) {
      CommFault(state, "REQUEST_WITHDRAWN_BEFORE_DONE", now);
    }
    return;
  }
  if (state->phase == IDLE && state->saw_low && state->armed && !state->used) {
    state->used = true;
    if (state->config.mode==COMM_AI_RUNTIME && !state->config.automatic_repeat) state->initial_consumed=true;
    ++state->request_id;
    state->request_at = now;
    state->saw_low = false;
    Phase(state, REQUEST_RECEIVED, "REQUEST_RECEIVED", now);
    if (state->config.mode == COMM_AI_RUNTIME) { state->ai_clear=false; return; }
    state->raw100[0] = state->config.test_ng ? 1 : 0;
    state->raw100[1] = state->raw100[2] = state->raw100[3] = 0;
    ++state->result_count;
    Phase(state, TEST_RESULT_READY, "SYNTHETIC_TEST_RESULT", now);
  }
}

void CommTick(CommState *state, double now) {
  if (state->armed || ActiveRequest(state)) {
    if (state->config.mode == COMM_AI_RUNTIME && now-state->ai_heartbeat_at > .5) {
      CommFault(state, "PYTHON_HEARTBEAT_STALE", now);
    } else if (state->config.mode != COMM_AI_RUNTIME && now - state->started_at >= state->config.session_timeout_s) {
      CommFault(state, "TRIAL_TIME_LIMIT", now);
    } else if (state->seen && !CommControlsValid(state, now)) {
      CommFault(state, "CYCLIC_DATA_STALE", now);
    } else if (ActiveRequest(state)
               && now - state->request_at >= state->config.request_timeout_s) {
      CommFault(state, "REQUEST_HANDSHAKE_TIMEOUT", now);
    }
  }
}

void CommPrepareOutput(CommState *state, double now) {
  CommTick(state, now);
  if (state->config.mode == COMM_RX_ONLY || !ActiveRequest(state)) {
    memset(state->raw100, 0, 4);
    return;
  }
  if (!CommControlsValid(state, now) || !PermissionSignals(state)) {
    CommFault(state, "OUTPUT_EVIDENCE_INVALID", now);
    return;
  }
  if (state->phase == RESULT_SENT) {
    /* Set only for a subsequent packet: RESULT_SENT is reachable exclusively
     * after successful sendto of the Result-only cyclic packet. */
    state->raw100[2] = 1;
  }
}

void CommTxComplete(CommState *state, const uint8_t sent[4], bool success,
                    uint32_t sequence, double now) {
  if (!success) {
    CommFault(state, "CYCLIC_SEND_FAILED", now);
    return;
  }
  ++state->send_count;
  state->last_tx_sequence = sequence;
  Event(state, "CYCLIC_TX_ACCEPTED_BY_KERNEL", now);
  if (!ActiveRequest(state)) return;
  if (memcmp(sent, state->raw100, 4) != 0 || !CommControlsValid(state, now)) {
    CommFault(state, "TX_STATE_OR_FRESHNESS_MISMATCH", now);
    return;
  }
  if (state->phase == TEST_RESULT_READY && sent[2] == 0) {
    state->result_sequence = sequence;
    Phase(state, RESULT_SENT, "RESULT_CYCLIC_SENT", now);
  } else if (state->phase == RESULT_SENT && sent[2] == 1) {
    if (sequence == state->result_sequence) {
      CommFault(state, "DONE_NOT_A_LATER_PACKET", now);
      return;
    }
    state->done_sequence = sequence;
    ++state->done_count;
    Phase(state, DONE_SENT, "DONE_CYCLIC_SENT", now);
    Phase(state, WAIT_REQUEST_OFF, "WAIT_REQUEST_OFF", now);
  } else if (state->phase == CLEARING_DONE && sent[2] == 0) {
    ++state->completed_count;
    state->completed_request=state->request_id;
    state->completed_session=state->session_id;
    state->armed = false;
    memset(state->raw100, 0, 4);
    state->reason = state->config.automatic_repeat ? "PLC_TRANSACTION_COMPLETE" : "ONE_SHOT_COMPLETE_REARM_REQUIRED";
    Phase(state, READY_NEXT, "DONE_RESET_SENT_ONE_SHOT_FINISHED", now);
  }
}
