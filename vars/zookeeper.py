# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2014, Serge van Ginderachter <serge@vanginderachter.be>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import, division, print_function

import os
import posixpath
import urlparse

import ansible.template
from ansible.vars import unsafe_proxy
from kazoo.client import KazooClient

__metaclass__ = type

class ZkConfAccessor(unsafe_proxy.AnsibleUnsafe):
    def __init__(self, zookeeper_uri=None, zk=None, basepath=None):
        """Configuration accessor from zookeeper.
        We load the zookeper values lazily
        """
        if zookeeper_uri is not None:
            if not zookeeper_uri.startswith("zk://"):
                raise ValueError("zookeeper_uri needs to be a zk:// uri")
            path = urlparse.urlparse(zookeeper_uri)
            hosts = path.netloc
            self.basepath = path.path
            self.zk = KazooClient(hosts=hosts)
            self.zk.start()
        else:
            self.zk = zk
            self.basepath = basepath

        self._attributes = self.zk.get_children(self.basepath)
        self.zk.stop()

    def __getattr__(self, name):
        path = posixpath.join(self.basepath, name)
        self.zk.start()
        value, metadata = self.zk.get(path)
        if metadata.numChildren > 0 :
            return ZkConfAccessor(zk=self.zk, basepath = path)
        else:
            self.zk.stop()
            return value

    __getitem__ = __getattr__

class VarsModule(object):

    """
    Loads variables for groups and/or hosts
    """

    def __init__(self, inventory):

        """ constructor """
        self.inventory = inventory
        self.inventory_basedir = inventory.basedir()


    def run(self, host, vault_password=None):
        """ For backwards compatibility, when only vars per host were retrieved
            This method should return both host specific vars as well as vars
            calculated from groups it is a member of """
        return {}


    def get_host_vars(self, host, vault_password=None):
        """ Get host specific variables. """
        return {'zk': ZkConfAccessor('zk://' + os.environ['ZK_HOST'] + '/etc')}


    def get_group_vars(self, group, vault_password=None):
        """ Get group specific variables. """
        return {}
