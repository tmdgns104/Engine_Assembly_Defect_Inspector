/* Disk diagnostics must not stall cyclic processing. Events remain ordered;
 * intermediate status snapshots may coalesce. Queue/storage failure fails
 * publication closed in the cyclic owner, never in this thread.
 */
#define _POSIX_C_SOURCE 200809L
#include "engine_evidence.h"
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define QUEUE_SIZE 128
typedef struct { char json[ENGINE_EVIDENCE_BYTES]; size_t size; } Record;
static Record queue[QUEUE_SIZE], latest;
static atomic_uint head, tail;
static int pending_status;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static atomic_int failed, started;
static atomic_ulong max_write_us, dropped_status;
static FILE *event_file;
static char status_path[4096], temporary[4096];

static double Clock(void) {
  struct timespec t;
  if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
  return t.tv_sec+t.tv_nsec/1e9;
}
static void *Writer(void *unused) {
  (void)unused;
  unsigned long event_count=0, event_bytes=0;
  for(;;) {
    Record r; int status_only=0;
    unsigned int h=atomic_load(&head);
    if(h!=atomic_load(&tail)) {
      r=queue[h];atomic_store(&head,(h+1)%QUEUE_SIZE);
    } else {
      pthread_mutex_lock(&lock);
      if(pending_status) { r=latest;pending_status=0;status_only=1; }
      pthread_mutex_unlock(&lock);
      if(!status_only) { struct timespec idle={0,1000000};nanosleep(&idle,NULL);continue; }
    }
    if(atomic_load(&failed))continue;
    double before=Clock();
    if(status_only) {
      FILE *f=fopen(temporary,"w");
      if(!f)atomic_store(&failed,1);
      else {
        int bad=fwrite(r.json,1,r.size,f)!=r.size;
        if(fclose(f))bad=1;
        if(bad || rename(temporary,status_path)) { atomic_store(&failed,1);unlink(temporary); }
      }
    } else {
      event_bytes+=r.size;
      if(++event_count>12000 || event_bytes>16*1024*1024 || !event_file ||
          fwrite(r.json,1,r.size,event_file)!=r.size || fflush(event_file))atomic_store(&failed,1);
    }
    unsigned long duration=(unsigned long)((Clock()-before)*1e6);
    if(duration>atomic_load(&max_write_us))atomic_store(&max_write_us,duration);
  }
  return NULL;
}
int EngineEvidenceStart(const char *events,const char *status) {
  if(atomic_exchange(&started,1))return -1;
  if(!events || events[0]!='/' || !status || status[0]!='/' || strlen(status)>4000)return -1;
  /* Startup before any network listener; this file open cannot block a cycle. */
  event_file=fopen(events,"wx");
  if(!event_file)return -1;
  strcpy(status_path,status);
  snprintf(temporary,sizeof(temporary),"%s.tmp.%ld",status,(long)getpid());
  pthread_t thread;
  if(pthread_create(&thread,NULL,Writer,NULL)) { fclose(event_file);return -1; }
  pthread_detach(thread);
  return 0;
}
int EngineEvidencePush(const char *json,size_t size,int status_only) {
  if(!atomic_load(&started) || atomic_load(&failed) || size>=ENGINE_EVIDENCE_BYTES)return -1;
  if(status_only) {
    if(pthread_mutex_trylock(&lock)) {atomic_fetch_add(&dropped_status,1);return 0;}
    if(pending_status)atomic_fetch_add(&dropped_status,1);
    memcpy(latest.json,json,size);latest.size=size;pending_status=1;
    pthread_mutex_unlock(&lock);
  } else {
    unsigned int t=atomic_load(&tail),next=(t+1)%QUEUE_SIZE;
    if(next==atomic_load(&head))atomic_store(&failed,1);
    else {
      memcpy(queue[t].json,json,size);queue[t].size=size;
      atomic_store(&tail,next);
    }
  }
  return atomic_load(&failed) ? -1 : 0;
}
int EngineEvidenceFailed(void) {return atomic_load(&failed);}
double EngineEvidenceMaxWrite(void) {return atomic_load(&max_write_us)/1e6;}
unsigned long EngineEvidenceDroppedStatus(void) {return atomic_load(&dropped_status);}
