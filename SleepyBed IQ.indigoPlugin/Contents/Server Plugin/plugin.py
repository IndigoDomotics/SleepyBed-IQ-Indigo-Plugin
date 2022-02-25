#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# SleepyBed IQ Plugin
#   by Nathan Sheldon
#
# Sleepyq library code by Josh Nichols (https://github.com/technicalpickles),
# Philip Dorr (https://github.com/tagno25), et al under MIT open licence.
#
#	Version 1.2.2
#
#	See the "VERSION_HISTORY.txt" file in the same location as this plugin.py
#	file for a complete version change history.
#
################################################################################

import indigo

import os
import sys
import requests
import indigoPluginUpdateChecker
from sleepyq import Sleepyq

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	# Loading and Starting Methods
	########################################
	
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get('showDebugInfo', False)
		self.debugLog(u"Initializing Plugin.")
		self.username = pluginPrefs.get('username', "")
		self.password = pluginPrefs.get('password', "")
		self.lastError = ""		# String of last error message shown in log.
		self.bedsList = []      # List of beds associated with the SleepIQ account.
		self.sleepersList = []  # List of sleepers registered in the SleepIQ account.
		self.connection = Sleepyq(self.username, self.password)
								# Creates a Sleepyq object with the SleepIQ account information.
		# Load the update checker module.
		self.updater = indigoPluginUpdateChecker.updateChecker(self, 'http://www.nathansheldon.com/files/PluginVersions/SleepyBed-IQ.html')

	# Unload Plugin
	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)
	
	# Startup
	########################################
	def startup(self):
		self.debugLog(u"startup called")
		self.debugLog(u"Running plugin version check (if enabled).")
		# Check for plugin updates right away.
		self.updater.checkVersionPoll()
		
		# Attempt to connect to the SleepIQ service.
		try:
			connected = self.connection.login()
			if not connected:
				errorText = u"Unable to connect to the SleepIQ service with the provided username and password.  Please verify the username and password settings in the SleepyBed IQ configuration."
				self.errorLog(errorText)
				return False
		except Exception, e:
			errorText = u"Unable to connect to the SleepIQ service. Error: %s" % (e)
			self.errorLog(errorText)
			return False
		
		# Everything went fine.
		return True

	# Shutdown
	########################################
	def shutdown(self):
		self.debugLog(u"shutdown called")
	
	# Start Devices
	########################################
	def deviceStartComm(self, device):
		self.debugLog(u"Starting device: " + device.name)
		# Clear any device error states first.
		device.setErrorStateOnServer("")
		# Reload the device states list.
		device.stateListOrDisplayStateIdChanged()

	# Stop Devices
	########################################
	def deviceStopComm(self, device):
		self.debugLog(u"Stopping device: " + device.name)



	########################################
	# Standard Plugin Methods
	########################################
	
	# Run Concurrent Thread
	########################################
	def runConcurrentThread(self):
		self.debugLog(u"Starting runConcurrentThread.")
		
		# Set a counter variable to control how often repeated error messages appear.
		loopCount = 0
		
		try:
			while True:
			
				# Populate the beds list, including sleeper status.
				try:
					self.debugLog(u"runConcurrentThread: Updating beds and sleepers list.")
					self.bedsList = self.connection.beds_with_sleeper_status()
					if len(self.bedsList) == 0:
						errorText = u"There are no beds associated with this SleepIQ account. This plugin only works with beds that are registered with the SleepIQ service."
						# Only display the error if it wasn't recently shown.
						if self.lastError != errorText:
							self.lastError = errorText
							self.errorLog(errorText)
				except Exception, e:
					# Detect authentication/session login errors.
					if str(e).startswith("401 Client Error"):
						# Attempt to re-connect to the SleepIQ service.
						try:
							connected = self.connection.login()
							if not connected:
								errorText = u"Unable to connect to the SleepIQ service with the provided username and password.  Please verify the username and password settings in the SleepyBed IQ configuration."
								# Only display the error if it wasn't recently shown.
								if self.lastError != errorText:
									self.lastError = errorText
									self.errorLog(errorText)
								# End if last error is not the same as this error.
							# End if not connected.
						except Exception, e:
							# If we still get an authentication error, let the user know.
							if str(e).startswith("401 Client Error"):
								errorText = u"Unable to connect to the SleepIQ service with the provided username and password.  Please verify the username and password settings in the SleepyBed IQ configuration."
								# Only display the error if it wasn't recently shown.
								if self.lastError != errorText:
									self.lastError = errorText
									self.errorLog(errorText)
								# End if last error is not the same as this error.
							else:
								errorText = u"Unable to connect to the SleepIQ service. Error: %s" % (e)
								# Only display the error if it wasn't recently shown.
								if self.lastError != errorText:
									self.lastError = errorText
									self.errorLog(errorText)
								# End if last error is not the same as this error.
							# End if this was a client authentication error.
						# End try to connect.
					else:
						errorText = u"Unable to load the list of beds associated with this SleepIQ account. Error: %s" % (e)
						# Only display the error if it wasn't recently shown.
						if self.lastError != errorText:
							self.lastError = errorText
							self.errorLog(errorText)
						# End if the last error is no the same as this error.
					# End if the original bed refresh resulted in a client auth error.
				# End try to refresh bed and sleeper status.
		
				# Parse the Bed data.
				self.parseBedData()
				
				# Increment the loop counter.
				loopCount += 1
				
				# Reset the loop counter every 19 loops (10 minutes) and clear the saved errors.
				if loopCount > 19:
					self.debugLog(u"runConcurrentThread: 10 minutes have passed. Resetting error conditions (if any).")
					loopCount = 0
					self.lastError = u""
				
				# Sleep for 30 seconds before looping again.
				self.sleep(30)
				
			# End while True continuous loop.
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.


	########################################
	# Standard Plugin Callback Methods
	########################################

	# Validate Device Configuration
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		self.debugLog(u"validateDeviceConfigUi called: typeId: %s  devId: %s valuesDict:\n%s" % (typeId, str(devId), str(valuesDict)))
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		isError = False
		
		# Check values based on device type ID.
		if typeId == "sleepNumberBed":
			# Make sure a bed was selected.
			if valuesDict.get('bedId', "") == "":
				isError = True
				errorsDict['bedId'] = u"Please select a SleepNumber Bed to monitor."
				errorsDict['showAlertText'] += errorsDict['bedId']
				return (False, valuesDict, errorsDict)
			# End if bedId property doesn't exist.
		# End if typeId is sleepNumberBed.

		return (True, valuesDict)

	# Validate Preferences Configuration.
	########################################
	def validatePrefsConfigUi(self, valuesDict):
		self.debugLog(u"validatePrefsConfigUi called: valuesDict:\n%s" % (str(valuesDict)))
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		# Reset the "accountVerified" valuesDict property to hide the "FAILED" or "VERIFIED" lable in the UI.
		valuesDict['accountVerified'] = "unknown"
		
		# Set up a local Sleepyq object with the passed username and password for account validation.
		username = valuesDict.get('username', "")
		password = valuesDict.get('password', "")
		connection = Sleepyq(username, password)
		
		# Validate the username field.
		if valuesDict.get('username', "") == "":
			# The field was left blank.
			self.debugLog(u"username \"%s\" is blank." % valuesDict['username'])
			isError = True
			errorsDict['username'] = u"The \"SleepIQ Username/Email\" field is blank. Please enter the username or email address you use to login to the SleepIQ web site."
			errorsDict['showAlertText'] += errorsDict['username'] + u"\n\n"
		
		else:
			# The field wasn't blank. Check to see if the format is valid.
			try:
				# Do this later.
				self.debugLog(u"Checking username format \"%s\"." % valuesDict['username'])
			
			except Exception, e:
				# Username format was invalid.
				self.debugLog(u"Username format is invalid.")
				isError = True
				errorsDict['username'] = u"The username is not valid. Please enter a valid username or email address."
				errorsDict['showAlertText'] += errorsDict['username'] + u"\n\n"
		
		# Validate the password field.
		if valuesDict.get('password', "") == "":
			# The field was left blank.
			self.debugLog(u"password \"%s\" is blank." % valuesDict['password'])
			isError = True
			errorsDict['password'] = u"The \"SleepIQ Password\" field is blank. Please enter the password you use to login to the SleepIQ web site."
			errorsDict['showAlertText'] += errorsDict['password'] + u"\n\n"
		
		else:
			# The field wasn't blank. Check to see if the format is valid.
			try:
				# Do this later.
				self.debugLog(u"Checking password format \"%s\"." % valuesDict['password'])
			
			except Exception, e:
				# Username format was invalid.
				self.debugLog(u"Password format is invalid.")
				isError = True
				errorsDict['password'] = u"The password is not valid. Please enter a valid password."
				errorsDict['showAlertText'] += errorsDict['password'] + u"\n\n"
		
		# Attempt to connect to the SleepIQ service and verify the username and password are correct.
		try:
			connected = connection.login()
		except Exception, e:
			isError = True
			if str(e).startswith("401 Client Error"):
				errorsDict['testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
				errorsDict['username'] = u"Invalid username or password"
				errorsDict['password'] = u"Invalid username or password"
				errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
				# Change the "accountVerified" valuesDict property so that the "FAILED" or "VEIFIED" label appears in the UI.
				valuesDict['accountVerified'] = "false"
			else:
				errorsDict['testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
				errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
				# Change the "accountVerified" valuesDict property so that the "FAILED" or "VEIFIED" label appears in the UI.
				valuesDict['accountVerified'] = "false"
				errorText = u"Unable to connect to the SleepIQ service. Error: %s" % (e)
				self.errorLog(errorText)

		# Return an error if one exists.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			return (False, valuesDict, errorsDict)
		else:
			return (True, valuesDict)

	# Sensor Action callback
	########################################
	def actionControlSensor(self, action, device):
		try:
			self.debugLog(u"actionControlSensor called for device " + device.name + u". action: " + str(action) + u"\n\ndevice: " + str(device))
		except Exception, e:
			self.debugLog(u"actionControlSensor called for device " + device.name + u". (Unable to display action or device data due to error: " + str(e) + u")")
		# Get the current sensor on-state of the device.
		sensorOnState = device.states.get('onOffState', None)
		
		# Act based on the type of device.
		#
		# -- SleepNumber Bed --
		#
		if device.deviceTypeId == "sleepNumberBed":
			bedId = device.pluginProps.get('bedId', False)
			
			###### TURN ON ######
			# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
			if action.sensorAction == indigo.kSensorAction.TurnOn:
				indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (device.name, "on"))

			###### TURN OFF ######
			# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
			elif action.sensorAction == indigo.kSensorAction.TurnOff:
				indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (device.name, "off"))

			###### TOGGLE ######
			# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
			elif action.sensorAction == indigo.kSensorAction.Toggle:
				indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (device.name, "toggle"))
		
			###### STATUS REQUEST ######
			elif action.sensorAction == indigo.kSensorAction.RequestStatus:
				# Query hardware module (device) for its current status here:
				indigo.server.log(u"sent \"%s\" %s" % (device.name, "status request"))
				# There's no method for updating just one bed status with the SleepyQ library, so
				# we'll just populate the beds list, including sleeper status then parse everything.
				try:
					self.bedsList = self.connection.beds_with_sleeper_status()
					if len(self.bedsList) == 0:
						errorText = u"There are no beds associated with this SleepIQ account. This plugin only works with beds that are registered with the SleepIQ service."
						# Only display the error if it wasn't recently shown.
						if self.lastError != errorText:
							elf.lastError = errorText
							self.errorLog(errorText)
						return False
				except Exception, e:
					errorText = u"Unable to load the list of beds associated with this SleepIQ account. Error: %s" % (e)
					# Only display the error if it wasn't recently shown.
					if self.lastError != errorText:
						elf.lastError = errorText
						self.errorLog(errorText)
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
		# Verify that the entered usernamne/email address and password work with the SleepIQ site.
		self.debugLog(u"testLogin called: valuesDict:\n%s" % (str(valuesDict)))
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""

		# Set up a local Sleepyq object with the passed username and password for account validation.
		username = valuesDict.get('username', "")
		password = valuesDict.get('password', "")

		if username.strip() == "":
			# The field was left blank (or had only white space in it).
			self.debugLog(u"username \"%s\" is blank." % valuesDict['username'])
			isError = True
			errorsDict['username'] = u"The \"SleepIQ Username/Email\" field is blank. Please enter the username or email address you use to login to the SleepIQ web site."
			errorsDict['showAlertText'] += errorsDict['username'] + u"\n\n"
		
		if password.strip() == "":
			# The field was left blank (or had only white space in it).
			self.debugLog(u"password \"%s\" is blank." % valuesDict['password'])
			isError = True
			errorsDict['password'] = u"The \"SleepIQ Password\" field is blank. Please enter the password you use to login to the SleepIQ web site."
			errorsDict['showAlertText'] += errorsDict['password'] + u"\n\n"

		# Attempt to connect to the SleepIQ service.
		try:
			connection = Sleepyq(username, password)
			connected = connection.login()
		except Exception, e:
			isError = True
			if str(e).startswith("401 Client Error"):
				errorsDict['testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
				errorsDict['username'] = u"Invalid username or password"
				errorsDict['password'] = u"Invalid username or password"
				errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
			else:
				errorsDict['testLogin'] = u"The \"SleepIQ Username/Email\" or \"Password\" are incorrect, or the SleepIQ site is not responding. Please verify you have a working network connection and that the username or email address and password you use to login to the SleepIQ web site is typed correctly."
				errorsDict['showAlertText'] += errorsDict['testLogin'] + u"\n\n"
				errorText = u"Unable to connect to the SleepIQ service. Error: %s" % (e)
				self.errorLog(errorText)
			
		# Return an error if one exists.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			# Change the "accountVerified" valuesDict property to reflect the error.
			valuesDict['accountVerified'] = "false"
			return (valuesDict, errorsDict)
		else:
			# Change the "accountVerified" valuesDict property to reflect the success.
			valuesDict['accountVerified'] = "true"
			return valuesDict

	# Bed List Generator (device callback)
	########################################
	def bedListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Generate an Indigo UI list of beds registered in the SleepIQ system.
		self.debugLog(u"bedListGenerator called.")

		returnBedList = list()
		
		# Iterate through beds, and return the available list in Indigo's format
		for bed in self.bedsList:
			bedId = bed.data.get('bedId', "")
			bedName = bed.data.get('name', "")
			returnBedList.append([bedId, bedName])

		# Debug
		self.debugLog(u"bedListGenerator: Return bed list is %s" % returnBedList)
		
		return returnBedList


	########################################
	# Plugin Specific Operational Methods
	########################################

	# Parse Bed Object Data and Update Device Status
	########################################
	def parseBedData(self):
		# Go through the bedsList list, find associated Indigo devices and update them.
		self.debugLog(u"parseBedData called.")

		if len(self.bedsList) > 0:
			for bed in self.bedsList:

				# We'll be using the following local variables...
				bedData				= bed.data # Dict containing data for the Bed object.
				bedBaseData			= dict()  # Dict containing data for the base of the bed.
				bedBaseFeatureData	= dict()  # Dict containing more data for the base of the bed.
				rightSideData		= dict()  # Dict containing data for the right side SideStatus object.
				rightSleeperData	= dict()  # Dict containing data for the right side Sleeper object.
				leftSideData		= dict()  # Dict containing data for the left side SideStatus object.
				leftSleeperData		= dict()  # Dict containing data for the left side Sleeper object.
				device				= None  # Single Indigo device object from this plugin.
				keyValueList		= []  # List of key:value touples to be used to update device states.
				pluginProps			= None  # Local writable copy of an Indigo device's properties.
				anyoneInBed			= False  # Boolean of whether anyone is in bed or not.
				everyoneInBed		= False  # Boolean of whether everyone is in bed.

				if bedData.get('base', None) != None:
					try:
						bedBaseData			= self.connection.foundation_status(bedId=bedData.get('bedId')).data
					except Exception, e:
						errorText = u"Unable to obtain status information for the base of the \"" + bedData.get('name', u"(unnamed)") + "\" bed. This may be temporary. Check the bed's network connection and this server connection if the error continues. The error was: " + str(e)
						# Only display the error if it wasn't recently shown.
						if self.lastError != errorText:
							self.lastError = errorText
							self.errorLog(errorText)
					try:
						bedBaseFeatureData	= self.connection.foundation_features(bedId=bedData.get('bedId')).data
					except Exception, e:
						errorText = u"Unable to obtain features list information for the base of the \"" + bedData.get('name', u"(unnamed)") + "\" bed. This may be temporary. Check the bed's network connection and this server connection if the error continues. The error was: " + str(e)
						# Only display the error if it wasn't recently shown.
						if self.lastError != errorText:
							self.lastError = errorText
							self.errorLog(errorText)

				rightSideData		= bed.right.data
				rightSleeperData	= bed.right.sleeper.data
				leftSideData		= bed.left.data
				leftSleeperData		= bed.left.sleeper.data

				for device in indigo.devices.iter("self"):
					if not device.enabled or not device.configured:
						continue

					if device.deviceTypeId == u"sleepNumberBed":
						# Create a key/value list to store all the device states before updating the device.
						# Use keyValueList.append({'key':'<keyName>', 'value':<value>, 'uiValue':<UI value>})
						# to add state/value list items.
						keyValueList = []
						# Create a temporary local copy of the device's properties.
						pluginProps = device.pluginProps
						
						# See if this Indigo device is associated with this Bed object.
						if device.pluginProps.get('bedId', "") == bedData.get('bedId', "x"):
							# Update the local copy of the device properties.
							pluginProps['accountId']			= bedData.get('accountId', "")
							pluginProps['address']				= bedData.get('bedId', "")
							pluginProps['base']					= bedData.get('base', "")
							pluginProps['baseConfigured']		= bedBaseData.get('fsConfigured', False)
							pluginProps['baseNeedsHoming']		= bedBaseData.get('fsNeedsHoming', False)
							pluginProps['baseType']				= bedBaseData.get('fsType', "")
							pluginProps['hasFootControl']		= bedBaseFeatureData.get('hasFootControl', False)
							pluginProps['hasFootWarming']		= bedBaseFeatureData.get('hasFootWarming', False)
							pluginProps['hasMassageAndLight']	= bedBaseFeatureData.get('hasMassageAndLight', False)
							pluginProps['hasUnderbedLight']		= bedBaseFeatureData.get('hasUnderbedLight', False)
							pluginProps['bedName']				= bedData.get('name', "")
							pluginProps['dualSleep']			= bedData.get('dualSleep', False)
							pluginProps['generation']			= bedData.get('generation', "")
							pluginProps['isKidsBed']			= bedData.get('isKidsBed', False)
							pluginProps['macAddress']			= bedData.get('macAddress', "")
							pluginProps['model']				= bedData.get('model', "")
							pluginProps['purchaseDate']			= bedData.get('purchaseDate', "")
							pluginProps['reference']			= bedData.get('reference', "")
							pluginProps['registrationDate']		= bedData.get('registrationDate', "")
							pluginProps['returnRequestStatus']	= bedData.get('returnRequestStatus', 0)
							pluginProps['serial']				= bedData.get('serial', "")
							pluginProps['size']					= bedData.get('size', "")
							pluginProps['sku']					= bedData.get('sku', "")
							pluginProps['status']				= bedData.get('status', 0)
							pluginProps['timeZone']				= bedData.get('timezone', "")
							pluginProps['version']				= bedData.get('version', "")
							pluginProps['zipCode']				= bedData.get('zipcode', "")
						
							# Update the key/value list for device states.
							keyValueList.append({'key':'leftIsInBed',		'value':leftSideData.get('isInBed', False)})
							keyValueList.append({'key':'leftPressure',		'value':leftSideData.get('pressure', 0)})
							keyValueList.append({'key':'leftFootPosition',	'value':int(bedBaseData.get('fsLeftFootPosition', u'00'), 16)})
							keyValueList.append({'key':'leftHeadPosition',	'value':int(bedBaseData.get('fsLeftHeadPosition', u'00'), 16)})
							keyValueList.append({'key':'leftSleepNumber',	'value':leftSideData.get('sleepNumber', 0)})
							keyValueList.append({'key':'leftSleeperId',		'value':leftSleeperData.get('sleeperId', 0)})
							keyValueList.append({'key':'leftSleeperName',	'value':leftSleeperData.get('firstName', "")})
							keyValueList.append({'key':'leftSleepGoal',		'value':leftSleeperData.get('sleepGoal', "")})
							keyValueList.append({'key':'leftAlertId',		'value':leftSideData.get('alertId', "")})
							keyValueList.append({'key':'leftAlertText',		'value':leftSideData.get('alertDetailedMessage', "")})
							
							keyValueList.append({'key':'rightIsInBed',		'value':rightSideData.get('isInBed', False)})
							keyValueList.append({'key':'rightPressure',		'value':rightSideData.get('pressure', 0)})
							keyValueList.append({'key':'rightFootPosition',	'value':int(bedBaseData.get('fsRightFootPosition', u'00'), 16)})
							keyValueList.append({'key':'rightHeadPosition',	'value':int(bedBaseData.get('fsRightHeadPosition', u'00'), 16)})
							keyValueList.append({'key':'rightSleepNumber',	'value':rightSideData.get('sleepNumber', 0)})
							keyValueList.append({'key':'rightSleeperId',	'value':rightSleeperData.get('sleeperId', 0)})
							keyValueList.append({'key':'rightSleeperName',	'value':rightSleeperData.get('firstName', "")})
							keyValueList.append({'key':'rightSleepGoal',	'value':rightSleeperData.get('sleepGoal', "")})
							keyValueList.append({'key':'rightAlertId',		'value':rightSideData.get('alertId', "")})
							keyValueList.append({'key':'rightAlertText',	'value':rightSideData.get('alertDetailedMessage', "")})
							
							# Update the calculated anyone and everyone in bed states.
							if leftSideData.get('isInBed', False) or rightSideData.get('isInBed', False):
								keyValueList.append({'key':'anyoneInBed',	'value':True})
								keyValueList.append({'key':'onOffState',	'value':True})
								# Send an Indigo log message if the onOffState will change.
								if device.onState == False:
									indigo.server.log(u"received \"" + device.name + u"\" status update is on", 'SleepyBed IQ')
							else:
								keyValueList.append({'key':'anyoneInBed',	'value':False})
								keyValueList.append({'key':'onOffState',	'value':False})
								# Send an Indigo log message if the onOffState will change.
								if device.onState == True:
									indigo.server.log(u"received \"" + device.name + u"\" status update is off", 'SleepyBed IQ')
							if leftSideData.get('isInBed', False) and rightSideData.get('isInBed', False):
								keyValueList.append({'key':'everyoneInBed',	'value':True})
							else:
								keyValueList.append({'key':'everyoneInBed',	'value':False})
						
							# Now update the device properties and states on the server.
							self.debugLog(u"parseBedData: Setting device \"" + device.name + "\" properties to:\n" + str(pluginProps))
							device.replacePluginPropsOnServer(pluginProps)	# Properties
							self.debugLog(u"parseBedData: Setting device \"" + device.name + "\" states to:\n" + str(keyValueList))
							device.updateStatesOnServer(keyValueList)		# States

						# End if Indigo device is connected to this Bed device.
					# End if this Indigo sevice is a type ID that we support.
				# End loop through our own Indigo devices.
			# End loop through Bed objects in SleepIQ account.
		# End if Beds list is empty.

	# Set SleepNumber value
	########################################
	def setSleepNumber(self, action):
		self.debugLog("setSleepNumber called.")
		try:
			self.debugLog("action: " + str(action))
		except Exception, e:
			self.debugLog("(Unable to display action content due to error: " + str(e) + ")")
		
		# Define the device based on the deviceId in the "action" obejct.
		device = indigo.devices[action.deviceId]
		# "device" should be an Indigo SleepyBed IQ SleepNumber Bed device.
		side = str(action.props.get('side', "L"))
		# "side" should be the string "L" or "R"
		SleepNumber = int(action.props.get('SleepNumber', -1))
		# "SleepNumber" should be an integer from 0 to 100 and evenly divisible by 5.
		if SleepNumber < 0 or SleepNumber > 100:
			errorText = u"The SleepNumber \"" + str(SleepNumber) + u"\" is invalid. No action taken."
			self.errorLog(errorText)
		
		bedId = device.pluginProps.get('bedId', "")
		
		self.connection.set_sleepnumber(side, SleepNumber, bedId)

	# Select FlexFit Preset
	########################################
	def selectFlexFitPreset(self, action):
		self.debugLog("selectFlexFitPreset called.")
		try:
			self.debugLog("action: " + str(action))
		except Exception, e:
			self.debugLog("(Unable to display action content due to error: " + str(e) + ")")

		# Define the device based on the deviceId in the "action" obejct.
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
			self.errorLog(errorText)


	# Select Base Position
	########################################
	def setBasePosition(self, action):
		self.debugLog("setBasePosition called.")
		try:
			self.debugLog("action: " + str(action))
		except Exception, e:
			self.debugLog("(Unable to display action content due to error: " + str(e) + ")")

		# Define the device based on the deviceId in the "action" obejct.
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
				self.errorLog(errorText)
		else:
			errorText = u"The \"" + device.name + u"\" doesn't support that feature.  No action taken."
			self.errorLog(errorText)

	# Actions Dialog
	########################################
	def validateActionConfigUi(self, valuesDict, typeId, deviceId):
		self.debugLog("validateActionConfigUi called.")
		self.debugLog("typeId: " + str(typeId) + u", deviceId: " + str(deviceId))
		try:
			self.debugLog("valuesDict: " + str(valuesDict))
		except Exception, e:
			self.debugLog("(Unable to display valuesDict due to error: " + str(e) + ")")
		
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
				return (False, valuesDict, errorMsgDict)
			
			if (SleepNumber < 0) or (SleepNumber > 100):
				errorMsgDict['SLeepNumber'] = u"The SleepNumber must be a number between 0 and 100 and be a multiple of 5."
				errorMsgDict['showAlertText'] = errorMsgDict['SleepNumber']
				return (False, valuesDict, errorMsgDict)
				
			if SleepNumber % 5 != 0:
				errorMsgDict['SleepNumber'] = u"The SleepNumber must be a multiple of 5."
				errorMsgDict['showAlertText'] = errorMsgDict['SleepNumber']
				return (False, valuesDict, errorMsgDict)

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
				errorMsgDict['deviceId'] = u"The selected bed doesn't have a base with adjustable height. Please select a bed with an adjustable base."
				errorMsgDict['showAlertText'] = errorMsgDict['deviceId']
				return (False, valuesDict, errorMsgDict)

			try:
				FlexFitPreset = int(valuesDict.get('FlexFitPreset', 1))
				# FlexFitPreset should be an integer from 1 to 6.
			except ValueError:
				errorMsgDict['FlexFitPreset'] = u"Select a FlexFit Preset."
				errorMsgDict['showAlertText'] = errorMsgDict['FlexFitPreset']
				return (False, valuesDict, errorMsgDict)
			
			try:
				speed = int(valuesDict.get('speed', 0))
				# "speed" should be an integer of 0 or 1.
			except ValueError:
				errorMsgDict['speed'] = u"Select a Speed."
				errorMsgDict['showAlertText'] = errorMsgDict['speed']
				return (False, valuesDict, errorMsgDict)
			
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
			
			descString += u"set the " + sideName + u" side FlexFit position of \"" + device.name + u"\" to preset " + str(FlexFitPresetName) + " at a " + str(speedName) + " speed"

		#
		# Set Base Position
		#
		if typeId == "setBasePosition":
			# Make sure the bed supports adjusting the base position.
			if device.pluginProps.get('base', "") == "":
				errorMsgDict['deviceId'] = u"The selected bed doesn't have a base with adjustable height. Please select a bed with an adjustable base."
				errorMsgDict['showAlertText'] = errorMsgDict['deviceId']
				return (False, valuesDict, errorMsgDict)

			try:
				basePosition = int(valuesDict.get('basePosition', 0))
				# basePosition should be an integer from 0 (flat) to 100 (fully raised).
			except ValueError:
				errorMsgDict['basePosition'] = u"Set the Percent Raised between 0 (flat) and 100 (fully raised)."
				errorMsgDict['showAlertText'] = errorMsgDict['basePosition']
				return (False, valuesDict, errorMsgDict)

			try:
				speed = int(valuesDict.get('speed', 0))
				# "speed" should be an integer of 0 or 1.
			except ValueError:
				errorMsgDict['speed'] = u"Select a Speed."
				errorMsgDict['showAlertText'] = errorMsgDict['speed']
				return (False, valuesDict, errorMsgDict)

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
					errorMsgDict['headOrFoot'] = u"The selected bed has a base that does not support foot adjustments. Either select \"Head\" for the \"Head or Foot\" control, or select a bed whose base has adjustable foot controls."
					errorMsgDict['showAlertText'] = errorMsgDict['headOrFoot']
					return (False, valuesDict, errorMsgDict)
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
				except Exception, e:
					errorMsgDict['basePosition'] = u"Percent Raised can only be a number between 0 and 100."
					errorMsgDict['showAlertText'] = errorMsgDict['basePosition']
					return (False, valuesDict, errorMsgDict)

			if speed == 0:
				speedName = u"Fast"
			elif speed == 1:
				speedName = u"Slow"

			descString += u"set the " + sideName + u" side " + headOrFootName + u" position of \"" + device.name + u"\" to " + str(basePosition) + " at a " + str(speedName) + " speed"

		valuesDict['description'] = descString
		return (True, valuesDict)

