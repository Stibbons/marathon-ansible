import os
import urlparse

from kazoo.client import KazooClient



def conf_from_zkpath(zookeeper_uri, path):
    data = {}
    zk = KazooClient(hosts=zookeeper_uri)
    zk.start()
    def get_fs(path):
        root = path
        for child in zk.get_children(root):
            cwd = os.path.join(root, child)
            if len(zk.get_children(cwd)) > 0 :
                get_fs(path=cwd)
            else:
                data[child] = zk.get(cwd)[0]
    get_fs(path)
    return data

class FilterModule(object):
    """
    Specific filters
    """

    def filters(self):
        return {
            'conf_from_zkpath': conf_from_zkpath
        }
