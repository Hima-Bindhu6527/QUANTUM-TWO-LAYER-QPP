# QUANTUM-TWO-LAYER-QPP
Quantum based two-layer permutation cipher with dual-source key generation using decoy state BB84 protocol and QRNG via Qiskit

Overview

Classical permutation ciphers are considered weak due to key predictability and single-layer structure. This work addresses both:

Two-layer architecture: First permutation at byte level, second at bit level
Dual-source key: BB84 protocol key XORed with QRNG key for a 256-bit final key

Key Generation

BB84: Sequential single-qubit circuits (Qiskit Aer), 20,000 quantum pulses per attempt, with decoy states and QBER estimation
QRNG: 100-qubit Hadamard circuits for true quantum randomness
Final key: XOR of both sources

Implementation
Built with Qiskit and Qiskit Aer simulator.
Paper
Accepted at SPARC Conference 2026, forthcoming in Springer LNNS Proceedings (Paper ID 132).
