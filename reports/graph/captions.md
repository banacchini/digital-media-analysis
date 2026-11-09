# Podpisy do wykresów (reports/graph/)

## fig_model_ladder.png
**Rys. 1.** Względna redukcja loglossu (im więcej, tym lepiej) względem modelu
naiwnego (zgadywanie proporcją pozytywów) dla modeli M0–M4 w protokole P1.
Słupki błędów: 95% CI z bootstrapu po nadawcach (konserwatywny z dwóch widoków).
*Czego to NIE znaczy*: wyższy logloss M4 niż M1 oznaczałby, że sieciowa propagacja
nie wnosi informacji ponad propensje węzłów – to pełnoprawny wynik, nie błąd modelu.

## fig_lift_at_20.png
**Rys. 2.** Lift@20%: wśród profili zajmujących górne 20% wg predykcji out-of-fold,
jaki odsetek jest faktycznie polubiony, podzielony przez ogólny odsetek polubień
danego nadawcy.
*Czego to NIE znaczy*: lift = 1 oznacza brak informacji ponad losowy wybór,
a nie że model jest zły – wynik zależy od heterogeniczności upodobań.

## fig_calibration_*.png
**Rys. 3.** Wykres niezawodności: gdy model przewiduje p%, obserwowany odsetek
polubień powinien wynosić p%. Pasmo CI z bootstrapu po nadawcach.
*Czego to NIE znaczy*: dobra kalibracja nie gwarantuje trafnych rankingów
(można być dobrze skalibrowanym przy AUC = 0,5).

## fig_reciprocity_observed_vs_expected.png
**Rys. 4.** Obserwowane vs oczekiwane matche w parach z obustronną decyzją,
w koszach wg oczekiwanej szansy matcha (p̂_AB·p̂_BA). Wyniki warunkowane
ekspozycją (G1 – nieznany mechanizm feedu).
*Czego to NIE znaczy*: nadwyżka obserwowanych matchy nie dowodzi przyczynowego
efektu wzajemności – może wynikać z homofylii nieuwzględnionej przez model.

## fig_league_p_right.png
**Rys. 5.** P(prawy swipe) w funkcji różnicy percentylu „pożądania"
(odbiorca minus nadawca, gdzie pożądanie = cross-fitted efekt odbiorcy z M1).
*Czego to NIE znaczy*: nie obserwujemy wszystkich potencjalnych par
(ekspozycja ≠ populacja), więc krzywa opisuje zachowanie w widocznych parach.

## fig_league_reciprocate.png
**Rys. 6.** P(B→A prawo | A→B prawo) w funkcji różnicy rangi pożądania.
Warunkowane na ekspozycji B na profil A.
*Czego to NIE znaczy*: nie wiadomo, czy B w ogóle zobaczył(-a) A –
brak wzajemności może oznaczać brak ekspozycji, nie odrzucenie.
