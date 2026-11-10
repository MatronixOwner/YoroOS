/*
 * Minimal UEFI definitions for YoroOS (no gnu-efi dependency).
 * Only the structures and services the YoroOS EFI shell needs:
 * console in/out, memory map, time, reset, watchdog.
 */
#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define EFIAPI __attribute__((ms_abi))

typedef uint64_t UINTN;
typedef int64_t INTN;
typedef uint64_t EFI_STATUS;
typedef uint16_t CHAR16;
typedef void *EFI_HANDLE;
typedef void *EFI_EVENT;

#define EFI_SUCCESS 0

/* EFI_SIMPLE_TEXT_INPUT_PROTOCOL */
struct EFI_INPUT_KEY {
    uint16_t ScanCode;
    CHAR16 UnicodeChar;
};

struct EFI_SIMPLE_TEXT_INPUT {
    void *Reset;
    void *ReadKeyStroke; /* (This, Key) */
    EFI_EVENT WaitForKey;
};

typedef EFI_STATUS (EFIAPI *EFI_INPUT_READ_KEY)(void *This,
                                                struct EFI_INPUT_KEY *Key);

/* EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL */
struct EFI_SIMPLE_TEXT_OUTPUT {
    void *Reset;
    void *OutputString; /* (This, String) */
    void *TestString;
    void *QueryMode;
    void *SetMode;
    void *SetAttribute; /* (This, Attribute) */
    void *ClearScreen;  /* (This) */
    void *SetCursorPosition;
    void *EnableCursor;
    void *Mode;
};

typedef EFI_STATUS (EFIAPI *EFI_TEXT_OUTPUT_STRING)(void *This,
                                                     CHAR16 *String);
typedef EFI_STATUS (EFIAPI *EFI_TEXT_SET_ATTRIBUTE)(void *This, UINTN Attr);
typedef EFI_STATUS (EFIAPI *EFI_TEXT_CLEAR_SCREEN)(void *This);

/* Text colors (same numbering as VGA). */
#define EFI_BLACK 0x00
#define EFI_BLUE 0x01
#define EFI_GREEN 0x02
#define EFI_CYAN 0x03
#define EFI_RED 0x04
#define EFI_MAGENTA 0x05
#define EFI_BROWN 0x06
#define EFI_LIGHTGRAY 0x07
#define EFI_BRIGHT 0x08
#define EFI_LIGHTGREEN (EFI_GREEN | EFI_BRIGHT)
#define EFI_LIGHTCYAN (EFI_CYAN | EFI_BRIGHT)

/* EFI_BOOT_SERVICES (fields up to SetWatchdogTimer, rest unused) */
struct EFI_BOOT_SERVICES {
    uint8_t _hdr[24];
    void *RaiseTPL;
    void *RestoreTPL;
    void *AllocatePages;
    void *FreePages;
    void *GetMemoryMap; /* (Size, Map, Key, DescSize, DescVersion) */
    void *AllocatePool;
    void *FreePool;
    void *CreateEvent;
    void *SetTimer;
    void *WaitForEvent; /* (NumEvents, Events, Index) */
    void *SignalEvent;
    void *CloseEvent;
    void *CheckEvent;
    void *InstallProtocolInterface;
    void *ReinstallProtocolInterface;
    void *UninstallProtocolInterface;
    void *HandleProtocol;
    void *Reserved;
    void *RegisterProtocolNotify;
    void *LocateHandle;
    void *LocateDevicePath;
    void *InstallConfigurationTable;
    void *LoadImage;
    void *StartImage;
    void *Exit;
    void *UnloadImage;
    void *ExitBootServices;
    void *GetNextMonotonicCount;
    void *Stall;
    void *SetWatchdogTimer; /* (Timeout, Code, DataSize, Data) */
    void *ConnectController;
    void *DisconnectController;
    void *OpenProtocol;
    void *CloseProtocol;
    void *OpenProtocolInformation;
    void *ProtocolsPerHandle;
    void *LocateHandleBuffer;
    void *LocateProtocol;
};

struct EFI_MEMORY_DESCRIPTOR {
    uint32_t Type;
    uint64_t PhysicalStart;
    uint64_t VirtualStart;
    uint64_t NumberOfPages;
    uint64_t Attribute;
};

typedef EFI_STATUS (EFIAPI *EFI_GET_MEMORY_MAP)(
    UINTN *MemoryMapSize, struct EFI_MEMORY_DESCRIPTOR *MemoryMap,
    UINTN *MapKey, UINTN *DescriptorSize, uint32_t *DescriptorVersion);
typedef EFI_STATUS (EFIAPI *EFI_WAIT_FOR_EVENT)(UINTN NumberOfEvents,
                                                EFI_EVENT *Event,
                                                UINTN *Index);
typedef EFI_STATUS (EFIAPI *EFI_SET_WATCHDOG_TIMER)(UINTN Timeout,
                                                    uint64_t WatchdogCode,
                                                    UINTN DataSize,
                                                    CHAR16 *WatchdogData);

/* EFI_RUNTIME_SERVICES (fields up to ResetSystem) */
struct EFI_TIME {
    uint16_t Year;
    uint8_t Month;
    uint8_t Day;
    uint8_t Hour;
    uint8_t Minute;
    uint8_t Second;
    uint8_t Pad1;
    uint32_t Nanosecond;
    int16_t TimeZone;
    uint8_t Daylight;
    uint8_t Pad2;
};

struct EFI_RUNTIME_SERVICES {
    uint8_t _hdr[24];
    void *GetTime; /* (Time, Capabilities) */
    void *SetTime;
    void *GetWakeupTime;
    void *SetWakeupTime;
    void *SetVirtualAddressMap;
    void *ConvertPointer;
    void *GetVariable;
    void *GetNextVariableName;
    void *SetVariable;
    void *GetNextHighMonotonicCount;
    void *ResetSystem; /* (Type, Status, DataSize, Data) */
};

typedef EFI_STATUS (EFIAPI *EFI_GET_TIME)(struct EFI_TIME *Time, void *Caps);
typedef void (EFIAPI *EFI_RESET_SYSTEM)(int ResetType, EFI_STATUS Status,
                                        UINTN DataSize, void *ResetData);

#define EFI_RESET_COLD 0
#define EFI_RESET_WARM 1
#define EFI_RESET_SHUTDOWN 2

/* EFI_SYSTEM_TABLE */
struct EFI_SYSTEM_TABLE {
    uint8_t _hdr[24];
    CHAR16 *FirmwareVendor;
    uint32_t FirmwareRevision;
    uint32_t _pad;
    EFI_HANDLE ConsoleInHandle;
    struct EFI_SIMPLE_TEXT_INPUT *ConIn;
    EFI_HANDLE ConsoleOutHandle;
    struct EFI_SIMPLE_TEXT_OUTPUT *ConOut;
    EFI_HANDLE StandardErrorHandle;
    struct EFI_SIMPLE_TEXT_OUTPUT *StdErr;
    struct EFI_RUNTIME_SERVICES *RuntimeServices;
    struct EFI_BOOT_SERVICES *BootServices;
    UINTN NumberOfTableEntries;
    void *ConfigurationTable;
};

EFI_STATUS EFIAPI efi_main(EFI_HANDLE ImageHandle,
                           struct EFI_SYSTEM_TABLE *SystemTable);
