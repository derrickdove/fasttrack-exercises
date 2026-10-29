#ifndef PSU_REGS_H
#define PSU_REGS_H

#include <stdint.h>

/* PSU = power supply unit. A register is an integer-sized hardware storage
 * location. This station reads an unsigned 8-bit status register (0..255).
 * Bit 0 is the rightmost, least significant bit; 1 means the flag is active.
 * Python decode_status keys are given beside each mask. Reserved bits must
 * be ignored, even if they are 1. There are no other output keys.
 */
#define PSU_READY         (1u << 0)  /* "ready": supply can accept commands */
#define PSU_OUTPUT_ON     (1u << 2)  /* "output_on": output is enabled */
#define PSU_OVERCURRENT   (1u << 4)  /* "overcurrent": current limit exceeded */
#define PSU_OVERTEMP      (1u << 7)  /* "overtemp": temperature limit exceeded */
/* Bits 1, 3, 5 and 6 are reserved (not assigned a meaning). */

/* A separate unsigned 8-bit configuration register uses bits 4..6 for range.
 * A field is a group of adjacent bits representing one unsigned number.
 * The shift is the number of lower bits below the field; width is its size.
 * set_bits/clear_bits may receive any 8-bit mask, not just the status masks.
 * field must also work for other valid shifts and widths in an 8-bit register.
 */
#define PSU_RANGE_SHIFT 4u
#define PSU_RANGE_WIDTH 3u

/* This station's sender uses little-endian byte order: the lowest-value byte
 * of each multi-byte integer comes first. Always decode that byte order,
 * regardless of the computer running Python. All values are integers.
 *
 * Packed means no padding (unused bytes for alignment) between members.
 * The transmitted frame is exactly 7 bytes, with no extra header or checksum:
 * offset  size  member       meaning
 *   0      1    status       raw status register, unsigned (0..255)
 *   1      2    voltage_mv   voltage in millivolts, unsigned (0..65535)
 *   3      2    current_ma   current in milliamps, signed (-32768..32767)
 *   5      2    sequence     frame counter, unsigned (0..65535)
 * Signed current uses two's complement, the usual signed integer encoding.
 * Negative current means current is flowing back into the supply.
 * A millivolt is 1/1000 volt; a milliamp is 1/1000 ampere.
 * Return exactly these member names as Python dictionary keys, with raw
 * integer values: do not convert units or decode status into flags here.
 */
#pragma pack(push, 1)
struct status_frame {
    uint8_t status;
    uint16_t voltage_mv;
    int16_t current_ma;
    uint16_t sequence;
};
#pragma pack(pop)

/* E4 reading cards. These are independent snippets, not a program to run.
 * Context: status_ptr points to a writable uint8_t status byte;
 * frame_ptr points to a struct status_frame; raw is an unsigned 16-bit value;
 * status_reg points to a volatile uint8_t hardware register.
 * uint8_t is an unsigned 8-bit integer type. volatile tells the compiler
 * that a hardware value can change independently and reads must occur.
 *
 * A: value = *status_ptr;
 * B: *status_ptr = 0;
 * C: value = frame_ptr->voltage_mv;
 * D: value = (uint8_t)raw;
 * E: value = *status_reg;
 */

#endif
