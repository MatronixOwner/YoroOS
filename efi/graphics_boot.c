/* UEFI graphical bootstrap. The native kernel shares this image but does not
 * use firmware services after ExitBootServices. No disk writes are performed. */
#include "efi.h"
#include "../native64/bootinfo.h"

struct guid { uint32_t a; uint16_t b, c; uint8_t d[8]; };
struct pixel_masks { uint32_t red, green, blue, reserved; };
struct gop_info {
    uint32_t version, width, height, format;
    struct pixel_masks masks;
    uint32_t pixels_per_scanline;
};
struct gop_mode {
    uint32_t max_mode, mode;
    struct gop_info *info;
    UINTN info_size;
    uint64_t framebuffer_base;
    UINTN framebuffer_size;
};
struct gop { void *query_mode, *set_mode, *blt; struct gop_mode *mode; };
typedef EFI_STATUS (EFIAPI *locate_protocol)(struct guid *, void *, void **);
typedef EFI_STATUS (EFIAPI *exit_boot_services)(EFI_HANDLE, UINTN);
#define EFI_INVALID_PARAMETER (0x8000000000000002ULL)
#define EFI_UNSUPPORTED (0x8000000000000003ULL)
#define EFI_BUFFER_TOO_SMALL (0x8000000000000005ULL)

static struct yoro_framebuffer framebuffer;
/* More than sufficient for typical UEFI maps, including Hyper-V. Fail cleanly
 * instead of allocating after the final map is acquired. */
static uint64_t map_storage[32768];
static void error(struct EFI_SYSTEM_TABLE *st, CHAR16 *text) {
    ((EFI_TEXT_OUTPUT_STRING)st->ConOut->OutputString)(st->ConOut, text);
}
EFI_STATUS EFIAPI __attribute__((section(".text.efi_entry")))
efi_main(EFI_HANDLE image, struct EFI_SYSTEM_TABLE *st) {
    struct EFI_BOOT_SERVICES *bs = st->BootServices;
    ((EFI_SET_WATCHDOG_TIMER)bs->SetWatchdogTimer)(0, 0, 0, 0);
    struct guid gop_guid = {0x9042a9de, 0x23dc, 0x4a38,
                            {0x96,0xfb,0x7a,0xde,0xd0,0x80,0x51,0x6a}};
    struct gop *gop = 0;
    EFI_STATUS status = ((locate_protocol)bs->LocateProtocol)(&gop_guid, 0, (void **)&gop);
    if (status != EFI_SUCCESS || !gop || !gop->mode || !gop->mode->info) {
        error(st, L"YoroOS: no UEFI graphics framebuffer.\r\n");
        return EFI_UNSUPPORTED;
    }
    struct gop_info *i = gop->mode->info;
    if (i->format == 0) {
        framebuffer.red_mask = 0x000000ff; framebuffer.green_mask = 0x0000ff00; framebuffer.blue_mask = 0x00ff0000;
    } else if (i->format == 1) {
        framebuffer.red_mask = 0x00ff0000; framebuffer.green_mask = 0x0000ff00; framebuffer.blue_mask = 0x000000ff;
    } else if (i->format == 2 && i->masks.red && i->masks.green && i->masks.blue &&
               !(i->masks.red & i->masks.green) && !(i->masks.red & i->masks.blue) && !(i->masks.green & i->masks.blue)) {
        framebuffer.red_mask = i->masks.red; framebuffer.green_mask = i->masks.green; framebuffer.blue_mask = i->masks.blue;
    } else {
        error(st, L"YoroOS: unsupported framebuffer format.\r\n");
        return EFI_UNSUPPORTED;
    }
    framebuffer.base = (volatile uint32_t *)(uintptr_t)gop->mode->framebuffer_base;
    framebuffer.size = gop->mode->framebuffer_size;
    framebuffer.width = i->width; framebuffer.height = i->height; framebuffer.stride = i->pixels_per_scanline;
    if (!framebuffer.base || !framebuffer.width || !framebuffer.height ||
        framebuffer.stride < framebuffer.width || framebuffer.width > 8192 || framebuffer.height > 8192 ||
        (uint64_t)framebuffer.stride * framebuffer.height > framebuffer.size / 4) {
        error(st, L"YoroOS: invalid framebuffer.\r\n");
        return EFI_UNSUPPORTED;
    }
    EFI_GET_MEMORY_MAP get_map = (EFI_GET_MEMORY_MAP)bs->GetMemoryMap;
    exit_boot_services exit_bs = (exit_boot_services)bs->ExitBootServices;
    for (int attempt = 0; attempt < 4; ++attempt) {
        UINTN size = sizeof(map_storage), key = 0, desc_size = 0;
        uint32_t version = 0;
        status = get_map(&size, (struct EFI_MEMORY_DESCRIPTOR *)map_storage, &key, &desc_size, &version);
        if (status != EFI_SUCCESS) {
            if (status == EFI_BUFFER_TOO_SMALL) error(st, L"YoroOS: memory map exceeds bootstrap buffer.\r\n");
            return status;
        }
        /* No firmware calls between GetMemoryMap and ExitBootServices. */
        status = exit_bs(image, key);
        if (status == EFI_SUCCESS) yoro_enter_kernel(&framebuffer);
        if (status != EFI_INVALID_PARAMETER) return status;
    }
    return status;
}
