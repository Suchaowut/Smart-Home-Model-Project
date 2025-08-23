import network, socket, json, _thread
from irover import *
from time import sleep
from machine import Pin
import neopixel


w = IROVER()
w.output(i5,0)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)


prevAngle = 0
def smooth_servo(targetAngle, gap_ms):
    global prevAngle
    # if targetAngle == prevAngle: return
    step = 2 if targetAngle > prevAngle else -2
    for angle in range(prevAngle, targetAngle + step, step):
        w.servo(10,angle)
        time.sleep_ms(gap_ms)
    prevAngle = targetAngle


# w.servo(10, 0)
smooth_servo(0, 10)


# ===== Connect WiFi =====
def connect_wifi(ssid, password):
    if not wlan.isconnected():
        w.fill(0)
        w.show()
        print("Connecting to WiFi network: %s..." % ssid)
        w.text("Connect to %s " % ssid,0,0*8)
        w.show()
        wlan.connect(ssid, password)
        retries = 0
        while not wlan.isconnected() and retries < 10:
            sleep(1)
            retries += 1
        w.fill(0)
        w.show()
        print("Retry %d..." % retries)
        w.text("Retry %d..." % retries,0,0*8)
        if wlan.isconnected():
            print("WiFi connected!")
            print("Network config:", wlan.ifconfig())
            w.text("WiFi connected!",0,1*8)
            w.text("Network config",0,2*8)
            w.text("{}".format(wlan.ifconfig()[0]) ,0,3*8)
        else:
            print("Failed to connect")
            w.text("Failed to connect",0,1*8)
        w.show()

if not wlan.isconnected():
    pass
if not wlan.isconnected():
    connect_wifi('benchama', '')


gateEnable = False   # ปิดประตูไว้
indoorLightEnable = False  # ปิดไฟไว้
outdoorLightEnable = False # ปิดไฟไว้


gateState = False
indoorLightState = False
outdoorLightState = False
colorValue = '#342d2d'
busy_gate = False


# ===== NeoPixel Indoor Light =====
np = neopixel.NeoPixel(Pin(19), 12)
indoorLightColor = (0, 0, 0)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2],16) for i in (0,2,4))


def update_indoor_light():
    global indoorLightEnable, indoorLightColor
    indoorLightColor = hex_to_rgb(colorValue)
    for i in range(12):
        np[i] = indoorLightColor if indoorLightEnable else (0,0,0)
    np.write()
#     print("np {}".format(indoorLightColor))


# ===== Gate control =====
def gate():
    global gateEnable, gateState, busy_gate
    busy_gate = True
    if gateEnable:
        print("door opening")
#         w.servo(10, 180)
        smooth_servo(180, 10)  # เปิด
        sleep(0.5)
        gateState = True
    else:
        print("door closing")
#         w.servo(10, 0)
        smooth_servo(0, 10)    # ปิด
        sleep(0.5)
        gateState = False
    busy_gate = False

# ===== Background Sensoring =====
def sensoring():
    global outdoorLightState
    while True:
        if outdoorLightEnable:
            LDRval = w.analog(32)
            if LDRval != -1:
                # light_percent = (LDRval / 4095) * 100
                print("Light Level:", LDRval, "%")
                if LDRval < 60: # เปิดไฟ
#                     if not outdoorLightState:
                    w.output(i5, 1)
                    outdoorLightState = True
                    print("Outdoor light turned ON (auto)")
                else:  # ปิดไฟ
#                     if outdoorLightState:
                    w.output(i5, 0)
                    outdoorLightState = False
                    print("Outdoor light turned OFF (auto)")
            else: print("Can't read LDRval")
        else:
            w.output(i5,0)
            


            # อ่านค่า Ultrasonic
#         distance = w.analog(34)
#         if distance != -1:
#             print("Distance:", distance, "cm")
               
        sleep(1)

_thread.start_new_thread(sensoring, ())


def web(gateEnable, indoorLightEnable, outdoorLightEnable, colorValue):
    checked_gate = "checked" if gateEnable else ""
    checked_indoor = "checked" if indoorLightEnable else ""
    checked_outdoor = "checked" if outdoorLightEnable else ""
    checked_alarm = ""
    css="""
    body {
        display: flex !important;
        flex-direction: column !important;
        min-height: 100vh !important;
        margin: 0 !important;
    }
    .container {
        flex: 1 0 auto !important;
    }
    footer {
        flex-shrink: 0 !important;
    }
    h2 {
        font-weight: bold;
        margin-bottom: 20px;
    }
    .blocky {
        background-color: #fff;
        border-radius: 20px;
        padding: 20px;
        width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: left;
        margin-bottom: 20px;
    }
    .block-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .status-text {
        font-size: 16px;
        margin-bottom: 15px;
    }
    
    .toggle-switch {
        width: 60px;
        height: 30px;
        position: relative;
        display: inline-block;
    }
    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }
    .toggle-slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(145deg, #ccc, #e0e0e0);
        transition: 0.3s;
        border-radius: 34px;
    }
    .toggle-slider:before {
        position: absolute;
        content: "";
        height: 22px;
        width: 22px;
        left: 4px;
        bottom: 4px;
        background: #fff;
        transition: transform 0.3s ease, background 0.3s ease;
        border-radius: 50%;
    }
    input:checked + .toggle-slider {
        background: linear-gradient(145deg, #0d6efd, #3b82f6);
    }
    input:checked + .toggle-slider:before {
        transform: translateX(30px);
        background: #f0f9ff;
    }
    
    .gate-toggle {
        width: 60px;
        height: 30px;
        position: relative;
        display: inline-block;
    }
    .gate-toggle input {
        opacity: 0;
        width: 0;
        height: 0;
    }
    .gate-toggle .toggle-slider {
        position: relative;
        display: flex;
        align-items: center;
        border-radius: 30px;
        background: linear-gradient(145deg, #d32f2f, #ef5350);
        padding: 0 5px;
        height: 100%;
        box-sizing: border-box;
        transition: background 0.3s ease;
    }
    .gate-toggle .toggle-slider:before {
        content: "";
        position: absolute;
        height: 22px;
        width: 22px;
        top: 4px;
        left: 4px;
        background: #fff;
        border-radius: 50%;
        transition: transform 0.3s ease;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25), inset 0 2px 2px rgba(255,255,255,0.6);
    }
    .gate-toggle .toggle-slider::after {
        content: "🔒";
        position: absolute;
        top: 50%;
        right: 5px;
        transform: translateY(-50%);
        font-size: 16px;
        pointer-events: none;
        color: white;
        transition: all 0.3s ease;
        z-index: 0;
    }
    .gate-toggle input:checked + .toggle-slider {
        background: linear-gradient(145deg, #2e7d32, #66bb6a);
    }
    .gate-toggle input:checked + .toggle-slider:before {
        transform: translateX(30px);
    }
    .gate-toggle input:checked + .toggle-slider::after {
        content: "🔓";
        left: 5px;
    }
    
    .color-picker {
        width: 100%;
        margin-bottom: 10px;
        padding: 8px;
        border-radius: 10px;
        font-size: 15px;
        border: 1px solid #ddd;
    }
    .value-display {
        font-size: 15px;
        font-weight: bold;
        color: #333;
        margin-top: 5px;
    }
    footer {
        flex-shrink: 0;
        background: #1f2937;
        color: #fff;
        padding: 20px;
        border-radius: 20px 20px 0 0;
        box-shadow: 0 -3px 12px rgba(0,0,0,0.2);
        text-align: center;
    }
    .team-container {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 15px;
    }
    .team-card {
        background: #374151;
        color: #fff;
        border-radius: 15px;
        padding: 10px 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        font-size: 14px;
    }
    .team-card img {
        object-fit: cover;
        object-position: 50% 30%;
        border-radius: 50%;
        vertical-align: middle;
    }
    .team-card span {
        vertical-align: middle;
        font-weight: 500;
    }
    """
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Home Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>{css}</style>
    </head>
    <body>
        <div class="container">
            <h2 class="text-center text-dark">🏠 Smart Home Dashboard</h2>
            <div class="d-flex flex-wrap gap-3 justify-content-center">
                <!-- Fence Gate -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>Fence Gate</h3>
                        <label class="toggle-switch gate-toggle">
                            <input type="checkbox" id="gateToggle" onchange="updateGateState()" {checked_gate}>
                            <span class="toggle-slider"></span>
                        </label>
                        <!-- Spinner -->
                        <div id="gateSpinner" class="spinner" style="display:none;"></div>
                    </div>
                    <p class="status-text">Status: <span id="gateState">{gate_state}</span></p>
                </div>

                <!-- Indoor Light -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>Indoor Light</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="indoorLightToggle" onchange="updateIndoorLightState()" {checked_indoor}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">Status: <span id="indoorLightState">{indoor_state}</span></p>
                    <label for="rgbColor" class="mb-2">Select RGB Color:</label>
                    <input type="color" id="rgbColor" class="color-picker" value="{color}" onchange="updateRGBColor()">
                    <p class="value-display">Selected Color: <span id="colorValue">{color}</span></p>
                </div>

                <!-- Outdoor Light -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>Outdoor Light</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="outdoorLightToggle" onchange="updateOutdoorLightState()" {checked_outdoor}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">Status: <span id="outdoorLightState">{outdoor_state}</span></p>
                </div>

                <!-- Burglar Alarm -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>Burglar Alarm</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="alarmToggle" onchange="updateAlarmState()" {checked_alarm}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">Status: <span id="alarmState">{alarm_state}</span></p>
                </div>
            </div>
        </div>

        <footer>
            <h6 class="mb-3">ผู้จัดทำ</h6>
            <div class="team-container">
                <div class="team-card">
                    <img src="https://img2.pic.in.th/pic/download4aee50d21065ec30.jpg" width="40" height="40">
                    <span class="ms-2">นายธฤต สูนสมงาม</span>
                </div>
                <div class="team-card">
                    <img src="https://img5.pic.in.th/file/secure-sv1/download-13669a60cd5f7fdfb.jpg" width="40" height="40">
                    <span class="ms-2">นายศุภกร อุไรกุล</span>
                </div>
                <div class="team-card">
                    <img src="https://img2.pic.in.th/pic/download4ad9e99a6422243a.png" width="40" height="40">
                    <span class="ms-2">นายสุเชาวุฒิ ดำฤทธิ์</span>
                </div>
                <div class="team-card">
                    <img src="https://img5.pic.in.th/file/secure-sv1/download-26ed3cbfd4ffc145a.jpg" width="40" height="40">
                    <span class="ms-2">นางสาวภคพร ทองสุทธิ์</span>
                </div>
            </div>
            <p class="mt-3">Smart Home Project</p>
        </footer>
        
        <script>
            function sendStateToServer(endpoint, state) {{
                fetch(endpoint, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ state: state }}),
                }})
                .then(response => response.json())
                .then(data => {{
                    console.log('State updated:', data);
                    fetchData();
                }})
                .catch(error => {{
                    console.error('Error updating state:', error);
                }});
            }}

            function fetchData() {{
                fetch('/data')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('gateState').innerText = data.gateState ? "Open" : "Closed";
                        document.getElementById('indoorLightState').innerText = data.indoorLightState ? "On" : "Off";
                        document.getElementById('outdoorLightState').innerText = data.outdoorLightState ? "On" : "Off";
                        document.getElementById('colorValue').innerText = data.color;
                        document.getElementById('gateToggle').disabled = data.busy_gate;
                    }})
                    .catch(error => console.error('Error fetching data:', error));
            }}

            setInterval(fetchData, 2000);

            function updateGateState() {{
                const toggle = document.getElementById('gateToggle');
                document.getElementById('gateToggle').disabled = true;
                const state = toggle.checked;
                fetch('/gate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ state: state }})
                }})
                .then(res => res.json())
                .then(data => {{
                    if (data.status === "busy") {{
                        document.getElementById('gateToggle').disabled = true;
                    }}
                    fetchData();
                }})
                .catch(err => {{
                    console.error(err);
                    spinner.style.display = "none";
                    toggle.parentElement.style.display = "inline-block";
                }});
            }}

            function updateIndoorLightState() {{
                const state = document.getElementById('indoorLightToggle').checked;
                sendStateToServer('/indoor', state);
            }}

            function updateRGBColor() {{
                const color = document.getElementById('rgbColor').value;
                sendStateToServer('/color', color);
            }}

            function updateOutdoorLightState() {{
                const state = document.getElementById('outdoorLightToggle').checked;
                sendStateToServer('/outdoor', state);
            }}

            function updateAlarmState() {{
                const state = document.getElementById('alarmToggle').checked;
                sendStateToServer('/alarm', state);
            }}
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """.format(
        checked_gate = "checked" if gateEnable else "",
        gate_state   = "Open" if gateEnable else "Closed",
        checked_indoor = "checked" if indoorLightEnable else "",
        indoor_state   = "On" if indoorLightEnable else "Off",
        color = colorValue,
        checked_outdoor = "checked" if outdoorLightEnable else "",
        outdoor_state   = "On" if outdoorLightEnable else "Off",
        checked_alarm = checked_alarm,
        alarm_state   = "On" if checked_alarm else "Off"
    )



# ===== Web server thread =====
def web_server():
    global gateEnable, indoorLightEnable, outdoorLightEnable, colorValue, indoorLightColor
    addr = socket.getaddrinfo("0.0.0.0",80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server listening", addr)
    while True:
        try:
            cl, addr = s.accept()
            req = cl.recv(1024).decode()
            
            if req.startswith('GET /data'):
                response = json.dumps({
                    'gateState': gateState,
                    'indoorLightState': indoorLightEnable,
                    'outdoorLightState': outdoorLightEnable,
                    'color': colorValue,
                    'busy_gate': busy_gate
                })
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                cl.send(response)
            
            elif req.startswith('GET / '): 
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                cl.send(web(gateEnable, indoorLightEnable, outdoorLightEnable, colorValue))
            
            elif req.startswith('POST'):
                req_line = req.split("\r\n")[0]
                method, path, _ = req_line.split()
                body = req.split("\r\n\r\n",1)[1] if "\r\n\r\n" in req else ""
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                
                data = json.loads(body or "{}")
                
                if path=="/gate":
                    if not busy_gate:
                        gateEnable = data.get("state",False)
                        _thread.start_new_thread(gate,())
                        cl.send(json.dumps({"status":"success"}))
                    else:
                        cl.send(json.dumps({"status":"busy"}))
                elif path=="/indoor":
                    indoorLightEnable = data.get("state",False)
                    update_indoor_light()
                    cl.send(json.dumps({"status":"success"}))
                elif path=="/outdoor":
                    outdoorLightEnable = data.get("state",False)
                    cl.send(json.dumps({"status":"success"}))
                elif path=="/color":
                    colorValue = data.get("state","#000000")
                    update_indoor_light()
                    cl.send(json.dumps({"status":"success"}))
                else:
                    cl.send(json.dumps({"status":"error"}))
            
            cl.close()
        except Exception as e:
            print("Web server error:", e)

_thread.start_new_thread(web_server, ())

# ===== Main loop =====
while True:
    update_indoor_light()
    sleep(0.1)

