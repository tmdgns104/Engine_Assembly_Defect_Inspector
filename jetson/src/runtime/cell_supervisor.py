"""제품 결과와 셀 준비 상태를 분리하는 상위 정책. Tracking 내부는 변경하지 않는다."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging


@dataclass(frozen=True)
class FaultPolicy:
    """생산 한도는 미설정. 자동 retry는 없고 명시적 요청당 시도는 한 번이다."""
    consecutive_error_limit: int | None = None
    recovery_attempt_limit: int | None = None

    def __post_init__(self):
        for value in (self.consecutive_error_limit,self.recovery_attempt_limit):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError('복구 정책 한도는 양의 정수 또는 null이어야 합니다')


class CellSupervisor:
    def __init__(self, service, plc, policy=None):
        self.service, self.plc = service, plc
        self.policy = policy or FaultPolicy()
        self.cycle_error = None
        self.alarm = None
        self.last_cycle = None
        self.error_counts = {}
        self.recovery_attempts = 0
        self.recovery_evidence_ids = set()
        self.logger = logging.getLogger(__name__)

    def audit(self, event, context, **details):
        payload = dict(context,timestamp=datetime.now(timezone.utc).isoformat(),**details)
        self.logger.warning(json.dumps(dict(event=event,**payload),ensure_ascii=False))
        try:
            with self.service.lock,self.service.journal.lock,self.service.journal.db:
                self.service.journal._event(event,payload)
        except Exception:
            self.alarm = 'JOURNAL_UNAVAILABLE'
            self.logger.exception('복구/처분 audit 저장 실패; NOT_READY 유지')
            raise
        return payload

    def disposition(self, context, decision, reason, recovery_action='NONE'):
        disposition = self.plc.disposition_for(decision)
        payload = self.audit('CELL_DISPOSITION_REQUESTED',context,decision=decision,reason=reason,
            runtime_state='DEGRADED' if decision=='ERROR' else 'RUNNING',
            recovery_action=recovery_action,plc_disposition=disposition)
        self.plc.publish_result(payload)

    def fault(self, context, code, reason, subsystem):
        if self.cycle_error is not None:
            return
        self.cycle_error = dict(code=code,reason=str(reason),subsystem=subsystem)
        self.error_counts[subsystem] = self.error_counts.get(subsystem,0)+1
        limit = self.policy.consecutive_error_limit
        if limit is not None and self.error_counts[subsystem] >= limit:
            self.alarm = 'ERROR_LIMIT: '+subsystem
        self.audit('CELL_CYCLE_ERROR',context,decision='ERROR',error_code=code,reason=str(reason),
            runtime_state='NOT_READY' if self.alarm else 'DEGRADED',
            recovery_action='WAIT_EXPLICIT_CLEARANCE',plc_disposition='ERROR')
        self.disposition(context,'ERROR',str(reason),'WAIT_EXPLICIT_CLEARANCE')

    def finish(self, context, decision, state):
        self.last_cycle = dict(context,decision=decision,state=state)
        if decision != 'ERROR':
            self.error_counts.clear()
        self.cycle_error = None

    def status(self):
        return {'cycle_error':deepcopy(self.cycle_error),'alarm':self.alarm,
            'last_cycle':deepcopy(self.last_cycle),'consecutive_errors':dict(self.error_counts),
            'policy':{'consecutive_error_limit':self.policy.consecutive_error_limit,
                'recovery_attempt_limit':self.policy.recovery_attempt_limit,'automatic_retries':0},
            'recovery_attempts':self.recovery_attempts,'physical_safety_authority':'PLC_OR_SAFETY_HARDWARE'}
