#!../../bin/linux-x86_64/valve

#- You may have to change valve to something else
#- everywhere it appears in this file

< envPaths

cd "${TOP}"

epicsEnvSet("STREAM_PROTOCOL_PATH", "/home/bar/Projects/HVEE_Simulation/ads-ioc/data")

## Register all support components
dbLoadDatabase "dbd/valve.dbd"
valve_registerRecordDeviceDriver pdbbase

# Set local AMS net ID
#AdsSetLocalAMSNetID("192.168.1.7.1.1")

drvAsynIPPortConfigure ("V1", "localhost:9999")

epicsEnvSet("PREFIX_VALVEDEMO", "VALVE-DEMO-01")
epicsEnvSet("PORT_VALVEDEMO", "valve-demo-port")
#epicsEnvSet("IP_VALVEDEMO", "127.0.0.1")
#epicsEnvSet("AMS_ID_VALVEDEMO", "127.0.0.1.1.1")

## Load record instances
dbLoadRecords("db/valve.db","P=$(PREFIX_VALVEDEMO), PORT=$(PORT_VALVEDEMO)")

# Open ADS port
# AdsOpen(port_name,
#         remote_ip_address,
#         remote_ams_net_id,
#         sum_buffer_nelem (default: 500),
#         ads_timeout (default: 500 ms),
#         device_ads_port (default: 851),
#         sum_read_period (default: 1 ms))
#AdsOpen("$(PORT_VALVEDEMO)", "$(IP_VALVEDEMO)", "$(AMS_ID_VALVEDEMO)", "500", "500", "48898")

# Enable asyn trace output for errors and warnings
#asynSetTraceMask("$(PORT_VALVEDEMO)", 0, 0x21)
# Alternatively, output everything
#asynSetTraceMask("$(PORT_VALVEDEMO)", 0, 0xff)

cd "${TOP}/iocBoot/${IOC}"
iocInit
