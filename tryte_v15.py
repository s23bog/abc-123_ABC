#!/usr/bin/env python3
"""
Tribble Protocol v1.5: Universal Conceptual Interlingua
Supports v1.4.3-H (Character Mode) and v1.5 (Tryte/Concept Mode)
"""

import sys
import argparse
import re

# --- CONFIGURATION ---
CARRIER_PATTERN = "+=-="
BASE_SYNC = "++++"
ERROR_FLAG = "■"

# v1.4 Mode Map (Legacy)
MODE_MAP_V14 = {"+-": 4, "+=": 6, "++": 8, "-+": 12}
INV_MODE_MAP_V14 = {v: k for k, v in MODE_MAP_V14.items()}

# LED Visualization
LED_MAP = {'+': '🔴', '=': '⚫', '-': '🟢'}
REV_LED = {v: k for k, v in LED_MAP.items()}

# --- CATEGORY REGISTRY (v1.5) ---
CATEGORIES = {
    '+++': 'System',      '++=': 'Directions', '++-': 'Numbers',
    '+==': 'Time',        '+=-': 'Logic',      '+=+': 'Elements',
    '+--': 'Biological',  '=++': 'Social'
}

# --- DECIMAL-TO-TRIT CONVERTER ---
def decimal_to_trit(n):
    """Convert decimal (-13 to +13) to 3-trit balanced ternary"""
    trits = ""
    temp = n
    for _ in range(3):
        rem = temp % 3
        if rem == 0:
            trits = "=" + trits
            temp //= 3
        elif rem == 1:
            trits = "+" + trits
            temp = (temp - 1) // 3
        else:  # rem == 2
            trits = "-" + trits
            temp = (temp + 1) // 3
    return trits

def trit_to_decimal(trits):
    """Convert 3-trit balanced ternary to decimal"""
    vals = {'+': 1, '=': 0, '-': -1}
    result = 0
    for i, t in enumerate(reversed(trits)):
        result += vals[t] * (3 ** i)
    return result

# --- COMPLETE LEXICON (ALL 27 LEMMAS PER CATEGORY) ---
def build_lexicon():
    """Generate full lemma maps for all categories"""
    
    logic_lemmas = {
        -13: 'Impossible', -12: 'Never', -11: 'None', -10: 'Against', 
        -9: 'From', -8: 'Without', -7: 'Despite', -6: 'Or', -5: 'If',
        -4: 'Not', -3: 'Different', -2: 'Less', -1: 'Before',
        0: 'Same', 1: 'After', 2: 'More', 3: 'Similar', 4: 'Yes',
        5: 'Then', 6: 'And', 7: 'With', 8: 'To', 9: 'Through',
        10: 'Because', 11: 'Always', 12: 'All', 13: 'Must'
    }
    
    social_lemmas = {
        -13: 'Harm', -12: 'Steal', -11: 'Abandon', -10: 'Deceive',
        -9: 'Exclude', -8: 'Threaten', -7: 'Compete', -6: 'Disagree',
        -5: 'Stranger', -4: 'Other', -3: 'Separate', -2: 'Tell',
        -1: 'You', 0: 'Self', 1: 'We', 2: 'Child', 3: 'Elder',
        4: 'Guide', 5: 'Follow', 6: 'Agree', 7: 'Trust', 8: 'Include',
        9: 'Share', 10: 'Protect', 11: 'Friend', 12: 'Give', 13: 'Help'
    }
    
    system_lemmas = {
        -13: 'STOP', -12: 'CLAUSE_BREAK', -11: 'LIST_ITEM', -10: 'QUOTE',
        -9: 'QUERY_MODE', -8: 'COMMAND_MODE', -7: 'NARRATIVE_MODE',
        -4: 'ERROR', -1: 'ACK', 0: 'STANDBY', 1: 'EMERGENCY',
        2: 'RESPONSE', 4: 'TX_START', 10: 'COMPRESS', 11: 'ENCRYPT',
        12: 'RESERVED', 13: 'SYNC'
    }
    
    return {
        'Logic': logic_lemmas,
        'Social': social_lemmas,
        'System': system_lemmas
    }

LEXICON = build_lexicon()

# --- MODIFIER INTERPRETERS ---
def interpret_tense(trits):
    """Tense/Aspect (trits 7-8)"""
    if trits == '==': return 'Present'
    elif trits == '++': return 'Future'
    elif trits == '--': return 'Past'
    elif trits == '+=': return 'Ongoing'
    elif trits == '-=': return 'Habitual'
    return 'Unknown'

def interpret_intensity(trits):
    """Scale/Intensity (trits 9-10)"""
    if trits == '==': return 'Neutral'
    elif trits == '++': return 'Extreme'
    elif trits == '--': return 'Minor'
    elif trits == '+=': return 'Rising'
    elif trits == '-=': return 'Falling'
    return 'Unknown'

def interpret_polarity(trits):
    """Status/Polarity (trits 11-12)"""
    if trits == '==': return 'Affirm'
    elif trits == '--': return 'Inverse'
    elif trits == '+=': return 'Query'
    elif trits == '-+': return 'Possible'
    return 'Unknown'

# --- CARRIER WAVE (v1.4 COMPATIBILITY) ---
def apply_carrier(block):
    """Apply carrier wave modulation"""
    vals = {'+': 1, '=': 0, '-': -1}
    invs = {-1: '-', 0: '=', 1: '+'}
    result = ""
    for i in range(len(block)):
        mod_val = (vals[block[i]] + vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1
        result += invs[mod_val]
    return result

def remove_carrier(block):
    """Remove carrier wave modulation"""
    vals = {'+': 1, '=': 0, '-': -1}
    invs = {-1: '-', 0: '=', 1: '+'}
    result = ""
    for i in range(len(block)):
        mod_val = (vals[block[i]] - vals[CARRIER_PATTERN[i % 4]] + 1) % 3 - 1
        result += invs[mod_val]
    return result

# --- v1.5 TRYTE PARSER ---
class TryteParser:
    def __init__(self, verbose=False):
        self.mode = "NARRATIVE"
        self.buffer = []
        self.output = []
        self.verbose = verbose
    
    def parse_tryte(self, tryte_raw):
        """Parse a single 12-trit tryte"""
        if len(tryte_raw) != 12:
            return f"[INVALID_LENGTH:{len(tryte_raw)}]"
        
        tryte = remove_carrier(tryte_raw)
        
        cat_code = tryte[0:3]
        lemma_code = tryte[3:6]
        tense = interpret_tense(tryte[6:8])
        intensity = interpret_intensity(tryte[8:10])
        polarity = interpret_polarity(tryte[10:12])
        
        category = CATEGORIES.get(cat_code, 'Unknown')
        
        if category == 'System':
            return self.handle_system(lemma_code)
        else:
            return self.handle_content(category, lemma_code, tense, intensity, polarity)
    
    def handle_system(self, lemma_code):
        """Process system/meta trytes"""
        lemma_dec = trit_to_decimal(lemma_code)
        lemma = LEXICON['System'].get(lemma_dec, f'SYS:{lemma_dec}')
        
        if lemma == 'COMMAND_MODE':
            self.mode = 'COMMAND'
            return "[!COMMAND MODE!] "
        elif lemma == 'QUERY_MODE':
            self.mode = 'QUERY'
            return "[?QUERY MODE?] "
        elif lemma == 'NARRATIVE_MODE':
            self.mode = 'NARRATIVE'
            return ""
        elif lemma == 'STOP':
            return ".\n"
        elif lemma == 'EMERGENCY':
            return " [!!!EMERGENCY!!!] "
        else:
            return f"[{lemma}] "
    
    def handle_content(self, category, lemma_code, tense, intensity, polarity):
        """Process content trytes"""
        lemma_dec = trit_to_decimal(lemma_code)
        
        # Get lemma name
        category_map = LEXICON.get(category, {})
        lemma = category_map.get(lemma_dec, f'{category}:{lemma_dec}')
        
        # Build output string
        mods = []
        if tense != 'Present': mods.append(tense)
        if intensity != 'Neutral': mods.append(intensity)
        if polarity != 'Affirm': mods.append(polarity)
        
        mod_str = f"[{'/'.join(mods)}]" if mods else ""
        
        if self.verbose:
            return f"({category}:{lemma}{mod_str}) "
        else:
            return f"{lemma}{mod_str} "

# --- v1.4 CHARACTER DECODER (LEGACY) ---
def decode_v14_character(normalized, frame_size):
    """Decode v1.4.3-H character-based stream"""
    chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,?!;:'\"()[]{}/\\-_"
    
    # Build codec
    enc = {}
    for i, c in enumerate(chars):
        if c == ' ': val = 0
        elif 'A' <= c <= 'Z': val = ord(c) - ord('A') + 1
        elif 'a' <= c <= 'z': val = -(ord(c) - ord('a') + 1)
        elif '0' <= c <= '9': val = ord(c) - ord('0') + 27
        else:
            p_idx = ".,?!;:'\"()[]{}/\\-_".find(c)
            val = (37 + p_idx) if p_idx < 4 else (-(27 + (p_idx - 4)))
        enc[c] = decimal_to_core(val, frame_size)
    
    trit_map = {v: k for k, v in enc.items()}
    
    # Decode
    chunks = [normalized[i:i+frame_size] for i in range(0, len(normalized), frame_size)]
    decoded = ""
    for chunk in chunks:
        if len(chunk) < frame_size:
            continue
        clean = remove_carrier(chunk)
        decoded += trit_map.get(clean, ERROR_FLAG)
    
    return decoded

def decimal_to_core(n, size):
    """Convert decimal to balanced ternary of specific size"""
    trits = ""
    temp_n = n
    for _ in range(size):
        rem = temp_n % 3
        if rem == 0:
            trits = "=" + trits
            temp_n //= 3
        elif rem == 1:
            trits = "+" + trits
            temp_n = (temp_n - 1) // 3
        else:
            trits = "-" + trits
            temp_n = (temp_n + 1) // 3
    return trits

# --- PROTOCOL VERSION DETECTION ---
def detect_protocol(stream):
    """Detect v1.4 or v1.5 from sync header"""
    sync_match = re.search(r'\+{4}', stream)
    if not sync_match:
        return None, None, None
    
    sync_idx = sync_match.start()
    
    # Check for v1.5 version flag
    if len(stream) >= sync_idx + 9:
        version_flag = stream[sync_idx+4:sync_idx+7]
        
        if version_flag == '++-':  # v1.5 indicator
            mode_suffix = stream[sync_idx+7:sync_idx+9]
            if mode_suffix == '++':
                return '1.5', 12, sync_idx + 9
            else:
                return 'error', None, None
    
    # v1.4 detection (legacy)
    if len(stream) >= sync_idx + 6:
        mode_suffix = stream[sync_idx+4:sync_idx+6]
        frame_size = MODE_MAP_V14.get(mode_suffix, 8)
        return '1.4', frame_size, sync_idx + 6
    
    return None, None, None

# --- MAIN ---
def main():
    parser = argparse.ArgumentParser(description="Tribble Protocol v1.5")
    parser.add_argument("message", help="LED stream or text to encode/decode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-l", "--led", action="store_true", help="LED visualization")
    
    args = parser.parse_args()
    
    # Normalize input (convert LED to trits)
    raw_in = args.message
    for led, trit in REV_LED.items():
        raw_in = raw_in.replace(led, trit)
    
    normalized = "".join(c for c in raw_in if c in '+-=')
    
    # Detect protocol version
    version, frame_size, data_start = detect_protocol(normalized)
    
    if not version:
        print("ERROR: No valid sync header detected")
        print("Expected: '+++' for v1.4 or '+++|++-|++' for v1.5")
        return
    
    print(f">> Tribble Protocol v{version} Detected")
    print(f">> Frame Size: {frame_size} trits")
    
    if version == '1.5':
        # v1.5 Tryte Mode
        payload = normalized[data_start:]
        engine = TryteParser(verbose=args.verbose)
        
        chunks = [payload[i:i+12] for i in range(0, len(payload), 12)]
        result = "".join([engine.parse_tryte(c) for c in chunks if len(c) == 12])
        
        print(f"\n>> Decoded Message:\n{result}")
    
    elif version == '1.4':
        # v1.4 Character Mode
        payload = normalized[data_start:]
        result = decode_v14_character(payload, frame_size)
        
        print(f"\n>> Decoded Message:\n{result}")
    
    else:
        print("ERROR: Invalid protocol configuration")

if __name__ == "__main__":
    main()
