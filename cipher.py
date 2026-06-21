
def bits_to_seed(bits):
    bit_string = ''.join(map(str, bits))
    return int(bit_string, 2)


# def generate_permutation_from_seed(seed, length):
#     np.random.seed(seed % (2**128))
#     perm = np.arange(length)
#     np.random.shuffle(perm)
#     return perm




def generate_permutation_from_seed(seed, length):
    """
    FIXED: Uses Python's random.Random which accepts arbitrary-sized seeds
    This preserves full 128-bit entropy (not limited to 32 bits like NumPy)
    """
    rng = random.Random(seed)  # Accepts full 128-bit integer!
    perm = list(range(length))
    rng.shuffle(perm)  # Still uses Fisher-Yates algorithm
    return np.array(perm)

# def generate_permutation_from_seed(seed, length):
#     # Use full 128-bit entropy via hash-based seeding
#     seed_bytes = seed.to_bytes(16, 'big')  # 128 bits = 16 bytes
#     hash_val = int(hashlib.sha256(seed_bytes).hexdigest()[:8], 16)  # Take first 32 bits of hash
#     np.random.seed(hash_val)
#     perm = np.arange(length)
#     np.random.shuffle(perm)
#     return perm




def generate_inverse_permutation(perm):
    inverse = np.empty_like(perm)
    inverse[perm] = np.arange(len(perm))
    return inverse


class KeyStreamGenerator:
    """Generates XOR keystream for confusion layer - THE CRITICAL FIX"""
    
    def __init__(self, key_256_bits, session_id):
        # Combine key and session for unique keystream
        key_hex = bits_to_hex(key_256_bits)
        seed_string = f"{key_hex}:{session_id}"
        self.seed_hash = hashlib.sha256(seed_string.encode()).digest()
    
    def generate(self, length_bytes):
        """Generate keystream matching plaintext length"""
        keystream = bytearray()
        counter = 0
        
        while len(keystream) < length_bytes:
            # Counter mode for synchronous stream generation
            data = self.seed_hash + counter.to_bytes(4, 'big')
            chunk = hashlib.sha256(data).digest()
            keystream.extend(chunk)
            counter += 1
        
        return bytes(keystream[:length_bytes])


class ByteLevelQPP:
    def __init__(self, key_bits_128):
        self.key_bits = key_bits_128
        self.seed = bits_to_seed(key_bits_128)
    
    def encrypt(self, plaintext_bytes):
        if len(plaintext_bytes) == 0:
            return plaintext_bytes
        
        n_bytes = len(plaintext_bytes)
        perm = generate_permutation_from_seed(self.seed, n_bytes)
        
        plaintext_array = np.frombuffer(plaintext_bytes, dtype=np.uint8)
        encrypted_array = plaintext_array[perm]
        
        return bytes(encrypted_array)
    
    def decrypt(self, ciphertext_bytes):
        if len(ciphertext_bytes) == 0:
            return ciphertext_bytes
        
        n_bytes = len(ciphertext_bytes)
        perm = generate_permutation_from_seed(self.seed, n_bytes)
        inv_perm = generate_inverse_permutation(perm)
        
        ciphertext_array = np.frombuffer(ciphertext_bytes, dtype=np.uint8)
        decrypted_array = ciphertext_array[inv_perm]
        
        return bytes(decrypted_array)


class BitLevelQPP:
    def __init__(self, key_bits_128):
        self.key_bits = key_bits_128
        self.seed = bits_to_seed(key_bits_128)
    
    def bytes_to_bits(self, data_bytes):
        bit_list = []
        for byte in data_bytes:
            bits = [(byte >> i) & 1 for i in range(8)]
            bit_list.extend(bits)
        return np.array(bit_list, dtype=np.uint8)
    
    def bits_to_bytes(self, bits):
        padding = (8 - len(bits) % 8) % 8
        if padding > 0:
            bits = np.concatenate([bits, np.zeros(padding, dtype=np.uint8)])
        
        byte_array = bytearray()
        for i in range(0, len(bits), 8):
            byte_val = 0
            for j in range(8):
                byte_val |= (bits[i + j] << j)
            byte_array.append(byte_val)
        
        return bytes(byte_array)
    
    def encrypt(self, data_bytes):
        if len(data_bytes) == 0:
            return data_bytes
        
        bits = self.bytes_to_bits(data_bytes)
        n_bits = len(bits)
        
        perm = generate_permutation_from_seed(self.seed, n_bits)
        encrypted_bits = bits[perm]
        
        return self.bits_to_bytes(encrypted_bits)
    
    def decrypt(self, ciphertext_bytes):
        if len(ciphertext_bytes) == 0:
            return ciphertext_bytes
        
        bits = self.bytes_to_bits(ciphertext_bytes)
        n_bits = len(bits)
        
        perm = generate_permutation_from_seed(self.seed, n_bits)
        inv_perm = generate_inverse_permutation(perm)
        
        decrypted_bits = bits[inv_perm]
        
        return self.bits_to_bytes(decrypted_bits)


class EnhancedTwoLayerQPP:
    """
    FIXED VERSION: Includes XOR confusion layer
    Architecture: XOR → Byte Permutation → Bit Permutation
    """
    
    def __init__(self, key_256_bits, session_id=None):
        if len(key_256_bits) != 256:
            raise ValueError(f"Key must be 256 bits, got {len(key_256_bits)}")
        
        if session_id is None:
            session_id = str(time.time())
        
        session_hash = hashlib.sha256(session_id.encode()).digest()
        session_bits = np.unpackbits(np.frombuffer(session_hash, dtype=np.uint8))
        
        dynamic_key = np.bitwise_xor(key_256_bits, session_bits)
        
        self.key_layer1 = dynamic_key[:128]
        self.key_layer2 = dynamic_key[128:256]
        
        # Initialize confusion layer
        self.keystream_gen = KeyStreamGenerator(key_256_bits, session_id)
        
        # Initialize permutation layers
        self.byte_qpp = ByteLevelQPP(self.key_layer1)
        self.bit_qpp = BitLevelQPP(self.key_layer2)
        
        self.session_id = session_id
    
    def encrypt(self, plaintext):
        """
        Enhanced encryption with confusion layer:
        Plaintext → XOR with KeyStream → Byte Permutation → Bit Permutation
        """
        if isinstance(plaintext, str):
            plaintext_bytes = plaintext.encode('utf-8')
        else:
            plaintext_bytes = plaintext
        
        # STEP 1: XOR Confusion Layer (THE CRITICAL FIX)
        keystream = self.keystream_gen.generate(len(plaintext_bytes))
        xor_result = bytes(a ^ b for a, b in zip(plaintext_bytes, keystream))
        
        # STEP 2: Byte-level permutation
        after_byte = self.byte_qpp.encrypt(xor_result)
        
        # STEP 3: Bit-level permutation
        ciphertext = self.bit_qpp.encrypt(after_byte)
        
        return ciphertext
    
    def decrypt(self, ciphertext_bytes):
        """
        Decryption in reverse:
        Ciphertext → Inverse Bit Perm → Inverse Byte Perm → XOR with KeyStream
        """
        # STEP 1: Inverse bit-level permutation
        after_bit_decrypt = self.bit_qpp.decrypt(ciphertext_bytes)
        
        # STEP 2: Inverse byte-level permutation
        after_byte_decrypt = self.byte_qpp.decrypt(after_bit_decrypt)
        
        # STEP 3: XOR with same keystream to recover plaintext
        keystream = self.keystream_gen.generate(len(after_byte_decrypt))
        plaintext_bytes = bytes(a ^ b for a, b in zip(after_byte_decrypt, keystream))
        
        try:
            return plaintext_bytes.decode('utf-8')
        except:
            return plaintext_bytes


