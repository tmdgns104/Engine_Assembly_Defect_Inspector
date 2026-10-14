/* Exercise actual application callbacks with a slow filesystem, no NIC/PLC.
 * --wrap=fclose adds 250 ms only to real file streams (not memory formatting).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <assert.h>
#include "engine_ipc.h"
typedef uint8_t EipUint8;
typedef uint32_t EipUint32;
typedef bool EipBool8;
typedef int EipStatus;
enum { kEipStatusOk=0,kEipStatusError=1 };
typedef struct { unsigned int instance_number; } CipInstance;
typedef enum { kIoConnectionEventOpened,kIoConnectionEventTimedOut,kIoConnectionEventClosed } IoConnectionEvent;
static uint8_t g_assembly_data064[4];
static EngineIpcTiming timing;
const EngineIpcTiming *EngineIpcGetTiming(void) {return &timing;}
int EngineIpcInit(const char *path) {(void)path;return 0;}
void EngineIpcPoll(CommState *s,double now) {(void)s;(void)now;}
int __real_fclose(FILE *file);
int __wrap_fclose(FILE *file) {
  if(fileno(file)>=0)usleep(250000);
  return __real_fclose(file);
}
#include "engine_callbacks.c.inc"
int main(int argc,char **argv) {
  assert(argc==3 || argc==4);
  setenv("ENGINE_OPENER_MODE","COMM_AI_RUNTIME",1);
  setenv("ENGINE_OPENER_ENCODING","BOOL16_LE_0_1_VERIFIED",1);
  setenv("ENGINE_OPENER_EVENTS",argv[1],1);
  setenv("ENGINE_OPENER_STATUS",argv[2],1);
  EngineInitialize();
  double started=EngineMonotonic();
  CheckIoConnectionEvent(150,100,kIoConnectionEventOpened);
  uint8_t stopped[8]={0,0,1,0,0,0,1,0};
  EngineCyclicReceived(stopped,1,0);
  double elapsed=EngineMonotonic()-started;
  printf("callback_elapsed_s=%.6f injected_file_close_s=0.250\n",elapsed);
  fflush(stdout);
  assert(elapsed<0.05);
  assert(!memcmp(engine_state.raw100,"\0\0\0\0",4));
  usleep(800000);
  if(argc==4) {
    EngineCheck();
    assert(engine_state.phase==DISARMED);
    assert(!strcmp(engine_state.reason,"EVIDENCE_WRITE_FAILURE"));
    assert(!memcmp(engine_state.raw100,"\0\0\0\0",4));
    puts("storage_failure_blocked_without_result");
  }
  return 0;
}
