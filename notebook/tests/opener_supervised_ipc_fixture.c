/* AF_UNIX-only fixture. PLC input and successful TX are explicitly synthetic.
 * Never links the EtherNet/IP stack; cannot open PLC network sockets. */
#define _POSIX_C_SOURCE 200809L
#include "engine_commissioning.h"
#include "engine_ipc.h"
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
static CommState s;
static double clock_now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
int main(int argc,char **argv){
  if(argc!=2)return 2;
  CommConfig c={COMM_AI_RUNTIME,false,false,1,1,.2,10,0,true};
  double start=clock_now();CommInit(&s,&c,start,NULL,NULL);CommOpen(&s,start);
  if(EngineIpcInit(argv[1]))return 3;
  fcntl(0,F_SETFL,O_NONBLOCK);unsigned request=0,run=0,seq=0;double tx=0;
  while(clock_now()-start<30){
    char command;while(read(0,&command,1)>0){if(command=='S')run=1;if(command=='R')request=1;if(command=='Q')goto end;}
    double now=clock_now();uint8_t b[8]={request,0,1,0,run,0,1,0};
    CommReceive(&s,b,1,false,now);EngineIpcPoll(&s,now);CommTick(&s,now);
    if(now-tx>=.05){CommPrepareOutput(&s,now);CommTxComplete(&s,s.raw100,true,++seq,now);tx=now;}
    if(s.phase==DONE_SENT||s.phase==WAIT_REQUEST_OFF)request=0;
    if(s.phase==READY_NEXT)run=0;
    struct timespec wait={0,5000000};nanosleep(&wait,NULL);
  }
end:
  printf("synthetic requests=%lu results=%lu done=%lu completed=%lu approvals=%u\n",s.request_id,s.result_count,s.done_count,s.completed_count,s.approval_count);
  EngineIpcClose();return 0;
}
