# H3a: jak uruchomić

Analiza hipotezy H3a (staranność bio odbiorcy a prawy swipe). Specyfikacja:
`docs/prompts/h3a-notebook-prompt.md`; decyzje: `docs/h3a/decision-log.md`; nowe zmienne:
`docs/codebook_addendum_h3a.md`.

## Kod

- `src/rentfriends/h3a/`: `data.py` (wczytanie, reguła as-of D7, tabela swipe'ów), `variables.py`
  (definicje zmiennych), `models.py` (GLMM GPBoost, pooled logit z klastrowaniem CGM, logit z FE
  nadawcy), `classify.py` (reguła werdyktu), `m4.py`, `predictive.py` (M6), `sim.py` (sanity
  check), `figs.py` (`save_fig`, styl), `privacy.py` (tłumienie < 5), `runner.py` (cache, timeout,
  czasy), `analysis.py` (kroki notebooka), `summary.py` (`summary.md`).
- `notebooks/H3a.ipynb`: cienki notebook z parametrami papermill; wersja z wynikami:
  `notebooks/H3a-rendered.ipynb` (tylko agregaty).
- Testy: `uv run pytest tests/test_h3a.py`.

## Uruchomienie

```bash
uv sync
# smoke test (10% nadawców, ok. 1 min; wyniki poza gitem)
scripts/run_h3a.sh 1 0.1 reports/h3a_smoke reports/h3a_smoke/H3a-smoke.ipynb
# pełny przebieg: poziom 1, potem poziom 2, odłączony od terminala (setsid + nohup);
# koniec sesji/terminala go nie przerywa; na końcu run.log: "H3A DONE" albo "H3A FAILED"
scripts/run_h3a_full.sh
# albo poziomy osobno; poziom 1 na pełnych danych (w tle, log: reports/h3a/run.log)
scripts/run_h3a.sh 1
# poziom 2 (refity GLMM S1, S3, S4, S7 + lme4, jeśli jest R); fity z poziomu 1 idą z cache
scripts/run_h3a.sh 2
```

`H3A_FOREGROUND=1` uruchamia na pierwszym planie. Parametry notebooka: `RUN_LEVEL`,
`SAMPLE_FRAC`, `SAMPLE_BY`, `SEED`, `MARGIN`, `FIT_TIMEOUT_MIN`, `REPORT_DIR`.

## Wyniki (`reports/h3a/`)

- `summary.md` (ostatni poziom), `summary_level1.md`, `summary_level2.md`: werdykt i wszystkie
  liczby.
- `tables/*.csv|md`: wynik główny, wszystkie współczynniki, wrażliwość, przepływ próby, kontrola
  zgodności z kartą, M4, M5, M6, balans.
- `figures/h3a_<nn>_<slug>.png|svg` (300 dpi, 16:9) + `figure_data/*.csv` (dane do przerysowania)
  + `figures_manifest.csv` (podpisy po polsku, model, N).
- `results.json` (wszystkie agregaty), `cache/*.json` (wyniki fitów), `timings.csv`, `env.txt`.

Do repo trafiają tylko agregaty; komórki z < 5 użytkownikami są wytłumione.
Cache jest unieważniany automatycznie, gdy zmienią się dane wejściowe modelu (hash).

## Poziom 3 (diagnostyka post hoc, SE dla GLMM, figury)

Specyfikacja: `docs/prompts/h3a-level3-prompt.md`. Kod: `level3.py` (A1-A5, B1-B3, C4/C5),
`story_figs.py` (figury A, B, C), `theme.py`, `export3.py` (`h3a_numbers.json`, podpisy,
`summary_level3.md`), `stats3.py` (E-value, LRT, profil, prawdopodobieństwa standaryzowane).

```bash
scripts/run_h3a.sh 3                      # wszystko (fity z poziomów 1-2 z cache), ok. 1-2 min
scripts/run_h3a.sh 3 only=figures         # tylko A5 i figury A-C + liczby/podpisy
scripts/run_h3a.sh 3 only=diagnostics     # A1-A5 + figury C4, C5
scripts/run_h3a.sh 3 only=se              # B1 (LRT, profil), B2 (lme4), raport szczebli
scripts/run_h3a.sh 3 only=lme4            # tylko lme4 (wymaga R i lme4; ok. 1 min)
scripts/run_h3a.sh 3 bootstrap=1          # B3: bootstrap po nadawcach (B = 200, noc)
```

Parametry notebooka poziomu 3: `RUN_LEVEL = 3`, `ONLY` (`diagnostics` | `se` | `figures` | `lme4` |
pusty), `RUN_BOOTSTRAP`. Nie uruchamiaj dwóch przebiegów naraz: oba zapisują `results.json`.

Wyniki: `reports/h3a/summary_level3.md`, `reports/h3a/tables/h3a_a*.csv|md`, `h3a_b_ladder`,
figury C4/C5 w `figures/h3a_09_*`, `h3a_10_*`, a dla składu slajdów `reports/h3a/export/`
(`h3a_fig_{A,B,C}.svg|png`, `h3a_numbers.json`, `h3a_captions.md`, `theme.json`; motyw do
użycia przez H1/H2: `from rentfriends.h3a.theme import apply_theme`).
