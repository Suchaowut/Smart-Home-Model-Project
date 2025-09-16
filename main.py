import network, socket, json, _thread, random
from irover import *
from time import sleep
from machine import Pin
import neopixel

w = IROVER()
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

LEDpins = (i5,i6,5)
for pin in LEDpins:
    w.output(pin, 0)

prevAngle10 = 90
prevAngle11 = 0
prevAngle12 = 90

def smooth_servo11(targetAngle, gap_ms):
    global prevAngle11
    step = 2 if targetAngle > prevAngle11 else -2
    for angle in range(prevAngle11, targetAngle + step, step):
        w.servo(11,angle)
        time.sleep_ms(gap_ms)
    prevAngle11 = targetAngle

def smooth_both_servos(target10, target12, gap_ms):
    global prevAngle10, prevAngle12

    # คำนวณ step สำหรับแต่ละ servo
    step10 = 2 if target10 > prevAngle10 else -2
    step12 = 2 if target12 > prevAngle12 else -2

    # กำหนดจำนวน step ที่ต้องวน
    steps10 = abs((target10 - prevAngle10) // step10) # abs[(0-90) // 2] = 45 ครั้ง
    steps12 = abs((target12 - prevAngle12) // step12)
    max_steps = max(steps10, steps12) + 1 # ใครมีค่ามากสุดเอามา +1 steps เก็บไว้ใน max_steps

    angle10 = prevAngle10
    angle12 = prevAngle12

    for i in range(max_steps):
        if (step10 > 0 and angle10 < target10) or (step10 < 0 and angle10 > target10): # ยังไม่ถึงมุม target ต้องเพิ่มอีก step ละ 2 องศา
            angle10 += step10
            if (step10 > 0 and angle10 > target10) or (step10 < 0 and angle10 < target10): # angle10 += step10 แล้ว เกินมุม target ให้เซ็ตเท่า target ไปเลย
                angle10 = target10
            w.servo(10, angle10)

        if (step12 > 0 and angle12 < target12) or (step12 < 0 and angle12 > target12):
            angle12 += step12
            if (step12 > 0 and angle12 > target12) or (step12 < 0 and angle12 < target12):
                angle12 = target12
            w.servo(12, angle12)

        time.sleep_ms(gap_ms)
    prevAngle10 = target10
    prevAngle12 = target12
    
smooth_both_servos(prevAngle10, prevAngle12, 15)

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
    connect_wifi('benchama', '')


gateEnable = False   # ปิดประตูไว้
indoorLightEnable = False  # ปิดไฟไว้
outdoorLightEnable = True # เปิดไฟไว้
ClothesReEnable = False

AngleGate1 = 90
AngleGate2 = 90

gateState = False
busy_gate = False
indoorLightState = False
outdoorLightState = True
indoorPartyEnable = False
colorValue = '#ff1493'
ClothesRe_state = False
busy_clothesre = False
ClothesReAutoMode = False

LDRval = 0
LDRComparator = 60
Moistval = 0
MoistComparator = 3000

# ===== NeoPixel Indoor Light =====
np2 = neopixel.NeoPixel(Pin(12),3)
for t in range(3):
    np2[t] = (0, 0, 0)
    np2.write()

np = neopixel.NeoPixel(Pin(19), 12)
indoorLightColor = (0, 0, 0)

def hex_to_rgb(hex_color): # #ff1493
    hex_color = hex_color.lstrip('#') # result ff1493
    return tuple(int(hex_color[i:i+2],16) for i in (0,2,4)) # result ( 255, 20, 147 )


def update_indoor_light():
    global indoorLightEnable, indoorLightColor, indoorPartyEnable
    if indoorLightEnable:
        if indoorPartyEnable:
            for i in range(12):
                np[i] = (random.randrange(0, 256),random.randrange(0, 256),random.randrange(0, 256))
            np.write()
        else:
            indoorLightColor = hex_to_rgb(colorValue)
            for i in range(12):
                np[i] = indoorLightColor if indoorLightEnable else (0,0,0)
            np.write()
    else :
        for i in range(12):
            np[i] = (0,0,0)
            np.write()

_thread.start_new_thread(update_indoor_light, ())

# ===== Gate control =====
def gate():
    global gateEnable, gateState, busy_gate
    busy_gate = True
    if gateEnable:
        print("door opening")
        smooth_both_servos(0, 180, 15)
        sleep(0.5)
        gateState = True
    else:
        print("door closing")
        smooth_both_servos(90, 90, 15)
        sleep(0.5)
        gateState = False
    busy_gate = False
    
def update_gateAngle():
    global gateEnable, gateState, busy_gate, AngleGate1, AngleGate2
    busy_gate = True
    if gateEnable:
        smooth_both_servos(AngleGate1, AngleGate2, 15)
    busy_gate = False

# ===== Background Sensoring =====
def LDRsensoring():
    global outdoorLightEnable, outdoorLightState, LDRval
    while True:
        if outdoorLightEnable:
            LDRval = w.analog(32)
            if LDRval != -1:
                print("Light Analog:", LDRval)
                if LDRval < LDRComparator: # เปิดไฟ
                    for pin in LEDpins:
                        w.output(pin, 1)
                    outdoorLightState = True
                    print("Outdoor light turned ON (auto)")
                else:  # ปิดไฟ
                    for pin in LEDpins:
                        w.output(pin, 0)
                    outdoorLightState = False
                    print("Outdoor light turned OFF (auto)")
            else: print("Can't read LDRval")
        else:
            w.output(i5,0)
        sleep(1)

def Moistsensoring():
    global ClothesReEnable, ClothesRe_state, ClothesReAutoMode, Moistval, busy_clothesre
    while True:
        if ClothesReEnable:
            if ClothesReAutoMode:
                Moistval = w.analog(33)
                if Moistval != -1:
                    print("Moist Analog:", Moistval)
                    if Moistval > MoistComparator: # Retrieved
                        smooth_servo11(0, 20)
                        ClothesRe_state = False
                        ClothesReAutoMode = False
                        ClothesReEnable = False
                        print("Clothes Retrieved (auto)")
                else: print("Can't read Moistval")
            else :
                busy_clothesre = True
                smooth_servo11(180, 20)
                busy_clothesre = False
                ClothesRe_state = True
        else :
            busy_clothesre = True
            smooth_servo11(0, 20)
            busy_clothesre = False
            ClothesRe_state = False
        sleep(1)

_thread.start_new_thread(LDRsensoring, ())
_thread.start_new_thread(Moistsensoring, ())


def web(gateEnable, indoorLightEnable, outdoorLightEnable, colorValue, MoistVal, MoistComparator, ClothesReAutoMode, LDRval, LDRComparator):
    checked_gate = "checked" if gateEnable else ""
    checked_indoor = "checked" if indoorLightEnable else ""
    checked_party = "checked" if indoorPartyEnable else ""
    checked_outdoor = "checked" if outdoorLightEnable else ""
    checked_ClothesRe = "checked" if ClothesReEnable else ""
    checked_ClothesReAutoMode = "checked" if ClothesReAutoMode else ""
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Home Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/Suchaowut/Smart-Home-Model-Project/style.css">
        <style>body{{display:flex!important;flex-direction:column!important;min-height:100vh!important;margin:0!important}}.container{{flex:1 0 auto!important}}footer{{flex-shrink:0!important}}</style>
        <style>
            .progress-container {{
                margin-top: 10px;
            }}
            .progress-bar {{
                position: relative;
                width: 100%;
                height: 20px;
                background-color: #eee;
                border-radius: 10px;
                overflow: hidden;
            }}
            .sensor-value {{
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                width: 0%;
                background-color: #0d6efd;
                transition: width 0.2s;
                z-index: 1;
            }}
            .threshold-mark {{
                position: absolute;
                top: 0;
                height: 100%;
                width: 2px;
                background-color: red;
                left: 0%;
                z-index: 2;
            }}
            .progress-labels {{
                display: flex;
                justify-content: space-between;
                font-size: 12px;
            }}
            </style>
    </head>
    <body>
        <div class="container">
            <h2 class="text-center text-dark">🏠 Smart Home Dashboard</h2>
            <div class="d-flex flex-wrap gap-3 justify-content-center">
            
                <!-- Fence Gate -->
                <div class="blocky">
                  <div class="block-header">
                    <h3>ประตูรั้วบ้าน</h3>
                    <label class="toggle-switch gate-toggle">
                      <input type="checkbox" id="gateToggle" onchange="updateGateState()" {checked_gate}>
                      <span class="toggle-slider"></span>
                    </label>
                  </div>
                  <div class="mb-3">
                    <label for="customDoorRange1" class="form-label">
                        ประตูบานที่ 1 : <output id="doorValue1" class="fw-bold">90</output> องศา
                    </label>
                    <div class="d-flex align-items-center gap-2">
                      <input type="range" class="form-range flex-grow-1" id="customDoorRange1" min="0" max="180" value="90"  oninput="doorValue1.value=this.value">
                    </div>
                  </div>

                  <div class="mb-3">
                    <label for="customDoorRange2" class="form-label">
                      ประตูบานที่ 2 : <output id="doorValue2" class="fw-bold">90</output> องศา
                    </label>
                    <div class="d-flex align-items-center gap-2">
                      <input type="range" class="form-range flex-grow-1" id="customDoorRange2" min="0" max="180" value="90" oninput="doorValue2.value=this.value">
                    </div>
                  </div>
                  <div class="d-flex justify-content-center">
                      <button id="confirmAngle" type="button" class="btn btn-primary btn-xs" onclick="sendGateAngle()">ยืนยันการปรับแต่งองศาประตู</button>
                  </div>
                </div>

                <!-- Indoor Light -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>ไฟในบ้าน</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="indoorLightToggle" onchange="updateIndoorLightState()" {checked_indoor}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">สถานะ: <span id="indoorLightState">{indoor_state}</span></p>
                    <label for="rgbColor" class="mb-2">
                        สีที่เลือก : <span class="value-display" id="NameColor">{color}</span>
                    </label>
                    <input type="color" id="rgbColor" class="color-picker" value="{color}" onchange="updateRGBColor()">
                    <div class="block-header">
                        <h5>โหมดปาร์ตี้</h5>
                        <label class="toggle-switch">
                            <input type="checkbox" id="partyModeToggle" onchange="updateIndoorPartyState()" {checked_party}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                <!-- Outdoor Light -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>ไฟนอกบ้าน</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="outdoorLightToggle" onchange="updateOutdoorLightState()" {checked_outdoor}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">สถานะ: <span id="outdoorLightState">{outdoor_state}</span></p>
                    <p class="status-text">ค่าจากเซ็นเซอร์: <span id="LDRVal">{LDRvalNum}</span></p>
                    <label for="LDRThreshold" class="status-text">ตั้งค่า Treashold:</label>
                    <input type="number" id="LDRThreshold" value="{LDRComparatorInput}" min="0" max="4095" step="1" onchange="updateLDRThreshold()">
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="threshold-mark" id="threshold-mark-ldr"></div>
                            <div class="sensor-value" id="sensor-value-ldr"></div>
                        </div>
                        <p class="progress-labels">
                            <span>0</span>
                            <span>4095</span>
                        </p>
                    </div>
                </div>

                <!-- Clothes Retrieval System -->
                <div class="blocky">
                    <div class="block-header">
                        <h3>ราวตากผ้า</h3>
                        <label class="toggle-switch">
                            <input type="checkbox" id="ClothesReToggle" onchange="updateClothesReState()" {checked_ClothesRe}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">สถานะ: <span id="ClothesReState">{ClothesRe_state}</span></p>
                    <div class="block-header">
                        <h6>โหมดอัตโนมัติ</h6>
                        <label class="toggle-switch">
                            <input type="checkbox" id="ClothesReAutoModeToggle" onchange="updateAutoMode()" {checked_ClothesReAutoMode}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p class="status-text">ค่าจากเซ็นเซอร์: <span id="MoistVal">{MoistvalNum}</span></p>
                    <label for="moistThreshold" class="status-text">ตั้งค่า Threshold:</label>
                    <input type="number" id="moistThreshold" value="{MoistComparatorInput}" min="0" max="4095" step="1" onchange="updateMoistThreshold()">
                    <!-- Progress Bar Container -->
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="threshold-mark" id="threshold-mark"></div>
                            <div class="sensor-value" id="sensor-value"></div>
                        </div>
                        <p class="progress-labels">
                            <span>0</span>
                            <span>4095</span>
                        </p>
                    </div>
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
                    body: JSON.stringify({{ state: state }}), // Output: {"state":True}
                }})
                .then(response => response.json()) // เมื่อ server ตอบกลับมา จะเอา response มาแปลงเป็น JSON object Output: {"state":True}
                .then(data => {{ // เอา data จากเมื่อกี้มาแสดงใน log
                    console.log('State updated:', data);
                    fetchData();
                }})
                .catch(error => {{
                    console.error('Error updating state:', error);
                }});
            }}

            function fetchData() {{
                fetch('/data') // ส่ง request GET ไปที่ endpoint(IP Address ของ Server) /data ของ server
                    .then(response => response.json())
                    .then(data => {{
                        //document.getElementById('gateState').innerText = data.gateState ? "เปิดอยู่" : "ปิดอยู่";
                        document.getElementById('indoorLightState').innerText = data.indoorLightState ? "เปิด" : "ปิด";
                        document.getElementById('outdoorLightState').innerText = data.outdoorLightState ? "เปิด" : "ปิด";
                        document.getElementById('ClothesReState').innerText = data.clothes_re ? "ตากผ้าอยู่" : "เก็บราวแล้ว";
                        document.getElementById('gateToggle').disabled = data.busy_gate;
                        document.getElementById('confirmAngle').disabled = data.busy_gate;
                        
                        document.getElementById('LDRVal').innerText = data.LDRVal;
                        
                        document.getElementById('MoistVal').innerText = data.moistVal;
                        document.getElementById("ClothesReToggle").checked = data.clothes_re_enable;
                        document.getElementById("ClothesReAutoModeToggle").checked = data.clothes_re_auto;
                        document.getElementById('ClothesReToggle').disabled = data.busy_clothesre;
                    }})
                    .catch(error => console.error('Error fetching data:', error));
            }}
            
            setInterval(fetchData, 2000);
            setInterval(updateMoistProgressBar, 500);
            setInterval(updateLDRProgressBar, 500);

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
                    return fetchData();
                }})
                .catch(err => {{
                    console.error(err);
                    document.getElementById('gateToggle').disabled = false;
                }});
            }}
            function sendGateAngle() {{
                document.getElementById('confirmAngle').disabled = true;
                const rangeInput1 = document.getElementById('customDoorRange1').value;
                const rangeInput2 = document.getElementById('customDoorRange2').value;
                
                fetch('/anglegate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ gates: [rangeInput1, rangeInput2] }})
                }})
                .then(res => res.json())
                .then(data => {{
                if (data.status === "busy") {{
                        document.getElementById('confirmAngle').disabled = true;
                    }}
                    return fetchData();
                    console.log("Angles updated:", data);
                }})
                .catch(err => {{
                    console.error("Error:", err);
                    document.getElementById('confirmAngle').disabled = false;
                }});
            }}


            function updateIndoorLightState() {{
                const state = document.getElementById('indoorLightToggle').checked;
                sendStateToServer('/indoor', state);
            }}
            function updateIndoorPartyState() {{
                const state = document.getElementById('partyModeToggle').checked;
                sendStateToServer('/party', state);
            }}
            const colorNames = {{
              "#f0f8ff":"AliceBlue", "#faebd7":"AntiqueWhite", "#00ffff":"Aqua", "#7fffd4":"Aquamarine",
              "#f0ffff":"Azure", "#f5f5dc":"Beige", "#ffe4c4":"Bisque", "#000000":"Black",
              "#ffebcd":"BlanchedAlmond", "#0000ff":"Blue", "#8a2be2":"BlueViolet", "#a52a2a":"Brown",
              "#deb887":"BurlyWood", "#5f9ea0":"CadetBlue", "#7fff00":"Chartreuse", "#d2691e":"Chocolate",
              "#ff7f50":"Coral", "#6495ed":"CornflowerBlue", "#fff8dc":"Cornsilk", "#dc143c":"Crimson",
              "#00ffff":"Cyan", "#00008b":"DarkBlue", "#008b8b":"DarkCyan", "#b8860b":"DarkGoldenRod",
              "#a9a9a9":"DarkGray", "#006400":"DarkGreen", "#bdb76b":"DarkKhaki", "#8b008b":"DarkMagenta",
              "#556b2f":"DarkOliveGreen", "#ff8c00":"DarkOrange", "#9932cc":"DarkOrchid", "#8b0000":"DarkRed",
              "#e9967a":"DarkSalmon", "#8fbc8f":"DarkSeaGreen", "#483d8b":"DarkSlateBlue", "#2f4f4f":"DarkSlateGray",
              "#00ced1":"DarkTurquoise", "#9400d3":"DarkViolet", "#ff1493":"DeepPink", "#00bfff":"DeepSkyBlue",
              "#696969":"DimGray", "#1e90ff":"DodgerBlue", "#b22222":"FireBrick", "#fffaf0":"FloralWhite",
              "#228b22":"ForestGreen", "#ff00ff":"Fuchsia", "#dcdcdc":"Gainsboro", "#f8f8ff":"GhostWhite",
              "#ffd700":"Gold", "#daa520":"GoldenRod", "#808080":"Gray", "#008000":"Green",
              "#adff2f":"GreenYellow", "#f0fff0":"HoneyDew", "#ff69b4":"HotPink", "#cd5c5c":"IndianRed",
              "#4b0082":"Indigo", "#fffff0":"Ivory", "#f0e68c":"Khaki", "#e6e6fa":"Lavender",
              "#fff0f5":"LavenderBlush", "#7cfc00":"LawnGreen", "#fffacd":"LemonChiffon", "#add8e6":"LightBlue",
              "#f08080":"LightCoral", "#e0ffff":"LightCyan", "#fafad2":"LightGoldenRodYellow",
              "#d3d3d3":"LightGray", "#90ee90":"LightGreen", "#ffb6c1":"LightPink", "#ffa07a":"LightSalmon",
              "#20b2aa":"LightSeaGreen", "#87cefa":"LightSkyBlue", "#778899":"LightSlateGray",
              "#b0c4de":"LightSteelBlue", "#ffffe0":"LightYellow", "#00ff00":"Lime", "#32cd32":"LimeGreen",
              "#faf0e6":"Linen", "#ff00ff":"Magenta", "#800000":"Maroon", "#66cdaa":"MediumAquaMarine",
              "#0000cd":"MediumBlue", "#ba55d3":"MediumOrchid", "#9370db":"MediumPurple", "#3cb371":"MediumSeaGreen",
              "#7b68ee":"MediumSlateBlue", "#00fa9a":"MediumSpringGreen", "#48d1cc":"MediumTurquoise",
              "#c71585":"MediumVioletRed", "#191970":"MidnightBlue", "#f5fffa":"MintCream", "#ffe4e1":"MistyRose",
              "#ffe4b5":"Moccasin", "#ffdead":"NavajoWhite", "#000080":"Navy", "#fdf5e6":"OldLace",
              "#808000":"Olive", "#6b8e23":"OliveDrab", "#ffa500":"Orange", "#ff4500":"OrangeRed",
              "#da70d6":"Orchid", "#eee8aa":"PaleGoldenRod", "#98fb98":"PaleGreen", "#afeeee":"PaleTurquoise",
              "#db7093":"PaleVioletRed", "#ffefd5":"PapayaWhip", "#ffdab9":"PeachPuff", "#cd853f":"Peru",
              "#ffc0cb":"Pink", "#dda0dd":"Plum", "#b0e0e6":"PowderBlue", "#800080":"Purple",
              "#663399":"RebeccaPurple", "#ff0000":"Red", "#bc8f8f":"RosyBrown", "#4169e1":"RoyalBlue",
              "#8b4513":"SaddleBrown", "#fa8072":"Salmon", "#f4a460":"SandyBrown", "#2e8b57":"SeaGreen",
              "#fff5ee":"SeaShell", "#a0522d":"Sienna", "#c0c0c0":"Silver", "#87ceeb":"SkyBlue",
              "#6a5acd":"SlateBlue", "#708090":"SlateGray", "#fffafa":"Snow", "#00ff7f":"SpringGreen",
              "#4682b4":"SteelBlue", "#d2b48c":"Tan", "#008080":"Teal", "#d8bfd8":"Thistle",
              "#ff6347":"Tomato", "#40e0d0":"Turquoise", "#ee82ee":"Violet", "#f5deb3":"Wheat",
              "#ffffff":"White", "#f5f5f5":"WhiteSmoke", "#ffff00":"Yellow", "#9acd32":"YellowGreen",
              "#ff1493":"DeepPink","#1e90ff":"DodgerBlue","#32cd32":"LimeGreen","#ffa07a":"LightSalmon",
              "#20b2aa":"LightSeaGreen","#87cefa":"LightSkyBlue","#778899":"LightSlateGray","#b0c4de":"LightSteelBlue",
              "#ff6347":"Tomato","#00ced1":"DarkTurquoise","#ff4500":"OrangeRed","#daa520":"GoldenRod","#4682b4":"SteelBlue","#556b2f":"DarkOliveGreen"
            }};
            function updateRGBColor() {{
                const color = document.getElementById('rgbColor').value;
                const colorHex = color.toLowerCase();
                const colorName = colorNames[colorHex] || colorHex;
                document.getElementById('NameColor').innerText = colorName;
                sendStateToServer('/color', color);
            }}


            function updateOutdoorLightState() {{
                const state = document.getElementById('outdoorLightToggle').checked;
                sendStateToServer('/outdoor', state);
            }}
            function updateLDRProgressBar() {{
                const sensorVal = parseInt(document.getElementById("LDRVal").innerText);
                const thresholdVal = parseInt(document.getElementById("LDRThreshold").value) || 0;
                
                const sensorBar = document.getElementById("sensor-value-ldr");
                const thresholdMark = document.getElementById("threshold-mark-ldr");

                const maxVal = 4095;
                let sensorPercent = Math.min(Math.max(sensorVal / maxVal * 100, 0), 100);
                let thresholdPercent = Math.min(Math.max(thresholdVal / maxVal * 100, 0), 100);

                sensorBar.style.width = sensorPercent + "%";
                thresholdMark.style.left = thresholdPercent + "%";
            }}
            function updateLDRThreshold() {{
                const val = parseInt(document.getElementById("LDRThreshold").value);
                fetch('/ldrval', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ value: val }})
                }})
                .then(res => res.json())
                .then(data => {{
                    console.log("LDR Threshold updated:", data);
                }})
                .catch(err => console.error(err));
            }}


            function updateClothesReState() {{
                document.getElementById('ClothesReToggle').disabled = true;
                const state = document.getElementById('ClothesReToggle').checked;
                sendStateToServer('/clothesre', state);
            }}
            function updateMoistThreshold() {{
                const val = document.getElementById("moistThreshold").value;
                fetch('/moistval', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ value: val }})
                }})
                .then(res => res.json())
                .then(data => {{
                    console.log("Moist Threshold updated:", data);
                }})
                .catch(err => console.error(err));
            }}
            function updateMoistProgressBar() {{
                const sensorVal = parseInt(document.getElementById("MoistVal").innerText);
                const thresholdVal = parseInt(document.getElementById("moistThreshold").value) || 0;
                
                const sensorBar = document.getElementById("sensor-value");
                const thresholdMark = document.getElementById("threshold-mark");

                const maxVal = 4095;
                let sensorPercent = Math.min(Math.max(sensorVal / maxVal * 100, 0), 100);
                let thresholdPercent = Math.min(Math.max(thresholdVal / maxVal * 100, 0), 100);

                sensorBar.style.width = sensorPercent + "%";
                thresholdMark.style.left = thresholdPercent + "%";
            }}
            function updateAutoMode() {{
                const state = document.getElementById('ClothesReAutoModeToggle').checked;
                sendStateToServer('/ClothesReAutoModeStates', state);
            }}
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """.format(
        checked_gate = "checked" if gateEnable else "",
        gate_state   = "เปิดอยู่" if gateEnable else "ปิดอยู่",
        checked_indoor = "checked" if indoorLightEnable else "",
        indoor_state   = "เปิด" if indoorLightEnable else "ปิด",
        checked_party = "checked" if indoorPartyEnable else "",
        color = colorValue,
        checked_outdoor = "checked" if outdoorLightEnable else "",
        outdoor_state   = "เปิด" if outdoorLightEnable else "ปิด",
        LDRvalNum = LDRval,
        LDRComparatorInput = LDRComparator,
        checked_ClothesRe = "checked" if ClothesReEnable else "",
        ClothesRe_state   = "ตากผ้าอยู่" if ClothesRe_state else "เก็บราวแล้ว",
        MoistComparatorInput = MoistComparator,
        MoistvalNum = MoistVal,
        checked_ClothesReAutoMode = "checked" if ClothesReAutoMode else ""
    )

# ===== Web server thread =====
def web_server():
    global gateEnable, indoorLightEnable, outdoorLightEnable, LDRval, LDRComparator, colorValue, indoorLightColor, indoorPartyEnable, ClothesReEnable, ClothesRe_state, Moistval, MoistComparator, ClothesReAutoMode, AngleGate1, AngleGate2
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
                    'busy_gate': busy_gate,
                    'indoorLightState': indoorLightEnable,
                    'color': colorValue,
                    'outdoorLightState': outdoorLightState,
                    'LDRVal' : LDRval,
                    'clothes_re_enable': ClothesReEnable,
                    'clothes_re_auto': ClothesReAutoMode,
                    'clothes_re': ClothesRe_state,
                    'busy_clothesre': busy_clothesre,
                    'moistVal' : Moistval
                })
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                cl.send(response)
            
            elif req.startswith('GET / '): 
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                cl.send(web(gateEnable, indoorLightEnable, outdoorLightEnable, colorValue, Moistval, MoistComparator, ClothesReAutoMode, LDRval, LDRComparator))
            
            elif req.startswith('POST'):
                req_line = req.split("\r\n")[0]
                method, path, _ = req_line.split()
                body = req.split("\r\n\r\n",1)[1] if "\r\n\r\n" in req else ""
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                
                data = json.loads(body or "{}")
                
                if path=="/gate":
                    if not busy_gate:
                        gateEnable = data.get("state",gateEnable)
                        _thread.start_new_thread(gate,())
                        cl.send(json.dumps({"status":gateEnable}))
                    else:
                        cl.send(json.dumps({"status":"busy"}))
                        
                elif path=="/anglegate":
                    gates = data.get("gates", [])
                    g1 = gates[0]
                    g2 = gates[1]
                    if not busy_gate:
                        # ถ้าเป็น dict ให้ดึงค่า .get("value")
                        if isinstance(g1, dict):
                            g1 = g1.get("value", AngleGate1)
                        if isinstance(g2, dict):
                            g2 = g2.get("value", AngleGate2)
                        AngleGate1 = int(g1)
                        AngleGate2 = int(g2)
                        print("Updated angles => Gate1:", AngleGate1, "Gate2:", AngleGate2)
                        _thread.start_new_thread(update_gateAngle,())
                        cl.send(json.dumps({"status": "ok", "gate1": AngleGate1, "gate2": AngleGate2}))
                    else:
                        cl.send(json.dumps({"status":"busy"}))
                        
                elif path=="/indoor":
                    indoorLightEnable = data.get("state",indoorLightEnable)
                    update_indoor_light()
                    cl.send(json.dumps({"status":indoorLightEnable}))
                    
                elif path=="/party":
                    indoorPartyEnable = data.get("state",indoorPartyEnable)
                    update_indoor_light()
                    cl.send(json.dumps({"status":indoorPartyEnable}))
                    
                elif path=="/color":
                    colorValue = data.get("state",colorValue)
                    update_indoor_light()
                    cl.send(json.dumps({"status":colorValue}))
                    
                elif path=="/outdoor":
                    outdoorLightEnable = data.get("state",outdoorLightEnable)
                    cl.send(json.dumps({"status":outdoorLightEnable}))
                    
                elif path=="/ldrval":
                    try: LDRComparator = int(data.get("value", LDRComparator))
                    except: pass
                    cl.send(json.dumps({"status":"success", "value": LDRComparator}))
                    
                elif path=="/clothesre":
                    ClothesReEnable = data.get("state",ClothesReEnable)
                    cl.send(json.dumps({"status":"success"}))
                    
                elif path=="/moistval":
                    try: MoistComparator = int(data.get("value", MoistComparator))
                    except: pass
                    cl.send(json.dumps({"status":"success", "value": MoistComparator}))
                    
                elif path=="/ClothesReAutoModeStates":
                    ClothesReAutoMode = data.get("state",ClothesReAutoMode)
                    cl.send(json.dumps({"status":ClothesReAutoMode}))
                    
                else:
                    cl.send(json.dumps({"status":"error"}))

            cl.close()
        except Exception as e:
            print("Web server error:", e)
            
_thread.start_new_thread(web_server, ())
