#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# SleepyBed IQ Plugin
#   by Nathan Sheldon
#
# Sleepyq library code by Josh Nichols (https://github.com/technicalpickles),
# Philip Dorr (https://github.com/tagno25), et al. under MIT open licence.
#
# Version 1.2.1
#
# See the "VERSION_HISTORY.txt" file in the same location as this plugin.py
# file for a complete version change history.
#
################################################################################

import logging
import requests

from sleepyq import Sleepyq

################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    # Loading and Starting Methods
    ########################################

    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)
        
        self.logLevel = int(pluginPrefs.get("logLevel", logging.INFO))
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(f"logLevel = {self.logLevel}")

        self.username = pluginPrefs.get('username', "")
        self.password = pluginPrefs.get('password', "")
        self.lastError = ""  # String of last error message shown in log.
        self.bedsList = []  # List of beds associated with the SleepIQ account.
        self.sleepersList = []  # List of sleepers registered in the SleepIQ account.

        self.connection = None

    # Creates a Sleepyq object with the SleepIQ account information.

    # Startup
    ########################################
    def startup(self):
        self.logger.debug("startup called")

        # Attempt to connect to the SleepIQ service.
        try:
            self.connection = Sleepyq(self.username, self.password)
            connected = self.connection.login()
            if not connected:
                self.logger.error("Unable to connect to the SleepIQ service with the provided username and password.  \
                Please verify the username and password settings in the SleepyBed IQ configuration.")
                return False
        except Exception as e:
            self.logger.error(f"Unable to connect to the SleepIQ service. Error: {e}")
            return False

        # Everything went fine.
        return True

    # Shutdown
    ########################################
    def shutdown(self):
        self.logger.debug("shutdown called")

    # Start Devices
    ########################################
    def deviceStartComm(self, device):
        self.logger.debug(f"Starting device: {device.name}")
        # Clear any device error states first.
        device.setErrorStateOnServer("")
        # Reload the device states list.
        device.stateListOrDisplayStateIdChanged()

    # Stop Devices
    ########################################
    def deviceStopComm(self, device):
        self.logger.debug(f"Stopping device: {device.name}")

    ########################################
    # Standard Plugin Methods
    ########################################

    # Run Concurrent Thread
    ########################################
    def runConcurrentThread(self):
        self.logger.debug("Starting runConcurrentThread.")

        # Set a counter variable to control how often repeated error messages appear.
        loopCount = 0

        try:
            while True:

                # Populate the beds list, including sleeper status.
                try:
                    self.logger.debug("runConcurrentThread: Updating beds and sleepers list.")
                    self.bedsList = self.connection.beds_with_sleeper_status()
                    if len(self.bedsList) == 0:
                        errorText = "There are no beds associated with this SleepIQ account. This plugin only works with beds that are registered with the SleepIQ service."
                        # Only display the error if it wasn't recently shown.
                        if self.lastError != errorText:
                            self.lastError = errorText
                            self.logger.error(errorerrorText)
                except Exception as e:
                    # Detect authentication/session login errors.
                    if str(e).startswith("401 Client Error"):
                        # Attempt to re-connect to the SleepIQ service.
                        try:
                            connected = self.connection.login()
                            if not connected:
                                errorText = u"Unable to connect to the SleepIQ service with the provided username and password.  \
                                Please verify the username and password settings in the SleepyBed IQ configuration."
                                # Only display the error if it wasn't recently shown.
                                if self.lastError != errorText:
                                    self.lastError = errorText
                                    self.logger.error(errorText)
                            # End if last error is not the same as this error.
                        # End if not connected.
                        except Exception as e:
                            # If we still get an authentication error, let the user know.
                            if str(e).startswith("401 Client Error"):
                                errorText = "Unable to connect to the SleepIQ service with the provided username and password.  \
                                Please verify the username and password settings in the SleepyBed IQ configuration."
                                # Only display the error if it wasn't recently shown.
                                if self.lastError != errorText:
                                    self.lastError = errorText
                                    self.logger.error(errorText)
                            # End if last error is not the same as this error.
                            else:
                                errorText = f"Unable to connect to the SleepIQ service. Error: {e}"
                                # Only display the error if it wasn't recently shown.
                                if self.lastError != errorText:
                                    self.lastError = errorText
                                    self.logger.error(errorText)
                            # End if last error is not the same as this error.
                        # End if this was a client authentication error.
                    # End try to connect.
                    else:
                        errorText = f"Unable to load the list of beds associated with this SleepIQ account. Error: {e}"
                        # Only display the error if it wasn't recently shown.
                        if self.lastError != errorText:
                            self.lastError = errorText
                            self.logger.error(errorText)
                    # End if the last error is no the same as this error.
                # End if the original bed refresh resulted in a client auth error.
                # End try to refresh bed and sleeper status.

                # Parse the Bed data.
                self.parseBedData()

                # Increment the loop counter.
                loopCount += 1

                # Reset the loop counter every 19 loops (10 minutes) and clear the saved errors.
                if loopCount > 19:
                    self.logger.debug("runConcurrentThread: 10 minutes have passed. Resetting error conditions (if any).")
                    loopCount = 0
                    self.lastError = ""

                # Sleep for 30 seconds before looping again.
                self.sleep(30)

        # End while True continuous loop.
        except self.StopThread:
            pass  # Optionally catch the StopThread exception and do any needed cleanup.

    ########################################
    # Standard Plugin Callback Methods
    ########################################

    # Validate Device Configuration
    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.logger.debug(f"validateDeviceConfigUi called: typeId: {typeId}  devId: {devId} valuesDict:\n{valuesDict}")
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        isError = False

        # Check values based on device type ID.
        if typeId == "sleepNumberBed":
            # Make sure a bed was selected.
            if valuesDict.get('bedId', "") == "":
                isError = True
                errorsDict['bedId'] = "Please select a SleepNumber Bed to monitor."
                errorsDict['showAlertText'] += errorsDict['bedId']
                return False, valuesDict, errorsDict

        return True, valuesDict

    # Validate Preferences Configuration.
    ########################################
    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(f"validatePrefsConfigUi called: valuesDict:\n{valuesDict}")
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        # Reset the "accountVerified" valuesDict property to hide the "FAILED" or "VERIFIED" label in the UI.
        valuesDict['accountVerified'] = "unknown"

        # Set up a local Sleepyq object with the passed username and password for account validation.
        username = valuesDict.get('username', "")
        password = valuesDict.get('password', "")
        connection = Sleepyq(username, password)

        # Validate the username field.
        if valuesDict.get('username', "") == "":
            # The field was left blank.
            self.logger.debug(f"username \"{valuesDict['username']}\" is blank.")
            isError = True
            errorsDict[
                'username'] = "The 'SleepIQ Username/Email' field is blank. Please enter the username or email address you use to login to the SleepIQ web site."
            errorsDict['showAlertText'] += errorsDict['username'] + u"\n\n"

        else:
            # The field wasn't blank. Check to see if the format is valid.
            try:
                # Do this later.
                self.logger.debug(f"Checking username format '{valuesDict['username']}'.")

            except Exception as e:
                # Username format was invalid.
                self.logger.debug("Username format is invalid.")
                isError = True
                errorsDict['username'] = "The username is not valid. Please enter a valid username or email address."
                errorsDict['showAlertText'] += errorsDict['username'] + "\n\n"

        # Validate the password field.
        if valuesDict.get('password', "") == "":
            # The field was left blank.
            self.logger.debug(f"password '{valuesDict['password']}' is blank.")
            isError = True
            errorsDict['password'] = "The 'SleepIQ Password' field is blank. Please enter the password you use to login to the SleepIQ web site."
            errorsDict['showAlertText'] += errorsDict['password'] + "\n\n"

        else:
            # The field wasn't blank. Check to see if the format is valid.
            try:
                # Do this later.
                self.logger.debug(u"Checking password format \"%s\"." % valuesDict['password'])

            except Exception as e:
                # Username format was invalid.
                self.logger.debug("Password format is invalid.")
                isError = True
                errorsDict['password'] = "The password is not valid. Please enter a valid password."
                errorsDict['showAlertText'] += errorsDict['password'] + "\n\n"

        # Attempt to connect to the SleepIQ service and verify the username and password are correct.
        try:
            connected = connection.login()
        except Exception as e:
            isError = True
            if str(e).startswith("401 Client Error"):
                errorsDict[
                    'testLogin'] = "The 'SleepIQ Username/Email' or 'Password' are incorrect, or the SleepIQ site is not responding. \
                    Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
                errorsDict['username'] = "Invalid username or password"
                errorsDict['password'] = "Invalid username or password"
                errorsDict['showAlertText'] += errorsDict['testLogin'] + "\n\n"
                # Change the "accountVerified" valuesDict property so that the "FAILED" or "VERIFIED" label appears in the UI.
                valuesDict['accountVerified'] = "false"
            else:
                errorsDict[
                    'testLogin'] = "The 'SleepIQ Username/Email' or 'Password' are incorrect, or the SleepIQ site is not responding. \
                    Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
                errorsDict['showAlertText'] += errorsDict['testLogin'] + "\n\n"
                # Change the "accountVerified" valuesDict property so that the "FAILED" or "VERIFIED" label appears in the UI.
                valuesDict['accountVerified'] = "false"
                errorText = f"Unable to connect to the SleepIQ service. Error: {e}"
                self.logger.error(errorText)

        # Return an error if one exists.
        if isError:
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            return False, valuesDict, errorsDict
        else:
            return True, valuesDict

    # Sensor Action callback
    ########################################
    def actionControlSensor(self, action, device):
        try:
            self.logger.debug(f"actionControlSensor called for device {device.name}, action: {action}\n\ndevice: {device}")
        except Exception as e:
            self.logger.debug(f"actionControlSensor called for device {device.name}. (Unable to display action or device data due to error: {e})")
        # Get the current sensor on-state of the device.
        sensorOnState = device.states.get('onOffState', None)

        # Act based on the type of device.
        #
        # -- SleepNumber Bed --
        #
        if device.deviceTypeId == "sleepNumberBed":
            bedId = device.pluginProps.get('bedId', False)

            if action.sensorAction == indigo.kSensorAction.RequestStatus:
                # Query hardware module (device) for its current status here:
                indigo.server.log(u"sent \"%s\" %s" % (device.name, "status request"))
                # There's no method for updating just one bed status with the SleepyQ library, so
                # we'll just populate the beds list, including sleeper status then parse everything.
                try:
                    self.bedsList = self.connection.beds_with_sleeper_status()
                    if len(self.bedsList) == 0:
                        errorText = "There are no beds associated with this SleepIQ account. This plugin only works with beds that are registered with the SleepIQ service."
                        # Only display the error if it wasn't recently shown.
                        if self.lastError != errorText:
                            elf.lastError = errorText
                            self.logger.error(errorText)
                        return False
                except Exception as e:
                    errorText = f"Unable to load the list of beds associated with this SleepIQ account. Error: {e}"
                    # Only display the error if it wasn't recently shown.
                    if self.lastError != errorText:
                        elf.lastError = errorText
                        self.logger.error(errorText)
                    return False

                # Parse the Bed data.
                self.parseBedData()
        # End if/else sensor action checking.

    # End if this is a sensor device.

    ########################################
    # Plugin Custom Callback Methods
    ########################################

    # Toggle Debug Logging Menu Action
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.pluginPrefs['showDebugInfo'] = False
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs['showDebugInfo'] = True
        self.debug = not self.debug

    # Test Login (plugin prefs config UI)
    ########################################
    def testLogin(self, valuesDict):
        # Verify that the entered username/email address and password work with the SleepIQ site.
        self.logger.debug(f"testLogin called: valuesDict:\n{valuesDict}")
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""

        # Set up a local Sleepyq object with the passed username and password for account validation.
        username = valuesDict.get('username', "")
        password = valuesDict.get('password', "")

        if username.strip() == "":
            # The field was left blank (or had only white space in it).
            self.logger.debug(f"username \"{valuesDict['username']}\" is blank.")
            isError = True
            errorsDict[
                'username'] = "The \"SleepIQ Username/Email\" field is blank. Please enter the username or email address you use to login to the SleepIQ web site."
            errorsDict['showAlertText'] += errorsDict['username'] + u"\n\n"

        if password.strip() == "":
            # The field was left blank (or had only white space in it).
            self.logger.debug(f"password \"{valuesDict['password']}\" is blank.")
            isError = True
            errorsDict['password'] = u"The \"SleepIQ Password\" field is blank. Please enter the password you use to login to the SleepIQ web site."
            errorsDict['showAlertText'] += errorsDict['password'] + u"\n\n"

        # Attempt to connect to the SleepIQ service.
        try:
            connection = Sleepyq(username, password)
            connected = connection.login()
        except Exception as e:
            isError = True
            if str(e).startswith("401 Client Error"):
                errorsDict[
                    'testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. \
                    Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
                errorsDict['username'] = u"Invalid username or password"
                errorsDict['password'] = u"Invalid username or password"
                errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
            else:
                errorsDict[
                    'testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. \
                    Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
                errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
                errorText = f"Unable to connect to the SleepIQ service. Error: {e}"
                self.logger.error(errorText)

        # Return an error if one exists.
        if isError:
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            # Change the "accountVerified" valuesDict property to reflect the error.
            valuesDict['accountVerified'] = "false"
            return valuesDict, errorsDict
        else:
            # Change the "accountVerified" valuesDict property to reflect the success.
            valuesDict['accountVerified'] = "true"
            return valuesDict

    # Bed List Generator (device callback)
    ########################################
    def bedListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Generate an Indigo UI list of beds registered in the SleepIQ system.
        self.logger.debug("bedListGenerator called.")

        returnBedList = list()

        # Iterate through beds, and return the available list in Indigo's format
        for bed in self.bedsList:
            bedId = bed.data.get('bedId', "")
            bedName = bed.data.get('name', "")
            returnBedList.append([bedId, bedName])

        self.logger.debug(f"bedListGenerator: Return bed list is {returnBedList}")
        return returnBedList

    ########################################
    # Plugin Specific Operational Methods
    ########################################

    # Parse Bed Object Data and Update Device Status
    ########################################
    def parseBedData(self):
        # Go through the bedsList list, find associated Indigo devices and update them.
        self.logger.debug(u"parseBedData called.")

        if len(self.bedsList) > 0:
            for bed in self.bedsList:

                # We'll be using the following local variables...
                bedData = bed.data  # Dict containing data for the Bed object.
                bedBaseData = dict()  # Dict containing data for the base of the bed.
                bedBaseFeatureData = dict()  # Dict containing more data for the base of the bed.
                rightSideData = dict()  # Dict containing data for the right side SideStatus object.
                rightSleeperData = dict()  # Dict containing data for the right side Sleeper object.
                leftSideData = dict()  # Dict containing data for the left side SideStatus object.
                leftSleeperData = dict()  # Dict containing data for the left side Sleeper object.
                device = None  # Single Indigo device object from this plugin.
                keyValueList = []  # List of key:value tuples to be used to update device states.
                pluginProps = None  # Local writable copy of an Indigo device's properties.
                anyoneInBed = False  # Boolean of whether anyone is in bed or not.
                everyoneInBed = False  # Boolean of whether everyone is in bed.

                if bedData.get('base', None):
                    try:
                        bedBaseData = self.connection.foundation_status(bedId=bedData.get('bedId')).data
                    except Exception as e:
                        errorText = f"Unable to obtain status information for the base of the '{bedData.get('name', '(unnamed)')}' bed. \
                        This may be temporary. Check the bed's network connection and this server connection if the error continues. The error was: {e}"
                        # Only display the error if it wasn't recently shown.
                        if self.lastError != errorText:
                            self.lastError = errorText
                            self.logger.error(errorText)
                    try:
                        bedBaseFeatureData = self.connection.foundation_features(bedId=bedData.get('bedId')).data
                    except Exception as e:
                        errorText = f"Unable to obtain features list information for the base of the '{bedData.get('name', '(unnamed)')}' bed. \
                        This may be temporary. Check the bed's network connection and this server connection if the error continues. The error was: {e}"

                        # Only display the error if it wasn't recently shown.
                        if self.lastError != errorText:
                            self.lastError = errorText
                            self.logger.error(errorText)

                rightSideData = bed.right.data
                rightSleeperData = bed.right.sleeper.data
                leftSideData = bed.left.data
                leftSleeperData = bed.left.sleeper.data

                for device in indigo.devices.iter("self"):
                    if not (device.enabled and device.configured):
                        continue

                    if device.deviceTypeId == "sleepNumberBed":
                        # Create a key/value list to store all the device states before updating the device.
                        # Use keyValueList.append({'key':'<keyName>', 'value':<value>, 'uiValue':<UI value>})
                        # to add state/value list items.
                        keyValueList = []
                        # Create a temporary local copy of the device's properties.
                        pluginProps = device.pluginProps

                        # See if this Indigo device is associated with this Bed object.
                        if device.pluginProps.get('bedId', "") == bedData.get('bedId', "x"):
                            # Update the local copy of the device properties.
                            pluginProps['accountId'] = bedData.get('accountId', "")
                            pluginProps['address'] = bedData.get('bedId', "")
                            pluginProps['base'] = bedData.get('base', "")
                            pluginProps['baseConfigured'] = bedBaseData.get('fsConfigured', False)
                            pluginProps['baseNeedsHoming'] = bedBaseData.get('fsNeedsHoming', False)
                            pluginProps['baseType'] = bedBaseData.get('fsType', "")
                            pluginProps['hasFootControl'] = bedBaseFeatureData.get('hasFootControl', False)
                            pluginProps['hasFootWarming'] = bedBaseFeatureData.get('hasFootWarming', False)
                            pluginProps['hasMassageAndLight'] = bedBaseFeatureData.get('hasMassageAndLight', False)
                            pluginProps['hasUnderbedLight'] = bedBaseFeatureData.get('hasUnderbedLight', False)
                            pluginProps['bedName'] = bedData.get('name', "")
                            pluginProps['dualSleep'] = bedData.get('dualSleep', False)
                            pluginProps['generation'] = bedData.get('generation', "")
                            pluginProps['isKidsBed'] = bedData.get('isKidsBed', False)
                            pluginProps['macAddress'] = bedData.get('macAddress', "")
                            pluginProps['model'] = bedData.get('model', "")
                            pluginProps['purchaseDate'] = bedData.get('purchaseDate', "")
                            pluginProps['reference'] = bedData.get('reference', "")
                            pluginProps['registrationDate'] = bedData.get('registrationDate', "")
                            pluginProps['returnRequestStatus'] = bedData.get('returnRequestStatus', 0)
                            pluginProps['serial'] = bedData.get('serial', "")
                            pluginProps['size'] = bedData.get('size', "")
                            pluginProps['sku'] = bedData.get('sku', "")
                            pluginProps['status'] = bedData.get('status', 0)
                            pluginProps['timeZone'] = bedData.get('timezone', "")
                            pluginProps['version'] = bedData.get('version', "")
                            pluginProps['zipCode'] = bedData.get('zipcode', "")

                            # Update the key/value list for device states.
                            keyValueList.append({'key': 'leftIsInBed', 'value': leftSideData.get('isInBed', False)})
                            keyValueList.append({'key': 'leftPressure', 'value': leftSideData.get('pressure', 0)})
                            keyValueList.append({'key': 'leftFootPosition', 'value': int(bedBaseData.get('fsLeftFootPosition', u'00'), 16)})
                            keyValueList.append({'key': 'leftHeadPosition', 'value': int(bedBaseData.get('fsLeftHeadPosition', u'00'), 16)})
                            keyValueList.append({'key': 'leftSleepNumber', 'value': leftSideData.get('sleepNumber', 0)})
                            keyValueList.append({'key': 'leftSleeperId', 'value': leftSleeperData.get('sleeperId', 0)})
                            keyValueList.append({'key': 'leftSleeperName', 'value': leftSleeperData.get('firstName', "")})
                            keyValueList.append({'key': 'leftSleepGoal', 'value': leftSleeperData.get('sleepGoal', "")})
                            keyValueList.append({'key': 'leftAlertId', 'value': leftSideData.get('alertId', "")})
                            keyValueList.append({'key': 'leftAlertText', 'value': leftSideData.get('alertDetailedMessage', "")})

                            keyValueList.append({'key': 'rightIsInBed', 'value': rightSideData.get('isInBed', False)})
                            keyValueList.append({'key': 'rightPressure', 'value': rightSideData.get('pressure', 0)})
                            keyValueList.append({'key': 'rightFootPosition', 'value': int(bedBaseData.get('fsRightFootPosition', u'00'), 16)})
                            keyValueList.append({'key': 'rightHeadPosition', 'value': int(bedBaseData.get('fsRightHeadPosition', u'00'), 16)})
                            keyValueList.append({'key': 'rightSleepNumber', 'value': rightSideData.get('sleepNumber', 0)})
                            keyValueList.append({'key': 'rightSleeperId', 'value': rightSleeperData.get('sleeperId', 0)})
                            keyValueList.append({'key': 'rightSleeperName', 'value': rightSleeperData.get('firstName', "")})
                            keyValueList.append({'key': 'rightSleepGoal', 'value': rightSleeperData.get('sleepGoal', "")})
                            keyValueList.append({'key': 'rightAlertId', 'value': rightSideData.get('alertId', "")})
                            keyValueList.append({'key': 'rightAlertText', 'value': rightSideData.get('alertDetailedMessage', "")})

                            # Update the calculated anyone and everyone in bed states.
                            if leftSideData.get('isInBed', False) or rightSideData.get('isInBed', False):
                                keyValueList.append({'key': 'anyoneInBed', 'value': True})
                                keyValueList.append({'key': 'onOffState', 'value': True})
                                # Send an Indigo log message if the onOffState will change.
                                if not device.onState:
                                    indigo.server.log(u"received \"" + device.name + u"\" status update is on", 'SleepyBed IQ')
                            else:
                                keyValueList.append({'key': 'anyoneInBed', 'value': False})
                                keyValueList.append({'key': 'onOffState', 'value': False})
                                # Send an Indigo log message if the onOffState will change.
                                if device.onState:
                                    indigo.server.log(u"received \"" + device.name + u"\" status update is off", 'SleepyBed IQ')
                            if leftSideData.get('isInBed', False) and rightSideData.get('isInBed', False):
                                keyValueList.append({'key': 'everyoneInBed', 'value': True})
                            else:
                                keyValueList.append({'key': 'everyoneInBed', 'value': False})

                            # Now update the device properties and states on the server.
                            self.logger.debug(u"parseBedData: Setting device \"" + device.name + "\" properties to:\n" + str(pluginProps))
                            device.replacePluginPropsOnServer(pluginProps)  # Properties
                            self.logger.debug(u"parseBedData: Setting device \"" + device.name + "\" states to:\n" + str(keyValueList))
                            device.updateStatesOnServer(keyValueList)  # States

    # Set SleepNumber value
    ########################################
    def setSleepNumber(self, action):
        self.logger.debug("setSleepNumber called.")
        try:
            self.logger.debug("action: " + str(action))
        except Exception as e:
            self.logger.debug(f"(Unable to display action content due to error: {e})")

        # Define the device based on the deviceId in the "action" object.
        device = indigo.devices[action.deviceId]
        # "device" should be an Indigo SleepyBed IQ SleepNumber Bed device.
        side = str(action.props.get('side', "L"))
        # "side" should be the string "L" or "R"
        SleepNumber = int(action.props.get('SleepNumber', -1))
        # "SleepNumber" should be an integer from 0 to 100 and evenly divisible by 5.
        if SleepNumber < 0 or SleepNumber > 100:
            errorText = f"The SleepNumber \"{SleepNumber}\" is invalid. No action taken."
            self.logger.error(errorText)

        bedId = device.pluginProps.get('bedId', "")

        self.connection.set_sleepnumber(side, SleepNumber, bedId)

    # Select FlexFit Preset
    ########################################
    def selectFlexFitPreset(self, action):
        self.logger.debug("selectFlexFitPreset called.")
        try:
            self.logger.debug("action: " + str(action))
        except Exception as e:
            self.logger.debug(f"(Unable to display action content due to error: {e})")

        # Define the device based on the deviceId in the "action" object.
        device = indigo.devices[action.deviceId]
        # "device" should be an Indigo SleepyBed IQ SleepNumber Bed device.
        side = str(action.props.get('side', "L"))
        # "side" should be the string "L" or "R"
        FlexFitPreset = int(action.props.get('FlexFitPreset', None))
        # "FlexFitPreset" should be an integer from 1 to 6.
        #   1: Favorite
        #   2: Read
        #   3: Watch TV
        #   4: Flat
        #   5: Zero G
        #   6: Snore
        speed = int(action.props.get('speed', 0))
        # "speed" should be either 0 (for fast) or 1 (for slow).

        bedId = device.pluginProps.get('bedId', "")

        if device.pluginProps.get('base', "") != "":
            self.connection.preset(FlexFitPreset, side, bedId, speed)
        else:
            errorText = u"The \"" + device.name + u"\" doesn't support that feature.  No action taken."
            self.logger.error(errorText)

    # Select Base Position
    ########################################
    def setBasePosition(self, action):
        self.logger.debug("setBasePosition called.")
        try:
            self.logger.debug("action: " + str(action))
        except Exception as e:
            self.logger.debug("(Unable to display action content due to error: " + str(e) + ")")

        # Define the device based on the deviceId in the "action" object.
        device = indigo.devices[action.deviceId]
        # "device" should be an Indigo SleepyBed IQ SleepNumber Bed device.
        side = str(action.props.get('side', "L"))
        # "side" should be the string "L" or "R"
        headOrFoot = str(action.props.get('headOrFoot', "H"))
        # "headOrFoot" should be the string "H" or "F"
        basePosition = int(action.props.get('basePosition', None))
        # "basePosition" should be an integer from 0 to 100.
        speed = int(action.props.get('speed', 0))
        # "speed" should be either 0 (for fast) or 1 (for slow).

        bedId = device.pluginProps.get('bedId', "")

        # Make sure the bed supports controlling what's been requested.
        if device.pluginProps.get('base', "") != "":
            if headOrFoot == "H" or (headOrFoot == "F" and device.pluginProps.get('hasFootControl', False)):
                self.connection.set_foundation_position(side, headOrFoot, basePosition, bedId, speed)
            else:
                errorText = u"The \"" + device.name + u"\" doesn't support that feature.  No action taken."
                self.logger.error(errorText)
        else:
            errorText = u"The \"" + device.name + u"\" doesn't support that feature.  No action taken."
            self.logger.error(errorText)

    # Actions Dialog
    ########################################
    def validateActionConfigUi(self, valuesDict, typeId, deviceId):
        self.logger.debug("validateActionConfigUi called.")
        self.logger.debug("typeId: " + str(typeId) + u", deviceId: " + str(deviceId))
        try:
            self.logger.debug("valuesDict: " + str(valuesDict))
        except Exception as e:
            self.logger.debug("(Unable to display valuesDict due to error: " + str(e) + ")")

        device = indigo.devices[deviceId]
        errorMsgDict = indigo.Dict()
        descString = u""

        #
        # Set SleepNumber
        #
        if typeId == "setSleepNumber":
            try:
                SleepNumber = int(valuesDict.get('SleepNumber', ""))
            except ValueError:
                errorMsgDict['SleepNumber'] = u"The SleepNumber must be a number between 0 and 100 and be a multiple of 5."
                errorMsgDict['showAlertText'] = errorMsgDict['SleepNumber']
                return False, valuesDict, errorMsgDict

            if (SleepNumber < 0) or (SleepNumber > 100):
                errorMsgDict['SleepNumber'] = "The SleepNumber must be a number between 0 and 100 and be a multiple of 5."
                errorMsgDict['showAlertText'] = errorMsgDict['SleepNumber']
                return False, valuesDict, errorMsgDict

            if SleepNumber % 5 != 0:
                errorMsgDict['SleepNumber'] = u"The SleepNumber must be a multiple of 5."
                errorMsgDict['showAlertText'] = errorMsgDict['SleepNumber']
                return False, valuesDict, errorMsgDict

            side = valuesDict.get('side', "L")
            if side == "L":
                sideName = "Left"
            else:
                sideName = "Right"

            descString += u"set the " + sideName + u" side of \"" + device.name + u"\" to SleepNumber " + str(SleepNumber)

        #
        # Select FlexFit Preset
        #
        if typeId == "selectFlexFitPreset":
            # Make sure the bed supports adjusting the base position.
            if device.pluginProps.get('base', "") == "":
                errorMsgDict[
                    'deviceId'] = u"The selected bed doesn't have a base with adjustable height. Please select a bed with an adjustable base."
                errorMsgDict['showAlertText'] = errorMsgDict['deviceId']
                return False, valuesDict, errorMsgDict

            try:
                FlexFitPreset = int(valuesDict.get('FlexFitPreset', 1))
            # FlexFitPreset should be an integer from 1 to 6.
            except ValueError:
                errorMsgDict['FlexFitPreset'] = u"Select a FlexFit Preset."
                errorMsgDict['showAlertText'] = errorMsgDict['FlexFitPreset']
                return False, valuesDict, errorMsgDict

            try:
                speed = int(valuesDict.get('speed', 0))
            # "speed" should be an integer of 0 or 1.
            except ValueError:
                errorMsgDict['speed'] = u"Select a Speed."
                errorMsgDict['showAlertText'] = errorMsgDict['speed']
                return False, valuesDict, errorMsgDict

            side = valuesDict.get('side', "L")
            if side == "R":
                sideName = "Right"
            else:
                sideName = "Left"

            if FlexFitPreset == 2:
                FlexFitPresetName = "Read"
            elif FlexFitPreset == 3:
                FlexFitPresetName = "Watch TV"
            elif FlexFitPreset == 4:
                FlexFitPresetName = "Flat"
            elif FlexFitPreset == 5:
                FlexFitPresetName = "Zero G"
            elif FlexFitPreset == 6:
                FlexFitPresetName = "Snore"
            else:
                FlexFitPresetName = "Favorite"

            if speed == 1:
                speedName = u"Slow"
            else:
                speedName = u"Fast"

            descString += u"set the " + sideName + u" side FlexFit position of \"" + device.name + u"\" to preset " + str(
                FlexFitPresetName) + " at a " + str(speedName) + " speed"

        #
        # Set Base Position
        #
        if typeId == "setBasePosition":
            # Make sure the bed supports adjusting the base position.
            if device.pluginProps.get('base', "") == "":
                errorMsgDict[
                    'deviceId'] = u"The selected bed doesn't have a base with adjustable height. Please select a bed with an adjustable base."
                errorMsgDict['showAlertText'] = errorMsgDict['deviceId']
                return False, valuesDict, errorMsgDict

            try:
                basePosition = int(valuesDict.get('basePosition', 0))
            # basePosition should be an integer from 0 (flat) to 100 (fully raised).
            except ValueError:
                errorMsgDict['basePosition'] = u"Set the Percent Raised between 0 (flat) and 100 (fully raised)."
                errorMsgDict['showAlertText'] = errorMsgDict['basePosition']
                return False, valuesDict, errorMsgDict

            try:
                speed = int(valuesDict.get('speed', 0))
            # "speed" should be an integer of 0 or 1.
            except ValueError:
                errorMsgDict['speed'] = u"Select a Speed."
                errorMsgDict['showAlertText'] = errorMsgDict['speed']
                return False, valuesDict, errorMsgDict

            side = valuesDict.get('side', "L")
            if side == "R":
                sideName = "Right"
            else:
                sideName = "Left"

            headOrFoot = valuesDict.get('headOrFoot', "H")
            if headOrFoot == "F":
                headOrFootName = "Foot"
                # Make sure the base of the bed has an adjustable foot.
                if not device.pluginProps.get('hasFootControl', False):
                    errorMsgDict[
                        'headOrFoot'] = u"The selected bed has a base that does not support foot adjustments. \
                        Either select \"Head\" for the \"Head or Foot\" control, or select a bed whose base has adjustable foot controls."
                    errorMsgDict['showAlertText'] = errorMsgDict['headOrFoot']
                    return False, valuesDict, errorMsgDict
            else:
                headOrFootName = "Head"

            # Constrain the base position value to between 0 and 100 and make sure it's a whole number.
            if basePosition < 0:
                basePosition = 0
            elif basePosition > 100:
                basePosition = 100
            else:
                try:
                    basePosition = int(basePosition)
                except Exception as e:
                    errorMsgDict['basePosition'] = u"Percent Raised can only be a number between 0 and 100."
                    errorMsgDict['showAlertText'] = errorMsgDict['basePosition']
                    return False, valuesDict, errorMsgDict

            if speed == 0:
                speedName = u"Fast"
            elif speed == 1:
                speedName = u"Slow"
            else:
                speedName = u"Unknown"
            descString += u"set the " + sideName + u" side " + headOrFootName + u" position of \"" + device.name + u"\" to " + str(
                basePosition) + " at a " + str(speedName) + " speed"

        valuesDict['description'] = descString
        return True, valuesDict
