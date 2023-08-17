SleepyBed IQ is a plugin for Indigo Domotics's Indigo 7 home control software which allows you to monitor your Select Comfort SleepNumber bed through the SleepIQ online sleep monitoring system.

SleepyBed IQ offers the following features:

•	Full Be Status. All known exposed data about your SleepNumber bed is populated into the SleepNumber Bed device's custom states list. SleepNumber Bed devices in Indigo appear as sensor devices that are "on" if anyone is in bed and "off" if no one is in bed. Bed status is updated every 15 seconds.

Installation

Download the SleepyBed IQ zip file (link above) to the computer running the Indigo server. If the file is not already unzipped, double-click the .zip file to unzip it. Open the folder that is expanded from the zip file and double-click the SleepyBed IQ.indigoPlugin file. The Indigo client will open and prompt to install the plugin. Click the option to install and enable the plugin. You'll be prompted to configure the plugin. Enter your SleepIQ web site username (usually your email address) and password then click the "Verify" button to verify the credentials. Click "Save".

Usage

You can create an Indigo device for each SleepNumber bed you've registered with the SleepIQ web site.

1.	Create a new Indigo device (click "New..." in the Devices window). Select the "SleepyBed IQ" plugin as the device Type. Select "SleepNumber Bed" as the device type.
2.	A "Configure SleepNumber Bed" dialog will appear. Select the "SleepNumber Bed" you want to monitor and click Okay.

Limitations

•	You cannot control any aspect of the SleepNumber Bed.
•	Historic sleep data from the SleepIQ web site is not available through this plugin.  However, you could track bed state changes and compile your own sleep history data.

