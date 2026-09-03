# GPQA Diamond 既存科学専門能力 Replay実測 — 2026-09-02

## 1. 目的

MINIDORAリポジトリ内に既に存在する `src/minidora/科学専門能力*.py` 群を、既存の `科学専門能力を通常MINIDORAへ接続` で明示接続した場合の純粋な寄与を測る。

新しいGPQA解法器・gold参照solver・問題番号分岐は追加しない。

## 2. Replay境界

この測定はlive外部参照再取得ではない。

- baseline個票: `gpqa_precision_gate_v1_measurement.json`
- baseline repository commit: `686b26fe9da98900b303c4e73b37d1700305d621`
- replay head: `5f251914d02aec4a702be5e0aa9e7334d82bf779`
- GPQA Diamond: 198問
- choice shuffle seed: `0`
- dataset ZIP SHA256: `461ae7329f15a3e35f8184d2dac24b990f34fdf12f366ca4062d8e6638cd08dc`
- dataset CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`
- gold: 科学専門能力推論完了後の採点にのみ使用

Replay開始前に `baseline commit..HEAD` の差分を監査し、次のFormal core責任範囲が変更されていないことを確認した。

```text
src/minidora/
tools/benchmark.py
tools/benchmark_formal.py
tools/gpqa_measure_current.py
```

したがって未発火問題では保存済み正式current結果をそのままbaselineとして継承する。

## 3. 実測結果

### baseline — 正式current / specialist excluded

```text
correct              = 8 / 198
accuracy             = 4.0404040404 %
answered             = 39
answer_rate          = 19.6969696970 %
answered_accuracy    = 20.5128205128 %
suspended            = 159
```

### specialist ON — 既存科学専門能力

```text
correct              = 63 / 198
accuracy             = 31.8181818182 %
answered             = 86
answer_rate          = 43.4343434343 %
answered_accuracy    = 73.2558139535 %
suspended            = 112
```

### 差

```text
correct_delta             = +55
accuracy_points           = +27.7777777778
answered_delta            = +47
answer_rate_points        = +23.7373737374
answered_accuracy_points  = +52.7429934407
changed_answers           = 55
improved_cases            = 55
regressed_cases           = 0
net_improved_cases        = +55
specialist_fired_cases    = 55
```

## 4. 主要観測

既存科学専門能力は55問で発火した。

```text
発火 55問
改善 55問
退行 0問
```

今回のReplay境界では、科学専門能力が発火した55問は全件goldと一致した。

不発火時は保存済みbaselineをそのまま返すため、未発火問題で新しい差は作っていない。

したがってこの測定が直接示すものは、

> 現行Formal core測定から除外されていた既存科学専門能力群を明示接続すると、保存済み正式current個票に対して55正答を追加し、8/198から63/198へ上昇した。

である。

## 5. 発火solver

55 solverが各1問で発火した。

```text
abundance_dex_ratio
angular_momentum_m_sum
anisotropic_oscillator_spectrum
binary_total_mass_ratio
black_hole_entropy_from_angular_size
blackbody_luminosity_radial_doppler
bloch_maximally_mixed
boltzmann_temperature_relation
conducting_sphere_external_field_latex
coplanar_transit_max_period
cumulative_complex_fraction
decay_survival_lorentz_scaling
dipole_operator_mass_dimension
edta_complex_dissociation
energy_time_resolution
exponential_decay_probability
fission_relativistic_correction
gamma_gamma_pair_threshold_latex
gauss_radial_flux
infinite_well_fermion_occupancy
larmor_frequency
lienard_wiechert_potentials
loop_factor_count
magnetic_monopole_maxwell_symmetry
mean_free_path_parallel_rates
neutralization_enthalpy
parallax_to_distance_jacobian
partial_wave_forward_imag
pauli_hamiltonian_exact_eigenvalues
pauli_superposition_expectation
phosphate_speciation
projective_measurement_probability_3x3
qpcr_direction_consistency
quantum_matrix_unitary_similarity
relativistic_light_medium
relativistic_oscillator_energy_conservation
relativistic_velocity_energy
resonance_width_decay_length
rhombohedral_111_spacing
rv_period_scaling
rv_to_teq_ratio
sequential_projective_measurement_3x3
spin_x_measurement
spin_y_expectation
spinor_xz_positive_eigenvector
starspot_equivalent_transit
synchrocyclotron_braced_symbols
teq_from_period_ratio
teq_period_chain
three_spin_ising_partition
two_body_decay_kinematics
uncertainty_energy_relativistic
uniform_parallax_jacobian
wavefunction_normalization_symbol
weak_acid_titration
```

## 6. 解釈境界

この31.818%は、既存科学専門能力の純寄与を保存済みFormal currentへ重ねたReplay値である。

次を意味しない。

- live外部参照再取得を含む最新HEADの正式実測が31.818%で確定した、とはまだ言わない。
- 55 solverがGPQA全域へ一般化した、とは言わない。
- GPQA性能を厳密言語模型成立証拠へ読み替えない。

live 198問 controlled A/Bは `.github/workflows/gpqa_scientific_specialist_ab.yml` で別途実行する。

## 7. 実行証拠

- GitHub Actions workflow: `MINIDORA GPQA scientific specialist replay`
- run id: `33564198661`
- job id: `100043505588`
- result: `SUCCESS`
- artifact: `minidora-gpqa-scientific-specialist-replay`
- artifact id: `9822445887`
- artifact digest: `sha256:de3d913b003a58be4ab0fe8d86cb9d8d50770dd206fdba3de0d2a372eeb3bcc7`

再現入口:

```bash
python tools/gpqa_scientific_specialist_replay.py --out gpqa_scientific_specialist_replay.json
```
