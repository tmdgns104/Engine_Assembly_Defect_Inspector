"""PC-owned mirror; event receipt and image receipt have independent durable acknowledgements."""
import json
import uuid

from apps.edge_service.bench import atomic_write
from src.journal.sqlite import ConflictError, Journal, now, validate_key
from src.recipe.package import canonical, sha256


class Collector:
    def __init__(self, root):
        self.journal=Journal(root,producer_id='pc-collector')

    def receive_event(self, event):
        body=canonical(event)
        if len(body.encode())>8_000_000 or event.get('schema_version')!=1:
            raise ValueError('INVALID_EVENT_SCHEMA_OR_SIZE')
        for key in ('event_id','producer_id','producer_session','occurred_at','event_type'):
            if not isinstance(event.get(key),str) or not event[key] or len(event[key])>200:
                raise ValueError('INVALID_EVENT_IDENTITY')
        if type(event.get('producer_seq')) is not int or event['producer_seq']<1:
            raise ValueError('INVALID_EVENT_SEQUENCE')
        digest=sha256(body.encode()); journal=self.journal
        with journal.lock:
            existing=journal.db.execute('SELECT payload_sha256 FROM events WHERE event_id=?',(event['event_id'],)).fetchone()
            sequence=journal.db.execute('SELECT event_id FROM events WHERE producer_id=? AND producer_session=? AND producer_seq=?',
                (event['producer_id'],event['producer_session'],event['producer_seq'])).fetchone()
            if existing and existing[0]==digest:
                return {'event_id':event['event_id'],'event_ack':True,'duplicate':True,'asset_ack':False}
            if existing or sequence:
                with journal.db:
                    journal.db.execute('INSERT INTO quarantine VALUES (?,?,?,?,?)',(uuid.uuid4().hex,event['event_id'],'EVENT_CONTENT_OR_SEQUENCE_CONFLICT',body,now()))
                raise ConflictError('EVENT_CONTENT_OR_SEQUENCE_CONFLICT')
            with journal.db:
                if event['event_type'] in ('INSPECTION_COMPLETED','INSPECTION_CANCELLED'):
                    result=event['payload']; request=result['request'];validate_key(request)
                    identifier=result['inspection_id']
                    if not isinstance(identifier,str) or len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
                        raise ValueError('INVALID_INSPECTION_ID')
                    previous=journal.db.execute('SELECT result_json FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()
                    if previous:
                        raise ConflictError('IMMUTABLE_INSPECTION_CONFLICT')
                    journal.db.execute('INSERT INTO cycles(cell_id,plc_session_id,cycle_id,started_at) VALUES (?,?,?,?) ON CONFLICT(cell_id,plc_session_id,cycle_id) DO NOTHING',
                        (request['cell_id'],request['plc_session_id'],request['cycle_id'],result.get('accepted_at',event['occurred_at'])))
                    journal.db.execute("INSERT INTO inspections(inspection_id,cell_id,plc_session_id,request_id,cycle_id,attempt,fingerprint,request_json,package_json,state,decision,result_json,accepted_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (identifier,request['cell_id'],request['plc_session_id'],request['request_id'],request['cycle_id'],request['attempt'],sha256(canonical(request).encode()),canonical(request),canonical(result['package']),
                         'COMPLETE' if event['event_type']=='INSPECTION_COMPLETED' else 'CANCELLED',result['decision'],canonical(result),result.get('accepted_at',event['occurred_at']),result['completed_at']))
                    for asset in result.get('assets',[]):
                        if asset['inspection_id']!=identifier or asset['kind'] not in ('raw','overlay'):
                            raise ValueError('INVALID_ASSET_IDENTITY')
                        asset_id=asset['asset_id']
                        if len(asset_id)!=32 or any(c not in '0123456789abcdef' for c in asset_id):
                            raise ValueError('INVALID_ASSET_ID')
                        relative='assets/'+identifier+'/'+asset_id+('.png' if asset['kind']=='raw' else '.jpg')
                        journal.db.execute('INSERT INTO frame_assets(asset_id,inspection_id,kind,relative_path,sha256,width,height,bytes,capture_at,view) VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (asset_id,identifier,asset['kind'],relative,asset['sha256'],asset['width'],asset['height'],asset['bytes'],asset['capture_at'],asset['view']))
                    for defect in result.get('defects',[]):
                        journal.db.execute('INSERT INTO defects VALUES (?,?,?,?,?)',(uuid.uuid4().hex,identifier,defect['code'],defect.get('slot'),canonical(defect)))
                elif event['event_type']=='CYCLE_TERMINAL':
                    value=event['payload']
                    journal.db.execute('UPDATE cycles SET terminal=? WHERE cell_id=? AND plc_session_id=? AND cycle_id=?',
                        (value['disposition'],value['cell_id'],value['plc_session_id'],value['cycle_id']))
                    journal.db.execute('INSERT INTO dispositions VALUES (?,?,?,?,?,?)',
                        (value['disposition_id'],value['inspection_id'],value['disposition'],value['actor'],value['reason'],value['occurred_at']))
                journal.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)',
                    (event['event_id'],event['producer_id'],event['producer_session'],event['producer_seq'],event['occurred_at'],now(),event['event_type'],body,digest))
        return {'event_id':event['event_id'],'event_ack':True,'duplicate':False,'asset_ack':False}

    def receive_asset(self, identifier, data):
        if not 0<len(data)<=20_000_000:raise ValueError('ASSET_SIZE_LIMIT')
        journal=self.journal
        with journal.lock:
            row=journal.db.execute('SELECT * FROM frame_assets WHERE asset_id=?',(identifier,)).fetchone()
            if not row:raise KeyError('EVENT_NOT_RECEIVED')
            if len(data)!=row['bytes'] or sha256(data)!=row['sha256']:
                with journal.db:
                    journal.db.execute('INSERT INTO quarantine VALUES (?,?,?,?,?)',(uuid.uuid4().hex,identifier,'ASSET_CONTENT_CONFLICT',canonical({'received_sha256':sha256(data)}),now()))
                raise ConflictError('ASSET_CONTENT_CONFLICT')
            path=(journal.root/row['relative_path']).resolve()
            if not path.is_relative_to(journal.root):raise ValueError('ASSET_PATH_ESCAPE')
            if path.exists():
                if sha256(path.read_bytes())!=row['sha256']:raise ConflictError('EXISTING_ASSET_CORRUPTED')
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                atomic_write(path,data)
            with journal.db:
                journal.db.execute("UPDATE frame_assets SET sync_state='ACKED' WHERE asset_id=?",(identifier,))
        return {'asset_id':identifier,'asset_ack':True}

    def status(self):
        with self.journal.lock:
            pending=self.journal.db.execute("SELECT count(*) FROM frame_assets WHERE sync_state!='ACKED'").fetchone()[0]
            latest=self.journal.db.execute('SELECT MAX(received_at) FROM events').fetchone()[0]
        return {'metrics':self.journal.metrics(),'pending_assets':pending,'last_received_at':latest,
                'camera_or_plc_ready':'NOT_OBSERVED_BY_COLLECTOR'}
