#include "engine_ipc.h"
/* The 4/8-byte commissioning application. Local IPC bridge; no input echo. */
#include "engine_commissioning.h"
#include "engine_evidence.h"

static CommState engine_state;
static int engine_log_failed = 0;
static double engine_last_status = -1.0;
static unsigned long engine_timeouts = 0;
static int engine_evidence_enabled = 0;
static int engine_initialized = 0;
static double engine_max_status_write_s, engine_max_event_write_s;
static double engine_last_callback_at, engine_max_callback_gap_s;

static double EngineMonotonic(void) {
  struct timespec value;
  if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) exit(EXIT_FAILURE);
  return value.tv_sec + value.tv_nsec / 1000000000.0;
}

static void EngineJson(FILE *file, const CommState *s, const char *event, double now) {
  fprintf(file, "{\"schema\":2,\"pid\":%ld,\"event\":\"%s\",\"monotonic_s\":%.6f,"
    "\"mode\":\"%s\",\"result_source\":\"%s\",\"test_result\":\"%s\","
    "\"phase\":\"%s\",\"reason\":\"%s\",\"connected\":%s,\"run_idle_run\":%s,"
    "\"has_received\":%s,\"bool_slots_valid\":%s,\"controls_valid\":%s,"
    "\"armed\":%s,\"one_shot_used\":%s,\"publication_enabled\":%s,"
    "\"connection_session\":%lu,\"trial_request_id\":%lu,\"assembly_updates\":%lu,\"opens\":%lu,\"timeouts\":%lu,"
    "\"duplicate_packets\":%lu,\"production_callbacks\":%lu,\"result_count\":%lu,"
    "\"done_count\":%lu,\"completed_count\":%lu,\"last_tx_sequence\":%u,"
    "\"result_sequence\":%u,\"done_sequence\":%u,\"last_receive_monotonic_s\":%.6f,"
    "\"ai_ready\":%s,\"ai_last_health_monotonic_s\":%.6f,\"ai_health_age_s\":%.6f,"
    "\"initial_revoked\":%s,\"raw150_hex\":\"",
    (long)getpid(), event, now,
    s->config.mode == COMM_RX_ONLY ? "COMM_RX_ONLY" : (s->config.mode==COMM_AI_RUNTIME ? "COMM_AI_RUNTIME":"COMM_SYNTHETIC_RESULT"),
    s->config.mode == COMM_RX_ONLY ? "NO_RESULT" : (s->config.mode==COMM_AI_RUNTIME ? "PYTHON_FINAL_RESULT_SEE_JOURNAL":"SYNTHETIC_TEST_RESULT"),
    s->config.mode == COMM_RX_ONLY ? "NONE" : (s->config.mode==COMM_AI_RUNTIME ? "NONE" : (s->config.test_ng ? "TEST_NG" : "TEST_PASS")), CommPhaseName(s->phase), s->reason,
    s->connected ? "true":"false", (s->connected && s->seen && s->run) ? "true":"false",
    s->seen ? "true":"false", s->bool_valid ? "true":"false",
    CommControlsValid(s, now) ? "true":"false", s->armed ? "true":"false",
    s->used ? "true":"false", (s->config.mode != COMM_RX_ONLY && s->armed) ? "true":"false",
    s->session_id, s->request_id, s->receive_count, s->session_id, engine_timeouts, s->duplicate_count, s->send_count,
    s->result_count, s->done_count, s->completed_count, s->last_tx_sequence,
    s->result_sequence, s->done_sequence, s->last_receive_at,
    s->ai_ready ? "true":"false", s->ai_heartbeat_at, now-s->ai_heartbeat_at,
    s->initial_revoked ? "true":"false");
  for (unsigned int i=0; i<8; ++i) fprintf(file, "%02x", s->raw150[i]);
  fprintf(file, "\",\"raw100_hex\":\"");
  for (unsigned int i=0; i<4; ++i) fprintf(file, "%02x", s->raw100[i]);
  fprintf(file, "\",\"slots\":{\"Inspection_Request\":%u,\"EStop_OK\":%u,"
    "\"Mc_Run\":%u,\"Stop_PB\":%u},\"plc_consumption_confirmed\":false,"
    "\"inspection_bridge\":\"MODE_DEPENDENT_SEE_IPC\",",
    s->words[0],s->words[1],s->words[2],s->words[3]);
  const EngineIpcTiming *t=EngineIpcGetTiming();
  fprintf(file,"\"timing\":{\"max_status_write_s\":%.6f,\"max_event_write_s\":%.6f,"
    "\"last_ipc_poll\":%.6f,\"max_ipc_poll_gap_s\":%.6f,"
    "\"last_command_at\":%.6f,\"last_command_age_s\":%.6f,"
    "\"last_snapshot_at\":%.6f,\"max_snapshot_gap_s\":%.6f,"
    "\"rejected_future\":%lu,\"rejected_stale\":%lu,\"rejected_context\":%lu,"
    "\"snapshot_would_block\":%lu,\"last_ipc_loss_at\":%.6f,\"last_ipc_loss\":\"%s\","
    "\"max_disk_write_s\":%.6f,\"status_snapshots_coalesced\":%lu,\"max_application_callback_gap_s\":%.6f}}\n",
    engine_max_status_write_s,engine_max_event_write_s,t->last_poll_at,t->max_poll_gap_s,
    t->last_command_at,t->last_command_age_s,t->last_snapshot_at,t->max_snapshot_gap_s,
    t->rejected_future,t->rejected_stale,t->rejected_context,t->snapshot_would_block,
    t->last_loss_at,t->last_loss_reason?t->last_loss_reason:"NONE",
    EngineEvidenceMaxWrite(),EngineEvidenceDroppedStatus(),engine_max_callback_gap_s);
}

static void QueueEngineJson(const CommState *s,const char *event,double now,int status_only) {
  if(!engine_evidence_enabled || engine_log_failed)return;
  char buffer[ENGINE_EVIDENCE_BYTES];
  FILE *memory=fmemopen(buffer,sizeof(buffer),"w");
  if(!memory) {engine_log_failed=1;return;}
  EngineJson(memory,s,event,now);
  long size=ftell(memory);
  int bad=ferror(memory);
  if(fclose(memory))bad=1;
  if(bad || size<0 || (size_t)size>=sizeof(buffer) ||
      EngineEvidencePush(buffer,(size_t)size,status_only))engine_log_failed=1;
}

static void EngineRecord(const CommState *s, const char *event, double now, void *context) {
  (void)context;
  if (s->config.mode==COMM_AI_RUNTIME && (strcmp(event,"CYCLIC_RX")==0 || strcmp(event,"CYCLIC_TX_ACCEPTED_BY_KERNEL")==0)) return;
  double started=EngineMonotonic();
  QueueEngineJson(s,event,now,0);
  double duration=EngineMonotonic()-started;
  if(duration>engine_max_event_write_s) engine_max_event_write_s=duration;
}

static int EngineEquals(const char *name, const char *expected) {
  const char *value=getenv(name);
  return value != NULL && strcmp(value, expected)==0;
}

static unsigned int EngineControlValue(const char *name) {
  if (EngineEquals(name,"0")) return 0;
  if (EngineEquals(name,"1")) return 1;
  fprintf(stderr, "Synthetic trial requires explicit 0/1 control polarity: %s\n",name);
  exit(EXIT_FAILURE);
}

static void EngineInitialize(void) {
  if (engine_initialized) return;
  engine_initialized=1;
  CommConfig config={COMM_RX_ONLY,false,true,1,1,0.20,10.0,120.0,false,false};
  const char *mode=getenv("ENGINE_OPENER_MODE");
  if (mode && strcmp(mode,"COMM_RX_ONLY") != 0) {
    if (strcmp(mode,"COMM_AI_RUNTIME")==0) {
      if (!EngineEquals("ENGINE_OPENER_ENCODING","BOOL16_LE_0_1_VERIFIED") ||
          EngineIpcInit(getenv("ENGINE_OPENER_IPC")) != 0) {
        fprintf(stderr,"AI mode requires verified encoding and exclusive private IPC socket\n"); exit(EXIT_FAILURE);
      }
      config.mode=COMM_AI_RUNTIME; config.session_timeout_s=0; config.request_timeout_s=120;
      const char *admission=getenv("ENGINE_OPENER_ADMISSION");
      if (admission && strcmp(admission,"FIRST_PRODUCT_ONLY") && strcmp(admission,"SUPERVISED_REPEAT_TEST") && strcmp(admission,"PLC_AUTOMATIC_REPEAT")) {
        fprintf(stderr,"Unknown AI admission policy\n"); exit(EXIT_FAILURE);
      }
      config.supervised_repeat=admission && !strcmp(admission,"SUPERVISED_REPEAT_TEST");
      config.automatic_repeat=admission && !strcmp(admission,"PLC_AUTOMATIC_REPEAT");
    } else {
    if (strcmp(mode,"COMM_SYNTHETIC_RESULT") != 0) {
      fprintf(stderr,"Unknown commissioning mode; no listener started\n"); exit(EXIT_FAILURE);
    }
    if (!EngineEquals("ENGINE_OPENER_ARM","ONE_SHOT_APPROVED")
        || !EngineEquals("ENGINE_OPENER_ENCODING","BOOL16_LE_0_1_VERIFIED")) {
      fprintf(stderr,"Synthetic trial requires explicit one-shot approval and verified encoding\n");
      exit(EXIT_FAILURE);
    }
    config.mode=COMM_SYNTHETIC_RESULT; config.armed=true;
    config.estop_ok_value=EngineControlValue("ENGINE_OPENER_ESTOP_OK_VALUE");
    config.stop_released_value=EngineControlValue("ENGINE_OPENER_STOP_RELEASED_VALUE");
    const char *result=getenv("ENGINE_OPENER_TEST_RESULT");
    if (result && strcmp(result,"TEST_NG") != 0 && strcmp(result,"TEST_PASS") != 0) {
      fprintf(stderr,"Unknown synthetic result\n"); exit(EXIT_FAILURE);
    }
    config.test_ng=!(result && strcmp(result,"TEST_PASS")==0);
    }
  }
  const char *engine_status_path=getenv("ENGINE_OPENER_STATUS");
  const char *events=getenv("ENGINE_OPENER_EVENTS");
  if(events && engine_status_path && !EngineEvidenceStart(events,engine_status_path))engine_evidence_enabled=1;
  if (config.mode!=COMM_RX_ONLY && !engine_evidence_enabled) {
    fprintf(stderr,"Runtime needs new absolute evidence paths\n"); exit(EXIT_FAILURE);
  }
  CommInit(&engine_state,&config,EngineMonotonic(),EngineRecord,NULL);
}

static void WriteEngineStatus(int force) {
  double now=EngineMonotonic();
  if (!engine_evidence_enabled) return;
  if (!force && now-engine_last_status<0.05) return;
  engine_last_status=now;
  QueueEngineJson(&engine_state,"STATUS",now,1);
  double duration=EngineMonotonic()-now;
  if(duration>engine_max_status_write_s) engine_max_status_write_s=duration;
}

static void EngineCheck(void) {
  if (engine_state.config.mode==COMM_AI_RUNTIME) EngineIpcPoll(&engine_state,EngineMonotonic());
  if (engine_log_failed || EngineEvidenceFailed()) CommFault(&engine_state,"EVIDENCE_WRITE_FAILURE",EngineMonotonic());
  CommTick(&engine_state,EngineMonotonic());
}

void HandleApplication(void) {
  double now=EngineMonotonic();
  if(engine_last_callback_at && now-engine_last_callback_at>engine_max_callback_gap_s)
    engine_max_callback_gap_s=now-engine_last_callback_at;
  engine_last_callback_at=now;
  EngineCheck(); WriteEngineStatus(0);
}

void CheckIoConnectionEvent(unsigned int consumed, unsigned int produced, IoConnectionEvent event) {
  if (consumed != 150 || produced != 100) return;
  if (event==kIoConnectionEventTimedOut) ++engine_timeouts;
  if (event==kIoConnectionEventOpened) CommOpen(&engine_state,EngineMonotonic());
  else CommDisconnect(&engine_state,event==kIoConnectionEventTimedOut ? "CONNECTION_TIMEOUT":"CONNECTION_CLOSED",EngineMonotonic());
  memcpy(g_assembly_data064,engine_state.raw100,4);
  WriteEngineStatus(1);
}

/* Called only from the validated cyclic data path, never CIP attribute writes. */
void EngineCyclicReceived(const EipUint8 *data, EipUint32 run_idle, int duplicate) {
  CommReceive(&engine_state,data,run_idle,duplicate != 0,EngineMonotonic());
  EngineCheck(); WriteEngineStatus(1);
}

void EngineCyclicRejected(void) {
  CommFault(&engine_state,"CYCLIC_SIZE_MISMATCH",EngineMonotonic());
  WriteEngineStatus(1);
}

void EngineCyclicSent(unsigned int consumed, unsigned int produced,
                      const EipUint8 *sent, EipStatus status, EipUint32 sequence) {
  if (consumed != 150 || produced != 100) return;
  CommTxComplete(&engine_state,sent,status==kEipStatusOk,sequence,EngineMonotonic());
  EngineCheck(); WriteEngineStatus(0);
}

EipStatus AfterAssemblyDataReceived(CipInstance *instance) {
  /* An Explicit attribute write must never manufacture a cyclic request or
   * write the produced image. Real RX handling is in EngineCyclicReceived. */
  if (instance->instance_number==100) {
    memcpy(g_assembly_data064,engine_state.raw100,4);
    return kEipStatusError;
  }
  return kEipStatusOk;
}

EipBool8 BeforeAssemblyDataSend(CipInstance *instance) {
  if (instance->instance_number==100) {
    EngineCheck(); CommPrepareOutput(&engine_state,EngineMonotonic());
    memcpy(g_assembly_data064,engine_state.raw100,4);
  }
  return true;
}

void RunIdleChanged(EipUint32 value) {
  /* Fresh per-packet header is passed to CommReceive. Avoid the stack's cached
   * RunIdleChanged behavior making reconnect or stale attributes look fresh. */
  if (value != 1 && engine_state.config.mode!=COMM_RX_ONLY)
    CommFault(&engine_state,"ORIGINATOR_IDLE_OR_INVALID",EngineMonotonic());
}
