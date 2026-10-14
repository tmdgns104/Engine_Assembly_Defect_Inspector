#ifndef ENGINE_EVIDENCE_H
#define ENGINE_EVIDENCE_H
#include <stddef.h>
#define ENGINE_EVIDENCE_BYTES 8192
/* Single cyclic producer, single disk consumer. No disk wait in Push. */
int EngineEvidenceStart(const char *events, const char *status);
int EngineEvidencePush(const char *json, size_t size, int status_only);
int EngineEvidenceFailed(void);
double EngineEvidenceMaxWrite(void);
unsigned long EngineEvidenceDroppedStatus(void);
#endif
