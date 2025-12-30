#!/usr/bin/env python3
"""
Tribble Protocol v1.4.3-H (Stable)
----------------------------------
- Auto-Sync: Detects 4, 6, 8, 12 trit blocks.
- Deep Heal: Fixed scoring logic to support '?' punctuation.
- Robustness: Uses '■' for decode errors to avoid collision.
"""

import sys
import argparse
import re

# --- CONFIGURATION ---
CARRIER_PATTERN = "+=-="
BASE_SYNC = "++++" 
DIALECTS = {'🔴': '+', '⚫': '=', '🟢': '-', '>': '+', '<': '-', '1': '+', '0': '=', '2': '-'}
ERROR_FLAG = "■"

MODE_MAP = {"+-": 4, "+=": 6, "++": 8, "-+": 12}
INV_MODE_MAP = {v: k for k, v in MODE_MAP.items()}

def decimal_to_core(n, size):
    trits = ""
    temp_n = n
    for _ in range(size):
        rem = temp_n % 3
        if rem == 0: trits = "=" + trits; temp_n //= 3
        elif rem == 1: trits = "+" + trits; temp_n = (temp_n - 1) // 3
        else: trits = "-" + trits; temp_n = (temp_n + 1) // 3
    return trits

def apply_carrier(block):
    vals, invs = {'+': 1, '=': 0, '-': -1}, {-1: '-', 0: '=', 1: '+'}
    return "".join(invs[(vals[block[i]] + vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1] for i in range(len(block)))

def remove_carrier(block):
    vals, invs = {'+': 1, '=': 0, '-': -1}, {-1: '-', 0: '=', 1: '+'}
    return "".join(invs[(vals[block[i]] - vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1] for i in range(len(block)))

def to_led(trits):
    m = {'+': '🔴', '=': '⚫', '-': '🟢'}
    return "".join(m.get(c, c) for c in trits)

def build_codec(size):
    chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,?!;:'\"()[]{}/\\-_"
    enc = {}
    for i, c in enumerate(chars):
        if c == ' ': val = 0
        elif 'A' <= c <= 'Z': val = ord(c) - ord('A') + 1
        elif 'a' <= c <= 'z': val = -(ord(c) - ord('a') + 1)
        elif '0' <= c <= '9': val = ord(c) - ord('0') + 27
        else:
            p_idx = ".,?!;:'\"()[]{}/\\-_".find(c)
            val = (37 + p_idx) if p_idx < 4 else (-(27 + (p_idx - 4)))
        enc[c] = decimal_to_core(val, size)
    return enc, {v: k for k, v in enc.items()}

def calculate_legibility(text):
    """
    High score = Likely correct English/Code.
    """
    if not text: return -1000
    
    weights = {
        'space': len(re.findall(r'\s', text)) * 5,
        'lowercase': len(re.findall(r'[a-z]', text)) * 2,
        'uppercase': len(re.findall(r'[A-Z]', text)) * 1.5,
        'digit': len(re.findall(r'[0-9]', text)) * 1,
        'punctuation': len(re.findall(r'[.,?!]', text)) * 1.5, # Boost for valid grammar
        'symbols': len(re.findall(r'[;:"\'(){}\[\]/\\-_]', text)) * 0.5,
        'decode_error': text.count(ERROR_FLAG) * -50, # Massive penalty for actual errors
        'garbage': len(re.findall(r'[^a-zA-Z0-9\s.,?!;:"\'(){}\[\]/\\-_' + ERROR_FLAG + r']', text)) * -10
    }
    
    raw_score = sum(weights.values())
    return raw_score / (len(text) + 1)

def decode_stream(normalized, frame_size, trit_map):
    chunks = [normalized[i:i+frame_size] for i in range(0, len(normalized), frame_size)]
    decoded = ""
    for chunk in chunks:
        if len(chunk) < frame_size: continue
        clean = remove_carrier(chunk)
        # Map unknown sequences to ERROR_FLAG instead of '?'
        decoded += trit_map.get(clean, ERROR_FLAG)
    return decoded

def main():
    parser = argparse.ArgumentParser(description="Tribble Protocol v1.4.3-H")
    parser.add_argument("message", help="Text to encode or LED stream to decode")
    parser.add_argument("-s", "--size", type=int, choices=[4, 6, 8, 12], default=8, help="Encoding frame size")
    parser.add_argument("-l", "--led", action="store_true", help="LED visualization")
    parser.add_argument("-v", "--verbose", action="store_true", help="Forensic Audit")
    
    args = parser.parse_args()
    
    raw_in = args.message
    for s, t in DIALECTS.items(): raw_in = raw_in.replace(s, t)
    normalized = "".join(c for c in raw_in if c in '+-=')
    
    sync_match = re.search(r'\+{4}', normalized)
    
    if sync_match and len(normalized) >= sync_match.start() + 6:
        # DECODE PATH
        sync_idx = sync_match.start()
        suffix = normalized[sync_idx+4 : sync_idx+6]
        frame_size = MODE_MAP.get(suffix, 8)
        
        data_start = sync_idx + 6
        raw_payload = normalized[data_start:]
        
        if args.verbose: print(f">> [AUTO-SYNC] {frame_size}-trit mode detected.")
        
        char_map, trit_map = build_codec(frame_size)
        
        candidates = []
        for shift in range(frame_size):
            shifted_payload = raw_payload[shift:]
            trial_text = decode_stream(shifted_payload, frame_size, trit_map)
            score = calculate_legibility(trial_text)
            candidates.append((score, shift, trial_text))
            
            if args.verbose:
                preview = trial_text[:20].replace('\n', ' ')
                print(f"   [Shift {shift}] Score: {score:.2f} | {preview}")

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_shift, best_text = candidates[0]
        
        if args.verbose and best_shift != 0:
            print(f">> HEALED: Corrected {best_shift}-trit drift.")
            
        print(f"\nDecoded Result: {best_text}")
        
    else:
        # ENCODE PATH
        frame_size = args.size
        suffix = INV_MODE_MAP.get(frame_size, "++")
        char_map, trit_map = build_codec(frame_size)
        
        if args.verbose: print(f">> Encoding {frame_size}-trit mode.")
        
        full_stream = BASE_SYNC + suffix
        for c in args.message:
            # Padding char depends on density
            fallback = "----" if frame_size == 4 else "=" * frame_size
            clean = char_map.get(c, char_map.get('?', fallback))
            full_stream += apply_carrier(clean)
            
        print(f"\nEncoded Output:\n{to_led(full_stream) if args.led else full_stream}")

if __name__ == "__main__":
    main()
