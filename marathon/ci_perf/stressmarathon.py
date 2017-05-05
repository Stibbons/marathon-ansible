import os
import statistics
import time

import argh
import requests
from kazoo.client import KazooClient
from requests.packages import urllib3
from multiprocessing.dummy import Pool as ThreadPool

urllib3.disable_warnings()
ZK_HOST = os.environ["ZK_HOST"]
zk = KazooClient(hosts=ZK_HOST)
zk.start()
MARATHON_URL, _ = zk.get("/etc/cloud/marathon_uri")
EXTERNAL_URL, _ = zk.get("/etc/cloud/nginx_external_url")
MASTER_URL = EXTERNAL_URL + "/ci_perf_buildbot/"
INFLUX_URL = EXTERNAL_URL + "/influxdb/"

MAX_WORKERS = 241
MAX_WORKERS_CONTAINERS = 15


def waitQuiet():
    while True:
        r = requests.get(MARATHON_URL + "/v2/deployments")
        j = r.json()
        if len(j) == 0:
            break
        affectedApps = set()
        for app in j:
            affectedApps.update(set(app['affectedApps']))
        time.sleep(1)


def waitMaster():
    print "waiting buildbot booted"
    while True:
        url = MASTER_URL
        try:
            r = requests.get(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot")
            state = r.json()['app']
            if state['tasksHealty'] != state['instances']:
                continue
        except:
            continue
        try:
            r = requests.get(
                url + "api/v2/forceschedulers/force", verify=False)
            print "forcescheduler API status_code: ", r.status_code, "\r"
            if r.status_code == 200:
                return
        except:
            pass
        time.sleep(1)


def waitAllConnected():
    print "waiting all workers connected"
    while True:
        url = MASTER_URL
        try:
            r = requests.get(
                url + "api/v2/workers?field=name&field=connected_to", verify=False)
            if r.status_code == 200:
                workers = [worker for worker in r.json()['workers'] if len(worker['connected_to']) > 0]
                print "connected workers: ", len(workers), '\r'
                if len(workers) >= MAX_WORKERS:
                    return
            else:
                print "worker list API status_code: ", r.status_code, r.content, '\r'
        except Exception as e:
            print e
            pass
        time.sleep(1)


def restartPgAndMaster(num_masters):
    print "stopping buildbot and workers"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/worker?force=True", json={"instances": 0})
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True", json={"instances": 0})
    print "restarting pg"
    requests.post(MARATHON_URL + "/v2/apps/ciperf/backend/pg/restart")
    waitQuiet()
    zk.delete("/workers", recursive=True)
    print "restarting buildbot"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True", json={"instances": 1})
    waitQuiet()
    waitMaster()
    print "scaling buildbot"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True",
                 json={"instances": num_masters})
    waitQuiet()
    waitMaster()
    print "scaling workers"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/worker?force=True",
                 json={"instances": MAX_WORKERS_CONTAINERS})
    waitAllConnected()


def sendCollectd(datas):
    message = ""
    for name, value in datas:
        message += 'ciperf {}={} {}\n'.format(
            name, value, int(time.time()))
    requests.post(INFLUX_URL + "/write?db=mydb", data=message, verify=False)


@argh.arg('num_builds', type=int)
@argh.arg('num_workers', type=int)
@argh.arg('num_masters', type=int)
def main(num_builds, num_workers, num_masters, config_kind, numlines, sleep, firstRestart=False):
    if firstRestart:
        restartPgAndMaster(num_masters)
    if num_masters == 0:
        return
    config_kind += str(num_masters)
    waitQuiet()
    url = MASTER_URL
    waitMaster()
    print "create {} build".format(num_builds)
    start = time.time()
    pool = ThreadPool(num_builds)
    session = requests.Session()

    def start_build(x):
        r = session.post(
            url + "api/v2/forceschedulers/force",
            json={"id": 1, "jsonrpc": "2.0", "method": "force", "params": {
                "builderNames": ['runtests' + str(num_workers)], "username": "", "reason": "force build",
                "project": "", "repository": "", "branch": "", "revision": "",
                "NUMLINES": str(numlines),
                "SLEEP": str(sleep)}}, verify=False)
        r.raise_for_status()
        print "force result: ", r.status_code, r.content, '\r'
    pool.map(start_build, range(num_builds))
    finished = False
    builds = []
    latencies = []
    while not finished:
        t1 = time.time()
        try:
            r = requests.get(url + "api/v2/buildrequests?complete=0", verify=False)
            r.raise_for_status()
        except Exception as e:
            time.sleep(1)
            print e
            continue
        brs = r.json()['buildrequests']
        t2 = time.time()
        try:
            r = requests.get(url + "api/v2/builds?complete=0", verify=False)
            r.raise_for_status()
        except Exception as e:
            time.sleep(1)
            print e
            continue
        builds.append(len(r.json()['builds']))
        latencies.append(t2 - t1)
        sendCollectd([
            ("concurrent_builds", builds[-1]),
            ("pending_buildrequests", len(brs)),
            ("www_latency", t2 - t1),
            ("num_workers", num_workers),
            ("numlines", numlines),
            ("sleep", sleep)
        ])
        print len(brs), t2 - t1, builds[-1], "\r",
        finished = not brs
        time.sleep(0.4)
        end = time.time()
        if end - start > 1000:
            finished = True  # timeout
            sendCollectd([("restarted", 1)])
            restartPgAndMaster()
        try:
            requests.delete(MARATHON_URL + "/v2/queue//ciperf/buildbot/worker/delay")
        except:
            pass
    print "finished in ", end - start
    requests.post("http://events.buildbot.net/events/ci_perfs", json=dict(
        config_kind=config_kind, num_builds=num_builds, num_workers=num_workers,
        numlines=numlines, sleep=sleep, time=end - start,
        mean_builds=statistics.mean(builds), mean_latencies=statistics.mean(latencies),
        pstdev_builds=statistics.pstdev(builds), pstdev_latencies=statistics.pstdev(latencies)))


argh.dispatch_command(main)
