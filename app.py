# from flask import Flask, request, jsonify
# import os, shutil, subprocess, platform, time
# from flask_cors import CORS 
# app = Flask(__name__)
# CORS(app) 
# @app.route("/file", methods=["POST"])
# def file_operations():
#     data = request.json
#     operation = data.get("operation")
#     path = data.get("path")
#     filename = data.get('filename')
#     abspath = path + f'/{filename}'
#     print(abspath)

#     try:
#         if operation == "list":
#             return jsonify({"files": os.listdir(path)})

#         elif operation == "open":
#             if platform.system() == "Windows":
#                 os.startfile(abspath)
#                 return jsonify({"stauts" : 'jhal ka bgh open'})
#             elif platform.system() == "Darwin":
#                 subprocess.call(["open", abspath])
#             else:
#                 subprocess.call(["xdg-open", abspath])
#             return jsonify({"status": "opened"})

#         elif operation == "delete":
#             if os.path.isfile(abspath):
#                 os.remove(abspath)
#             else:
#                 shutil.rmtree(paabspathth)
#             return jsonify({"status": "deleted"})

#         elif operation == "copy":
#             dst = data.get("destination")
#             if os.path.isdir(abspath):
#                 shutil.copytree(abspath, dst)
#             else:
#                 shutil.copy2(abspath, dst)
#             return jsonify({"status": "copied"})

#         elif operation == "move":
#             dst = data.get("destination")
#             shutil.move(abspath, dst)
#             return jsonify({"status": "moved"})

#         elif operation == "rename":
#             new_name = data.get("new_name")
#             new_path = os.path.join(os.path.dirname(abspath), new_name)
#             os.rename(abspath, new_path)
#             return jsonify({"status": "renamed", "new_path": new_path})

#         elif operation == "create_file":
#             open(abspath, "w").close()
#             return jsonify({"status": "file_created"})

#         elif operation == "create_folder":
#             os.makedirs(abspath, exist_ok=True)
#             return jsonify({"status": "folder_created"})

#         else:
#             return jsonify({"error": "unknown operation"}), 400

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# if __name__ == "__main__":
#     app.run(debug=True)


from flask import Flask, request, jsonify
import os, shutil, subprocess, platform, time, socket, json
from flask_cors import CORS 
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import threading

app = Flask(__name__)
CORS(app) 

# Global variables for discovery
zeroconf = None
discovered_devices = {}
discovery_cache_time = 0
CACHE_DURATION = 5  # seconds
our_service_name = None  # Track our own service name to filter it out

class DeviceListener(ServiceListener):
    """Listens for other FileX devices on the network"""
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated"""
        pass
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service goes offline"""
        # Remove from our discovered devices
        if name in discovered_devices:
            print(f"Device removed: {name}")
            del discovered_devices[name]
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a new service is discovered"""
        global our_service_name
        
        # Skip our own service
        if name == our_service_name:
            print(f"Skipping our own service: {name}")
            return
        
        info = zc.get_service_info(type_, name)
        if info:
            # Parse the TXT record to get device info
            txt_data = {}
            if info.properties:
                for key, value in info.properties.items():
                    txt_data[key.decode('utf-8')] = value.decode('utf-8')
            
            # Convert addresses to readable format
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            
            device_info = {
                'id': name.replace('._filex._tcp.local.', ''),
                'name': txt_data.get('name', name),
                'ip': addresses[0] if addresses else 'unknown',
                'port': info.port,
                'deviceType': txt_data.get('deviceType', 'unknown'),
                'lastSeen': time.time()
            }
            
            discovered_devices[name] = device_info
            print(f"Device discovered: {device_info}")

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Connect to a dummy address to find our local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_device_name():
    """Get a friendly name for this device"""
    try:
        hostname = socket.gethostname()
        return f"{hostname}-FileX"
    except:
        return "Unknown-FileX"

def start_zeroconf_service():
    """Start advertising our service and listening for others"""
    global zeroconf, our_service_name
    
    # Get network info
    local_ip = get_local_ip()
    device_name = get_device_name()
    port = 5000  # Flask default port
    
    print(f"Starting Zeroconf service on {local_ip}:{port}")
    print(f"Device name: {device_name}")
    
    # Create the service info
    service_name = f"{device_name}._filex._tcp.local."
    our_service_name = service_name  # Store our service name to filter it out
    
    # TXT record contains metadata about our service
    txt_record = {
        b'name': device_name.encode('utf-8'),
        b'deviceType': platform.system().encode('utf-8'),  # Windows, Darwin, Linux
        b'apiVersion': b'1.0'
    }
    
    service_info = ServiceInfo(
        "_filex._tcp.local.",
        service_name,
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties=txt_record,
        server=f"{device_name}.local."
    )
    
    # Start Zeroconf
    zeroconf = Zeroconf()
    
    # Register our service (so others can find us)
    zeroconf.register_service(service_info)
    print("Service registered successfully")
    
    # Start listening for other services
    listener = DeviceListener()
    browser = ServiceBrowser(zeroconf, "_filex._tcp.local.", listener)
    print("Started browsing for other devices")
    
    return zeroconf


def stop_zeroconf_service():
    """Stop the Zeroconf service"""
    global zeroconf
    if zeroconf:
        zeroconf.close()
        print("Zeroconf service stopped")

# Start Zeroconf in a background thread when the app starts
def init_discovery():
    """Initialize discovery in background thread"""
    discovery_thread = threading.Thread(target=start_zeroconf_service)
    discovery_thread.daemon = True  # Dies when main thread dies
    discovery_thread.start()

# Your existing file operations endpoint (with bug fixes)
@app.route("/file", methods=["POST"])
def file_operations():
    data = request.json
    operation = data.get("operation")
    path = data.get("path")
    filename = data.get('filename')
    
    # Fix the path joining issue
    if filename:
        abspath = os.path.join(path, filename)  # Use os.path.join for proper path handling
    else:
        abspath = path
    
    print(f"Operation: {operation}, Path: {abspath}")

    try:
        if operation == "list":
            return jsonify({"ok": True, "data": {"files": os.listdir(path)}})

        elif operation == "open":
            if platform.system() == "Windows":
                os.startfile(abspath)
                return jsonify({"ok": True, "data": {"status": "opened"}})
            elif platform.system() == "Darwin":
                subprocess.call(["open", abspath])
            else:
                subprocess.call(["xdg-open", abspath])
            return jsonify({"ok": True, "data": {"status": "opened"}})

        elif operation == "delete":
            if os.path.isfile(abspath):
                os.remove(abspath)
            else:
                shutil.rmtree(abspath)  # Fixed the typo: was 'paabspathth'
            return jsonify({"ok": True, "data": {"status": "deleted"}})

        elif operation == "copy":
            dst = data.get("destination")
            if not dst:
                return jsonify({"ok": False, "error": "destination required"}), 400
            if os.path.isdir(abspath):
                shutil.copytree(abspath, dst)
            else:
                shutil.copy2(abspath, dst)
            return jsonify({"ok": True, "data": {"status": "copied"}})

        elif operation == "move":
            dst = data.get("destination")
            if not dst:
                return jsonify({"ok": False, "error": "destination required"}), 400
            shutil.move(abspath, dst)
            return jsonify({"ok": True, "data": {"status": "moved"}})

        elif operation == "rename":
            new_name = data.get("new_name")
            if not new_name:
                return jsonify({"ok": False, "error": "new_name required"}), 400
            new_path = os.path.join(os.path.dirname(abspath), new_name)
            os.rename(abspath, new_path)
            return jsonify({"ok": True, "data": {"status": "renamed", "new_path": new_path}})

        elif operation == "create_file":
            open(abspath, "w").close()
            return jsonify({"ok": True, "data": {"status": "file_created"}})

        elif operation == "create_folder":
            os.makedirs(abspath, exist_ok=True)
            return jsonify({"ok": True, "data": {"status": "folder_created"}})

        else:
            return jsonify({"ok": False, "error": "unknown operation"}), 400

    except FileNotFoundError:
        return jsonify({"ok": False, "error": "File or directory not found"}), 404
    except PermissionError:
        return jsonify({"ok": False, "error": "Permission denied"}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# NEW ENDPOINTS FOR PART 2

@app.route("/lan/devices", methods=["GET"])
def get_lan_devices():
    """Get list of discovered devices on the LAN"""
    global discovery_cache_time, discovered_devices
    
    current_time = time.time()
    
    # Update lastSeen status and remove old devices
    devices_to_remove = []
    for name, device in discovered_devices.items():
        if current_time - device['lastSeen'] > 30:  # 30 seconds timeout
            devices_to_remove.append(name)
    
    for name in devices_to_remove:
        del discovered_devices[name]
    
    # Convert to list format expected by frontend
    device_list = []
    for name, device in discovered_devices.items():
        device_copy = device.copy()
        # Add online status based on lastSeen
        device_copy['online'] = (current_time - device['lastSeen']) < 20
        device_list.append(device_copy)
    
    return jsonify({
        "ok": True, 
        "data": {
            "devices": device_list,
            "lastRefresh": current_time
        }
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "ok": True,
        "data": {
            "status": "healthy",
            "time": time.time(),
            "service": "FileX",
            "version": "1.0"
        }
    })

if __name__ == "__main__":
    print("Starting FileX server...")
    
    # Initialize discovery service
    init_discovery()
    
    try:
        app.run(debug=True, host='0.0.0.0')  # Listen on all interfaces for LAN access
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_zeroconf_service()