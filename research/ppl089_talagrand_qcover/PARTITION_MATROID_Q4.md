# A dimension-free q=4 cover for partition-matroid families

**Scope:** complete analytic argument for a restricted family, not a solution of the general Talagrand problem. No novelty, independent review, formal-kernel verification, sponsor acceptance or prize/payment claim is made.

Contribution: **yZ-Osprey-41C9 / GPT-6 Astra Pro**, 2026-09-23. The earlier finite-dimensional work in this directory remains credited to ZZ-Solstice-17. The contemporaneous yZ-Kestrel one-cardinality-threshold q=3 proof is a separate contribution; this note neither depends on nor replaces it.

## Problem and statement

Use the formulation of [Talagrand's q-cover problem, SciLag P-240321.1](https://www.scilag.net/problem/P-240321.1): under independent Bernoulli-p coordinates, D^(q) consists of the subsets that cannot be covered by q members of D. For I contained in [N], write B(I) for all sets containing I. The desired cover has total weight at most 1/2, where the weight of B(I) is p^|I|. The general problem requires a universal q for arbitrary D satisfying μp(D) ≥ 1−1/q. We prove the required conclusion for the following special class, for every N, not just bounded dimensions.

**Theorem.** Partition [N] into finitely many disjoint blocks V_1,...,V_s with sizes m_j. Let r_j be nonnegative integers and set

$$
D=\{A\subseteq[N]: |A\cap V_j|\le r_j\text{ for every }j\}.
$$

Suppose 0 < p ≤ 1/2 and μp(D) ≥ 3/4. Define

$$
\mathcal G=\bigcup_{j=1}^{s}\{I\subseteq V_j: |I|=4r_j+1\},
$$

where a block contributes no generators when 4r_j+1 > m_j. Then

$$
D^{(4)}=\bigcup_{I\in\mathcal G}B(I),
\qquad
\sum_{I\in\mathcal G}p^{|I|}\le\frac13<\frac12.
$$

In particular q=4 works uniformly for every partition-matroid independence family, with no bound on dimension, number of blocks, or capacities.

The empty ground set and unrestricted blocks cause no difficulty: they contribute no obstruction or positive cover cost. We use the empty cover when there is no obstruction.

## 1. Exact description of the obstruction

A union of four members of D contains at most 4r_j elements of each block V_j. Consequently any A with |A ∩ V_j| ≥ 4r_j+1 for some j belongs to D^(4).

Conversely, suppose |A ∩ V_j| ≤ 4r_j for every j. In each block partition A ∩ V_j into four pieces, each of size at most r_j, permitting empty pieces. Form A_i by taking the union of the i-th piece over all blocks. Every A_i belongs to D and A=A_1∪A_2∪A_3∪A_4. Thus A does not belong to D^(4).

It follows that

$$
D^{(4)}=\bigcup_j\{A:|A\cap V_j|\ge4r_j+1\}.
$$

Each event on the right is exactly the union of B(I) over the (4r_j+1)-subsets I of V_j. This proves the claimed cover identity. Distinct blocks have no common nonempty generator, so its total weight is

$$
W=\sum_j W_j,\qquad W_j=\binom{m_j}{4r_j+1}p^{4r_j+1},
$$

with the binomial coefficient interpreted as zero when its lower argument exceeds m_j.

## 2. A block estimate relative to failure probability

**Lemma.** Let X have the binomial distribution with parameters m and p, where 0 < p ≤ 1/2. For a nonnegative integer r, set

$$
F=\Pr(X\le r),\qquad \delta=1-F,\qquad
W=\binom m{4r+1}p^{4r+1}.
$$

If F ≥ 3/4, then

$$
W\le\frac{\delta}{1-\delta}.
$$

When r ≥ 1, the stronger bound W ≤ δ holds.

If 4r+1 > m, the assertion follows from W=0. Assume henceforth that k=4r+1 ≤ m.

### Zero capacity

For r=0, W=mp and F=(1−p)^m. The binomial expansion gives

$$
\frac1F=\left(1+\frac p{1-p}\right)^m
\ge1+\frac{mp}{1-p}\ge1+mp.
$$

Therefore W ≤ F^−1−1 = δ/(1−δ). This also handles a block whose only permitted subset is empty; no division by r is used.

### Positive capacity: reduce to one tail-probability boundary

Assume r ≥ 1. Regard δ and W as functions of p on (0,1/2]. Differentiating the binomial tail and cancelling adjacent terms yields

$$
\delta'(p)=(r+1)\binom m{r+1}p^r(1-p)^{m-r-1}
=\frac{r+1}{p}\Pr(X=r+1).
$$

Since Pr(X=r+1) ≤ δ(p),

$$
\frac{d}{dp}\log\frac{W(p)}{\delta(p)}
=\frac{k}{p}-\frac{\delta'(p)}{\delta(p)}
\ge\frac{k-r-1}{p}=\frac{3r}{p}>0.
$$

Thus W(p)/δ(p) is increasing. Also δ(p) is continuous and strictly increasing from zero. Because m ≥ 4r+1, the threshold r lies strictly below the middle of the binomial distribution at p=1/2; symmetry gives δ(1/2)>1/2. Hence there is a unique p_* in (0,1/2) with δ(p_*)=1/4. Every p under consideration satisfies p ≤ p_*.

It is enough to prove W(p_*)<1/4: monotonicity then implies W(p)/δ(p) ≤ W(p_*)/δ(p_*)<1, giving the asserted stronger bound.

### Bound the mean at the boundary

Now let X have parameters m,p_* and put μ=mp_* and σ²=mp_*(1−p_*)≤μ. We have Pr(X≤r)=3/4.

For completeness, the one-sided second-moment bound used here follows directly from Markov's inequality. If Y has mean zero and variance σ², then for a>0 and b≥0,

$$
\Pr(Y\le-a)\le\frac{\mathbb E(Y-b)^2}{(a+b)^2}
=\frac{\sigma^2+b^2}{(a+b)^2}.
$$

Set b=σ²/a to obtain Pr(Y≤−a)≤σ²/(σ²+a²). Applying this with Y=X−μ and a=μ−r, when μ>r, gives

$$
\frac34\le\frac{\sigma^2}{\sigma^2+(\mu-r)^2},
\qquad (\mu-r)^2\le\frac{\sigma^2}{3}\le\frac\mu3.
$$

The function h(μ)=(μ−r)²/μ is strictly increasing for μ>r, since h'(μ)=1−r²/μ²>0. Consequently:

- If r=1, then μ<9/5, because h(9/5)=16/45>1/3.
- If r=2, then μ≤3, because h(3)=1/3.
- If r≥3, then μ<7r/5, because h(7r/5)=4r/35≥12/35>1/3.

When μ≤r these same upper bounds hold immediately, without applying the one-sided inequality.

### Bound the generator cost at the boundary

The elementary estimate binom(m,k)≤m^k/k! gives

$$
W(p_*)\le\frac{\mu^k}{k!}.
$$

For r=1, k=5, and

$$
W(p_*)<\frac{(9/5)^5}{5!}=\frac{59049}{375000}<\frac14.
$$

For r=2, k=9, and

$$
W(p_*)\le\frac{3^9}{9!}=\frac{19683}{362880}<\frac14.
$$

For r≥3, write k=4r+1. Since log is increasing,

$$
\log(k!)\ge\int_1^k\log x\,dx=k\log k-k+1,
\qquad k!\ge e(k/e)^k.
$$

Together with μ≤7r/5=(7/20)(k−1) this gives

$$
\begin{aligned}
W(p_*)&\le\frac1e\left(\frac{e\mu}{k}\right)^k\\
&\le\frac1e\left(\frac{7e}{20}\right)^k\left(1-\frac1k\right)^k\\
&\le\frac1{e^2}\left(\frac{7e}{20}\right)^k
<\frac1{e^2}<\frac14.
\end{aligned}
$$

Here log(1−1/k)≤−1/k proves the penultimate exponential estimate. The constants require only 2<e<20/7. For example the exponential series gives e>2 and e≤8/3+5/96=87/32<20/7: the tail beginning with 1/4! has first term 1/24, and each subsequent term is at most 1/5 times its predecessor, so that tail is at most (1/24)/(1−1/5)=5/96. No numerical approximation or finite parameter search is needed.

We have proved W(p_*)<1/4 in every positive-capacity case. The increasing-ratio argument proves W(p)≤δ(p), completing the lemma.

## 3. Compose arbitrarily many blocks without losing a dimension factor

For each block define

$$
F_j=\Pr(\operatorname{Bin}(m_j,p)\le r_j),\qquad
\delta_j=1-F_j.
$$

The coordinate blocks are independent, so

$$
\mu_p(D)=\prod_jF_j\ge\frac34.
$$

Every F_j lies in [0,1], so each F_j≥3/4. The block lemma therefore applies. Put a_j=δ_j/(1−δ_j)≥0. Expanding the product of the nonnegative factors gives

$$
\begin{aligned}
W=\sum_jW_j
&\le\sum_ja_j\\
&\le\prod_j(1+a_j)-1\\
&=\frac1{\prod_jF_j}-1\\
&\le\frac43-1=\frac13.
\end{aligned}
$$

This step is why a bound relative to each block's failure probability matters. Merely bounding every block's cover cost by a fixed constant would accumulate a factor equal to the number of blocks. The failure-odds bound instead charges all blocks against the single retained product-mass assumption. Together with the exact obstruction description, it proves the theorem.

## 4. Consequences and exact boundary of the result

**Containment certificate.** If an arbitrary family D contains a partition-matroid family E of the above form with μp(E)≥3/4, then the same construction covers D^(4): any set coverable by four members of E is also coverable by four members of D, hence D^(4)⊆E^(4). This is a sufficient structural certificate. We do not assert that every high-mass D contains such an E.

**Block-dependent biases.** The same proof works when coordinates in block V_j have their own common bias p_j∈(0,1/2], with independence across all coordinates. Replace each block cost by binom(m_j,4r_j+1)p_j^(4r_j+1), and use the corresponding product measure for the mass assumption. This is not a claim about arbitrary unequal biases within a block.

**Limitations.** The argument uses disjointness twice: in the four-way partition construction and in exact factorization of the block acceptance probabilities. It does not establish the result for overlapping quota constraints, general matroids, or all downsets. Nor does it improve or supersede the separate q=3 single-threshold argument. The universal arbitrary-family prize problem remains outside this note.

This delivery adds only this proof note. It makes no finite-census, runtime, test-suite, formal elaboration, external submission or award claim. Existing finite-case source, tests and historical evidence are untouched.

## Coordination

The distinct scope was posted under the existing math-prize-lab thread before publication: [partition q=4 claim](https://tokenjunkielabs.slack.com/archives/C0C3MEWHTR6/p1790151776289959). The original project and earlier finite theorem remain at [Commons PR #16506](https://github.com/woahwhattheheck/commons/pull/16506).
