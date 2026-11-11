# Hyper-V synthetic mouse: work in progress

These modules are **not yet connected to the kernel or to a real Hyper-V host**.
They cannot make the pointer move on their own. They implement and test two
pieces of the future driver without Linux:

* `ring.c`: VMBus packet ring framing, wrap-around, validation and signal hints.
* `mouse.c`: synthetic HID version 2 messages, a conservative HID absolute
  X/Y descriptor parser, and mapping an input report to screen coordinates.
  Unsupported or malformed descriptors are rejected rather than guessed.

Run `make test-hyperv-input`. The tests emulate packets and a common absolute
mouse descriptor; they do not replace Hyper-V hardware testing. There is no
runtime VMBus connection, actual mouse polling, interrupt handling, or click
handling yet, and no new mouse-enabled ISO should be published based on this.

Next steps for a Gen2-only prototype, before it can move a cursor:

1. Detect Microsoft Hyper-V and the required CPUID privileges. Before leaving
   UEFI, reserve page-aligned executable and shared pages, and pass their
   *physical* addresses to the kernel; never assume arbitrary virtual memory
   has identical physical addresses or is executable.
2. Establish hypercalls and SynIC safely with timeouts; implement a VMBus
   version handshake and offers, open only the mouse channel, establish GPADL
   and rings, implement signals, interrupt/EOI processing, cleanup and error
   diagnostics. The kernel currently disables interrupts and has no IDT.
3. Wire received in-band packets into this parser; send protocol request and
   device-info acknowledgement. Use the report coordinates to move Bibata,
   with no writes to any disk. Handle host disconnects and unsupported reports.
4. Test framing and state transitions in a simulated host, then run the
   experimental image in a Hyper-V Gen2 VM; QEMU/OVMF boot tests alone cannot
   prove synthetic mouse support.

Protocol references consulted:
* Microsoft Hypervisor Top Level Functional Specification (hypercalls/SynIC):
  https://github.com/MicrosoftDocs/Virtualization-Documentation/tree/main/tlfs
* Device and packet examples:
  https://github.com/dean-plude/os/pull/255
* USB HID 1.11 specification (report descriptor semantics):
  https://www.usb.org/document-library/device-class-definition-hid-111

The tests' representative descriptor describes the standard HID fields and is
not a promise that every Hyper-V configuration supplies an identical layout.
