#define _GNU_SOURCE
#include "engine_ipc.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/random.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <math.h>

static int server=-1, peer=-1;
static char socket_path[108], runtime_session[33];
static uint64_t boot_nonce;
static double last_snapshot;
static unsigned int result_ack, rejected;
static const uint8_t no_approval[32]={0};
static EngineIpcTiming timing;
const EngineIpcTiming *EngineIpcGetTiming(void) { return &timing; }
static double current_time(void) {
  struct timespec t;
  if(clock_gettime(CLOCK_MONOTONIC,&t)) abort();
  return t.tv_sec+t.tv_nsec/1e9;
}
static uint32_t u32(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static uint64_t u64(const uint8_t *p) { return u32(p)|((uint64_t)u32(p+4)<<32); }
static void put32(uint8_t *p,uint32_t v) { for(int i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8)); }
static void put64(uint8_t *p,uint64_t v) { put32(p,(uint32_t)v); put32(p+4,(uint32_t)(v>>32)); }
static double number(const uint8_t *p) { uint64_t v=u64(p); double d; memcpy(&d,&v,8); return d; }
static void putnumber(uint8_t *p,double d) { uint64_t v; memcpy(&v,&d,8); put64(p,v); }
static int identifier(const uint8_t *p) {
  for(int i=0;i<32;i++) if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f'))) return 0;
  return 1;
}
static void lost(CommState *s,double now,const char *reason) {
  if(peer>=0) close(peer);
  peer=-1; runtime_session[0]=0; s->ai_ready=false;
  timing.last_loss_reason=reason; timing.last_loss_at=now;
  CommFault(s,reason,now);
}
void EngineIpcClose(void) {
  if(peer>=0) close(peer);
  if(server>=0) { close(server); unlink(socket_path); }
  peer=server=-1;
}
int EngineIpcInit(const char *path) {
  /* The caller creates a private 0700 directory. Never remove an unknown file
   * or a previous process's socket to steal ownership. */
  if(!path || path[0]!='/' || strlen(path)>=sizeof(socket_path)) return -1;
  char parent[108]; strcpy(parent,path); char *slash=strrchr(parent,'/'); *slash=0;
  struct stat st;
  if(lstat(parent,&st) || !S_ISDIR(st.st_mode) || st.st_uid!=geteuid() || (st.st_mode&077)) return -1;
  if(getrandom(&boot_nonce,sizeof(boot_nonce),0)!=sizeof(boot_nonce) || !boot_nonce) return -1;
  int fd=socket(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK|SOCK_CLOEXEC,0);
  if(fd<0) return -1;
  struct sockaddr_un a={0}; a.sun_family=AF_UNIX; strcpy(a.sun_path,path);
  if(bind(fd,(struct sockaddr*)&a,sizeof(a))) { close(fd); return -1; }
  if(chmod(path,0600) || listen(fd,1)) { close(fd); unlink(path); return -1; }
  server=fd; strcpy(socket_path,path); atexit(EngineIpcClose); return 0;
}
void EngineIpcPoll(CommState *s,double now) {
  /* A caller samples before recv(). A command can arrive after that sample;
   * compare against the actual receipt clock, never extend the 500 ms lease. */
  now=current_time();
  if(timing.last_poll_at && now-timing.last_poll_at>timing.max_poll_gap_s)
    timing.max_poll_gap_s=now-timing.last_poll_at;
  timing.last_poll_at=now;
  if(server<0) { CommFault(s,"IPC_UNAVAILABLE",now); return; }
  int candidate=accept4(server,NULL,NULL,SOCK_NONBLOCK|SOCK_CLOEXEC);
  if(candidate>=0) {
    struct ucred cred; socklen_t n=sizeof(cred);
    if(peer>=0 || getsockopt(candidate,SOL_SOCKET,SO_PEERCRED,&cred,&n) || cred.uid!=geteuid()) close(candidate);
    else { peer=candidate; runtime_session[0]=0; result_ack=0; last_snapshot=0;
           CommFault(s,"IPC_NEW_SESSION_REQUIRES_STOP",now); }
  }
  if(peer<0) return;
  for(int i=0;i<8;i++) {
    uint8_t b[161]; ssize_t n=recv(peer,b,sizeof(b),MSG_DONTWAIT|MSG_TRUNC);
    if(n<0 && (errno==EAGAIN||errno==EWOULDBLOCK)) break;
    now=current_time();
    if(n<=0) { lost(s,now,"IPC_DISCONNECTED"); return; }
    if(n!=160 || memcmp(b,"EAI1\x03\x00\x02\x00",8) || !identifier(b+32)) {
      lost(s,now,"IPC_SCHEMA_INVALID"); return;
    }
    double generated=number(b+24);
    timing.last_command_at=now; timing.last_command_age_s=isfinite(generated)?now-generated:0;
    if(!isfinite(generated) || generated>now) { ++rejected; ++timing.rejected_future; continue; }
    if(now-generated>.5) { ++rejected; ++timing.rejected_stale; continue; }
    if(u64(b+8)!=boot_nonce || u32(b+16)!=s->session_id) { ++rejected; ++timing.rejected_context; continue; }
    if(runtime_session[0] && memcmp(runtime_session,b+32,32)) { lost(s,now,"IPC_RUNTIME_SESSION_CHANGED"); return; }
    if(!runtime_session[0]) { memcpy(runtime_session,b+32,32); runtime_session[32]=0; }
    uint32_t command=u32(b+104), flags=u32(b+100);
    if(command==1 && flags<=3) CommAiHealth(s,(flags&1)!=0,(flags&2)!=0,now);
    else if(command==4 && flags==0 && identifier(b+128) && u32(b+20)==s->request_id) {
      char approval[33]; memcpy(approval,b+128,32); approval[32]=0;
      if(!CommInitialArm(s,approval,now)) ++rejected;
    }
    else if(command==5 && flags==0 && identifier(b+128) && u32(b+20)==s->request_id) {
      char approval[33]; memcpy(approval,b+128,32); approval[32]=0;
      if(!CommSupervisedArm(s,approval,now)) ++rejected;
    }
    else if(command==2 && flags==7 && identifier(b+64)
            && ((s->config.automatic_repeat && !memcmp(b+128,no_approval,32))
                || (s->initial_consumed && !s->initial_revoked && !memcmp(b+128,s->approval_id,32)))
            && u32(b+20)==s->request_id) {
      if(CommAiResult(s,u32(b+16),u32(b+20),u32(b+96),true,now)) result_ack=s->request_id;
      else ++rejected;
    } else if(command==3 && flags==0 && u32(b+20)==s->request_id) CommFault(s,"PYTHON_CANCELLED",now);
    else ++rejected;
  }
  now=current_time();
  if(now-last_snapshot<.04) return;
  uint8_t b[160]={0}; memcpy(b,"EAI1\x03\x00\x01\x00",8);
  put64(b+8,boot_nonce); put32(b+16,s->session_id); put32(b+20,s->request_id);
  putnumber(b+24,now); putnumber(b+32,s->last_receive_at); putnumber(b+40,s->request_at);
  uint32_t flags=(s->connected?1:0)|(s->run?2:0)|(s->bool_valid?4:0)|(CommControlsValid(s,now)?8:0);
  /* Bit 16 ties reset completion to this connection/request, not aggregate
   * counts (an earlier cancelled request may have no Result/Done). */
  if(s->request_id && s->completed_request==s->request_id && s->completed_session==s->session_id) flags|=(1u<<16);
  for(int i=0;i<4;i++) if(s->words[i]) flags|=(1u<<(8+i));
  put32(b+48,flags); put32(b+52,s->phase);
  put32(b+56,s->result_count); put32(b+60,s->done_count); put32(b+64,s->completed_count);
  put32(b+68,result_ack); put32(b+72,rejected);
  memcpy(b+76,s->raw100,4); snprintf((char*)b+80,48,"%s",s->reason);
  memcpy(b+128,s->approval_id,32);
  ssize_t n=send(peer,b,sizeof(b),MSG_DONTWAIT|MSG_NOSIGNAL);
  if(n==160) {
    if(last_snapshot && now-last_snapshot>timing.max_snapshot_gap_s)
      timing.max_snapshot_gap_s=now-last_snapshot;
    last_snapshot=now; timing.last_snapshot_at=now;
  }
  else if(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) ++timing.snapshot_would_block;
  else if(n<0 && errno!=EAGAIN && errno!=EWOULDBLOCK) lost(s,now,"IPC_SEND_FAILED");
}
