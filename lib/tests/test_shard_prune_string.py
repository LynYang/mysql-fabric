#
# Copyright (c) 2014,2015, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""Tests RANGE shard splits and also the impact of the splits
on the global server.
"""

import unittest
import uuid as _uuid
import time
import tests.utils

from mysql.fabric import executor as _executor
from mysql.fabric.server import (
    Group,
    MySQLServer,
)
from tests.utils import (
    MySQLInstances,
    fetch_test_server,
)

class TestShardingPrune(tests.utils.TestCase):
    """Contains unit tests for testing the shard split operation and for
    verifying that the global server configuration remains constant after
    the shard split configuration.
    """
    def setUp(self):
        """Creates the topology for testing.
        """
        tests.utils.cleanup_environment()
        self.manager, self.proxy = tests.utils.setup_xmlrpc()

        self.__options_1 = {
            "uuid" :  _uuid.UUID("{aa75b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(0),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server1 = MySQLServer.discover_uuid(self.__options_1["address"])
        self.__options_1["uuid"] = _uuid.UUID(uuid_server1)
        self.__server_1 = MySQLServer(**self.__options_1)
        MySQLServer.add(self.__server_1)
        self.__server_1.connect()

        self.__group_1 = Group("GROUPID1", "First description.")
        Group.add(self.__group_1)
        self.__group_1.add_server(self.__server_1)
        tests.utils.configure_decoupled_master(self.__group_1, self.__server_1)

        self.__options_2 = {
            "uuid" :  _uuid.UUID("{aa45b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(1),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server2 = MySQLServer.discover_uuid(self.__options_2["address"])
        self.__options_2["uuid"] = _uuid.UUID(uuid_server2)
        self.__server_2 = MySQLServer(**self.__options_2)
        MySQLServer.add(self.__server_2)
        self.__server_2.connect()
        self.__server_2.exec_stmt("DROP DATABASE IF EXISTS db1")
        self.__server_2.exec_stmt("CREATE DATABASE db1")
        self.__server_2.exec_stmt("CREATE TABLE db1.t1"
                                  "(userID VARCHAR(20) PRIMARY KEY, name VARCHAR(30))")
        for i in range(1, 71):
            self.__server_2.exec_stmt("INSERT INTO db1.t1 "
                                  "VALUES('%s', 'TEST %s')" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_2.exec_stmt("INSERT INTO db1.t1 "
                                  "VALUES('%s', 'TEST %s')" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_2.exec_stmt("INSERT INTO db1.t1 "
                                  "VALUES('%s', 'TEST %s')" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_2.exec_stmt("INSERT INTO db1.t1 "
                                  "VALUES('%s', 'TEST %s')" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_2.exec_stmt("INSERT INTO db1.t1 "
                                  "VALUES('%s', 'TEST %s')" % ("e"+str(i), i))
        self.__server_2.exec_stmt("DROP DATABASE IF EXISTS db2")
        self.__server_2.exec_stmt("CREATE DATABASE db2")
        self.__server_2.exec_stmt("CREATE TABLE db2.t2"
                                  "(userID VARCHAR(20), salary INT, "
                                  "CONSTRAINT FOREIGN KEY(userID) "
                                  "REFERENCES db1.t1(userID))")
        for i in range(1, 71):
            self.__server_2.exec_stmt("INSERT INTO db2.t2 "
                                  "VALUES('%s', %s)" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_2.exec_stmt("INSERT INTO db2.t2 "
                                  "VALUES('%s', %s)" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_2.exec_stmt("INSERT INTO db2.t2 "
                                  "VALUES('%s', %s)" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_2.exec_stmt("INSERT INTO db2.t2 "
                                  "VALUES('%s', %s)" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_2.exec_stmt("INSERT INTO db2.t2 "
                                  "VALUES('%s', %s)" % ("e"+str(i), i))


        self.__group_2 = Group("GROUPID2", "Second description.")
        Group.add(self.__group_2)
        self.__group_2.add_server(self.__server_2)
        tests.utils.configure_decoupled_master(self.__group_2, self.__server_2)

        self.__options_3 = {
            "uuid" :  _uuid.UUID("{bb75b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(2),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server3 = MySQLServer.discover_uuid(self.__options_3["address"])
        self.__options_3["uuid"] = _uuid.UUID(uuid_server3)
        self.__server_3 = MySQLServer(**self.__options_3)
        MySQLServer.add( self.__server_3)
        self.__server_3.connect()
        self.__server_3.exec_stmt("DROP DATABASE IF EXISTS db1")
        self.__server_3.exec_stmt("CREATE DATABASE db1")
        self.__server_3.exec_stmt("CREATE TABLE db1.t1"
                                  "(userID VARCHAR(20)PRIMARY KEY, name VARCHAR(30))")
        for i in range(1, 71):
            self.__server_3.exec_stmt("INSERT INTO db1.t1 "
                                "VALUES('%s', 'TEST %s')" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_3.exec_stmt("INSERT INTO db1.t1 "
                                "VALUES('%s', 'TEST %s')" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_3.exec_stmt("INSERT INTO db1.t1 "
                                "VALUES('%s', 'TEST %s')" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_3.exec_stmt("INSERT INTO db1.t1 "
                                "VALUES('%s', 'TEST %s')" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_3.exec_stmt("INSERT INTO db1.t1 "
                                "VALUES('%s', 'TEST %s')" % ("e"+str(i), i))
        self.__server_3.exec_stmt("DROP DATABASE IF EXISTS db2")
        self.__server_3.exec_stmt("CREATE DATABASE db2")
        self.__server_3.exec_stmt("CREATE TABLE db2.t2"
                                  "(userID VARCHAR(20), salary INT, "
                                  "CONSTRAINT FOREIGN KEY(userID) "
                                  "REFERENCES db1.t1(userID))")
        for i in range(1, 71):
            self.__server_3.exec_stmt("INSERT INTO db2.t2 "
                                "VALUES('%s', %s)" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_3.exec_stmt("INSERT INTO db2.t2 "
                                "VALUES('%s', %s)" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_3.exec_stmt("INSERT INTO db2.t2 "
                                "VALUES('%s', %s)" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_3.exec_stmt("INSERT INTO db2.t2 "
                                "VALUES('%s', %s)" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_3.exec_stmt("INSERT INTO db2.t2 "
                                "VALUES('%s', %s)" % ("e"+str(i), i))

        self.__group_3 = Group("GROUPID3", "Third description.")
        Group.add( self.__group_3)
        self.__group_3.add_server(self.__server_3)
        tests.utils.configure_decoupled_master(self.__group_3, self.__server_3)

        self.__options_4 = {
            "uuid" :  _uuid.UUID("{bb45b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(3),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server4 = MySQLServer.discover_uuid(self.__options_4["address"])
        self.__options_4["uuid"] = _uuid.UUID(uuid_server4)
        self.__server_4 = MySQLServer(**self.__options_4)
        MySQLServer.add(self.__server_4)
        self.__server_4.connect()
        self.__server_4.exec_stmt("DROP DATABASE IF EXISTS db1")
        self.__server_4.exec_stmt("CREATE DATABASE db1")
        self.__server_4.exec_stmt("CREATE TABLE db1.t1"
                                  "(userID VARCHAR(20)PRIMARY KEY, name VARCHAR(30))")
        for i in range(1, 71):
            self.__server_4.exec_stmt("INSERT INTO db1.t1 "
                    "VALUES('%s', 'TEST %s')" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_4.exec_stmt("INSERT INTO db1.t1 "
                    "VALUES('%s', 'TEST %s')" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_4.exec_stmt("INSERT INTO db1.t1 "
                    "VALUES('%s', 'TEST %s')" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_4.exec_stmt("INSERT INTO db1.t1 "
                    "VALUES('%s', 'TEST %s')" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_4.exec_stmt("INSERT INTO db1.t1 "
                    "VALUES('%s', 'TEST %s')" % ("e"+str(i), i))
        self.__server_4.exec_stmt("DROP DATABASE IF EXISTS db2")
        self.__server_4.exec_stmt("CREATE DATABASE db2")
        self.__server_4.exec_stmt("CREATE TABLE db2.t2"
                                  "(userID VARCHAR(20), salary INT, "
                                  "CONSTRAINT FOREIGN KEY(userID) "
                                  "REFERENCES db1.t1(userID))")
        for i in range(1, 71):
            self.__server_4.exec_stmt("INSERT INTO db2.t2 "
                        "VALUES('%s', %s)" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_4.exec_stmt("INSERT INTO db2.t2 "
                        "VALUES('%s', %s)" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_4.exec_stmt("INSERT INTO db2.t2 "
                        "VALUES('%s', %s)" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_4.exec_stmt("INSERT INTO db2.t2 "
                        "VALUES('%s', %s)" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_4.exec_stmt("INSERT INTO db2.t2 "
                        "VALUES('%s', %s)" % ("e"+str(i), i))

        self.__group_4 = Group("GROUPID4", "Fourth description.")
        Group.add( self.__group_4)
        self.__group_4.add_server(self.__server_4)
        tests.utils.configure_decoupled_master(self.__group_4, self.__server_4)

        self.__options_5 = {
            "uuid" :  _uuid.UUID("{cc75b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(4),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server5 = MySQLServer.discover_uuid(self.__options_5["address"])
        self.__options_5["uuid"] = _uuid.UUID(uuid_server5)
        self.__server_5 = MySQLServer(**self.__options_5)
        MySQLServer.add(self.__server_5)
        self.__server_5.connect()
        self.__server_5.exec_stmt("DROP DATABASE IF EXISTS db1")
        self.__server_5.exec_stmt("CREATE DATABASE db1")
        self.__server_5.exec_stmt("CREATE TABLE db1.t1"
                                  "(userID VARCHAR(20)PRIMARY KEY, name VARCHAR(30))")
        for i in range(1, 71):
            self.__server_5.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_5.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_5.exec_stmt("INSERT INTO db1.t1 "
                            "VALUES('%s', 'TEST %s')" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_5.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_5.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("e"+str(i), i))
        self.__server_5.exec_stmt("DROP DATABASE IF EXISTS db2")
        self.__server_5.exec_stmt("CREATE DATABASE db2")
        self.__server_5.exec_stmt("CREATE TABLE db2.t2"
                                  "(userID VARCHAR(20), salary INT, "
                                  "CONSTRAINT FOREIGN KEY(userID) "
                                  "REFERENCES db1.t1(userID))")
        for i in range(1, 71):
            self.__server_5.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_5.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_5.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_5.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_5.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("e"+str(i), i))


        self.__group_5 = Group("GROUPID5", "Fifth description.")
        Group.add( self.__group_5)
        self.__group_5.add_server(self.__server_5)
        tests.utils.configure_decoupled_master(self.__group_5, self.__server_5)

        self.__options_6 = {
            "uuid" :  _uuid.UUID("{cc45b12b-98d1-414c-96af-9e9d4b179678}"),
            "address"  : MySQLInstances().get_address(5),
            "user" : MySQLInstances().user,
            "passwd": MySQLInstances().passwd,
        }

        uuid_server6 = MySQLServer.discover_uuid(self.__options_6["address"])
        self.__options_6["uuid"] = _uuid.UUID(uuid_server6)
        self.__server_6 = MySQLServer(**self.__options_6)
        MySQLServer.add(self.__server_6)
        self.__server_6.connect()
        self.__server_6.exec_stmt("DROP DATABASE IF EXISTS db1")
        self.__server_6.exec_stmt("CREATE DATABASE db1")
        self.__server_6.exec_stmt("CREATE TABLE db1.t1"
                                  "(userID VARCHAR(20)PRIMARY KEY, name VARCHAR(30))")
        for i in range(1, 71):
            self.__server_6.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_6.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_6.exec_stmt("INSERT INTO db1.t1 "
                            "VALUES('%s', 'TEST %s')" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_6.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_6.exec_stmt("INSERT INTO db1.t1 "
                        "VALUES('%s', 'TEST %s')" % ("e"+str(i), i))
        self.__server_6.exec_stmt("DROP DATABASE IF EXISTS db2")
        self.__server_6.exec_stmt("CREATE DATABASE db2")
        self.__server_6.exec_stmt("CREATE TABLE db2.t2"
                                  "(userID VARCHAR(20), salary INT, "
                                  "CONSTRAINT FOREIGN KEY(userID) "
                                  "REFERENCES db1.t1(userID))")
        for i in range(1, 71):
            self.__server_6.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("a"+str(i), i))
        for i in range(101, 401):
            self.__server_6.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("b"+str(i), i))
        for i in range(1001, 1201):
            self.__server_6.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("c"+str(i), i))
        for i in range(10001, 10601):
            self.__server_6.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("d"+str(i), i))
        for i in range(100001, 100801):
            self.__server_6.exec_stmt("INSERT INTO db2.t2 "
                      "VALUES('%s', %s)" % ("e"+str(i), i))

        self.__group_6 = Group("GROUPID6", "Sixth description.")
        Group.add( self.__group_6)
        self.__group_6.add_server(self.__server_6)
        tests.utils.configure_decoupled_master(self.__group_6, self.__server_6)

        status = self.proxy.sharding.create_definition("RANGE_STRING", "GROUPID1")
        self.check_xmlrpc_command_result(status, returns=1)

        status = self.proxy.sharding.add_table(1, "db1.t1", "userID")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.add_table(1, "db2.t2", "userID")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.add_shard(
            1,
            "GROUPID2/a,GROUPID3/b,GROUPID4/c,GROUPID5/d,GROUPID6/e",
            "ENABLED"
        )
        self.check_xmlrpc_command_result(status)

    def test_prune_shard(self):
        status = self.proxy.sharding.prune_shard("db1.t1")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.lookup_servers("db1.t1", "a3",  "LOCAL")
        for info in self.check_xmlrpc_iter(status):
            if info['status'] == MySQLServer.PRIMARY:
                shard_server = fetch_test_server(info['server_uuid'])
                shard_server.connect()
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db1.t1", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 70)

        status = self.proxy.sharding.prune_shard("db1.t1")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.lookup_servers("db1.t1", "b12",  "LOCAL")
        for info in self.check_xmlrpc_iter(status):
            if info['status'] == MySQLServer.PRIMARY:
                shard_server = fetch_test_server(info['server_uuid'])
                shard_server.connect()
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db1.t1", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 300)
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db2.t2", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 300)

        status = self.proxy.sharding.prune_shard("db1.t1")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.lookup_servers("db1.t1", "c35",  "LOCAL")
        for info in self.check_xmlrpc_iter(status):
            if info['status'] == MySQLServer.PRIMARY:
                shard_server = fetch_test_server(info['server_uuid'])
                shard_server.connect()
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db1.t1", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 200)
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db2.t2", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 200)

        status = self.proxy.sharding.prune_shard("db1.t1")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.lookup_servers("db1.t1", "d21",  "LOCAL")
        for info in self.check_xmlrpc_iter(status):
            if info['status'] == MySQLServer.PRIMARY:
                shard_server = fetch_test_server(info['server_uuid'])
                shard_server.connect()
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db1.t1", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 600)
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db2.t2", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 600)

        status = self.proxy.sharding.prune_shard("db1.t1")
        self.check_xmlrpc_command_result(status)

        status = self.proxy.sharding.lookup_servers("db1.t1", "e31",  "LOCAL")
        for info in self.check_xmlrpc_iter(status):
            if info['status'] == MySQLServer.PRIMARY:
                shard_server = fetch_test_server(info['server_uuid'])
                shard_server.connect()
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db1.t1", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 800)
                rows = shard_server.exec_stmt(
                    "SELECT COUNT(*) FROM db2.t2", {"fetch" : True}
                )
                self.assertTrue(int(rows[0][0]) == 800)

    def tearDown(self):
        """Clean up the existing environment
        """
        tests.utils.cleanup_environment()
