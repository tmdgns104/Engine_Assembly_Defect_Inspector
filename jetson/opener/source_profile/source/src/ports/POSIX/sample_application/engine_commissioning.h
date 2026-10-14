#ifndef ENGINE_COMMISSIONING_H
#define ENGINE_COMMISSIONING_H

#include <stdbool.h>
#include <stdint.h>

typedef enum { COMM_RX_ONLY, COMM_SYNTHETIC_RESULT, COMM_AI_RUNTIME } CommMode;
typedef enum {
  WAIT_CONNECTION, SYNC_LOW, IDLE, REQUEST_RECEIVED, TEST_RESULT_READY,
  RESULT_SENT, DONE_SENT, WAIT_REQUEST_OFF, CLEARING_DONE, READY_NEXT, DISARMED
} CommPhase;

typedef struct {
  CommMode mode;
  bool armed;
  bool test_ng;
  unsigned int estop_ok_value;
  unsigned int stop_released_value;
  double receive_max_age_s;
  double request_timeout_s;
  double session_timeout_s;
  bool supervised_repeat; /* Explicit local policy, never selected by PLC data. */
  bool automatic_repeat; /* PLC baselines/edges; no per-product permission. */
} CommConfig;

typedef struct CommState CommState;
typedef void (*CommEvent)(const CommState *, const char *, double, void *);

struct CommState {
  CommConfig config;
  CommPhase phase;
  CommEvent event;
  void *event_context;
  bool connected, seen, run, bool_valid, armed, used, saw_low;
  uint8_t raw150[8], raw100[4];
  unsigned int words[4];
  unsigned long session_id, request_id, result_count, done_count, completed_count;
  unsigned long receive_count, duplicate_count, send_count;
  unsigned long completed_request, completed_session;
  uint32_t result_sequence, done_sequence, last_tx_sequence;
  double started_at, last_receive_at, request_at;
  bool ai_ready, ai_clear, ai_stopped_seen;
  /* One explicit reservation per adapter process. Faults never clear "issued". */
  bool initial_issued, initial_consumed, initial_revoked;
  char approval_id[33];
  /* Keep spent IDs, including revoked grants. Exhaustion requires maintenance. */
  char issued_approvals[4096][33];
  unsigned int approval_count;
  double ai_heartbeat_at;
  const char *reason;
};

void CommInit(CommState *, const CommConfig *, double, CommEvent, void *);
void CommOpen(CommState *, double);
void CommDisconnect(CommState *, const char *, double);
void CommFault(CommState *, const char *, double);
void CommReceive(CommState *, const uint8_t[8], uint32_t, bool, double);
void CommTick(CommState *, double);
void CommPrepareOutput(CommState *, double);
void CommTxComplete(CommState *, const uint8_t[4], bool, uint32_t, double);
bool CommControlsValid(const CommState *, double);
const char *CommPhaseName(CommPhase);

void CommAiHealth(CommState *, bool, bool, double);
bool CommAiResult(CommState *, unsigned long, unsigned long, unsigned int, bool, double);

bool CommInitialArm(CommState *, const char *, double);
bool CommSupervisedArm(CommState *, const char *, double);

#endif
