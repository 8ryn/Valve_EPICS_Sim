import time
import threading
import struct
import ctypes
from datetime import datetime
from typing import Optional, Union, Callable

from pyads.testserver import AdvancedHandler, PLCVariable, AdsTestServer, AmsPacket
from pyads import constants, structs
from pyads.filetimes import dt_to_filetime
from pyads.pyads_ex import callback_store


def mapToBytes(value, ads_type):
    if isinstance(value, bytes):
        return value
    elif isinstance(value, str):
        return value.encode('utf-8')
    else:
        # try to pack value according to ads_type
        fmt = constants.DATATYPE_MAP[constants.ads_type_to_ctype[ads_type]]
        return struct.pack(fmt, value)


def mapFromBytes(value, ads_type):
    if isinstance(value, bytes):
        # try to unpack value according to ads_type
        fmt = constants.DATATYPE_MAP[constants.ads_type_to_ctype[ads_type]]
        return struct.unpack(fmt, value)[0]
    else:
        return value


#Extension of PLCVariable to allow custom behaviour when variables are written to
class ValvePLCVariable(PLCVariable):
    def __init__(
        self,
        name: str,
        value: Union[int, float, bytes],
        ads_type: int,
        symbol_type: str,
        valve: 'Valve',
        customSetter: Callable = None,
        index_group: Optional[int] = None,
        index_offset: Optional[int] = None,
    ) -> None:
        PLCVariable.__init__(self, name, value, ads_type, symbol_type, index_group=index_group, index_offset=index_offset)
        self.valve = valve
        self.customSetter = customSetter

    def write(self, value: bytes, request: AmsPacket = None):
        """Update the variable value, respecting notifications
            Replaces the default write function"""

        if self.value != value:
            if self.notifications:

                header = structs.SAdsNotificationHeader()
                header.hNotification = 0
                header.nTimeStamp = dt_to_filetime(datetime.now())
                header.cbSampleSize = len(value)

                # Perform byte-write into the header
                dst = ctypes.addressof(header) + structs.SAdsNotificationHeader.data.offset
                ctypes.memmove(dst, value, len(value))

                for notification_handle in self.notifications:

                    # It's hard to guess the exact AmsAddr from here, so instead
                    # ignore the address and search for the note_handle

                    for key, func in callback_store.items():

                        # callback_store is keyed by (AmsAddr, int)
                        if key[1] != notification_handle:
                            continue

                        header.hNotification = notification_handle
                        addr = key[0]

                        # Call c-wrapper for user callback
                        func(addr.amsAddrStruct(), header, 0)

        if self.customSetter is None: #Use default behaviour
            self.value = value
        else:
            self.customSetter(self, value)


def pressure_set(var: ValvePLCVariable, value: bytes):
    var.valve.pressure = mapFromBytes(value, var.ads_type)  #Pressure setter expects float


def open_set(var: ValvePLCVariable, value: bytes):
    var.valve.open()


def close_set(var: ValvePLCVariable, value: bytes):
    var.valve.close()

    
class Valve:
    def __init__(self):
        #Currently the variables are each implemented as both local variables and PLCVariables, this could be simplified now that this is working
        self._open_switch = False
        self._open_switch_var = PLCVariable("Valve.open_switch", self._open_switch, ads_type=constants.ADST_BIT, symbol_type="BOOL", index_group=61445, index_offset=10000)
        self._closed_switch = True
        self._closed_switch_var = PLCVariable("Valve.closed_switch", self._closed_switch, ads_type=constants.ADST_BIT, symbol_type="BOOL", index_group=61445, index_offset=10001)
        self._pressure = 1.0
        self._pressure_var = ValvePLCVariable("Valve.pressure", self._pressure, ads_type=constants.ADST_REAL64, symbol_type="LREAL", valve=self, customSetter=pressure_set, index_group=61445, index_offset=10002)
        self._interlock = False
        self._interlock_var = PLCVariable("Valve.interlock", self._interlock, ads_type=constants.ADST_BIT, symbol_type="BOOL", index_group=61445, index_offset=10003)
        self._state = 'closed'
        self._state_var = PLCVariable("Valve.state", self._state.encode('utf-8'), ads_type=constants.ADST_STRING, symbol_type="STRING", index_group=61445, index_offset=10004)
        self._transition_time = 1.0
        self.open_command_var = ValvePLCVariable("Valve.open", 0, ads_type=constants.ADST_BIT, symbol_type="BOOL", valve=self, customSetter=open_set, index_group=61445, index_offset=10005)
        self.close_command_var = ValvePLCVariable("Valve.close", 0, ads_type=constants.ADST_BIT, symbol_type="BOOL", valve=self, customSetter=close_set, index_group=61445, index_offset=10006)
        self._transition_error = False
        self._transition_error_var = PLCVariable("Valve.transition_error", self._transition_error, ads_type=constants.ADST_BIT, symbol_type="BOOL", index_group=61445, index_offset=10007)
        self._status_var = PLCVariable("Valve.status", 2, ads_type=constants.ADST_UINT16, symbol_type="UINT", index_group=61445, index_offset=10008)

    @property
    def open_switch(self):
        return self._open_switch

    @property
    def closed_switch(self):
        return self._closed_switch

    @property
    def pressure(self):
        return self._pressure

    @pressure.setter
    def pressure(self, value):
        self._pressure = value
        self.set_plc_var(self._pressure_var, value)
        if self._pressure < 1.0:
            self._interlock = True
            self.set_plc_var(self._interlock_var, True)
        else:
            self._interlock = False
            self.set_plc_var(self._interlock_var, False)
        self.__status_update()

    @property
    def interlock(self):
        return self._interlock

    @property
    def state(self):
        return self._state

    def __status_update(self):
        status = 0
        if self.open_switch:
            status += 1
        if self.closed_switch:
            status += 1 << 1
        if self._interlock:
            status += 1 << 2
        if self._transition_error:
            status += 1 << 3
        self.set_plc_var(self._status_var, status)

    def set_plc_var(self, var: PLCVariable, value):
        var.value = mapToBytes(value, var.ads_type)

    def get_plc_vars(self):
        return [self._open_switch_var, self._closed_switch_var, self._pressure_var, self._interlock_var, self._state_var, self.open_command_var, self.close_command_var, self._transition_error_var, self._status_var]

    def _transition(self, new_state):
        print(f"Transitioning from {self._state} to {new_state}")
        self._state = new_state
        self.set_plc_var(self._state_var, new_state)

    def open(self):
        open_thread = threading.Thread(target=self.__open_threaded)
        open_thread.start()

    def __open_threaded(self):
        if self._state == 'closed' and not self._interlock:
            self._transition_error = False
            self._closed_switch = False
            self.set_plc_var(self._closed_switch_var, False)
            self.set_plc_var(self._transition_error_var, False)
            self.__status_update()
            self._transition('opening')
            time.sleep(self._transition_time)
            self._open_switch = True
            self.set_plc_var(self._open_switch_var, True)
            self._transition('open')
        elif self._state == 'closed' and self._interlock:
            print("Cannot open the valve due to interlock")
            self._transition_error = True
            self.set_plc_var(self._transition_error_var, True)
        else:
            print("Valve already open")
        self.__status_update()

    def close(self):
        close_thread = threading.Thread(target=self.__close_threaded)
        close_thread.start()

    def __close_threaded(self):
        if self._state == 'open' and not self._interlock:
            self._open_switch = False
            self._transition_error = False
            self._open_switch_var.value = False
            self.set_plc_var(self._open_switch_var, False)
            self.set_plc_var(self._transition_error_var, False)
            self.__status_update()
            self._transition('closing')
            time.sleep(self._transition_time)
            self._closed_switch = True
            self._closed_switch_var.value = True
            self.set_plc_var(self._closed_switch_var, True)
            self._transition('closed')
        elif self._state == 'open' and self._interlock:
            print("Cannot close the valve due to interlock")
            self._transition_error = True
            self.set_plc_var(self._transition_error_var, True)
        else:
            print("Valve already closed")
        self.__status_update()


handler = AdvancedHandler()

#Construct valve object
valve = Valve()

for var in valve.get_plc_vars():
    handler.add_variable(var)

test_server = AdsTestServer(handler=handler, logging=True)
test_server.start()
test_server.join()