import time
import socketserver

    
class Valve:
    def __init__(self):
        self._open_switch = False
        self._closed_switch = True
        self._pressure = 1.0
        self._state = 'closed'
        self._interlock = False
        self._transition_time = 1

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

    def _transition(self, new_state):
        print(f"Transitioning from {self._state} to {new_state}")
        self._state = new_state

    def open(self):
        if self._state == 'closed' and not self._interlock:
            self._closed_switch = False
            self._transition('opening')
            time.sleep(self._transition_time)
            self._open_switch = True
            self._transition('open')
        else:
            print("Cannot open the valve due to interlock or current state")

    def close(self):
        if self._state == 'open' and not self._interlock:
            self._open_switch = False
            self._transition('closing')
            time.sleep(self._transition_time)
            self._closed_switch = True
            self._transition('closed')
        else:
            print("Cannot close the valve due to interlock or current state")


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

# Create the server, binding to localhost on port 9999
with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
