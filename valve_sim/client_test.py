import pyads

pyads.add_route("127.0.0.1.1.1", "127.0.0.1")
plc = pyads.Connection("127.0.0.1.1.1", 48898, "127.0.0.1")

with plc:
    print(plc.read_by_name("Valve.closed_switch"))
    print(plc.read_by_name("Valve.pressure"))