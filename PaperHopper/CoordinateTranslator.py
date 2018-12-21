from itertools import product
import json, math
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_message_builder
from pythonosc import udp_client

def multiply(matr_a, matr_b):
    """Return product of an MxP matrix A with an PxN matrix B."""
    cols, rows = len(matr_b[0]), len(matr_b)
    resRows = range(len(matr_a))
    rMatrix = [[0] * cols for _ in resRows]
    for idx in resRows:
        for j, k in product(range(cols), range(rows)):
            rMatrix[idx][j] += matr_a[idx][k] * matr_b[k][j]
    return rMatrix


def convert_pts_with_mmv(MMV, pts):
    return [convert_pt_with_mmv(MMV, pt.X, pt.Y) for pt in pts]

def convert_pt_with_mmv(MMV, rawx, rawy):
    d = [[rawx, rawy, 1]]
    MM = [[MMV[0], MMV[1], MMV[2]], [MMV[3], MMV[4], MMV[5]], [MMV[6], MMV[7], MMV[8]]]
    res = multiply(d, MM)[0]
    x = res[0] / res[2]
    y = res[1] / res[2]
    return [x, y]


with open('calibration.csv') as json_data:
    d = json.load(json_data)
    if "keys" in d and "vals" in d:
        MMV = [float(x) for x in d["vals"][d["keys"].index("CalibrationMMV")]]
        ADJ = d["vals"][d["keys"].index("CalibrationAdjustment")]
        print(MMV)
        print(ADJ)

tuiostate = {} 
client = None

def tuio2dobj(*args):
    global tuiostate
#    print(unused_addr)
    if(args[1] == 'source'):
        convert_and_send_tuiostate(tuiostate)
        tuiostate = {}
    if(args[1] == 'set'):
        tuiostate[args[3]] = [args[3],args[4],args[5],args[6] / 2 / math.pi]

def convert_and_send_tuiostate(ts):
    global client 
    if client is not None:
        sorted_ts = sorted(ts.values())
        converted_ts = [convert_pt_with_mmv(MMV, v[1], v[2]) for v in sorted_ts]
        merged_ts = [[t[0][0], t[1][0], t[1][1], t[0][3]] for t in zip(sorted_ts, converted_ts)]
        print(merged_ts)
        client.send_message("/calibratedtuio", merged_ts)
#    print(sorted_ts)

if __name__ == "__main__":
    TUIO_IP = "127.0.0.1"
    TUIO_PORT = 3333
    GH_IP = "127.0.0.1"
    GH_PORT = 3334

    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/tuio", print)
    dispatcher.map("/tuio/2Dobj", tuio2dobj)
    dispatcher.map("/", print)

    server = osc_server.ThreadingOSCUDPServer((TUIO_IP, TUIO_PORT), dispatcher)

    client = udp_client.SimpleUDPClient(GH_IP, GH_PORT)

    server.serve_forever()

