from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

def tick():
    print(f"[worker] tick {datetime.utcnow().isoformat()}", flush=True)
    # TODO: fetch RSS -> process -> DB

def main():
    print("[worker] start", flush=True)
    sched = BlockingScheduler()
    sched.add_job(tick, "interval", minutes=5)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("[worker] stop", flush=True)
