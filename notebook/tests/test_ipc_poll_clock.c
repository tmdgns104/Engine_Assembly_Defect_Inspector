/* AF_UNIX only. Reproduce a command arriving after the caller sampled now. */
#define _POSIX_C_SOURCE 200809L
#include "engine_commissioning.h"
#include "engine_ipc.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>

static double clock_now(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
  return t.tv_sec+t.tv_nsec/1e9;
}
static void stamp(unsigned char *b,double t) { memcpy(b+24,&t,8); }
int main(int argc,char **argv) {
  assert(argc==2);
  CommConfig c={COMM_AI_RUNTIME,false,false,1,1,.2,10,0,false,false};
  CommState s; double now=clock_now();
  CommInit(&s,&c,now,NULL,NULL); CommOpen(&s,now);
  assert(EngineIpcInit(argv[1])==0);
  int client=socket(AF_UNIX,SOCK_SEQPACKET,0); assert(client>=0);
  struct sockaddr_un a={0};a.sun_family=AF_UNIX;strcpy(a.sun_path,argv[1]);
  assert(connect(client,(struct sockaddr*)&a,sizeof(a))==0);
  EngineIpcPoll(&s,now);
  unsigned char snapshot[160], b[160]={0};assert(recv(client,snapshot,160,0)==160);
  memcpy(b,"EAI1\x03\0\x02\0",8);memcpy(b+8,snapshot+8,16);
  memset(b+32,'a',32);b[100]=1;b[104]=1;
  /* The IPC packet is genuinely current; only the caller's loop time is old. */
  stamp(b,clock_now());assert(send(client,b,160,0)==160);
  EngineIpcPoll(&s,now-.05);
  assert(s.ai_ready && "current IPC command rejected against old loop clock");
  s.ai_ready=false;
  stamp(b,clock_now()+1);assert(send(client,b,160,0)==160);
  EngineIpcPoll(&s,clock_now());assert(!s.ai_ready);
  stamp(b,clock_now()-1);assert(send(client,b,160,0)==160);
  EngineIpcPoll(&s,clock_now());assert(!s.ai_ready);
  stamp(b,clock_now());b[16]++;
  assert(send(client,b,160,0)==160);EngineIpcPoll(&s,clock_now());assert(!s.ai_ready);
  const EngineIpcTiming *timing=EngineIpcGetTiming();
  assert(timing->rejected_future==1 && timing->rejected_stale==1 && timing->rejected_context==1);
  /* Class1 timeout is a synthetic callback, not an actual network timeout. */
  CommDisconnect(&s,"CONNECTION_TIMEOUT",clock_now());
  assert(!s.connected && strcmp(s.reason,"CONNECTION_TIMEOUT")==0);
  CommOpen(&s,clock_now()); assert(s.connected);
  /* Independent real AF_UNIX peer loss must not be mislabelled Class1 loss. */
  close(client);EngineIpcPoll(&s,clock_now());
  assert(s.connected && !strcmp(s.reason,"IPC_DISCONNECTED"));
  assert(!strcmp(timing->last_loss_reason,"IPC_DISCONNECTED"));
  assert(s.result_count==0 && s.done_count==0);
  EngineIpcClose();puts("IPC clock, guards, synthetic Class1 callback vs actual AF_UNIX loss: PASS");
  return 0;
}
