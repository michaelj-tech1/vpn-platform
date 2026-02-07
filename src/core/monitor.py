import ctypes
import os
import subprocess
import sys

import keyring
import requests
import psutil

class SecurityMonitor:
    def __init__(self):

        self.suspicious_tools = {
            'network': [
                'wireshark', 'fiddler', 'charles', 'burpsuite', 'tcpdump',
                'networkminer', 'mitmproxy', 'etherape', 'ngrep', 'kismet',
                'snort', 'tshark', 'netwitness', 'cain', 'nmap'
            ],
            'debugging': [
                'ollydbg', 'idaq', 'idaq64', 'idaw', 'idaw64', 'x32dbg', 'x64dbg',
                'gdb', 'windbg', 'softice', 'frida', 'radare2', 'peid', 'hex-rays',
                'cheat engine', 'process hacker', 'immunity debugger'
            ]
        }
        self.common_ports = [8888, 8080, 9001, 3128, 1080, 8081, 8443, 8880]

    def run_security_check(self):
        if not self.perform_security_check():
            print("Security issue detected. Exiting application...")
            sys.exit(1)

    def perform_security_check(self):
        checks = [
            self.is_tool_running(),
            self.detect_debugger(),
            self.check_network_traffic(),
            self.detect_vm_environment(),
            self.check_proxy_settings(),
            self.detect_hooking_attempts()
        ]
        return not any(checks)


    def is_tool_running(self):
        for category, tools in self.suspicious_tools.items():
            for process in psutil.process_iter(['name']):
                try:
                    p_name = (process.info['name'] or '').lower()
                    if any(tool in p_name for tool in tools):
                        detection_message = f"Suspicious {category} tool detected: {p_name}"
                        print(detection_message)
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return False

    def detect_debugger(self):

        if sys.platform == 'win32':
            if ctypes.windll.kernel32.IsDebuggerPresent():
                print("Debugger is detected!")
                return True

            try:
                thread_handle = ctypes.windll.kernel32.GetCurrentThread()

                class CONTEXT(ctypes.Structure):
                    _fields_ = [
                        ("ContextFlags", ctypes.c_uint),
                        ("Dr0", ctypes.c_ulonglong),
                        ("Dr1", ctypes.c_ulonglong),
                        ("Dr2", ctypes.c_ulonglong),
                        ("Dr3", ctypes.c_ulonglong),
                        ("Dr6", ctypes.c_ulonglong),
                        ("Dr7", ctypes.c_ulonglong),
                    ]

                GetThreadContext = ctypes.windll.kernel32.GetThreadContext
                GetThreadContext.argtypes = [ctypes.c_void_p, ctypes.POINTER(CONTEXT)]
                context = CONTEXT()
                context.ContextFlags = 0x10010
                if GetThreadContext(thread_handle, ctypes.byref(context)):
                    if any([context.Dr0, context.Dr1, context.Dr2, context.Dr3]):
                        detection_message = "Hardware breakpoints detected!"
                        print(detection_message)
                        return True
            except Exception:
                pass

        return False

    def check_network_traffic(self):

        for conn in psutil.net_connections(kind='inet'):
            try:
                if conn.laddr and conn.laddr.port in self.common_ports:
                    detection_message = f"Unusual network traffic on port {conn.laddr.port}"
                    print(detection_message)
                    return True
            except (psutil.AccessDenied, AttributeError):
                continue
        return False

    def detect_vm_environment(self):

        vm_indicators = ["vbox", "virtual", "vmware", "qemu", "xen", "hyper-v", "parallels"]
        try:
            with open("/proc/cpuinfo", "r") as cpuinfo:
                cpu_data = cpuinfo.read().lower()
                if any(vm in cpu_data for vm in vm_indicators):
                    detection_message = "VM environment detected via CPU info!"
                    print(detection_message)
                    return True
        except FileNotFoundError:
            pass

        if sys.platform == "win32":
            try:
                output = subprocess.check_output("wmic computersystem get manufacturer", shell=True)
                manufacturer = output.decode().lower()
                if any(vm in manufacturer for vm in vm_indicators):
                    detection_message = "VM environment detected via system manufacturer!"
                    print(detection_message)
                    return True
            except Exception as e:
                print(f"Failed to check system manufacturer: {e}")

        return False

    def check_proxy_settings(self):

        if sys.platform.startswith('win'):
            try:
                output = subprocess.check_output("netsh winhttp show proxy", shell=True)
                decoded = output.decode().lower()
                if "proxy server" in decoded and "direct access" not in decoded:
                    detection_message = f"Suspicious proxy settings: {decoded.strip()}"
                    print(detection_message)
                    return True
            except Exception as e:
                print(f"Failed to check proxy settings on Windows: {e}")
        else:
            proxy_vars = ["http_proxy", "https_proxy", "all_proxy"]
            for var in proxy_vars:
                env_val = os.environ.get(var) or os.environ.get(var.upper())
                if env_val:
                    detection_message = f"Suspicious {var} set: {env_val}"
                    print(detection_message)
                    return True

        return False

    def detect_hooking_attempts(self):
        try:
            hooking_indicators = ["frida", "substrate", "cydia", "xposed", "injection"]

            if sys.platform.startswith('linux'):
                with open("/proc/self/maps", "r") as maps_file:
                    maps_data = maps_file.read().lower()
                    if any(indicator in maps_data for indicator in hooking_indicators):
                        detection_message = "Detected hooking/injection library in process memory!"
                        print(detection_message)
                        return True
            elif sys.platform == 'win32':
                p = psutil.Process(os.getpid())
                for dll in p.memory_maps():
                    module_path = dll.path.lower()
                    if any(indicator in module_path for indicator in hooking_indicators):
                        detection_message = f"Detected hooking module loaded: {module_path}"
                        print(detection_message)
                        return True

        except Exception:
            pass

        return False