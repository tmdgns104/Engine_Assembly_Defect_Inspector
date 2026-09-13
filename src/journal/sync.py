"""Bounded retry sender. Never share an SQLite file or equate JSON ACK with asset ACK."""
import json
import threading
import urllib.request

from src.journal.sqlite import now


class OutboxSender:
    def __init__(self,journal,url,token):
        if not url.startswith('http://127.0.0.1:'):raise ValueError('Use explicit loopback SSH tunnel')
        self.journal,self.url,self.token=journal,url.rstrip('/'),token
        self.stopping=threading.Event();self.error=None;self.last_success=None
        self.thread=threading.Thread(target=self.run,daemon=True)

    def post(self,path,data,content_type):
        request=urllib.request.Request(self.url+path,data=data,headers={'Content-Type':content_type,'X-Collector-Token':self.token})
        with urllib.request.urlopen(request,timeout=3) as response:return json.load(response)

    def once(self):
        journal=self.journal
        with journal.lock:
            events=journal.db.execute("SELECT events.event_id,payload_json FROM events JOIN outbox USING(event_id) WHERE state!='ACKED' ORDER BY occurred_at,producer_seq LIMIT 10").fetchall()
        for event in events:
            if self.stopping.is_set():return
            try:
                ack=self.post('/internal/v1/events',event['payload_json'].encode(),'application/json')
                if ack.get('event_id')!=event['event_id'] or ack.get('event_ack') is not True:raise ValueError('INVALID_EVENT_ACK')
                with journal.lock,journal.db:
                    journal.db.execute("UPDATE outbox SET state='ACKED',attempts=attempts+1,acknowledged_at=?,last_error=NULL WHERE event_id=?",(now(),event['event_id']))
            except Exception as error:
                with journal.lock,journal.db:
                    journal.db.execute('UPDATE outbox SET attempts=attempts+1,last_error=? WHERE event_id=?',(str(error)[:1000],event['event_id']))
                raise
        with journal.lock:
            assets=journal.db.execute("SELECT asset_id FROM frame_assets WHERE sync_state!='ACKED' LIMIT 20").fetchall()
        for row in assets:
            if self.stopping.is_set():return
            metadata,data=journal.asset(row['asset_id'])
            ack=self.post('/internal/v1/assets/'+row['asset_id'],data,'application/octet-stream')
            if ack.get('asset_id')!=row['asset_id'] or ack.get('asset_ack') is not True:raise ValueError('INVALID_ASSET_ACK')
            with journal.lock,journal.db:
                journal.db.execute("UPDATE frame_assets SET sync_state='ACKED' WHERE asset_id=?",(row['asset_id'],))
        self.last_success=now();self.error=None

    def run(self):
        delay=1
        while not self.stopping.is_set():
            try:self.once();delay=1
            except Exception as error:self.error=str(error)[:1000];delay=min(delay*2,60)
            self.stopping.wait(delay)

    def start(self):self.thread.start()
    def close(self):
        self.stopping.set();self.thread.join(5)
        if self.thread.is_alive():raise RuntimeError('PC_SENDER_STOP_PENDING')
