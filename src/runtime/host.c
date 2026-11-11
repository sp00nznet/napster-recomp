/*
 * Napster 2.0 beta 10.3 - static recompilation host.
 *
 * A 32-bit host on pcrecomp's runtime/native32 (the native bridge, callbacks,
 * threads and the machine lock; see its header). napster.exe and its two DLLs,
 * amp.dll and id3lib.dll, are lifted and mapped at the bases tools/catalog.py
 * gave them by native32's module loader (modules32.c). Windows, Winsock and
 * the C++ runtime (MSVCRT, MSVCP60) are the real ones, through the bridge.
 *
 * Two things are always on, for both the recompiled and the original code:
 *   - the network stays on this machine (native32_net_loopback_only): the
 *     client connects only to 127/8, its file server binds 127.0.0.1, and
 *     no name but localhost resolves. Read SECURITY.md.
 *   - the registry is the instance's own (native32_registry_sandbox, under
 *     HKCU\Software\pcrecomp\sandbox\napster-<profile>), so two clients run
 *     side by side as two users, and the real HKLM is never written.
 *
 * --original runs the modules' original machine code instead of their lift
 * (native32_set_native), with everything else the same: the reference the
 * harness compares the recompiled client with.
 *
 * Linked at /BASE:0x60000000 (CMakeLists.txt) so 0x00400000 (napster.exe) and
 * 0x10000000..0x10200000 (the DLLs) are free.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "native32.h"
#include "recomp_trace.h"

/* Same bases as work/bases.json (tools/catalog.py): the lifted C has them. */
static native32_module_t g_modules[] = {
    { "napster.exe", 0x00400000u },
    { "amp.dll",     0x10000000u },
    { "id3lib.dll",  0x10100000u },
};
#define NMODULES ((int)(sizeof g_modules / sizeof g_modules[0]))
#define EXE_BASE 0x00400000u

static DWORD g_watchdog_s;
static char  g_guest_cmdline[MAX_PATH + 1024];

#define ARG(n) MEM32(g_esp + 4 + 4 * (n))
#define RET(v, nargs) do { g_eax = (uint32_t)(v); g_esp += 4 + 4 * (nargs); } while (0)

static void shim_GetCommandLineA(void) { RET((uintptr_t)g_guest_cmdline, 0); }

static void shim_ExitProcess(void) {
    fprintf(stderr, "[exit] ExitProcess(%u)\n", ARG(0));
    ExitProcess(ARG(0));
}

static native32_shim_t g_shims[] = {
    { "GetCommandLineA", shim_GetCommandLineA },
    { "ExitProcess", shim_ExitProcess },
};

recomp_func_t recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }

void recomp_not_lifted(uint32_t va) {
    fprintf(stderr, "\n[not-lifted] sub_%08X  (called from 0x%08X)\n", va, g_cur_func);
    recomp_dump_trace("not-lifted");
    native32_dump_icalls(8);
    fflush(stderr);
    TerminateProcess(GetCurrentProcess(), 2);
}

static LONG CALLBACK crash(EXCEPTION_POINTERS* ep) {
    EXCEPTION_RECORD* r = ep->ExceptionRecord;
    static volatile LONG once;
    if ((r->ExceptionCode & 0xF0000000u) != 0xC0000000u) return EXCEPTION_CONTINUE_SEARCH;
    if (InterlockedExchange(&once, 1)) TerminateProcess(GetCurrentProcess(), 3);
    fprintf(stderr, "\n=== fault 0x%08lX at 0x%p, thread %lu ===\n", r->ExceptionCode,
            r->ExceptionAddress, GetCurrentThreadId());
    if (r->ExceptionCode == EXCEPTION_ACCESS_VIOLATION && r->NumberParameters >= 2) {
        ULONG_PTR op = r->ExceptionInformation[0];
        uint32_t at = (uint32_t)r->ExceptionInformation[1];
        fprintf(stderr, "  %s of 0x%08X%s\n", op == 0 ? "read" : op == 1 ? "write" : "execute", at,
                native32_in_guest(at) ? " (inside a guest module)" : at < 0x10000 ? " (null/low)" : "");
    }
    recomp_trace_flush();
    fprintf(stderr, "  in lifted sub_%08X, last native call %s\n", g_cur_func, g_cur_import);
    fprintf(stderr, "  eax=%08X ecx=%08X edx=%08X ebx=%08X esp=%08X ebp=%08X esi=%08X edi=%08X\n",
            g_eax, g_ecx, g_edx, g_ebx, g_esp, g_ebp, g_esi, g_edi);
    native32_dump_icalls(12);
    recomp_dump_trace("fault");
    TerminateProcess(GetCurrentProcess(), 3);
    return EXCEPTION_CONTINUE_SEARCH;
}

static DWORD WINAPI watchdog(LPVOID unused) {
    (void)unused;
    Sleep(g_watchdog_s * 1000);
    fprintf(stderr, "\n[watchdog] %lu s: in sub_%08X, last native call %s\n",
            g_watchdog_s, g_cur_func, g_cur_import);
    TerminateProcess(GetCurrentProcess(), 4);
    return 0;
}

int main(int argc, char** argv) {
    const char* dir = "game";
    const char* mods = "work\\rebased";
    const char* profile = "default";
    const char* args = "";
    int run = 0, original = 0;
    setvbuf(stderr, NULL, _IONBF, 0);
    for (int i = 1; i < argc; i++) {
        int n = recomp_trace_arg(argc, argv, i);
        if (n) { i += n - 1; continue; }
        if (!strcmp(argv[i], "--run")) run = 1;
        else if (!strcmp(argv[i], "--original")) original = 1;
        else if (!strcmp(argv[i], "--dir") && i + 1 < argc) dir = argv[++i];
        else if (!strcmp(argv[i], "--modules") && i + 1 < argc) mods = argv[++i];
        else if (!strcmp(argv[i], "--profile") && i + 1 < argc) profile = argv[++i];
        else if (!strcmp(argv[i], "--args") && i + 1 < argc) args = argv[++i];
        else if (!strcmp(argv[i], "--watchdog") && i + 1 < argc) g_watchdog_s = strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--native-trace")) native32_trace_native = 1;
        else if (!strcmp(argv[i], "--callbacks")) native32_trace_callbacks = 1;
        else {
            printf("usage: napsterrecomp [--run] [--original] [--dir DIR] [--profile NAME] [--modules DIR]\n"
                   "                     [--args \"GUEST ARGS\"] [--watchdog S] [--native-trace] [--callbacks]\n"
                   "  --dir      the client's folder (its .dat files, shared and downloaded files); default game\n"
                   "  --profile  registry sandbox HKCU\\Software\\pcrecomp\\sandbox\\napster-NAME; default 'default'\n"
                   "  --original run the original machine code, not the lift (the harness's reference)\n"
                   "  without --run: map and bind the modules, then stop\n");
            recomp_trace_help();
            return argv[i][1] == 'h' || argv[i][2] == 'h' ? 0 : 1;
        }
    }
    char modsfull[MAX_PATH], dirfull[MAX_PATH], box[128];
    GetFullPathNameA(mods, MAX_PATH - 1, modsfull, NULL);
    GetFullPathNameA(dir, MAX_PATH - 1, dirfull, NULL);
    _snprintf(g_guest_cmdline, sizeof g_guest_cmdline - 1, "\"%s\\napster.exe\" %s", dirfull, args);
    _snprintf(box, sizeof box - 1, "napster-%s", profile);

    native32_init();
    AddVectoredExceptionHandler(0, crash);
    native32_net_loopback_only();
    if (!native32_registry_sandbox(box)) { fprintf(stderr, "registry sandbox %s failed\n", box); return 1; }
    printf("Napster recomp host (%s)\n  lifted functions in dispatch: %u\n  folder %s, profile %s\n",
           original ? "original code" : "recompiled", recomp_dispatch_count, dirfull, profile);
    if (!native32_modules_map(modsfull, dirfull, g_modules, NMODULES)) return 1;
    int unresolved = native32_modules_bind(g_shims, (int)(sizeof g_shims / sizeof g_shims[0]));
    printf("  %d modules mapped and bound, %d unresolved\n", NMODULES, unresolved);
    if (unresolved) return 1;
    if (original)
        for (int i = 0; i < NMODULES; i++) native32_set_native(g_modules[i].base);
    uint8_t* b = (uint8_t*)(uintptr_t)EXE_BASE;
    uint32_t entry = EXE_BASE + ((IMAGE_NT_HEADERS32*)(b + ((IMAGE_DOS_HEADER*)b)->e_lfanew))
                                    ->OptionalHeader.AddressOfEntryPoint;
    if (!run) {
        printf("\n(dry run: modules mapped and bound; --run enters 0x%08X)\n", entry);
        return 0;
    }
    SetCurrentDirectoryA(dirfull);
    if (g_watchdog_s) CloseHandle(CreateThread(NULL, 0, watchdog, NULL, 0, NULL));
    if (!native32_attach_imports(EXE_BASE)) return 1;
    printf("  entering 0x%08X: %s\n\n", entry, g_guest_cmdline);
    fflush(stdout);
    native32_call_guest(entry, 0, NULL);
    printf("\nentry returned eax=%08X\n", g_eax);
    return (int)g_eax;
}
