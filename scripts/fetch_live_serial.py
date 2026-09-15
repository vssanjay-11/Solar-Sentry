import sys
import time
import re
import json
import serial

def fetch_telemetry_from_serial(port='COM3', baudrate=115200, timeout=15):
    print(f"Opening {port} at {baudrate} baud (timeout {timeout}s)...")
    try:
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = baudrate
        ser.timeout = 1
        ser.dtr = False
        ser.rts = False
        ser.open()
    except Exception as e:
        print(f"Error opening {port}: {e}")
        return None

    print(f"Connected to {port}. Listening for telemetry reports...")
    data = {}
    reports = []
    start_time = time.time()

    current_report = {}

    try:
        while time.time() - start_time < timeout:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace').strip()
            if not line:
                continue

            # Output raw line
            try:
                sys.stdout.buffer.write(f"ESP32: {line}\n".encode('utf-8', errors='replace'))
                sys.stdout.flush()
            except Exception:
                pass

            if "================================================" in line:
                if len(current_report) >= 5:
                    reports.append(dict(current_report))
                    data.update(current_report)
                    print("\n>>> CAPTURED TELEMETRY BLOCK <<<")
                    for k, v in current_report.items():
                        print(f"  {k:20s}: {v}")
                    print("--------------------------------\n")
                    current_report = {}
                continue

            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip().lower()
                val_str = parts[1].strip()

                if key == "temperature":
                    try: current_report["temperature"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif key == "humidity":
                    try: current_report["humidity"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif key == "pressure":
                    try: current_report["pressure"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif key == "light":
                    try: current_report["lux"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "rain adc" in key:
                    try: current_report["rain_raw"] = int(re.findall(r"\d+", val_str)[0])
                    except: pass
                elif key == "dht22":
                    try: current_report["dht22_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif key == "bmp280":
                    try: current_report["bmp280_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif key == "bh1750":
                    try: current_report["bh1750_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "rain sensor" in key:
                    try: current_report["rain_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "overall health" in key:
                    try: current_report["overall_health"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "environment score" in key:
                    try: current_report["environment_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "local readiness" in key:
                    try: current_report["local_readiness"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "vision score" in key:
                    try: current_report["vision_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "solar data score" in key:
                    try: current_report["solar_data_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "confidence" in key and "observation" not in key:
                    try: current_report["confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                    except: pass
                elif "ai decision" in key:
                    current_report["ai_decision"] = val_str
                elif "current state" in key:
                    current_report["current_state"] = val_str
                elif key == "pan":
                    try: current_report["pan"] = int(re.findall(r"\d+", val_str)[0])
                    except: pass
                elif key == "tilt":
                    try: current_report["tilt"] = int(re.findall(r"\d+", val_str)[0])
                    except: pass
                elif key == "wi-fi":
                    current_report["wifi"] = val_str
                elif "device id" in key:
                    current_report["device_id"] = val_str
                elif "uptime" in key:
                    try: current_report["uptime"] = val_str
                    except: pass

            if len(reports) >= 1 and len(current_report) >= 5:
                # Got 2 blocks
                reports.append(dict(current_report))
                data.update(current_report)
                break

    finally:
        ser.close()
        print(f"Closed {port}.")

    return data

if __name__ == '__main__':
    telemetry = fetch_telemetry_from_serial(timeout=14)
    print("\n================ FINAL LATEST TELEMETRY ================")
    print(json.dumps(telemetry, indent=2))
