/* Pure state machine. No device, network or camera opened. */
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
static void fresh(void) {
  CommConfig c={COMM_AI_RUNTIME,false,false,1,1,.2,10,0,true,false};
  CommInit(&s,&c,t,NULL,NULL);CommOpen(&s,t);rx(0,0,1,1);
}
static void grant(unsigned n) {
  char id[33];snprintf(id,sizeof id,"%032x",n);
  assert(CommSupervisedArm(&s,id,t));assert(!CommSupervisedArm(&s,id,t));
  rx(0,1,1,1);rx(1,1,1,1);assert(s.phase==REQUEST_RECEIVED);
}
int main(void) {
  fresh();assert(!CommInitialArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  for(unsigned n=1;n<=4;n++) {
    grant(n);assert(s.request_id==n);rx(1,1,1,1);assert(s.request_id==n);
    assert(!CommAiResult(&s,s.session_id,n-1,n,true,t));
    assert(CommAiResult(&s,s.session_id,n,n,true,t));
    assert(s.raw100[0]==(n!=1) && !s.raw100[2]);
    assert(!CommAiResult(&s,s.session_id,n,n,true,t));
    CommTxComplete(&s,s.raw100,true,n*10,t);CommPrepareOutput(&s,t);
    assert(s.raw100[2]==1);CommTxComplete(&s,s.raw100,true,n*10+1,t);
    rx(0,1,1,1);CommTxComplete(&s,s.raw100,true,n*10+2,t);
    assert(s.phase==READY_NEXT && s.done_count==n && s.completed_count==n);
    rx(1,1,1,1);assert(s.request_id==n);rx(0,0,1,1);
    assert(!CommSupervisedArm(&s,"00000000000000000000000000000001",t));
    assert(s.approval_count==n);assert(!s.ai_clear);
  }
  assert(s.result_count==4 && s.done_count==4 && s.request_id==4);
  s.raw100[2]=1;assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t));s.raw100[2]=0;
  rx(0,0,0,1);assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t));
  rx(0,0,1,0);assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t));
  rx(1,0,1,1);assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t));
  rx(0,0,1,1);assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t+.3));
  grant(5);rx(1,1,1,0);assert(s.phase==DISARMED);
  assert(!CommAiResult(&s,s.session_id,5,1,true,t));
  CommDisconnect(&s,"fixture",t);CommOpen(&s,t);rx(0,0,1,1);
  assert(!CommSupervisedArm(&s,"ffffffffffffffffffffffffffffffff",t));
  fresh();assert(CommSupervisedArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  CommDisconnect(&s,"fixture",t);CommOpen(&s,t);rx(0,0,1,1);
  assert(!s.armed);assert(!CommSupervisedArm(&s,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",t));
  assert(CommSupervisedArm(&s,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",t));
  CommTick(&s,t+1);assert(!s.armed);
  puts("ISOLATED_PASS: four outcomes, ordered packets, counters, reuse, control/connection/lease guards");
}
