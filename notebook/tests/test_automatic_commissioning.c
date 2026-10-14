/* Pure state machine; no network, PLC or camera. */
#include "engine_commissioning.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static CommState s;
static double t=1;
static void rx(unsigned request,unsigned run,unsigned estop,unsigned stop) {
  uint8_t b[8]={request,0,estop,0,run,0,stop,0};
  t+=.05;CommAiHealth(&s,true,false,t);CommReceive(&s,b,1,false,t);
}
static void init(void) {
  CommConfig c={COMM_AI_RUNTIME,false,false,1,1,.2,10,0,false,true};
  CommInit(&s,&c,t,NULL,NULL);CommOpen(&s,t);rx(0,0,1,1);
}
int main(void) {
  init();
  assert(!CommInitialArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  assert(!CommSupervisedArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  rx(0,1,1,1);assert(!CommAutomaticArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  rx(0,0,1,1);
  for(unsigned n=1;n<=4;n++) {
    char id[33];snprintf(id,sizeof id,"%032x",n);
    assert(!s.ai_clear); /* Transport accepts even if global Area is UNKNOWN. */
    assert(CommAutomaticArm(&s,id,t));
    assert(!CommAutomaticArm(&s,id,t));
    rx(0,1,1,1);rx(1,1,1,1);rx(1,1,1,1);
    assert(s.request_id==n && s.phase==REQUEST_RECEIVED);
    assert(!CommAiResult(&s,s.session_id,n-1,n,true,t));
    assert(CommAiResult(&s,s.session_id,n,n,true,t));
    assert(s.raw100[0]==(n!=1) && !s.raw100[2]);
    CommTxComplete(&s,s.raw100,true,n*10,t);CommPrepareOutput(&s,t);
    assert(s.raw100[2]);CommTxComplete(&s,s.raw100,true,n*10+1,t);
    rx(0,1,1,1);CommTxComplete(&s,s.raw100,true,n*10+2,t);
    assert(s.phase==READY_NEXT && s.completed_count==n && s.done_count==n);
  }
  CommDisconnect(&s,"test loss",t);CommOpen(&s,t);
  rx(0,1,1,1);CommAiHealth(&s,true,true,t);
  assert(!CommAutomaticArm(&s,"ffffffffffffffffffffffffffffffff",t));
  rx(0,0,1,1);assert(CommAutomaticArm(&s,"ffffffffffffffffffffffffffffffff",t));
  rx(0,1,1,1);rx(1,1,1,1);rx(1,1,1,0);
  assert(s.phase==DISARMED && !s.raw100[2]);
  assert(!CommAiResult(&s,s.session_id,5,1,true,t));
  rx(0,0,1,1);assert(!CommAutomaticArm(&s,"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",t));
  init();assert(CommAutomaticArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  rx(1,1,1,1);assert(!s.request_id); /* START with residual HIGH isn't an edge. */
  CommTick(&s,t+1);assert(s.phase==DISARMED);
  puts("ISOLATED_PASS automatic4 decisions; one START; no CLEAR required for transport; old-result/STOP/lease guards");
}
