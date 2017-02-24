import os
import urlparse

import requests


def proxies_from_env(ret):
    for env in ['http_proxy', 'https_proxy', 'no_proxy', 'ALL_PROXY']:
        if env in os.environ:
            ret[env] = os.environ[env]
    return ret


def zkhttp_discover(marathon_url):
    if not marathon_url.endswith("/"):
        marathon_url += "/"
    ret = requests.get(marathon_url + "v2/apps//core/lb/zkhttp")
    if ret.status_code == 200:
        for task in ret.json()['app']['tasks']:
            return "http://%s:%s/" % (task['host'], task['ports'][0])
    return ""


def host_from_url(ret):
    parsed = urlparse.urlparse(ret)
    return parsed.netloc.split(":")[0]


class FilterModule(object):
    """
    Specific filters
    """

    def filters(self):
        return {
            'proxies_from_env': proxies_from_env,
            'host_from_url': host_from_url,
            'zk_http_discover': zkhttp_discover
        }
