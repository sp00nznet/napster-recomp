"""desk.py - run GUI programs headless, on a desktop of their own.

A Win32 desktop made with CreateDesktop is never shown on a screen (only the
interactive one, WinSta0\\Default, is), but programs started on it get real
windows, real messages and real GDI drawing. So a 2001 GUI client can be
driven by window messages, and photographed with PrintWindow, without a
monitor, a VM or an RDP console: the real screens never see it.

    d = Desktop('napster-harness')
    p = d.start([exe, args...], cwd)
    for hwnd, cls, text in d.windows(p.pid): ...
    d.shot(hwnd, 'out/x.png')
"""
import ctypes
import ctypes.wintypes as W
import struct
import subprocess
import time
import zlib

u32 = ctypes.WinDLL('user32', use_last_error=True)
g32 = ctypes.WinDLL('gdi32')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

DESKTOP_ALL = 0x01FF | 0x000F0000
WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
u32.CreateDesktopW.restype = W.HANDLE
u32.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, ctypes.c_void_p, W.DWORD, W.DWORD, ctypes.c_void_p]
u32.EnumDesktopWindows.argtypes = [W.HANDLE, WNDENUMPROC, W.LPARAM]
u32.EnumChildWindows.argtypes = [W.HWND, WNDENUMPROC, W.LPARAM]
u32.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.SendMessageW.restype = W.LPARAM
u32.SendMessageTimeoutW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM, W.UINT, W.UINT, ctypes.POINTER(ctypes.c_size_t)]
u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.SetThreadDesktop.argtypes = [W.HANDLE]


class STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb', W.DWORD), ('lpReserved', W.LPWSTR), ('lpDesktop', W.LPWSTR), ('lpTitle', W.LPWSTR),
                ('dwX', W.DWORD), ('dwY', W.DWORD), ('dwXSize', W.DWORD), ('dwYSize', W.DWORD),
                ('dwXCountChars', W.DWORD), ('dwYCountChars', W.DWORD), ('dwFillAttribute', W.DWORD),
                ('dwFlags', W.DWORD), ('wShowWindow', W.WORD), ('cbReserved2', W.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', W.HANDLE), ('hStdOutput', W.HANDLE),
                ('hStdError', W.HANDLE)]


class PROCINFO(ctypes.Structure):
    _fields_ = [('hProcess', W.HANDLE), ('hThread', W.HANDLE), ('dwProcessId', W.DWORD), ('dwThreadId', W.DWORD)]


class Proc:
    def __init__(self, pi):
        self.pid, self.handle = pi.dwProcessId, pi.hProcess
        k32.CloseHandle(pi.hThread)

    def alive(self):
        return k32.WaitForSingleObject(self.handle, 0) == 0x102

    def kill(self):
        k32.TerminateProcess(self.handle, 9)
        k32.WaitForSingleObject(self.handle, 5000)


class Desktop:
    def __init__(self, name):
        self.name = name
        self.h = u32.CreateDesktopW(name, None, None, 0, DESKTOP_ALL, None)
        if not self.h:
            raise OSError(ctypes.get_last_error(), 'CreateDesktop')

    def start(self, argv, cwd, log=None):
        si = STARTUPINFO()
        si.cb = ctypes.sizeof(si)
        si.lpDesktop = self.name
        pi = PROCINFO()
        cmd = subprocess.list2cmdline(argv)
        flags = 0x08000000                                   # CREATE_NO_WINDOW: no console on the real desktop
        inherit = False
        if log:
            # stdout/stderr to a file: an inheritable handle in STARTF_USESTDHANDLES
            import msvcrt
            f = open(log, 'wb')
            h = msvcrt.get_osfhandle(f.fileno())
            k32.SetHandleInformation(W.HANDLE(h), 1, 1)
            si.dwFlags |= 0x100
            si.hStdOutput = si.hStdError = h
            inherit = True
            self._log = f
        if not k32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None, inherit, flags,
                                  None, cwd, ctypes.byref(si), ctypes.byref(pi)):
            raise OSError(ctypes.get_last_error(), 'CreateProcess ' + cmd)
        return Proc(pi)

    def windows(self, pid=None, visible=True):
        """[(hwnd, class, text)] of the top-level windows on this desktop."""
        out = []

        def cb(h, _):
            p = W.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if (pid is None or p.value == pid) and (not visible or u32.IsWindowVisible(h)):
                out.append((h, cls_of(h), text_of(h)))
            return True
        u32.EnumDesktopWindows(self.h, WNDENUMPROC(cb), 0)
        return out

    def shot(self, hwnd, path):
        shot(hwnd, path)


def cls_of(h):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, b, 256)
    return b.value


def send(h, msg, wp=0, lp=0, ms=2000):
    """SendMessage that gives up after `ms` on a window whose thread is busy (0 then)."""
    r = ctypes.c_size_t()
    return r.value if u32.SendMessageTimeoutW(h, msg, wp, lp, 2, ms, ctypes.byref(r)) else 0


def text_of(h):
    """A window's text by WM_GETTEXT (works across processes for edit controls too)."""
    n = send(h, 0x000E)                                           # WM_GETTEXTLENGTH
    b = ctypes.create_unicode_buffer(n + 1)
    send(h, 0x000D, n + 1, ctypes.addressof(b))                   # WM_GETTEXT
    return b.value


def children(h):
    out = []

    def cb(c, _):
        out.append((c, cls_of(c), text_of(c), u32.GetDlgCtrlID(c)))
        return True
    u32.EnumChildWindows(h, WNDENUMPROC(cb), 0)
    return out


def set_text(h, s):
    b = ctypes.create_unicode_buffer(s)
    send(h, 0x000C, 0, ctypes.addressof(b))                       # WM_SETTEXT


def click(h):
    u32.PostMessageW(h, 0x00F5, 0, 0)                             # BM_CLICK


def command(h, cid):
    u32.PostMessageW(h, 0x0111, cid, 0)                           # WM_COMMAND


def wait(fn, timeout, step=0.25):
    end = time.time() + timeout
    while time.time() < end:
        r = fn()
        if r:
            return r
        time.sleep(step)
    return None


class RECT(ctypes.Structure):
    _fields_ = [('l', W.LONG), ('t', W.LONG), ('r', W.LONG), ('b', W.LONG)]


def shot(hwnd, path):
    """PrintWindow into a 24-bit PNG (no PIL needed)."""
    r = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = max(1, r.r - r.l), max(1, r.b - r.t)
    hdc = u32.GetDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, bi, 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    raw = b''.join(b'\0' + bytes(buf.raw[y * w * 4 + x * 4 + c] for x in range(w) for c in (2, 1, 0))
                   for y in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def lv_count(h):
    return send(h, 0x1004)                                        # LVM_GETITEMCOUNT


def lv_select(h, index):
    """Select row `index` of a list view in another (32-bit) process: the
    LVITEM has to live in that process, so it is written there."""
    pid = W.DWORD()
    u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    k32.OpenProcess.restype = W.HANDLE
    k32.VirtualAllocEx.restype = ctypes.c_void_p
    k32.VirtualAllocEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_size_t, W.DWORD, W.DWORD]
    k32.WriteProcessMemory.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
    k32.VirtualFreeEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_size_t, W.DWORD]
    ph = k32.OpenProcess(0x0008 | 0x0010 | 0x0020, False, pid.value)   # VM_OPERATION | VM_READ | VM_WRITE
    mem = k32.VirtualAllocEx(ph, None, 64, 0x3000, 0x04)
    item = struct.pack('<13I', 8, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0)   # LVIF_STATE, SELECTED|FOCUSED
    k32.WriteProcessMemory(ph, mem, item, len(item), None)
    r = send(h, 0x102B, index, mem)                                  # LVM_SETITEMSTATE
    k32.VirtualFreeEx(ph, mem, 0, 0x8000)
    k32.CloseHandle(ph)
    return r


def find(h, cls=None, cid=None, text=None):
    """First child of h with this class / control id / text (any depth)."""
    for c, k, t, i in children(h):
        if (cls is None or k == cls) and (cid is None or i == cid) and (text is None or t.replace('&', '') == text):
            return c
    return None
