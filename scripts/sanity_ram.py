import ctypes
from ctypes import wintypes
import time

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ('cb', ctypes.c_uint32),
        ('PageFaultCount', ctypes.c_uint32),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
        ('PrivateUsage', ctypes.c_size_t),
    ]

def get_peak_ram_mb():
    try:
        current_process = ctypes.windll.kernel32.GetCurrentProcess()
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        if ctypes.windll.psapi.GetProcessMemoryInfo(current_process, ctypes.byref(counters), ctypes.sizeof(counters)):
            return float(counters.PeakWorkingSetSize) / (1024.0 * 1024.0)
    except Exception as e:
        print(f"Error: {e}")
        return 0.0
    return 0.0

print(f"RAM Check: {get_peak_ram_mb():.2f} MB")
print("Verification Complete")
