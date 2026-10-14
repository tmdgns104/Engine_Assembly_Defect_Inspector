#include "engine_ipc.h"
/* The 4/8-byte commissioning application. Local IPC bridge; no input echo. */
#include "engine_commissioning.h"

static CommState engine_state;
static FILE *engine_event_file = NULL;
static int engine_log_failed = 0;
static double engine_last_status = -1.0;
static unsigned long engine_event_count = 0;
static unsigned long engine_timeouts = 0;
static const char *engine_status_path = NULL;
static int engine_initialized = 0;

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
    "\"raw150_hex\":\"",
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
    s->result_sequence, s->done_sequence, s->last_receive_at);
  for (unsigned int i=0; i<8; ++i) fprintf(file, "%02x", s->raw150[i]);
  fprintf(file, "\",\"raw100_hex\":\"");
  for (unsigned int i=0; i<4; ++i) fprintf(file, "%02x", s->raw100[i]);
  fprintf(file, "\",\"slots\":{\"Inspection_Request\":%u,\"EStop_OK\":%u,"
    "\"Mc_Run\":%u,\"Stop_PB\":%u},\"plc_consumption_confirmed\":false,"
    "\"inspection_bridge\":\"MODE_DEPENDENT_SEE_IPC\"}\n",
    s->words[0],s->words[1],s->words[2],s->words[3]);
}

static void EngineRecord(const CommState *s, const char *event, double now, void *context) {
  (void)context;
  if (s->config.mode==COMM_AI_RUNTIME && (strcmp(event,"CYCLIC_RX")==0 || strcmp(event,"CYCLIC_TX_ACCEPTED_BY_KERNEL")==0)) return;
  if (engine_event_file == NULL || engine_log_failed) return;
  /* Bounded trial evidence: fail closed instead of unlimited device logging. */
  if (++engine_event_count > 12000 || ftell(engine_event_file) > 16*1024*1024) {
    engine_log_failed = 1;
    return;
  }
  EngineJson(engine_event_file, s, event, now);
  if (fflush(engine_event_file) != 0 || ferror(engine_event_file)) engine_log_failed = 1;
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
  engine_status_path=getenv("ENGINE_OPENER_STATUS");
  const char *events=getenv("ENGINE_OPENER_EVENTS");
  if (events && events[0]=='/') engine_event_file=fopen(events,"wx");
  if (config.mode!=COMM_RX_ONLY && (!engine_event_file || !engine_status_path
      || engine_status_path[0]!='/' || strlen(engine_status_path)>4000)) {
    fprintf(stderr,"Synthetic trial needs new absolute evidence paths\n"); exit(EXIT_FAILURE);
  }
  CommInit(&engine_state,&config,EngineMonotonic(),EngineRecord,NULL);
}

static void WriteEngineStatus(int force) {
  double now=EngineMonotonic();
  if (!engine_status_path || engine_status_path[0]!='/' || strlen(engine_status_path)>4000) return;
  if (!force && now-engine_last_status<0.05) return;
  engine_last_status=now;
  char temporary[4096];
  snprintf(temporary,sizeof(temporary),"%s.tmp.%ld",engine_status_path,(long)getpid());
  FILE *file=fopen(temporary,"w");
  if (!file) { engine_log_failed=1; return; }
  EngineJson(file,&engine_state,"STATUS",now);
  if (fclose(file) != 0 || rename(temporary,engine_status_path) != 0) {
    engine_log_failed=1; unlink(temporary);
  }
}

static void EngineCheck(void) {
  if (engine_state.config.mode==COMM_AI_RUNTIME) EngineIpcPoll(&engine_state,EngineMonotonic());
  if (engine_log_failed) CommFault(&engine_state,"EVIDENCE_WRITE_FAILURE",EngineMonotonic());
  CommTick(&engine_state,EngineMonotonic());
}

void HandleApplication(void) {
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
