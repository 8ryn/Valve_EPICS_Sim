import time
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
        self._open_switch_var = PLCVariable("Valve.open_switch", self._open_switch, ads_type=constants.ADST_BIT, symbol_type="BOOL")
        self._closed_switch = True
        self._closed_switch_var = PLCVariable("Valve.closed_switch", self._closed_switch, ads_type=constants.ADST_BIT, symbol_type="BOOL")
        self._pressure = 1.0
        self._pressure_var = ValvePLCVariable("Valve.pressure", self._pressure, ads_type=constants.ADST_REAL64, symbol_type="LREAL", valve=self, customSetter=pressure_set)
        self._interlock = False
        self._interlock_var = PLCVariable("Valve.interlock", self._interlock, ads_type=constants.ADST_BIT, symbol_type="BOOL")
        self._state = 'closed'
        self._state_var = PLCVariable("Valve.state", self._state.encode('utf-8'), ads_type=constants.ADST_STRING, symbol_type="STRING")
        self._transition_time = 1.0
        self.open_command_var = ValvePLCVariable("Valve.open", 0, ads_type=constants.ADST_BIT, symbol_type="BOOL", valve=self, customSetter=open_set)
        self.close_command_var = ValvePLCVariable("Valve.close", 0, ads_type=constants.ADST_BIT, symbol_type="BOOL", valve=self, customSetter=close_set)

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

    @property
    def interlock(self):
        return self._interlock

    @property
    def state(self):
        return self._state
    
    def set_plc_var(self, var: PLCVariable, value):
        var.value = mapToBytes(value, var.ads_type)

    def get_plc_vars(self):
        return [self._open_switch_var, self._closed_switch_var, self._pressure_var, self._interlock_var, self._state_var, self.open_command_var, self.close_command_var]

    def _transition(self, new_state):
        print(f"Transitioning from {self._state} to {new_state}")
        self._state = new_state
        self.set_plc_var(self._state_var, new_state)

    def open(self):
        if self._state == 'closed' and not self._interlock:
            self._closed_switch = False
            self.set_plc_var(self._closed_switch_var, False)
            self._transition('opening')
            time.sleep(self._transition_time)
            self._open_switch = True
            self.set_plc_var(self._open_switch_var, True)
            self._transition('open')
        else:
            print("Cannot open the valve due to interlock or current state")

    def close(self):
        if self._state == 'open' and not self._interlock:
            self._open_switch = False
            self._open_switch_var.value = False
            self.set_plc_var(self._open_switch_var, False)
            self._transition('closing')
            time.sleep(self._transition_time)
            self._closed_switch = True
            self._closed_switch_var.value = True
            self.set_plc_var(self._closed_switch_var, True)
            self._transition('closed')
        else:
            print("Cannot close the valve due to interlock or current state")


handler = AdvancedHandler()

#Construct valve object
valve = Valve()

for var in valve.get_plc_vars():
    handler.add_variable(var)

test_server = AdsTestServer(handler=handler, logging=True)
test_server.start()
test_server.join()