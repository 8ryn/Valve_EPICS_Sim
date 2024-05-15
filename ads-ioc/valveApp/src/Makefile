TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================

#=============================
# Build the IOC application

PROD_IOC = valve
# valve.dbd will be created and installed
DBD += valve.dbd

# valve.dbd will be made up from these files:
valve_DBD += base.dbd

# Include dbd files from all support applications:
#valve_DBD += xxx.dbd
valve_DBD += asyn.dbd ads.dbd busySupport.dbd calcSupport.dbd stream.dbd drvAsynIPPort.dbd asSupport.dbd
valve_DBD += pvxsIoc.dbd

# Add all the support libraries needed by this IOC
#valve_LIBS += xxx
valve_LIBS += asyn ads busy calc stream autosave
valve_LIBS += pvxsIoc pvxs

# valve_registerRecordDeviceDriver.cpp derives from valve.dbd
valve_SRCS += valve_registerRecordDeviceDriver.cpp

# Build the main IOC entry point on workstation OSs.
valve_SRCS_DEFAULT += valveMain.cpp
valve_SRCS_vxWorks += -nil-

# Add support from base/src/vxWorks if needed
#valve_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# Finally link to the EPICS Base libraries
valve_LIBS += $(EPICS_BASE_IOC_LIBS)

#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

