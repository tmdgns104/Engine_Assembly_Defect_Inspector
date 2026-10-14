#ifndef ENGINE_IPC_H
#define ENGINE_IPC_H
#include "engine_commissioning.h"
/* Same-host, fixed little-endian 160-byte v3 packets. No PLC tags are added. */
typedef struct {
  double last_poll_at, max_poll_gap_s, last_command_at, last_command_age_s;
  double last_snapshot_at, max_snapshot_gap_s, last_loss_at;
  unsigned long rejected_future, rejected_stale, rejected_context, snapshot_would_block;
  const char *last_loss_reason;
} EngineIpcTiming;
const EngineIpcTiming *EngineIpcGetTiming(void);
int EngineIpcInit(const char *path);
void EngineIpcPoll(CommState *state, double now);
void EngineIpcClose(void);
#endif
