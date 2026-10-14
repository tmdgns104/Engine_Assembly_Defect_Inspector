#include "engine_commissioning.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static CommState s;
static double t;
static const char *id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static unsigned checks;
static void ok(const char *name) { puts(name); ++checks; }
static void rx(int request,int estop,int run,int stop) {
  uint8_t b[8]={(uint8_t)request,0,(uint8_t)estop,0,(uint8_t)run,0,(uint8_t)stop,0};
  t+=.05; CommAiHealth(&s,true,false,t); CommReceive(&s,b,1,false,t);
}
static void fresh(void) {
  CommConfig c={COMM_AI_RUNTIME,false,false,1,1,.2,10,0,false,false};
  t=1; CommInit(&s,&c,t,NULL,NULL); CommOpen(&s,t);
  rx(0,1,0,1);
}
static void start(void) {
  fresh(); assert(CommInitialArm(&s,id,t)); assert(!s.ai_clear);
  rx(0,1,0,1); assert(s.phase==SYNC_LOW);
  rx(0,1,1,1); assert(s.phase==IDLE);
  rx(1,1,1,1); assert(s.phase==REQUEST_RECEIVED && s.initial_consumed);
}
int main(void) {
  fresh(); rx(0,1,1,1);rx(1,1,1,1); assert(s.request_id==0);ok("no approval blocked");
  fresh(); rx(1,1,0,1);assert(!CommInitialArm(&s,id,t));ok("request HIGH blocked");
  fresh(); rx(0,1,1,1);assert(!CommInitialArm(&s,id,t));ok("run HIGH blocked");
  fresh(); rx(0,0,0,1);assert(!CommInitialArm(&s,id,t));ok("EStop blocked");
  fresh(); rx(0,1,0,0);assert(!CommInitialArm(&s,id,t));ok("STOP blocked");
  fresh();assert(!CommInitialArm(&s,id,t+.3));ok("stale receive blocked");
  fresh();CommAiHealth(&s,false,false,t);assert(!CommInitialArm(&s,id,t));ok("not ready blocked");
  fresh();s.raw100[0]=1;assert(!CommInitialArm(&s,id,t));ok("residual result blocked");
  fresh();assert(!CommInitialArm(&s,"bad",t));ok("invalid approval blocked");
  start();ok("clear false explicit arm then fresh START/request accepted");
  assert(!CommInitialArm(&s,id,t));rx(1,1,1,1);assert(s.request_id==1);ok("grant and request duplicates blocked");
  assert(!CommAiResult(&s,s.session_id,99,1,true,t));
  assert(!CommAiResult(&s,s.session_id,1,1,false,t));ok("wrong result token and durability blocked");
  for(unsigned decision=1;decision<=4;decision++){
    start();assert(CommAiResult(&s,s.session_id,1,decision,true,t));
    {
      assert(s.raw100[0]==(decision!=1) && !s.raw100[2]);
      CommTxComplete(&s,s.raw100,true,10,t);CommPrepareOutput(&s,t);
      assert(s.raw100[2]==1);CommTxComplete(&s,s.raw100,true,11,t);
      assert(s.done_count==1 && s.result_sequence==10 && s.done_sequence==11);
      rx(0,1,1,1);CommTxComplete(&s,s.raw100,true,12,t);
      assert(s.phase==READY_NEXT && !s.raw100[2]);
      CommAiHealth(&s,true,true,t);rx(0,1,1,1);rx(1,1,1,1);
      assert(s.request_id==1 && s.done_count==1);
    }
    ok(decision==1?"PASS ordered":"FAIL/REVIEW/ERROR expected output");
  }
  start();rx(1,1,1,0);rx(0,1,0,1);rx(0,1,1,1);rx(1,1,1,1);
  assert(s.request_id==1 && !CommAiResult(&s,s.session_id,1,1,true,t));ok("STOP cannot rearm/late result blocked");
  assert(!CommAiResult(&s,s.session_id,1,3,true,t));
  assert(!CommAiResult(&s,s.session_id,1,4,true,t));ok("STOP blocks REVIEW/ERROR completion too");
  start();CommDisconnect(&s,"test",t);CommOpen(&s,t);rx(0,1,0,1);
  assert(!CommInitialArm(&s,id,t));ok("reconnect consumed approval blocked");
  start();CommTick(&s,t+1);assert(s.phase==DISARMED);ok("heartbeat timeout");
  start();rx(0,1,1,1);assert(s.phase==DISARMED);ok("latched PLC premature request withdrawal");
  fresh();assert(CommInitialArm(&s,id,t));CommAiHealth(&s,false,false,t);rx(0,1,0,1);
  assert(!CommInitialArm(&s,id,t));ok("unused grant revoked on health loss");
  printf("%u checks PASS\n",checks);return 0;
}
