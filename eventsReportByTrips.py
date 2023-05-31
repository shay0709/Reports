# Below packages must be installed via pip
# This script generates two types of reports, event report and trip summary report.
# The script retrieves a list of devices from a cloud API and iterates over each device to get a list of trips recorded within the specified time frame.
# For each trip, the script retrieves a list of events and generates an event report.
# It also generates a summary report for each device with the total distance covered during the trips.
import requests
import json
import pprint
import time
import datetime as DT
from jproperties import Properties
from datetime import datetime, timedelta
import subprocess

configs = Properties()
with open('app-config.properties', 'rb') as config_file:
    configs.load(config_file)

if (configs.get("CLOUD").data == 'EU'):
    cloud_url = "https://api.de.surfsight.net"
else:
    cloud_url = "https://api-prod.surfsight.net"

reportStartTime = configs.get("REPORT_START_TIME").data
reportStartDate = configs.get("REPORT_START_DATE").data
reportEndTime = configs.get("REPORT_END_TIME").data
reportEbdDate = configs.get("REPORT_END_DATE").data
reportFileLocation = configs.get("REPORT_LOCATION").data
# datetime object containing current date and time
now = datetime.now()
dt_string = now.strftime("%d%m%Y %H%M%S")
reportFileName = reportFileLocation + "EVENT_REPORT_" + dt_string + ".csv"
summaryFileName = reportFileLocation + "TRIP_SUMMARY_REPORT_" + dt_string + ".csv"
with open(reportFileName, "w") as o:
    o.write('***EVENT Report from ' + reportStartDate + ' at ' + reportStartTime + ' until ' + reportEbdDate + ' at ' + reportEndTime + '***' + "\n")
    o.write('IMEI , '
          'Device Name , '
          'Trip Start Time , '
          'Trip End Time , '
          'Trip Distance , '
          'Total Events Number Without Beeps , '
          'Event Type , '
          'Event Time'
          "\n")
# Generate Login Token
with open(summaryFileName, "w") as s:
    s.write(
        '***TRIPS SUMMARY Report from ' + reportStartDate + ' at ' + reportStartTime + ' until ' + reportEbdDate + ' at ' + reportEndTime + '***' + "\n")
    s.write('IMEI , '
            'Device Name , '
            'Date Time From , '
            'Date Time To , '
            'Trips Distance Total'
            "\n")
auth_data = {"email":configs.get("CLOUD_USER").data,"password":configs.get("CLOUD_PASSWORD").data}
login_api = requests.post(cloud_url + '/v2/authenticate',json=auth_data)
login_data = json.loads(login_api.content.decode('utf-8'))
token = login_data['data']['token']

dateTimeFromStr = reportStartDate + " " + reportStartTime
dateTimeToStr = reportEbdDate + " " + reportEndTime

dayDelta = DT.timedelta(days=1)

dateTimeFromObj = datetime.strptime(dateTimeFromStr, '%Y-%m-%d %H:%M:%S')
dateTimeToObj = datetime.strptime(dateTimeToStr, '%Y-%m-%d %H:%M:%S')


try:
        token_header = {"Authorization": "Bearer " + token}
        getDevicesList = requests.get(cloud_url + '/v2/organizations/' + configs.get("ORGANIZATION_ID").data + '/devices',
                                      headers=token_header)
        getDevicesListResponse = json.loads(getDevicesList.content.decode('utf-8'))
        print('Total devices in the list:', len(getDevicesListResponse['data']))
        for n in getDevicesListResponse['data']:
            imei = n['imei']
            deviceName = n['name']
            time.sleep(0.5)
            for i in range((dateTimeToObj - dateTimeFromObj).days + 1):
                try:
                    iterationStartDate = dateTimeFromObj + i * dayDelta
                    iterationEndDate = iterationStartDate + 1 * dayDelta
                    if(iterationEndDate > dateTimeToObj):
                        iterationEndDate = dateTimeToObj
                    getListOfTrips = requests.get(
                        cloud_url + '/v2/devices/' + imei + '/trips?start=' + str(iterationStartDate.date()) + 'T' + iterationStartDate.strftime("%H:%M:%S") + 'Z&end=' + str(iterationEndDate.date()) + 'T' + iterationEndDate.strftime("%H:%M:%S") + 'Z',
                        headers=token_header)
                    getListOfTrips.raise_for_status()
                    print(cloud_url + '/v2/devices/' + imei + '/trips?start=' + str(iterationStartDate.date()) + 'T' + iterationStartDate.strftime("%H:%M:%S") + 'Z&end=' + str(iterationEndDate.date()) + 'T' + iterationEndDate.strftime("%H:%M:%S") + 'Z')
                    getListOfTripsResponse = json.loads(getListOfTrips.content.decode('utf-8'))
                    if len(getListOfTripsResponse['data']) == 0:
                        with open(summaryFileName, "a") as s:
                            s.write(imei + "," + deviceName + "," + str(
                                iterationStartDate.date()) + 'T' + iterationStartDate.strftime("%H:%M:%S")
                                    + "," + str(iterationEndDate.date()) + 'T' + iterationEndDate.strftime(
                                "%H:%M:%S") + ", 0" + "\n")
                        continue
                    dailyDistance = 0
                    for index, j in enumerate(getListOfTripsResponse['data']):
                        tripStartTime = j['start']['time']
                        tripStartTimeIso = DT.datetime.utcfromtimestamp(tripStartTime).isoformat()
                        tripStartTimeIsoForEventsList = tripStartTimeIso + '.000Z'
                        tripEndTime = j['end']['time']
                        tripEndTimeIso = DT.datetime.utcfromtimestamp(tripEndTime).isoformat()
                        tripEntTimeIsoForEventsList = tripEndTimeIso + '.000Z'
                        tripDistance = j['distance']
                        totalNumberOfEvents = j['eventsCount']
                        dailyDistance += tripDistance
                        if (totalNumberOfEvents == 0):
                            continue
                        else:
                            getEventsList = requests.get(
                                cloud_url + '/v2/devices/' + imei + '/events?start=' + tripStartTimeIsoForEventsList + '&end=' + tripEntTimeIsoForEventsList,
                                headers=token_header)
                            getEventsList.raise_for_status()
                            if getEventsList.status_code != 204:
                                getEventsListResponse = json.loads(getEventsList.content.decode('utf-8'))
                            for ind, i in enumerate(getEventsListResponse['data']):
                                eventEntry = str(imei) + "," + deviceName + "," + tripStartTimeIso + "," + tripEndTimeIso + "," + str(tripDistance) + "," + str(totalNumberOfEvents) + "," + i['eventType'] + "," + i['time'] + "\n"
                                with open(reportFileName, "a") as o:
                                    o.write(eventEntry)
                    with open(summaryFileName, "a") as s:
                                    s.write( imei + "," + deviceName + "," + str(iterationStartDate.date()) + 'T' + iterationStartDate.strftime("%H:%M:%S")
                                            + "," + str(iterationEndDate.date()) + 'T' + iterationEndDate.strftime("%H:%M:%S")+ ","  + str(dailyDistance) + "\n")
                except requests.exceptions.HTTPError:
                    print (imei + ' Request time out')
                    continue
        subprocess.call(['chmod', '0744', reportFileName])
except KeyError:
    print(imei + ' offline')


