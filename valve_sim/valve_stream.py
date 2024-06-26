import time
import threading
import socketserver

    
class Valve:
    def __init__(self):
        self._open_switch = False
        self._closed_switch = True
        self._pressure = 1.0
        self._state = 'closed'
        self._interlock = False
        self._transition_time = 5
        self._transition_error = False

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
        if self._pressure < 1.0:
            self._interlock = True
        else:
            self._interlock = False

    @property
    def interlock(self):
        return self._interlock

    @property
    def state(self):
        return self._state
    
    @property
    def transition_error(self):
        return self._transition_error

    def get_status(self):
        status = 0
        if self.open_switch:
            status += 1
        if self.closed_switch:
            status += 1 << 1
        if self._interlock:
            status += 1 << 2
        if self._transition_error:
            status += 1 << 3
        return status

    def _transition(self, new_state):
        print(f"Transitioning from {self._state} to {new_state}")
        self._state = new_state

    def open(self):
        open_thread = threading.Thread(target=self.__open_threaded)
        open_thread.start()

    def __open_threaded(self):
        if self._state == 'closed' and not self._interlock:
            self._transition_error = False
            self._closed_switch = False
            self._transition('opening')
            time.sleep(self._transition_time)
            self._open_switch = True
            self._transition('open')
        elif self._state == 'closed' and self._interlock:
            print("Cannot open the valve due to interlock")
            self._transition_error = True
        else:
            print("Valve already open")


    def close(self):
        close_thread = threading.Thread(target=self.__close_threaded)
        close_thread.start()

    def __close_threaded(self):
        if self._state == 'open' and not self._interlock:
            self._transition_error = False
            self._open_switch = False
            self._transition('closing')
            time.sleep(self._transition_time)
            self._closed_switch = True
            self._transition('closed')
        elif self._state == 'open' and self._interlock:
            print("Cannot close the valve due to interlock")
            self._transition_error = True
        else:
            print("Valve already closed")
   

valve = Valve()


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        #print("Received from {}:".format(self.client_address[0]))
        string = str(self.data, "utf-8")
        #print(string)
        args = string.split()
        if args[0] == "get":
            match args[1]:
                case "open_switch":
                    reply = int(valve.open_switch)
                case "closed_switch":
                    reply = int(valve.closed_switch)
                case "interlock":
                    reply = int(valve.interlock)
                case "pressure":
                    reply = valve.pressure
                case "state":
                    reply = valve.state
                case "status":
                    reply = valve.get_status()
                case "transition_error":
                    reply = int(valve.transition_error)
                case _:
                    reply = "Invalid valve property"
        elif args[0] == "set":
            match args[1]:
                case "open":
                    valve.open()
                    reply = "OK"
                case "close":
                    reply = "OK"
                    valve.close()
                case "pressure":
                    if args[2] is None:
                        reply = "Pressure value required"
                    else:
                        try:
                            valve.pressure = float(args[2])
                            reply = "OK"
                        except ValueError:
                            reply = "Invalid pressure value"
                case _:
                    reply = "Invalid valve property"           
        else:
            print("Error: First argument must be get or set")

        reply_string = str(reply)
        self.request.sendall(bytes(reply_string + "\n", "utf-8"))


HOST, PORT = "localhost", 9999

#Old blocking code:
# Create the server, binding to localhost on port 9999
with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
