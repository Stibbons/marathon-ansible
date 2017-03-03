import os
import statistics
import time

import argh
import requests
from kazoo.client import KazooClient
from requests.packages import urllib3

urllib3.disable_warnings()
ZK_HOST = os.environ["ZK_HOST"]
zk = KazooClient(hosts=ZK_HOST)
zk.start()
MARATHON_URL, _ = zk.get("/etc/cloud/marathon_uri")
EXTERNAL_URL, _ = zk.get("/etc/cloud/nginx_external_url")
MASTER_URL = EXTERNAL_URL + "/ci_perf_buildbot/"
INFLUX_URL = EXTERNAL_URL + "/influxdb/"


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
            r = requests.get(
                url + "api/v2/forceschedulers/force", verify=False)
            print r.status_code
            if r.status_code == 200:
                return
        except:
            pass
        time.sleep(1)

def restartPgAndMaster():
    print "stopping buildbot"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True", json={"instances": 0})
    print "restarting pg"
    requests.post(MARATHON_URL + "/v2/apps/ciperf/backend/pg/restart")
    waitQuiet()
    print "restarting buildbot"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True", json={"instances": 1})
    waitQuiet()
    waitMaster()


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
        restartPgAndMaster()
    if num_masters == 0:
        return
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/buildbot?force=True", json={"instances": num_masters})
    config_kind += str(num_masters)
    waitQuiet()
    url = MASTER_URL
    print "stop workers"
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/worker?force=True", json={"instances": 0})
    waitQuiet()
    print "create {} build".format(num_builds)
    waitMaster()
    start = time.time()
    for i in xrange(num_builds):
        r = requests.post(
            url + "api/v2/forceschedulers/force",
            json={"id": 1, "jsonrpc": "2.0", "method": "force", "params": {
                "builderid": "1", "username": "", "reason": "force build",
                "project": "", "repository": "", "branch": "", "revision": "",
                "NUMLINES": str(numlines),
                "SLEEP": str(sleep)}}, verify=False)
        r.raise_for_status()
    print "create {} workers".format(num_workers)
    requests.put(MARATHON_URL + "/v2/apps/ciperf/buildbot/worker?force=True", json={"instances": num_workers})
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
