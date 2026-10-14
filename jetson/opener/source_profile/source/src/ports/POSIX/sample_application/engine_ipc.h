#ifndef ENGINE_IPC_H
#define ENGINE_IPC_H
#include "engine_commissioning.h"
/* Same-host, fixed little-endian 128-byte packets. No PLC tags are added. */
int EngineIpcInit(const char *path);
void EngineIpcPoll(CommState *state, double now);
void EngineIpcClose(void);
#endif
