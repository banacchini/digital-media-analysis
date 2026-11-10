# H3a: poprawki po audycie (2026-11-09/10)

Gałąź `fix/h3a-audit`. Prompt: `docs/prompts/fix-h3a-prompt-v2.md`. Wykonano P1 i P2; P3 oraz
odtworzenie liczb bazowych pominięto na polecenie Dominika (patrz `open-questions.md`).
Wszystkie zmiany: `post hoc (audyt)`; reguła etykiet bez zmian. Estymatory: M2 = pooled logit z
klastrowaniem dwukierunkowym; M3 = FE nadawcy; M1 = lme4 (Wald).

| Problem | Ustalenie | Zmiana | Przed | Po | Status |
|---|---|---|---|---|---|
| Z1: etykieta vs margines | Zgodna z regułą: `equiv` fałszywe (górna 90% CI 1,207 > 1,105), `sig_pos` prawdziwe | `audit.label_trace`, tabela i flaga w summary, D-H3a-36 | „potwierdzony” | „potwierdzony” + flaga (dolna 95% CI 1,044 w paśmie) | post hoc |
| Z2: M1 bez SE | lme4 już w `results.json`; „nie uruchomiony” = stare pole; „wrażliwy na estymator” = błędne porównanie z M1 „brak” | lme4 jako raportowany M1; porównanie z M2 gdy M1 bez SE; D-H3a-37 | M1 brak; flaga estymatora | M1 lme4 OR 1,132 (1,028-1,247) | post hoc |
| Z3: płeć nadawcy | Interakcja p = 0,020; F silniejszy niż M | Tabela F/M/O (M2, M3, lme4) | – | F: 1,259 (1,133-1,399), lme4 1,253; M: 1,031 (0,937-1,134), lme4 1,069; O: 1,268 (0,905-1,776), nie do wnioskowania | eksploracyjne |
| Z4: as-of | Oczekiwane 1068 stałych potwierdzone (291 ze zmianą, 128 status) | Scenariusze stałego bio, bez zmiany statusu, S2a + lme4 | S2a M2 1,064 (0,972-1,165) | stałe: M2 1,132, lme4 1,193; bez statusu: M2 1,143, lme4 1,233; S2a lme4 1,128 (1,002-1,269) | post hoc |
| Z5: identyfikacja | M4 niewykonalny (17 < 30); efekt tylko między odbiorcami | Ograniczenia w summary; wiek jak H1; aktywność; tagi v1 | M2 1,130 | wiek H1: 1,137; aktywność: 1,097 (lme4 1,093, 0,992-1,205); wiek+aktywność: 1,106 (lme4 1,105, 1,002-1,218); tagi v1: 1,130 | post hoc |
| Z5: słownik tagów | Zależne od słownika: `tag_count_receiver` (10,3% swipe'ów zmienia wartość), `tag_cap` (6307 wierszy); `tag_zero` bez zmian | Przeliczenie na v1 | OR 1,130 | OR 1,130 (bez różnicy) | post hoc |
| Z7: summary | Brak wielkości efektu dla laika, brak flag | `write_summary`: sekcja audytu, p.p., zastrzeżenie MDE/winner's curse | – | – | post hoc |

Najważniejsza obserwacja: dodanie kontroli aktywności odbiorcy obniża OR do ok. 1,10 (lme4: 1,093,
CI obejmuje 1), więc część związku może wynikać z ogólnej aktywności profilu; to kontrola
potencjalnie endogeniczna, a wniosek pozostaje ostrożny.

## Ujawnienie użycia AI

Claude Code (Claude Sonnet 5.5) napisał moduły `h3a/audit.py`, `h3a/audit_plots.py`, rozszerzenia
`Spec` i `summary.py`, testy i dokumentację; wyniki z `audit_results.json` zostały policzone lokalnie
(lme4 w R, bez zewnętrznych API). Incydenty środowiskowe: (1) pierwszy commit odrzucił hook ruff
(UP038), poprawiono i ponowiono; (2) obliczenia w tle uruchomiono przed zatwierdzeniem commitu, więc
działały na kodzie sprzed poprawki lintu (logicznie identycznym); (3) oczekiwanie na zakończenie
obliczeń zostało przerwane przez użytkownika, proces zatrzymywał się sam (bez `pkill`); (4) nie
używano `uv run --active`. Interpretację wyników musi zweryfikować autor.
