# Walidacja tagów, zadanie C: wspólny przegląd (po annotacji A i B)

> **Nie otwierać przed zakończeniem annotacji A i B przez wszystkich trzech annotatorów.** Plik zawiera informacje z propozycji agentów (ślepota).

Dla każdego klastra zdecydujcie: **scalić**, **zostawić** albo **zmienić**. Wynik do `tag_merge_decisions.csv` (kolumny: `cluster`, `decision`, `canonical_after`, `uzasadnienie`). Skutek: Jaccard zainteresowań i pary polaryzacji (D15) zależą od tego, czy bliskoznaczne tagi są jednym tagiem.

| Klaster | Tagi | Uwaga |
|---|---|---|
| Cisza | `likes_calm`, `quiet_evenings`, `peace_and_quite`, `silence_after_22` | cztery tagi jednego konstruktu; `peace_and_quite` to literówka sluga |
| Życie towarzyskie | `likes_parties`, `going_out_friends`, `often_out`, `often_outside`, `extrovert` | `often_out` i `often_outside` oznaczone w pliku jako duplikaty |
| Dom | `chill_at_home`, `mostly_home`, `netflix_relax`, `introvert` | granica z hobby (`netflix_relax`: spór modeli) |
| Zwierzęta | `animals`, `cat_person`, `dog_person`, `no_pets` | `animals` scala dwa surowe wejścia |
| Palenie | `smoker`, `non_smoker` | `smoker` scala `smoker_outside` i `vapes`: gubi różnicę (D14: kody `N`, `V`, `O`, `Y`) |
| Zawód lub zainteresowanie | `tech_it`, `marketing_social`, `bussiness`, `psychology`, `self_development` | `bussiness` to literówka; kategoria `unclear` |
| Status | `student` | jedyny tag `status` (D12) |

Do decyzji projektowych (bez κ): mapa tag → pole strukturalne (D13), pary polaryzacji (D15), `student` jako status (D12). Dla każdej zapiszcie, co zdecydowaliście, i uruchomcie wrażliwość z wyłączonym uzupełnianiem pól tagami (D13).
