# A dimension-free q=4 cover for partition-matroid families

**Scope:** complete analytic argument for a restricted family, not a solution of the general Talagrand problem. No novelty, independent review, formal-kernel verification, sponsor acceptance or prize/payment claim is made.

Original homogeneous/block-homogeneous proof: **yZ-Osprey-41C9 / GPT-6 Astra Pro**, 2026-09-23. Heterogeneous-coordinate extension and integration: **YZ-LATTICE-73A / GPT-6 Astra Pro**, 2026-09-23, completing Osprey's clipped-scaling continuation. The original obstruction construction, mean estimates and failure-odds composition are retained. Earlier finite-dimensional work remains credited to ZZ-Solstice-17. The contemporaneous yZ-Kestrel one-cardinality-threshold q=3 proof is separate; this note neither depends on nor replaces it.

## Problem and statement

In [Talagrand's q-cover problem, SciLag P-240321.1](https://www.scilag.net/problem/P-240321.1), D^(q) consists of the subsets that cannot be covered by q members of D. For I contained in [N], write B(I) for all sets containing I. In the homogeneous formulation its weight is p^|I|, and the desired cover has total weight at most 1/2 whenever μp(D) ≥ 1−1/q, for a universal q and arbitrary D.

Here we prove the q=4 conclusion for partition-matroid independence families, in every finite dimension, and allow **arbitrary independent coordinate probabilities** p_i∈[0,1]. Write μ_p for their product measure and

$$
w_p(I)=\mu_p(B(I))=\prod_{i\in I}p_i.
$$

**Theorem.** Partition [N] into finitely many disjoint blocks V_1,...,V_s. Let r_j be nonnegative integers and set

$$
D=\{A\subseteq[N]: |A\cap V_j|\le r_j\text{ for every }j\}.
$$

Suppose μ_p(D) ≥ 3/4. Define

$$
\mathcal G=\bigcup_{j=1}^{s}\{I\subseteq V_j: |I|=4r_j+1\},
$$

where a block contributes no generators when 4r_j+1 > |V_j|. Then

$$
D^{(4)}=\bigcup_{I\in\mathcal G}B(I),
\qquad
\sum_{I\in\mathcal G}w_p(I)\le\frac13<\frac12.
$$

There is no restriction on dimension, number of blocks, capacities, equality of biases, or whether some probabilities are 0 or 1. In particular, the original homogeneous case 0<p≤1/2 follows immediately.

The empty ground set and unrestricted blocks contribute no obstruction or positive cover cost. We use the empty cover when there is no obstruction. A generator containing a zero-probability coordinate still belongs to the literal cover, with cost zero; a zero cost is not a claim that its principal up-set is empty.

## 1. Exact description of the obstruction

A union of four members of D contains at most 4r_j elements of each block V_j. Consequently any A with |A ∩ V_j| ≥ 4r_j+1 for some j belongs to D^(4).

Conversely, suppose |A ∩ V_j| ≤ 4r_j for every j. In each block partition A ∩ V_j into four pieces, each of size at most r_j, permitting empty pieces. Form A_i by taking the union of the i-th piece over all blocks. Every A_i belongs to D and A=A_1∪A_2∪A_3∪A_4. Thus A does not belong to D^(4).

It follows that

$$
D^{(4)}=\bigcup_j\{A:|A\cap V_j|\ge4r_j+1\}.
$$

Each event on the right is exactly the union of B(I) over the (4r_j+1)-subsets I of V_j. Distinct blocks have no common nonempty generator, so the total weight is

$$
W=\sum_j W_j,\qquad W_j=e_{4r_j+1}((p_i)_{i\in V_j}),
$$

where e_k(x_1,...,x_m) is the elementary symmetric sum of products over all k-subsets, and e_k=0 for k>m. This is the actual product-weight cost, not a binomial coefficient evaluated at an average bias.

## 2. A heterogeneous block estimate

**Lemma.** Let X be the sum of independent Bernoulli variables with probabilities p_1,...,p_m∈[0,1]. For a nonnegative integer r, put

$$
F=\Pr(X\le r),\qquad \delta=1-F,\qquad
k=4r+1,\qquad W=e_k(p_1,\ldots,p_m).
$$

If F≥3/4, then

$$
W\le\frac{\delta}{1-\delta}.
$$

For r≥1, the stronger bound W≤δ holds.

If fewer than k coordinates have positive probability, every k-fold product is zero, so W=0 and the lemma is immediate. This includes k>m. If k≤m but positive support is smaller than k, the literal generators are retained at zero cost; they must not be silently removed from the cover. In the remaining argument the positive support has size at least k.

### Zero capacity

For r=0, W=Σ_i p_i and F=∏_i(1−p_i). Since F≥3/4, no p_i equals 1. Expanding a product of nonnegative factors gives

$$
\frac1F=\prod_i\left(1+\frac{p_i}{1-p_i}\right)
\ge1+\sum_i\frac{p_i}{1-p_i}
\ge1+\sum_i p_i.
$$

Thus W≤F^−1−1=δ/(1−δ), including zero coordinates. No division by r is used.

### Positive capacity: clipped scaling to a tail boundary

Assume r≥1 and positive support size at least k. For t≥1 define

$$
q_i(t)=\min\{t p_i,1\},\qquad
X_t=\sum_i\operatorname{Bernoulli}(q_i(t)),\qquad
\delta(t)=\Pr(X_t\ge r+1),\qquad W(t)=e_k(q(t)).
$$

Independence is understood at each t; no coupling assertion beyond the coordinatewise monotonicity of the probabilities is needed. Both δ(t) and W(t) are continuous. Also δ(t) is nondecreasing, δ(1)≤1/4, and δ(T)=1 at the finite value T=max_{p_i>0}(1/p_i), since at least k>r coordinates are then deterministic successes. There is therefore a first t_*∈[1,T] with δ(t_*)=1/4. If δ(1)=1/4, take t_*=1. Throughout [1,t_*], W(t)>0 and δ(t)>0 because the positive support has size at least k.

Consider any open interval between consecutive clamping values 1/p_i within [1,t_*]. Let j be the number of coordinates already clamped at 1; coordinates with p_i=1 are counted from t=1. Since δ(t)≤1/4<1, we have j≤r. Let S_t be the sum of the remaining, unclamped Bernoulli coordinates and set a=r−j+1≥1. Then δ(t)=Pr(S_t≥a), while every unclamped probability equals t p_i (including the zero probabilities).

Differentiating the finite multilinear tail polynomial gives

$$
t\delta'(t)=\sum_{i\ \mathrm{unclamped}}q_i(t)\Pr(S_t-\xi_i=a-1)
=a\Pr(S_t=a)\le a\delta(t).
$$

Here ξ_i is the i-th unclamped Bernoulli variable. The equality in the middle counts each outcome with S_t=a exactly a times: its contribution for index i is Pr(ξ_i=1,S_t=a). This identity does not require equal probabilities.

On the same interval, the generator cost is a polynomial with nonnegative coefficients:

$$
W(t)=\sum_{\ell=0}^{j}\binom j\ell\,t^{k-\ell}
 e_{k-\ell}((p_i)_{i\ \mathrm{unclamped}}).
$$

Every nonzero term has degree at least k−j, so tW'(t)≥(k−j)W(t). Consequently

$$
t\frac{d}{dt}\log\frac{W(t)}{\delta(t)}
\ge(k-j)-(r-j+1)=3r>0.
$$

There are only finitely many clamping values, including any simultaneous clamps. The positive ratio W(t)/δ(t) is continuous across each one, so intervalwise monotonicity proves monotonicity on the entire [1,t_*]. No derivative at a clamp is assumed. Hence it suffices to prove W(t_*)<1/4; then

$$
\frac{W(1)}{\delta(1)}\le\frac{W(t_*)}{\delta(t_*)}<1.
$$

This also covers t_*=1, when no scaling interval is needed.

### Bound the mean at the boundary

At t_* put μ=Σ_i q_i(t_*) and σ²=Σ_i q_i(t_*)(1−q_i(t_*))≤μ. Deterministic and zero coordinates are included in these sums. We have Pr(X_{t_*}≤r)=3/4.

For completeness, the one-sided second-moment bound used here follows directly from Markov's inequality. If Y has mean zero and variance σ², then for a>0 and b≥0,

$$
\Pr(Y\le-a)\le\frac{\mathbb E(Y-b)^2}{(a+b)^2}
=\frac{\sigma^2+b^2}{(a+b)^2}.
$$

Set b=σ²/a to obtain Pr(Y≤−a)≤σ²/(σ²+a²). Applying this with Y=X_{t_*}−μ and a=μ−r, when μ>r, gives

$$
\frac34\le\frac{\sigma^2}{\sigma^2+(\mu-r)^2},
\qquad (\mu-r)^2\le\frac{\sigma^2}{3}\le\frac\mu3.
$$

The function h(μ)=(μ−r)²/μ is strictly increasing for μ>r, since h'(μ)=1−r²/μ²>0. Consequently:

- If r=1, then μ<9/5, because h(9/5)=16/45>1/3.
- If r=2, then μ≤3, because h(3)=1/3.
- If r≥3, then μ<7r/5, because h(7r/5)=4r/35≥12/35>1/3.

When μ≤r these same upper bounds hold immediately, without applying the one-sided inequality.

### Bound the product-weight cost at the boundary

Expanding (Σ_i q_i)^k counts every product on k distinct indices exactly k! times, with all repeated-index terms nonnegative. Therefore

$$
k!e_k(q)\le\left(\sum_iq_i\right)^k,
\qquad W(t_*)\le\frac{\mu^k}{k!}.
$$

For r=1, k=5, and

$$
W(t_*)<\frac{(9/5)^5}{5!}=\frac{59049}{375000}<\frac14.
$$

For r=2, k=9, and

$$
W(t_*)\le\frac{3^9}{9!}=\frac{19683}{362880}<\frac14.
$$

For r≥3, write k=4r+1. Since log is increasing,

$$
\log(k!)\ge\int_1^k\log x\,dx=k\log k-k+1,
\qquad k!\ge e(k/e)^k.
$$

Together with μ≤7r/5=(7/20)(k−1) this gives

$$
\begin{aligned}
W(t_*)&\le\frac1e\left(\frac{e\mu}{k}\right)^k\\
&\le\frac1e\left(\frac{7e}{20}\right)^k\left(1-\frac1k\right)^k\\
&\le\frac1{e^2}\left(\frac{7e}{20}\right)^k
<\frac1{e^2}<\frac14.
\end{aligned}
$$

Here log(1−1/k)≤−1/k proves the penultimate exponential estimate. The constants require only 2<e<20/7. For example the exponential series gives e>2 and e≤8/3+5/96=87/32<20/7: the tail beginning with 1/4! has first term 1/24, and each subsequent term is at most 1/5 times its predecessor, so that tail is at most (1/24)/(1−1/5)=5/96. No numerical approximation or finite parameter search is needed.

Thus W(t_*)<1/4 in every positive-capacity case. The ratio argument yields W<δ whenever W>0, and the previously separated W=0 cases give W≤δ. Since δ≤δ/(1−δ), this completes the block lemma.

## 3. Compose arbitrarily many blocks without a dimension factor

For each block let X_j be its independent Bernoulli sum and define

$$
F_j=\Pr(X_j\le r_j),\qquad \delta_j=1-F_j.
$$

The coordinate blocks are independent, so

$$
\mu_p(D)=\prod_jF_j\ge\frac34.
$$

Every F_j lies in [0,1], hence every F_j≥3/4. Apply the heterogeneous block lemma and put a_j=δ_j/(1−δ_j)≥0. Expanding the product gives

$$
\begin{aligned}
\sum_{I\in\mathcal G}w_p(I)=\sum_jW_j
&\le\sum_ja_j\\
&\le\prod_j(1+a_j)-1\\
&=\frac1{\prod_jF_j}-1\\
&\le\frac43-1=\frac13.
\end{aligned}
$$

This charges all blocks against the single product-mass assumption instead of accumulating one fixed bound per block. For no blocks, the sum is zero and the empty product is one. Along with Section 1's literal obstruction identity, it proves the theorem for all stated probability and support cases.

## 4. Consequences and exact boundary

**Homogeneous and block-dependent biases.** Setting every p_i=p recovers Osprey's original homogeneous q=4 theorem, including the original 0<p≤1/2 regime. Taking a separate common bias in each block is another special case. The clipped-scaling argument removes both equality within a block and the upper restriction 1/2; it is not an assertion about arbitrary families.

**Containment certificate.** If an arbitrary family D contains a partition-matroid family E of the stated form with μ_p(E)≥3/4, then the same product-weight construction covers D^(4). Any set coverable by four members of E is coverable by four members of D, so D^(4)⊆E^(4). We do not assert that every high-mass D contains such an E.

**Limitations.** Disjointness is used both in the four-way partition construction and in exact factorization of block acceptance probabilities. The proof does not establish the result for overlapping quota constraints, general matroids, or all downsets. Nor does it improve or supersede the separate q=3 single-threshold argument. The universal arbitrary-family prize problem remains outside this note.

Both analytic deliveries affect only this proof note. There is no finite-census, runtime, test-suite, formal elaboration, external submission or award claim. Existing finite-case source, tests and historical evidence are untouched.

## Coordination and lineage

Original [partition q=4 claim](https://tokenjunkielabs.slack.com/archives/C0C3MEWHTR6/p1790151776289959), delivered in [Commons PR #19329](https://github.com/woahwhattheheck/commons/pull/19329). Osprey proposed the heterogeneous continuation in [the same math-prize-lab channel](https://tokenjunkielabs.slack.com/archives/C0C3MEWHTR6/p1790152059864239); LATTICE's [extension claim and proof discussion](https://tokenjunkielabs.slack.com/archives/C0C3MEWHTR6/p1790152230157969) stay in that work thread. The original project and earlier finite theorem remain at [Commons PR #16506](https://github.com/woahwhattheheck/commons/pull/16506).
