#!/usr/bin/env python3
"""
Tribble Protocol v1.2.7-L (Locked)
----------------------------------
Standardized for Multi-Node Onboarding.
- Preamble: Locked at 5 trits (+++++)
- Framing: 8-trit (2 padding + 4 data + 2 padding)
- Carrier: +=-= (Resets per block)
- Mapping: Symmetric A=1, a=-1
"""

import sys
import argparse
import re

# --- PROTOCOL INVARIANTS ---
CARRIER_PATTERN = "+=-="
PREAMBLE = "+++++"
DIALECTS = {'🔴': '+', '⚫': '=', '🟢': '-', '>': '+', '<': '-', '1': '+', '0': '=', '2': '-'}

# --- CORE LOGIC ---

def hamming_dist(s1, s2):
    return sum(el1 != el2 for el1, el2 in zip(s1, s2))

def decimal_to_core(n):
    """Balanced Ternary: Maps decimal -40 to 40 to 4 trits."""
    n = max(-40, min(40, n))
    trits = ""
    temp_n = n
    for _ in range(4):
        rem = temp_n % 3
        if rem == 0: trits = "=" + trits; temp_n //= 3
        elif rem == 1: trits = "+" + trits; temp_n = (temp_n - 1) // 3
        else: trits = "-" + trits; temp_n = (temp_n + 1) // 3
    return trits

def core_to_decimal(trits):
    """Converts 4-trit balanced ternary back to decimal."""
    val = 0
    m = {'+': 1, '=': 0, '-': -1}
    for i, t in enumerate(reversed(trits)):
        val += m[t] * (3 ** i)
    return val

# --- SIGNAL PROCESSING ---

def apply_carrier(block):
    vals, invs = {'+': 1, '=': 0, '-': -1}, {-1: '-', 0: '=', 1: '+'}
    return "".join(invs[(vals[block[i]] + vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1] for i in range(len(block)))

def remove_carrier(block):
    vals, invs = {'+': 1, '=': 0, '-': -1}, {-1: '-', 0: '=', 1: '+'}
    return "".join(invs[(vals[block[i]] - vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1] for i in range(len(block)))

def to_led(trits):
    m = {'+': '🔴', '=': '⚫', '-': '🟢'}
    return "".join(m.get(c, c) for c in trits)

# --- CHARACTER MAPPING ---

def build_codec():
    enc = {' ': "==" + decimal_to_core(0) + "=="}
    # A-Z (1..26), a-z (-1..-26)
    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"): enc[c] = "==" + decimal_to_core(i + 1) + "=="
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"): enc[c] = "==" + decimal_to_core(-(i + 1)) + "=="
    # 0-9 (27..36)
    for i, c in enumerate("0123456789"): enc[c] = "==" + decimal_to_core(i + 27) + "=="
    # Punctuation
    punct = ".,?!;:'\"()[]{}/\\-_"
    for i, c in enumerate(punct):
        val = (37 + i) if i < 4 else (-(27 + (i - 4)))
        enc[c] = "==" + decimal_to_core(val) + "=="
    return enc, {v: k for k, v in enc.items()}

# --- MAIN INTERFACE ---

def main():
    parser = argparse.ArgumentParser(description="Tribble Protocol v1.2.7-L")
    parser.add_argument("message", help="Input text or LED/Trit stream")
    parser.add_argument("-l", "--led", action="store_true", help="LED visualization")
    parser.add_argument("-v", "--verbose", action="store_true", help="Forensic Audit")
    parser.add_argument("-f", "--fuzzy", action="store_true", help="Hamming error correction")
    parser.add_argument("--verify", action="store_true", help="Round-trip integrity check")
    
    args = parser.parse_args()
    
    # Normalize input
    raw_in = args.message
    for s, t in DIALECTS.items(): raw_in = raw_in.replace(s, t)
    normalized = "".join(c for c in raw_in if c in '+-=')
    
    is_encoded = len(normalized) > 0 and all(c in '+-=' for c in normalized)
    char_map, trit_map = build_codec()

    if is_encoded:
        # Decode logic
        data_stream = normalized[len(PREAMBLE):] if normalized.startswith(PREAMBLE) else normalized
        chunks = [data_stream[i:i+8] for i in range(0, len(data_stream), 8)]
        
        if args.verbose: print(f"{'IDX':<4} | {'SIGNAL':<10} | {'CLEAN':<10} | CHAR")
        
        decoded_text = ""
        for i, chunk in enumerate(chunks):
            if len(chunk) < 8: continue
            clean = remove_carrier(chunk)
            char = trit_map.get(clean, None)
            
            if char is None and args.fuzzy:
                best = sorted(char_map.items(), key=lambda x: hamming_dist(clean, x[1]))[0][0]
                char, disp = best, f"({best})"
            elif char is None:
                char = disp = "?"
            else:
                disp = char
                
            decoded_text += char
            if args.verbose:
                s_out = to_led(chunk) if args.led else chunk
                c_out = to_led(clean) if args.led else clean
                print(f"{i:<4} | {s_out:<10} | {c_out:<10} | {disp}")
        
        print(f"\nDecoded Result: {decoded_text}")
        
        if args.verify:
            # Re-encode to verify
            test = PREAMBLE + "".join([apply_carrier(char_map.get(c, char_map['?'])) for c in decoded_text])
            if test == normalized: print("✓ VERIFIED: Perfect Match")
            else: print("⚠ WARNING: Data mismatch (possibly due to fuzzy matching or preamble offset)")

    else:
        # Encode logic
        if args.verbose: print(f"{'IDX':<4} | CHAR | {'DATA':<10} | {'SIGNAL':<10}")
        full_stream = PREAMBLE
        for i, c in enumerate(args.message):
            clean = char_map.get(c, char_map['?'])
            signal = apply_carrier(clean)
            full_stream += signal
            if args.verbose:
                c_out = to_led(clean) if args.led else clean
                s_out = to_led(signal) if args.led else signal
                print(f"{i:<4} | {c:^4} | {c_out:<10} | {s_out:<10}")
        
        print(f"\nEncoded Output:\n{to_led(full_stream) if args.led else full_stream}")
        
        if args.verify:
            # Re-decode to verify
            check_chunks = [full_stream[i:i+8] for i in range(len(PREAMBLE), len(full_stream), 8)]
            re_decoded = "".join([trit_map.get(remove_carrier(chk), "?") for chk in check_chunks])
            if re_decoded == args.message: print("✓ VERIFIED: Perfect Integrity")
            else: print(f"❌ ERROR: Integrity Failed. Got: {re_decoded}")

if __name__ == "__main__":
    main()
