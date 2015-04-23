#!/usr/bin/env python
# adaptor_a.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Written by Peter Claydon
#
BATTERY_CHECK_INTERVAL   = 10800      # How often to check battery (secs) = 3 hours
SENSOR_POLL_INTERVAL     = 600        # How often to request sensor values = 10 mins
CONNECTION_CHECK_TIME    = SENSOR_POLL_INTERVAL*3

import sys
import time
import os
import pexpect
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor
from twisted.internet import task
 
class Adaptor(CbAdaptor):
    def __init__(self, argv):
        self.status =           "ok"
        self.state =            "stopped"
        self.apps =             {"number_buttons": []}
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def setState(self, action):
        # error is only ever set from the running state, so set back to running if error is cleared
        if action == "error":
            self.state == "error"
        elif action == "clear_error":
            self.state = "running"
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def sendCharacteristic(self, characteristic, data, timeStamp):
        msg = {"id": self.id,
               "content": "characteristic",
               "characteristic": characteristic,
               "data": data,
               "timeStamp": timeStamp}
        for a in self.apps[characteristic]:
            self.sendMessage(msg, a)

    def onAppInit(self, message):
        self.cbLog("debug", "onAppInit, message: " + str(message))
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "service": [{"characteristic": "number_buttons", "interval": 0}],
                "content": "service"}
        self.sendMessage(resp, message["id"])

    def onAppRequest(self, message):
        # Switch off anything that already exists for this app
        for a in self.apps:
            if message["id"] in self.apps[a]:
                self.apps[a].remove(message["id"])
        # Now update details based on the message
        for f in message["service"]:
            if message["id"] not in self.apps[f["characteristic"]]:
                self.apps[f["characteristic"]].append(message["id"])
        self.cbLog("debug", "apps: " + str(self.apps))
        if self.state = "starting":
            self.startScan()
        self.setState("running")

    def onAppCommand(self, message):
        if "data" not in message:
            self.cbLog("warning", "app message without data: " + str(message))
        else:
            self.cbLog("warning", "This is a sensor. Message not understood: " +  str(message))

    def onConfigureMessage(self, config):
        """Config is based on what apps are to be connected.
            May be called again if there is a new configuration, which
            could be because a new app has been added.
        """
        self.setState("starting")

    def scanBT(self):
        while not self.doStop:
            try:
                index = self.hcidump.expect(['successful'])
                raw = self.gatt.after.split()
                self.cbLog("scanBT. raw: " + str(raw))
            except Exception as ex:
                self.cbLog("warning", "scanBT. Exception: " + str(type(ex)) + " " + str(ex.args))

    def startScan(self):
        try:
            self.hcidump = pexpect.spawn("sudo hcidump -i hci0")
            reactor.callInThread(self.scanBT)
            t = task.LoopingCall(self.checkStop)
            t.start(1.0)
        except Exception as ex:
            self.cbLog("warning", 'startScan. Could not launch lescan pexpect')
            self.cbLog("warning", "startScan. Exception: " + str(type(ex)) + " " + str(ex.args))

    def checkStop(self):
        if self.dostop:
            self.hcidump.kill(9)
            reactor.stop()

if __name__ == '__main__':
    Adaptor(sys.argv)
