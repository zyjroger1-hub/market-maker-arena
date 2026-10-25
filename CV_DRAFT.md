# Conditional CV wording — not a claim of independent completion

The project was built and checked with substantial AI assistance in this session. The student supplied the project requirements and intended application context. The implementation, strategy heuristics, tests, experiment scripts, UI and documentation were AI-assisted/generated. There is no evidence yet that the student independently coded or personally mastered these components.

Use the following drafts only after personally running and explaining the project. Keep “AI-assisted” unless the final wording is supported by a truthful account of your own work. Never describe simulated P&L as real investment performance, invent users/deployment, or claim strategy optimality.

## Trading / research version (maximum two bullets)

- Developed an AI-assisted market-making research project comparing three quoting policies across five synthetic regimes and 100 paired evaluation seeds per regime; examined inventory, drawdown and net P&L rather than assuming profitability.
- Evaluated 5,480 synthetic strategy runs, including original sensitivities, width/skew ablations and an identical-price adverse-selection control; distinguished robust inventory reductions from seed-sensitive mean-profit rankings.

## Tech version (maximum two bullets)

- Built an AI-assisted Python/Streamlit simulator with turn-based human–algorithm play, five causal quoting policies, an offline research interface and matched exogenous market tapes.
- Verified execution accounting, hard inventory limits, quote bounds and causal strategy observations with 59 automated tests; independently reconstructed 9,015 saved equity marks from execution records using decimal arithmetic.

## Personal evidence required before adoption

1. Run `zsh launch.command` and complete a match, including pausing a side and replaying the seed.
2. Run `bash reproduce.sh`, inspect a raw result row and independently rebuild one paired comparison.
3. Explain `Ledger.fill`, the order of operations in `advance`, `vol_ratio`, the information boundary and the adverse-selection construction without relying on AI text.
4. Make and test one modest code change yourself. Record what you changed, why, and whether the outcome matched your prediction.
5. Explain the synthetic fill assumptions, terminal marking and why a relative improvement is not evidence of real profitability.

After these checks, tailor the verbs to your actual contribution. If you only explored and audited an AI-generated implementation, “Investigated and validated an AI-assisted…” is more accurate than claiming independent development. The existing CV master was not edited.

The follow-up code and results were also AI-assisted. The original five-regime
main experiment compares three policies; the follow-up compares five policies
in three selected regimes. Do not imply all five policies were evaluated in
all five regimes, or that 5,480 runs are independent market paths.
