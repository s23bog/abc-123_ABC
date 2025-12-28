#!/usr/bin/env python3
"""
Balanced Ternary Encoder/Decoder (trcode)
Default: 8-trit framed tribbles with carrier wave
Usage: trcode "message" [-v for verbose]
"""

import sys
import argparse

def decimal_to_trits_4(n):
    """Convert decimal to 4-trit balanced ternary core"""
    trits = ""
    for _ in range(4):
        rem = n % 3
        if rem < 0:
            rem += 3
        
        if rem == 0:
            trits = "=" + trits
            n = n // 3
        elif rem == 1:
            trits = "+" + trits
            n = (n - 1) // 3
        else:
            trits = "-" + trits
            n = (n + 1) // 3
    
    return trits

def decimal_to_trits(n, trit_size=8):
    """
    Convert to balanced ternary with framing
    Default: 8-trit = 1 training wheel + 6-trit tribble + 1 training wheel
    """
    core_4 = decimal_to_trits_4(n)
    
    if trit_size == 4:
        return core_4
    elif trit_size == 6:
        return "=" + core_4 + "="
    elif trit_size == 8:
        tribble_6 = "=" + core_4 + "="
        return "=" + tribble_6 + "="
    elif trit_size == 12:
        tribble_6 = "=" + core_4 + "="
        return "===" + tribble_6 + "==="
    else:
        raise ValueError(f"Unsupported size: {trit_size}. Use 4, 6, 8, or 12.")

def build_mappings(trit_size=8):
    """Build character mappings"""
    char_to_trits = {}
    trits_to_char = {}
    
    char_to_trits[' '] = decimal_to_trits(0, trit_size)
    
    for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        char_to_trits[c] = decimal_to_trits(i + 1, trit_size)
    
    for i, c in enumerate('abcdefghijklmnopqrstuvwxyz'):
        char_to_trits[c] = decimal_to_trits(-(i + 1), trit_size)
    
    for i, c in enumerate('0123456789'):
        char_to_trits[c] = decimal_to_trits(i + 27, trit_size)
    
    punct = {
        '.': 37, ',': 38, '?': 39, '!': 40, ';': 41, ':': 42, "'": 43, '"': 44,
        '(': 45, ')': 46, '[': 47, ']': 48, '{': 49, '}': 50, '/': 51, '\\': 52,
        '-': 53, '_': 54, '+': 55, '=': 56, '*': 57, '%': 58, '<': 59, '>': 60,
        '&': 61, '|': 62, '^': 63, '~': 64, '@': 65, '#': 66, '$': 67, '`': 68,
        '\n': 69, '\t': 70,
    }
    
    for char, val in punct.items():
        char_to_trits[char] = decimal_to_trits(val, trit_size)
    
    for char, trits in char_to_trits.items():
        trits_to_char[trits] = char
    
    return char_to_trits, trits_to_char

def encode(text, char_to_trits):
    """Encode text to trits"""
    result = ""
    for c in text:
        if c in char_to_trits:
            result += char_to_trits[c]
    return result

def decode(trits, trits_to_char, trit_size):
    """Decode trits to text"""
    result = ""
    for i in range(0, len(trits), trit_size):
        block = trits[i:i+trit_size]
        if len(block) == trit_size:
            result += trits_to_char.get(block, '?')
    return result

def overlay_carrier(message, trit_size=8):
    """Apply carrier wave to ALL trits"""
    carrier = "+=-="
    result = ""
    
    for i, trit in enumerate(message):
        msg_val = {'+': 1, '=': 0, '-': -1}[trit]
        car_val = {'+': 1, '=': 0, '-': -1}[carrier[i % 4]]
        
        total = msg_val + car_val
        while total < -1:
            total += 3
        while total > 1:
            total -= 3
        
        result += {-1: '-', 0: '=', 1: '+'}[total]
    
    return result

def remove_carrier(encoded, trit_size=8):
    """Remove carrier wave from ALL trits"""
    carrier = "+=-="
    result = ""
    
    for i, trit in enumerate(encoded):
        enc_val = {'+': 1, '=': 0, '-': -1}[trit]
        car_val = {'+': 1, '=': 0, '-': -1}[carrier[i % 4]]
        
        diff = enc_val - car_val
        while diff < -1:
            diff += 3
        while diff > 1:
            diff -= 3
        
        result += {-1: '-', 0: '=', 1: '+'}[diff]
    
    return result

def trit_to_visual(trit):
    """Convert to LED symbols"""
    return {'+': '🔴', '=': '⚫', '-': '🟢'}[trit]

TRIBBLE_VOCAB = {
    'HELLO': '==+===',
    'ACK': '==++==',
    'NACK': '==--==',
    'DONE': '==+=+==',
    'ERROR': '==+-==',
    'READY': '==-+==',
    'YES': '==++++',
    'NO': '==----',
    'MAYBE': '======',
    'OK': '==+++=',
    'BUSY': '==--+=',
    'WAIT': '===-==',
    'DATA': '==+-+=',
    'EOF': '==++--',
    'MORE': '==-++=',
}

TRIBBLE_DECODE = {v: k for k, v in TRIBBLE_VOCAB.items()}

def get_tribble_opcode(word):
    return TRIBBLE_VOCAB.get(word.upper())

def decode_tribble_opcode(trits):
    return TRIBBLE_DECODE.get(trits)

def analyze_repeating_pattern(text):
    """Detect if message is 3 repeating characters"""
    unique = list(set(text))
    if len(unique) != 3:
        return None
    
    counts = {c: text.count(c) for c in unique}
    
    return {
        'chars': unique,
        'counts': counts,
        'note': 'Message contains exactly 3 unique characters'
    }

def main():
    parser = argparse.ArgumentParser(
        description='Balanced Ternary Encoder/Decoder',
        usage='%(prog)s "message" [-v] [-d]'
    )
    parser.add_argument('message', help='Message to encode/decode')
    parser.add_argument('-4', '--trumb', action='store_const', const=4, dest='size')
    parser.add_argument('-6', '--tribble', action='store_const', const=6, dest='size')
    parser.add_argument('-8', '--framed', action='store_const', const=8, dest='size')
    parser.add_argument('-12', '--tryte', action='store_const', const=12, dest='size')
    parser.add_argument('--no-carrier', action='store_true')
    parser.add_argument('-d', '--decode', action='store_true')
    parser.add_argument('--vocab', action='store_true')
    parser.add_argument('--opcode', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    
    args = parser.parse_args()
    
    if args.vocab:
        print("=== BABY TRIBBLE VOCABULARY ===")
        for word, trits in sorted(TRIBBLE_VOCAB.items()):
            visual = " ".join([trit_to_visual(t) for t in trits])
            print(f"  {word:12} {trits:12} {visual}")
        return
    
    message = args.message
    is_encoded = all(c in '+=-' for c in message) and len(message) > 0
    
    if not args.decode and is_encoded:
        args.decode = True
    
    trit_size = args.size if args.size else 8
    use_carrier = not args.no_carrier
    
    char_to_trits, trits_to_char = build_mappings(trit_size)
    
    if args.decode:
        trits = args.message
        if use_carrier:
            trits = remove_carrier(trits, trit_size)
            print(f"DEBUG: After carrier removal: {trits}")
        decoded = decode(trits, trits_to_char, trit_size)
        
        if args.verbose:
            opcode = decode_tribble_opcode(trits[:8] if len(trits) >= 8 else trits)
            if opcode:
                print(f"[TRIBBLE OPCODE: {opcode}]")
        
        print(decoded)
    else:
        if args.opcode:
            opcode = get_tribble_opcode(args.message)
            if opcode:
                if use_carrier:
                    output = overlay_carrier(opcode, 6)
                else:
                    output = opcode
                
                if args.verbose:
                    print(f"Tribble Opcode: {args.message.upper()}")
                    visual = " ".join([trit_to_visual(t) for t in output])
                    print(f"  {visual}")
                    print()
                
                print(output)
                return
            else:
                print(f"Unknown opcode: {args.message}")
                return
        
        text = args.message
        pattern = analyze_repeating_pattern(text)
        encoded = encode(text, char_to_trits)
        
        if use_carrier:
            output = overlay_carrier(encoded, trit_size)
        else:
            output = encoded
        
        if args.verbose:
            print(f"Message: {text}")
            print(f"Format: {trit_size}-trit {'with' if use_carrier else 'without'} carrier")
            print()
            
            if use_carrier:
                print("WITHOUT CARRIER:")
                for i, char in enumerate(text):
                    char_trits = encoded[i*trit_size:(i+1)*trit_size]
                    visual = " ".join([trit_to_visual(t) for t in char_trits])
                    label = "SPC" if char == " " else char
                    print(f"  {label:>4}: {visual}")
                print()
                print("WITH CARRIER:")
            
            for i, char in enumerate(text):
                char_trits = output[i*trit_size:(i+1)*trit_size]
                visual = " ".join([trit_to_visual(t) for t in char_trits])
                label = "SPC" if char == " " else char
                print(f"  {label:>4}: {visual}")
            
            print()
            print("Encoded:")
            print(output)
            print()
            
            # Auto-decode verification
            print("=== DECODE VERIFICATION ===")
            test_trits = output
            if use_carrier:
                test_trits = remove_carrier(test_trits, trit_size)
                print(f"DEBUG: Plain trits should be: {encoded}")
                print(f"DEBUG: After carrier removal: {test_trits}")
            decoded_test = decode(test_trits, trits_to_char, trit_size)
            print(f"Decoded back: {decoded_test}")
            if decoded_test == text:
                print("✓ Round-trip successful!")
            else:
                print("✗ Round-trip FAILED!")
                print(f"  Expected: {text}")
                print(f"  Got:      {decoded_test}")
            print()
        
        print(output)
        
        if args.verbose and pattern:
            print()
            print("="*60)
            print("PATTERN DETECTED: 3 unique characters")
            print("="*60)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    main()
