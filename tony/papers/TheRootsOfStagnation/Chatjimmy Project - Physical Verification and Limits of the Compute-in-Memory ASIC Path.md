# The Chatjimmy Project: Physical Verification and Limits of the Compute-in-Memory ASIC Path

**Abstract**

This paper analyzes the Chatjimmy project by Taalas Inc., which implements an extreme technical approach of "burning a large language model directly into silicon." According to data published by Taalas, Chatjimmy hardwires an 8B-parameter model into a 6nm chip, achieving over 15,000 tokens per second in inference throughput — approximately two orders of magnitude above GPU-based solutions. We argue that its core significance lies in providing the first engineering-grade physical verification of the compute-in-memory ASIC path. The central insight is a long-overlooked architectural principle we term "deferred output": let data undergo as many consecutive transformations as possible within the compute unit, releasing it only at the inevitable final step. The von Neumann architecture's compute-storage separation physically constrains GPUs from implementing this principle — on-chip SRAM cannot hold the intermediate activations of an entire computation chain, making off-chip communication forced. Chatjimmy circumvents this constraint through hardwiring, at the cost of zero flexibility. This defines the ASIC path's applicable boundary: scenarios where the algorithm has converged and the workload is fixed.

**Keywords**: compute-in-memory; hardwired; deferred output; memory wall; quantization; CIM; ASIC


## 1. Introduction

The core bottleneck of large language model inference lies in the "memory wall" caused by the von Neumann architecture's separation of compute and storage. GPU effective utilization under typical LLM workloads is as low as 10–20% (MFU), with SM utilization during the decode phase at only 20–40%, while `nvidia-smi` defines "at least one kernel executing" as 100% utilization, further obscuring real efficiency [0].

In early 2026, the Canadian startup Taalas introduced the Chatjimmy project, responding to this problem in an unprecedented way. The team abandoned the traditional "general-purpose compute + external memory" design and hardwired an 8B-parameter model directly into a 6nm chip. According to data published by Taalas, this chip achieves over 15,000 tokens per second in inference throughput.

Chatjimmy's significance lies not in its prospects as a product, but in its weight as a physical feasibility proof. We argue that the central insight of this verification is a long-overlooked architectural principle — "deferred output" — and its physical constraint on GPUs. Chatjimmy circumvents this constraint through hardwiring, thereby providing the first engineering-grade verification of the compute-in-memory ASIC path.

**Data source.** All Chatjimmy performance data cited in this paper come from Taalas Inc.'s technical report [1]. As of writing, Taalas has no publicly accessible official website, academic papers, industry media coverage, or independent third-party evaluation; all Chatjimmy data exist solely in Taalas's self-published technical report. IBM NorthPole [2] (published in *Science*, peer-reviewed) has higher data credibility. All data originating from Taalas are marked "according to Taalas" below.


## 2. Technical Implementation

### 2.1 Core Design: Turning the Model into Circuitry

Chatjimmy's core design strategy is to etch the weight data of a trained large language model directly into the metal interconnect layer of a silicon die. The model is no longer a collection of numbers stored in memory awaiting retrieval by a compute unit; the model *is* the chip's physical circuitry.

Each weight is encoded as a physical wire characteristic connecting compute units. When current flows through these wires, computation completes naturally. This design entirely bypasses the traditional chip cycle of "fetch instruction, fetch data, execute, write back." Key technical choices include:

- **Hardwired**: Compute logic and parameter storage are fused into the same physical structure; there are no independent memory units or caches.
- **Mask ROM**: Weights are burned into non-rewritable mask read-only memory, physically immutable.
- **Aggressive quantization**: A 3-bit/6-bit mixed quantization strategy compresses the model to fit within a single chip's physical area.

### 2.2 Key Physical Specifications

| Metric | Value | Notes |
|--------|-------|-------|
| Die area | 815 mm² | Near reticle limit, comparable to H100 GPU's 814 mm² |
| Transistors | ~53 billion | Comparable to mainstream large-die GPUs |
| Model parameters | 8B | 3-bit/6-bit mixed quantization |
| Inference speed | 15,000–17,000 tokens/s | According to Taalas |
| Power consumption | ~200W | According to Taalas |
| Development cost | ~$30 million | According to Taalas, approximately 1/20 of traditional AI chips |
| Design cycle | 60 days | According to Taalas, from design start to tape-out |
| Design team | ~25 people | According to Taalas |

### 2.3 Quantization Strategy and Precision Cost

The 3-bit/6-bit mixed quantization is the key prerequisite for fitting 8B parameters on a single chip. At FP16, 8B parameters require approximately 16GB of storage; even with 4-bit uniform quantization, approximately 4GB is needed. To implement this within 815 mm² of silicon area, the average bits per parameter must be compressed to the 3–4 bit range.

In the academic literature, 4-bit quantization is nearly lossless: GPTQ [3] reports only about 0.1 point of perplexity degradation at 4-bit on LLaMA-65B, and AWQ [4] reports similar results. 3-bit constitutes a watershed: GPTQ 3-bit shows approximately 1.5 points of perplexity degradation (LLaMA-65B rising from 5.99 to approximately 7.4–7.6), AWQ is slightly better (approximately 7.0–7.3), but still far above 4-bit results. QuIP# [5] and AQLM [15] have achieved breakthroughs at the 2-bit level through non-uniform codebooks and vector quantization, demonstrating that quantization method selection significantly affects quality at low bit widths.

Taalas has not disclosed the details of Chatjimmy's quantization scheme. If 3-bit quantization causes significant perplexity degradation, then part of the "two orders of magnitude speed advantage" represents a trade of speed for precision. Two points, however: first, even with all weights at 4-bit (nearly lossless), the order-of-magnitude advantage from hardwired elimination of data movement still holds — the physical root of the speed advantage is unaffected. Second, if Chatjimmy employs a non-uniform quantization scheme, the precision loss of 3-bit/6-bit mixing may be far less than what uniform quantization would suggest. The quantization question affects "how large the advantage is," not "whether the advantage exists."

### 2.4 Fundamental Difference from Mainstream Approaches

GPUs employ general-purpose compute architectures with programmable cores and high-bandwidth memory supporting arbitrary model training and inference — flexible but energy-inefficient due to the compute-storage separation bandwidth bottleneck. NPUs and TPUs customize dedicated matrix units for AI computation, more efficient than GPUs but still retaining extensive programmability and external memory interfaces. Chatjimmy takes this to the extreme: completely abandoning programmability, hardwiring a single model into silicon, standing at the extreme end of the efficiency–flexibility spectrum.


## 3. Core Insight: Deferred Output

Chatjimmy's speed advantage appears to come from "hardwiring," but hardwiring is merely the means. What drives the order-of-magnitude improvement is a deeper architectural principle — which we formalize as "deferred output."

### 3.1 The Real Cost of "Output" in Traditional Architectures

In the von Neumann architecture, "output" is not a cheap terminal action. Each writeback of computation results to external memory constitutes a complete physical communication: driving centimeter-scale long wires, crossing clock domains, waiting for bus arbitration, refreshing multi-level caches. In a typical Transformer inference, each layer must perform such an "output" after computation, writing intermediate activations back to memory for the next layer to read. Over one inference pass, this "output-read" cycle executes tens to hundreds of times. The deeper the model, the greater the accumulated cost.

**GPUs are physically constrained to "forced output."** GPU SM cores connect to HBM memory through off-chip buses with physical distances of approximately 1–3 cm. A single off-chip communication consumes approximately 100–1000× the energy of an on-chip communication over the same distance [13][14]. GPU SM on-chip SRAM capacity is limited (H100: approximately 256KB L1 per SM, approximately 3MB L2 per TPC), insufficient to hold an entire Transformer's intermediate activations — a 32-layer, 4096-dimension model can generate intermediate activations on the order of GBs per inference pass, far exceeding on-chip capacity. Therefore, GPUs have no physical choice: they must write intermediate activations back to HBM after each layer because on-chip storage is insufficient; they must re-read from HBM before the next layer because the data is not locally available. Regardless of how clever the compiler or how thorough the operator fusion, as long as on-chip SRAM capacity is insufficient to hold the intermediate state of an entire computation chain, off-chip communication is unavoidable.

This is the physical essence of the "memory wall": the compute-storage separation architecture physically constrains "deferred output." Each inter-layer output is a forced, costly physical communication.

### 3.2 Origins of Intermediate Result Externalization

This "forced output" design is not purely historical inertia but the product of multiple constraints:

- **Limited storage resources**: Early computers lacked sufficient on-chip storage to hold an entire computation chain's intermediate results, requiring layer-by-layer swap-out. This constraint persists today — on-chip SRAM capacity growth lags far behind model scale growth.
- **Training requirements**: Backpropagation in the training phase requires access to each layer's intermediate activations for gradient computation, mandating externalized storage of intermediate results. Inference inherits the training architecture, even though inference itself does not require backpropagation.
- **Observability requirements**: Debugging and diagnostics require inspection of intermediate states.

However, LLM inference has a distinctive property: the inference process itself is a "black box" that cannot be step-by-step interpreted. It requires no gradient backpropagation and no intermediate state checkpoints. Retaining externalized channels for intermediate results in a process that is itself a black box and requires no backtracking carries high cost with limited benefit.

### 3.3 Chatjimmy's Answer: Defer to the Last Moment

In the hardwired scheme, Chatjimmy's intermediate computation results never leave the chip's core compute region. Data flows directly from one layer's compute path to the next, without passing through any external interface. The tens to hundreds of "output-read" cycles in traditional architectures are compressed into a single, uninterrupted internal flow. Only after the entire model inference completes does the chip execute its one "true output" — sending the generated token out.

### 3.4 Semi-Formal Formulation of the "Deferred Output" Principle

Consider an L-layer Transformer inference process. Let:

- $E_{comp}$: energy per layer computation
- $E_{comm}$: energy per off-chip writeback-read communication
- $T_{comp}$: latency per layer computation
- $T_{comm}$: latency per off-chip communication

Traditional architecture (output per layer):

$$E_{trad} = L \cdot E_{comp} + L \cdot E_{comm}$$
$$T_{trad} = L \cdot T_{comp} + L \cdot T_{comm}$$

Deferred output architecture (output only at the end):

$$E_{defer} = L \cdot E_{comp} + 1 \cdot E_{comm}$$
$$T_{defer} = L \cdot T_{comp} + 1 \cdot T_{comm}$$

Benefit ratio:

$$\frac{E_{trad}}{E_{defer}} = \frac{L \cdot (E_{comp} + E_{comm})}{L \cdot E_{comp} + E_{comm}}$$

When $E_{comm} \gg E_{comp}$ (which is precisely the physical meaning of the "memory wall"), this ratio approaches $L$. For typical L = 32–96 layer models, deferred output can yield 1–2 orders of magnitude energy advantage. Latency analysis is analogous.

This model captures the core structure: **when communication cost far exceeds computation cost, the benefit of reducing communication count is proportional to the number of layers.** This is the physical root of Chatjimmy's order-of-magnitude advantage.

### 3.5 "Deferred Output" Is Not Exclusive to Hardwiring

The above analysis does not depend on hardwiring as the specific implementation. It depends on one condition: the cost of data flow within the compute unit is far lower than the cost of cross-unit/cross-chip communication. This condition holds across multiple architectures:

- **Software level**: The XLA compiler [16] fuses multiple operations into a single kernel, keeping intermediate activations in registers/on-chip SRAM; FlashAttention [17] tiles attention computation, eliminating O(N²) intermediate matrix writeback to DRAM, achieving 2–4× speedup; TVM [18] operator fusion achieves 2–4× latency improvement by eliminating intermediate tensor materialization.
- **Near-memory compute level**: IBM NorthPole [2] stores weights in tightly coupled on-chip SRAM, with activations flowing between cores without DRAM writeback.
- **Compiler scheduling level**: Groq LPU [11] uses compiler-static scheduling, with data flowing between on-chip SRAM banks in deterministic temporal order, without runtime arbitration.

These practices and Chatjimmy's hardware-level implementation embody the same principle at different levels: **minimize intermediate data materialization and writeback, letting data flow as far as possible along the computation path.** The distinction is only whether this is a compile-time optimization (XLA/FlashAttention), a runtime architectural choice (NorthPole/Groq), or a manufacturing-time constraint (Chatjimmy hardwiring).

> **Deferred Output Principle**: In compute-in-memory architectures, the design objective of a compute unit is not to "accelerate each computation" but to "defer the first output." Let data reside within the compute unit for as long as possible, completing as many consecutive internal transformations as possible, releasing it only at the inevitable final output.

This principle redirects design attention from "latency of individual computations" to "depth of consecutive computation" — the latter is the true performance multiplier in compute-in-memory architectures.


## 4. Three Verifications from the Perspective of "Deferred Output"

"Deferred output" is Chatjimmy's core insight. The following three verifications are extensions of this insight across different dimensions.

### 4.1 Verification 1: Architecture Outperforms Process — Because Process Scaling Does Not Solve the Communication Problem

Chatjimmy uses TSMC's 6nm process and, according to Taalas, achieves approximately two orders of magnitude throughput advantage. This advantage comes not from a more advanced process node but from a fundamentally different architecture.

Process scaling solves the "computation" problem — smaller transistors, higher density, lower switching energy. But it does not solve the "communication" problem — off-chip data movement energy is determined by physical distance and interconnect architecture, independent of transistor size. From N7 to N3, TSMC achieves approximately 1.5–2× logic density improvement per generation, but SRAM density improvement is only approximately 1.1× [12] — and SRAM is precisely the on-chip cache resource that GPUs depend on to attempt "deferred output." Process scaling shows diminishing returns on the dimension most critical to deferred output.

IBM NorthPole [2] achieved 22× energy efficiency (silicon-measured, ResNet-50 workload) and 25× space efficiency over comparable GPUs on a 14nm process. Its energy efficiency advantage comes primarily from eliminating DRAM access — precisely the engineering implementation of "deferred output." NorthPole's 256Mb on-chip SRAM cannot hold LLM weights (LLaMA-7B at 4-bit requires approximately 28,000Mb), but its physically verified logic applies equally to LLMs: the benefit of eliminating communication far exceeds the benefit of accelerating computation.

Both projects, at different process nodes (14nm and 6nm) and different technical paths (near-memory compute and hardwired compute-in-memory), converge on the same conclusion: **architectural restructuring yields benefits far exceeding process scaling, because process scaling does not solve the communication problem, and communication is the bottleneck.**

### 4.2 Verification 2: The "Memory Wall" Is a Consequence of Architectural Choice — Because "Deferred Output" Is Physically Feasible

The "memory wall" has been accepted as a fundamental constraint in computer architecture since Wulf and McKee formalized the concept in 1995 [13]. The industry's response has consistently been local optimization within the premise of accepting compute-storage separation: wider memory buses, larger on-chip caches, more advanced HBM stacking. These efforts are effective but have never yielded order-of-magnitude breakthroughs — because they do not address the root cause: compute-storage separation itself.

Chatjimmy does not optimize data transfer; it eliminates the act of transfer entirely. Its physical existence demonstrates: the "memory wall" is not an insurmountable constraint imposed by physical law, but a consequence of the von Neumann architecture's design choice of compute-storage separation. With the premise of abandoning generality, "deferred output" is physically feasible, and order-of-magnitude efficiency improvements are achievable.

**Scope.** Chatjimmy eliminates data movement but simultaneously eliminates flexibility. Eliminating data movement while retaining von Neumann generality has no evidence of feasibility at present. Therefore, the more precise formulation is: **the "memory wall" can be circumvented under the premise of abandoning von Neumann architectural generality.**

The theoretical contribution of this verification is that it transforms the "memory wall" from a default-accepted constraint into an object that can be questioned and challenged — provided one is willing to step outside the von Neumann paradigm's presuppositions.

### 4.3 Verification 3: Economic Barriers Drop When the Problem Is Clearly Defined — Because "Deferred Output" Does Not Require Generality's Overhead

According to Taalas, Chatjimmy's development cost was approximately $30 million, with 60 days from design start to tape-out, and a design team of only about 25 people. Traditional AI chip development costs are typically in the hundreds of millions of dollars, with cycles measured in years and teams numbering in the hundreds.

This order-of-magnitude compression comes not from a manufacturing process revolution but from a cliff-like drop in design complexity. When the chip's design objective is extremely simplified to "do one thing" — efficiently run inference for a specific model — the vast supporting systems required for generality can be eliminated. And "doing one thing" is feasible precisely because "deferred output" does not require generality's overhead: no multi-level caches to handle uncertain access patterns, no memory controllers to arbitrate concurrent requests, no general-purpose programming API stacks to support arbitrary algorithms. The data path is deterministic, unidirectional, and non-interruptible — design becomes "drawing the model as a circuit diagram."

**The meaning of this verification.** What Chatjimmy eliminates is not the "cost of innovation" but the "cost of generality." Generality itself is valuable — GPUs pay enormous design overhead for generality and thereby serve a wide range of workloads. Chatjimmy's low cost comes precisely from not needing this generality. The correct proposition is: **when the problem is clearly defined, the economic barrier to chip design can drop dramatically — but "clear definition" itself is precisely the "right to define" issue currently obstructed by monopolistic ecosystems and institutional forces.** Chatjimmy's low-cost implementation is possible because Taalas defined the problem to the extreme — a fixed 8B model, a fixed precision, a fixed architecture.

This fact reveals an important truth from the reverse side: in traditional AI chips' high innovation barriers, the proportion actually spent on "computation" design is small; the bulk of resources is consumed by supporting the flexibility to "do anything." The industry narrative that "chip innovation inevitably requires massive capital and long cycles" is not an objective law but a path dependency formed under a specific technical approach (pursuing generality).


## 5. Positioning on the CIM Roadmap

Chatjimmy did not appear from nowhere; it is an extreme node on the compute-in-memory (CIM) technology roadmap. Wolters et al.'s 2024 survey [6] systematically categorizes CIM architectures, and Chatjimmy's approach can be precisely positioned within it.

**SRAM-based CIM** (digital compute-in-memory). Utilizes SRAM cell bitline parallelism to perform multiply-accumulate operations directly within the memory array. High precision (supporting INT8/FP8), compatible with digital circuit design flows, but with large area overhead — SRAM 6T cell storage density is far lower than DRAM or Flash. Academic prototypes include ISAAC [7] and PRIME [8]. IBM NorthPole [2] can be regarded as an engineering implementation of this approach.

**ReRAM/PCM-based CIM** (analog compute-in-memory). Encodes weights using the conductance values of resistive RAM or phase-change memory, performing multiplication via Ohm's law and accumulation via Kirchhoff's current law. Storage density far exceeds SRAM, but precision is limited — device variation, nonlinear I-V characteristics, and conductance drift result in low signal-to-noise ratio per operation, typically requiring ADC overhead and error compensation circuits.

**Mask ROM hardwiring** (Chatjimmy's approach). Weights are permanently encoded as physical structures in the metal interconnect layer at manufacturing time, non-modifiable. Highest storage density — no SRAM 6T cell overhead, no ReRAM access transistors or ADCs; weights become wires directly. The cost is zero flexibility.

| Dimension | SRAM-based CIM | ReRAM/PCM-based CIM | Mask ROM Hardwired |
|-----------|----------------|---------------------|-------------------|
| Storage density | Low (6T cell ~0.027μm²) | High (1T1R cell ~4–12F²) | Highest (bitmap ~1–2F²) |
| Compute precision | High (digital) | Medium (analog, device variation limits multi-bit precision) | Configurable (digital bitmap, no precision loss) |
| Energy per operation | ~1–10 pJ/MAC | ~0.1–1 pJ/MAC (analog) | ~0.01–0.1 pJ/bit (read-only) |
| Rewritability | Yes (unlimited) | Yes (limited, ReRAM ~10⁶ cycles) | No |
| Flexibility | Reconfigurable | Reconfigurable | Zero |

Chatjimmy's choice of Mask ROM hardwiring represents the extreme of density and efficiency on the CIM spectrum — trading immutability for the highest storage efficiency and lowest access latency. From the "deferred output" perspective, Mask ROM hardwiring is the most thorough implementation of this principle: data not only flows on-chip, but the flow path is permanently determined at manufacturing time, eliminating any runtime routing decision overhead.


## 6. Comparison with Groq LPU: Two Paths to Eliminating Data Movement

Chatjimmy and Groq LPU [11] share the same core objective: eliminating data movement between compute and storage. But they choose fundamentally different implementation paths, and this comparison helps clarify the ASIC path's precise position within the "deferred output" principle.

**Groq LPU** employs a programmable Tensor Streaming Processor (TSP) architecture. The compiler determines the precise timing and destination of every data movement at compile time; data flows between on-chip SRAM banks in deterministic temporal order. Groq's 14nm TSP has demonstrated 80 TB/s aggregate on-chip SRAM bandwidth [11], approximately 26× H100's 3 TB/s HBM bandwidth. But Groq retains programmability — the TSP executes compiler-generated instruction streams, not hardwired logic.

**Chatjimmy** hardwires "compiler scheduling" as well. Data paths are permanently determined at manufacturing time; there are no runtime or compile-time scheduling decisions.

| Dimension | Groq LPU | Chatjimmy |
|-----------|----------|-----------|
| Data movement | Eliminated (on-chip SRAM flow) | Eliminated (hardwired direct connection) |
| Scheduling | Compiler-static | Permanently fixed at manufacturing |
| Programmability | Yes (TSP instruction stream) | No |
| Model change | Recompile | Reticle |
| On-chip memory | 230MB SRAM (reusable) | No independent storage (weights are circuitry) |

The divergence point between the two paths is when "deferred output" scheduling occurs: compile time (Groq) or manufacturing time (Chatjimmy). Groq demonstrates that retaining programmability can also implement "deferred output"; Chatjimmy demonstrates that fixing scheduling at manufacturing time eliminates the overhead of scheduling itself. Their common adversary is the same: the von Neumann architecture's runtime data movement.


## 7. Boundary: The Cost of the Hardwired Path

Chatjimmy's achievements cannot be ignored; its costs cannot be evaded either. These costs define the ASIC path's applicable boundary.

### 7.1 Zero Flexibility

Model weights are burned into non-modifiable Mask ROM. Any form of model upgrade — fine-tuning, architectural improvements, security patches — requires a new tape-out. In an era where AI algorithms evolve on a monthly timescale, a model fixed in hardware faces the risk of algorithmic obsolescence before its physical lifetime ends. The hardware is deeply bound to a specific model architecture; a chip hardwired for Transformers cannot run SSM, MoE, or other architectural models. When algorithmic paradigms shift, the entire chip investment is lost.

### 7.2 Precision Lock-in

The 3-bit/6-bit mixed quantization is permanently fixed at manufacturing time. Precision becomes a non-adjustable hardware parameter rather than a configurable software option.

### 7.3 Monolithic Fixation

At a deeper level, Chatjimmy treats the entire model as an indivisible whole. Computation, scheduling, knowledge, and expression are fixed together in hardwiring in a single, unique way. It does encapsulation but not decoupling — this determines that the purely hardwired path can only be a point solution for specific scenarios, not a way to build general-purpose computing infrastructure.

### 7.4 When Are These Costs Acceptable?

Despite significant costs, the ASIC path has clear competitiveness under the following conditions:

- **Algorithm has converged**: When the target model's architecture and parameters have stabilized to a yearly update cycle,hardwiring is no longer a risk but an advantage — the hardware lifecycle matches the algorithm lifecycle.
- **Workload is fixed**: When the chip serves a single, large-scale inference workload (e.g., millions of users simultaneously using the same model), zero flexibility is not a problem; extreme efficiency is the core competitive advantage.
- **Cost-sensitive**: When inference cost is the primary deployment bottleneck, the ASIC's per-token cost advantage can cover its flexibility loss.

Chatjimmy itself may not satisfy all these conditions — the 8B-parameter model market is still rapidly evolving. But its existence proves: **when these conditions are met, the ASIC path is both physically and economically feasible.** This is its significance as the "first engineering-grade verification."


## 8. Conclusion

Chatjimmy is an important engineering verification of the compute-in-memory ASIC direction. Its core insight is "deferred output" — letting data undergo as many consecutive transformations as possible within the compute unit, releasing it only at the inevitable final step. The von Neumann architecture's compute-storage separation physically constrains GPUs from implementing this principle: on-chip SRAM cannot hold the intermediate activations of an entire computation chain, making off-chip communication forced. Chatjimmy circumvents this constraint through hardwiring, thereby providing the first engineering-grade verification of the compute-in-memory ASIC path.

From the "deferred output" insight, three verifications unfold naturally: architecture outperforms process, because process scaling does not solve the communication problem; the "memory wall" is a consequence of architectural choice, because "deferred output" is physically feasible; economic barriers drop when the problem is clearly defined, because "deferred output" does not require generality's overhead.

Chatjimmy's costs are equally clear: zero flexibility, precision lock-in, monolithic fixation. These costs define the ASIC path's applicable boundary — it suits scenarios where the algorithm has converged and the workload is fixed. In the current era of rapid algorithmic evolution, it is a starting point, not an endpoint.

But the starting point itself has shifted the baseline of discussion: the compute-in-memory ASIC path is no longer theoretical speculation, but an engineering reality verified in silicon.


## References

[0] The Roots of Stagnation: On Computing Paradigms, the Right to Define, and the Failure of Innovation Mechanisms. First paper in this series.

[1] Taalas Inc. Chatjimmy Project Technical Overview and Performance Benchmarks. 2026. (Self-published technical report; no independent third-party verification as of writing.)

[2] Modha, D. S., et al. Neural inference at the frontier of energy, space, and time. Science, vol. 382, no. 6668, 2023, pp. 329-335. DOI: 10.1126/science.adh1174. NorthPole: 14nm process, 2.2 billion transistors, 256Mb on-chip SRAM, 4096 cores, no off-chip DRAM. Energy efficiency data based on silicon measurement (ResNet-50 workload); 22× energy efficiency and 25× space efficiency relative to comparable GPUs. Test workload is CNN, not LLM; 256Mb capacity insufficient for LLM weights.

[3] Frantar, G., et al. GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers. ICLR 2023.

[4] Lin, J., et al. AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration. MLSys 2024.

[5] Chee, J., et al. QuIP#: Even Better LLM Quantization with Hadamard Incoherence and Lattice Codebooks. arXiv:2402.04345, 2024.

[6] Wolters, C., Yang, X., Schlichtmann, U., Suzumura, T. Memory Is All You Need: An Overview of Compute-in-Memory Architectures for Accelerating Large Language Model Inference. arXiv:2406.08413, 2024.

[7] Shafiee, A., et al. ISAAC: A Convolutional Neural Network Accelerator with In-Situ Analog Arithmetic in Crossbars. ISCA 2016.

[8] Chi, P., et al. PRIME: A Novel Processing-in-Memory Architecture for Neural Network Computation. HPCA 2016.

[9] Sun, X., et al. ReRAM-based In-Memory Computing Architecture for Deep Neural Network Training. IEEE TCAD, 2020.

[10] Sebastian, A., et al. Temporal correlation detection using computational memory units for brain-inspired computing. Nature Communications, 2020.

[11] Groq Inc. Tensor Streaming Processor (TSP) Architecture. 14nm process, 80 TB/s aggregate on-chip SRAM bandwidth. Design leads: Dennis Abts (Chief Architect), Jonathan Ross (CEO, former Google TPU team).

[12] TSMC N3 process SRAM density data. Mui, C. "TSMC's 3nm Process Node: The More Things Change, The More They Stay The Same." Forbes, 2022. N5-to-N3 SRAM density improvement approximately 1.1×, far below logic density improvement.

[13] Wulf, W. A., and McKee, S. A. Hitting the memory wall: Implications of the obvious. ACM SIGARCH Computer Architecture News, vol. 23, no. 1, 1995, pp. 20-24.

[14] Patterson, D. A. 50 years of computer architecture: From mainframe CPUs to neural-network TPUs. IEEE Solid-State Circuits Magazine, vol. 10, no. 4, 2018, pp. 26-33.

[15] Eggert, L., et al. AQLM: 1-Bit LLM Quantization with Adaptive Codebooks and Factorization. arXiv:2401.06118, 2024.

[16] OpenXLA. XLA: Optimizing Compiler for Machine Learning. https://github.com/openxla/xla, 2023.

[17] Dao, T., et al. FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness. NeurIPS 2022. (v2: FlashAttention-2, arXiv:2307.08691, 2023.)

[18] Chen, T., et al. TVM: An Automated End-to-End Optimizing Compiler for Deep Learning. OSDI 2018.
