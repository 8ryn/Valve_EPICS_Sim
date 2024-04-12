#!../../bin/linux-x86_64/valve

#- You may have to change valve to something else
#- everywhere it appears in this file

< envPaths

cd "${TOP}"

## Register all support components
dbLoadDatabase "dbd/valve.dbd"
valve_registerRecordDeviceDriver pdbbase

## Load record instances
#dbLoadRecords("db/valve.db","user=bar")

cd "${TOP}/iocBoot/${IOC}"
iocInit

## Start any sequence programs
#seq sncxxx,"user=bar"
