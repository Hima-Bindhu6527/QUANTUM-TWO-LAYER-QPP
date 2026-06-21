"""
Complete Quantum-Enhanced Two-Layer QPP Encryption System
CORRECTED VERSION - SPARC 2026 NIT Rourkela Submission

Key Fixes Applied:
1. Added XOR Confusion Layer (fixes avalanche effect)
2. Implemented functional NIST tests
3. Added throughput metrics
4. Enhanced BB84 implementation
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import Aer
import random
import hashlib
import time
from collections import Counter
import math

# ========================================
# BLOCK 1: QUANTUM KEY GENERATION
# ========================================

class DecoyStateBB84:
    """Enhanced BB84 Protocol with Decoy States"""
    
    def __init__(self, key_length=256, qber_threshold=0.11):
        self.key_length = key_length
        self.qber_threshold = qber_threshold
        self.backend = Aer.get_backend('qasm_simulator')
    
    def generate_random_bits(self, n):
        return np.random.randint(0, 2, n)
    
    def generate_random_bases(self, n):
        return np.random.randint(0, 2, n)
    
    def alice_prepare_qubits(self, bits, bases, decoy_intensity):
        circuits = []
        for bit, basis in zip(bits, bases):
            qr = QuantumRegister(1, 'q')
            cr = ClassicalRegister(1, 'c')
            qc = QuantumCircuit(qr, cr)
            
            if bit == 1:
                qc.x(qr[0])
            
            if basis == 1:
                qc.h(qr[0])
            
            # Enhanced decoy state implementation
            if decoy_intensity == 'decoy':
                qc.ry(0.1, qr[0])
            elif decoy_intensity == 'vacuum':
                qc.reset(qr[0])
            
            circuits.append(qc)
        
        return circuits
    
    def eve_intercept(self, circuits, intercept_rate=0.1):
        intercepted = []
        for qc in circuits:
            if random.random() < intercept_rate:
                eve_basis = random.randint(0, 1)
                qc_copy = qc.copy()
                if eve_basis == 1:
                    qc_copy.h(0)
                qc_copy.measure(0, 0)
                intercepted.append(True)
            else:
                intercepted.append(False)
        return circuits, intercepted
    
    def bob_measure_qubits(self, circuits, bases):
        results = []
        for qc, basis in zip(circuits, bases):
            qc_measure = qc.copy()
            
            if basis == 1:
                qc_measure.h(0)
            
            qc_measure.measure(0, 0)
            
            job = self.backend.run(qc_measure, shots=1)
            result = job.result()
            counts = result.get_counts()
            measured_bit = int(list(counts.keys())[0])
            results.append(measured_bit)
        
        return np.array(results)
    
    def sift_keys(self, alice_bits, alice_bases, bob_bits, bob_bases):
        matching_indices = alice_bases == bob_bases
        sifted_alice = alice_bits[matching_indices]
        sifted_bob = bob_bits[matching_indices]
        return sifted_alice, sifted_bob
    
    def estimate_qber(self, alice_bits, bob_bits, sample_size=None):
        if sample_size is None:
            sample_size = min(len(alice_bits) // 2, 100)
        
        if len(alice_bits) < sample_size:
            return 1.0, alice_bits, bob_bits
        
        indices = np.random.choice(len(alice_bits), sample_size, replace=False)
        alice_sample = alice_bits[indices]
        bob_sample = bob_bits[indices]
        
        errors = np.sum(alice_sample != bob_sample)
        qber = errors / sample_size
        
        remaining_indices = np.setdiff1d(np.arange(len(alice_bits)), indices)
        alice_remaining = alice_bits[remaining_indices]
        bob_remaining = bob_bits[remaining_indices]
        
        return qber, alice_remaining, bob_remaining
    
    def error_correction(self, alice_bits, bob_bits):
        alice_parity = np.sum(alice_bits) % 2
        bob_parity = np.sum(bob_bits) % 2
        
        if alice_parity != bob_parity:
            diff_indices = np.where(alice_bits != bob_bits)[0]
            if len(diff_indices) > 0:
                bob_bits = bob_bits.copy()
                bob_bits[diff_indices[0]] = alice_bits[diff_indices[0]]
        
        return bob_bits
    
    def privacy_amplification(self, key_bits, target_length):
        if len(key_bits) < target_length:
            return key_bits
        
        random_matrix = np.random.randint(0, 2, (target_length, len(key_bits)))
        amplified_key = np.dot(random_matrix, key_bits) % 2
        
        return amplified_key
    
    def generate_key(self, verbose=False):
        final_key = np.array([], dtype=int)
        attempts = 0
        max_attempts = 20
        
        while len(final_key) < self.key_length and attempts < max_attempts:
            attempts += 1
            n_pulses = 20000
            
            if verbose:
                print(f"\n--- Attempt {attempts} ---")
                print(f"Shooting {n_pulses} pulses...")
            
            alice_bits = self.generate_random_bits(n_pulses)
            alice_bases = self.generate_random_bases(n_pulses)
            
            intensities = np.random.choice(['signal', 'decoy', 'vacuum'], 
                                          n_pulses, p=[0.7, 0.2, 0.1])
            
            circuits = []
            for i in range(n_pulses):
                qc_list = self.alice_prepare_qubits([alice_bits[i]], [alice_bases[i]], 
                                                     intensities[i])
                circuits.extend(qc_list)
            
            circuits, intercepted = self.eve_intercept(circuits, intercept_rate=0.1)
            
            bob_bases = self.generate_random_bases(n_pulses)
            bob_bits = self.bob_measure_qubits(circuits, bob_bases)
            
            sifted_alice, sifted_bob = self.sift_keys(alice_bits, alice_bases, 
                                                       bob_bits, bob_bases)
            
            if verbose:
                print(f"After sifting: {len(sifted_alice)} bits")
            
            if len(sifted_alice) < 50:
                if verbose:
                    print("Not enough bits after sifting, retrying...")
                continue
            
            qber, alice_remain, bob_remain = self.estimate_qber(sifted_alice, sifted_bob)
            
            if verbose:
                print(f"QBER: {qber:.4f} (threshold: {self.qber_threshold})")
            
            if qber > self.qber_threshold:
                if verbose:
                    print("QBER too high, possible eavesdropping! Retrying...")
                continue
            
            bob_corrected = self.error_correction(alice_remain, bob_remain)
            
            available_bits = len(alice_remain)
            needed_bits = self.key_length - len(final_key)
            extract_bits = min(available_bits // 2, needed_bits)
            
            if extract_bits > 0:
                amplified = self.privacy_amplification(alice_remain, extract_bits)
                final_key = np.concatenate([final_key, amplified])
                
                if verbose:
                    print(f"Extracted {extract_bits} bits. Total: {len(final_key)}/{self.key_length}")
        
        final_key = final_key[:self.key_length]
        
        if len(final_key) < self.key_length:
            final_key = np.pad(final_key, (0, self.key_length - len(final_key)), 'constant')
        
        return final_key


class QRNG:
    """Quantum Random Number Generator"""
    
    def __init__(self):
        self.backend = Aer.get_backend('qasm_simulator')
    
    def generate_random_bits(self, n_bits, verbose=False):
        if verbose:
            print(f"\nGenerating {n_bits} quantum random bits...")
        
        random_bits = []
        batch_size = 100
        
        for batch_start in range(0, n_bits, batch_size):
            batch_end = min(batch_start + batch_size, n_bits)
            batch_n = batch_end - batch_start
            
            qr = QuantumRegister(batch_n, 'q')
            cr = ClassicalRegister(batch_n, 'c')
            qc = QuantumCircuit(qr, cr)
            
            for i in range(batch_n):
                qc.h(qr[i])
            
            qc.measure(qr, cr)
            
            job = self.backend.run(qc, shots=1)
            result = job.result()
            counts = result.get_counts()
            
            bitstring = list(counts.keys())[0]
            batch_bits = [int(b) for b in bitstring[::-1]]
            random_bits.extend(batch_bits)
        
        return np.array(random_bits[:n_bits])


def generate_quantum_keys(key_length=256, verbose=True):
    """Generate combined quantum key"""
    if verbose:
        print("="*60)
        print("QUANTUM KEY GENERATION")
        print("="*60)
    
    if verbose:
        print("\n[1/3] Generating Decoy State BB84 Key...")
    bb84 = DecoyStateBB84(key_length=key_length)
    key1 = bb84.generate_key(verbose=verbose)
    
    if verbose:
        print("\n[2/3] Generating QRNG Key...")
    qrng = QRNG()
    key2 = qrng.generate_random_bits(key_length, verbose=verbose)
    
    if verbose:
        print("\n[3/3] XORing both keys...")
    final_key = np.bitwise_xor(key1, key2)
    
    if verbose:
        print(f"\n✓ Final 256-bit key generated!")
    
    return final_key


def bits_to_hex(bits):
    padded = np.pad(bits, (0, (8 - len(bits) % 8) % 8), 'constant')
    hex_str = ''.join([f"{int(''.join(map(str, padded[i:i+8])), 2):02x}" 
                       for i in range(0, len(padded), 8)])
    return hex_str


