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
  assert(s.phase==SYNC_LOW && !s.approval_id[0] && !s.initial_issued);
  for(unsigned n=1;n<=4;n++) {

    assert(!s.ai_clear); /* Transport accepts even if global Area is UNKNOWN. */
    assert(!s.approval_id[0] && !s.initial_issued && !s.approval_count);
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
  assert(s.phase==DISARMED);
  rx(0,0,1,1);assert(s.phase==SYNC_LOW);
  rx(0,1,1,1);rx(1,1,1,1);rx(1,1,1,0);
  assert(s.phase==DISARMED && !s.raw100[2]);
  assert(!CommAiResult(&s,s.session_id,5,1,true,t));
  rx(0,0,1,1);assert(s.phase==SYNC_LOW);
  init();
  rx(1,1,1,1);assert(!s.request_id); /* START with residual HIGH isn't an edge. */
  CommTick(&s,t+1);assert(s.phase==DISARMED);
  /* Recovery and fault matrix in automatic mode, without any arm API. */
  init(); rx(1,1,1,1); assert(s.phase==SYNC_LOW && s.request_id==0);
  CommDisconnect(&s,"CONNECTION_TIMEOUT",t);CommOpen(&s,t);
  rx(1,1,1,1); assert(s.phase==DISARMED && s.request_id==0);
  rx(0,0,1,1);rx(0,1,1,1);rx(1,1,1,1);
  assert(s.phase==REQUEST_RECEIVED && s.request_id==1);
  rx(1,1,0,1);assert(s.phase==DISARMED && !s.raw100[0] && !s.raw100[2]);
  assert(!CommAiResult(&s,s.session_id,1,3,true,t));
  init();rx(0,1,1,1);rx(1,1,1,1);CommAiHealth(&s,false,false,t);
  assert(s.phase==DISARMED && !s.raw100[2]);
  init();rx(0,1,1,1);rx(1,1,1,1);
  assert(!CommAiResult(&s,s.session_id,1,4,false,t));
  assert(CommAiResult(&s,s.session_id,1,4,true,t));
  CommTxComplete(&s,s.raw100,false,1,t);assert(s.phase==DISARMED && !s.done_count);
  /* A cancelled request leaves counters unequal. Settlement belongs to the
   * exact completed request/session, never to aggregate counter equality. */
  init();rx(0,1,1,1);rx(1,1,1,1);rx(1,1,1,0);
  assert(s.phase==DISARMED && s.request_id==1 && s.completed_count==0);
  rx(0,0,1,1);rx(0,1,1,1);rx(1,1,1,1);
  assert(s.request_id==2 && CommAiResult(&s,s.session_id,2,3,true,t));
  CommTxComplete(&s,s.raw100,true,10,t);CommPrepareOutput(&s,t);
  CommTxComplete(&s,s.raw100,true,11,t);rx(0,1,1,1);
  CommTxComplete(&s,s.raw100,true,12,t);
  assert(s.completed_count==1 && s.completed_request==2 && s.completed_session==s.session_id);
  assert(!memcmp(s.raw100,"\0\0\0\0",4));
  rx(0,1,1,1);rx(1,1,1,1);assert(s.request_id==3 && s.phase==REQUEST_RECEIVED);
  puts("ISOLATED_PASS automatic4 decisions; cancellation recovery; no software grants; STOP/lease guards");
}
