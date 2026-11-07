# H3a: podpisy, teksty alternatywne i tytuły-wnioski (do składu w Typst)

Wszystkie liczby: `h3a_numbers.json`. Tytuły są ułożone od najostrożniejszego do najbardziej odważnego; każdy jest zgodny z wynikami.

## Figura A: bez bio vs z bio

**Podpis.** Odsetek prawych swipe'ów dla profili bez bio i z bio, osobno dla kobiet i mężczyzn oceniających profile (model z kontrolą płci, wieku, miasta, kompletności profilu i liczby zainteresowań). Kobiety: 14,4% → 17,3%, różnica 3,0 p.p. (95%: 1,6 do 4,3). Mężczyźni: 25,4% → 26,0%, różnica 0,6 p.p. (95%: −1,2 do 2,3). Wartości wyświetlane z zaokrągleniem do 0,1; różnica liczona z niezaokrąglonych.

**Tekst alternatywny.** Dwa panele ze strzałką od szarego punktu (bez bio) do niebieskiego (z bio). U kobiet strzałka rośnie z 14,4% do 17,3%; u mężczyzn niemal płasko, z 25,4% do 26,0%.

**Tytuły-wnioski:**

1. Różnicę widać u kobiet; u mężczyzn nie da się jej odróżnić od zera.
2. Kobiety swipe'ują w prawo profile z bio o ok. 3 p.p. częściej; u mężczyzn brak wyraźnej różnicy.
3. Bio w profilu wiąże się z większą liczbą prawych swipe'ów kobiet, nie mężczyzn.

**Ograniczenia.** Związek, nie przyczyna (dane obserwacyjne z jednej aplikacji); brak zdjęć profilowych w danych; ekspozycja profili zależy od feedu aplikacji; model z efektami losowymi: oszacowanie z `lme4` (GPBoost nie podał błędów std.).

## Figura B: na 100 swipe'ów

**Podpis.** To samo co na figurze A, w postaci 100 swipe'ów na profile: kolorowe kropki to prawe swipe'y, szare to lewe (ułamek kropki oddaje część dziesiętną). Zakresy: 95% CI (delta method, klastrowanie po nadawcy i odbiorcy).

**Tekst alternatywny.** Cztery siatki 10 × 10 kropek: kobiety bez bio (14,4 kolorowych), kobiety z bio (17,3), mężczyźni bez bio (25,4), mężczyźni z bio (26,0).

**Tytuły-wnioski:**

1. Na 100 swipe'ów kobiet: ok. 14 w prawo bez bio, ok. 17 z bio.
2. Na każde 100 profili z bio kobiety zaznaczają w prawo ok. 3 więcej niż bez bio.
3. Profil z bio dostaje od kobiet około trzech dodatkowych prawych swipe'ów na 100.

**Ograniczenia.** Związek, nie przyczyna (dane obserwacyjne z jednej aplikacji); brak zdjęć profilowych w danych; ekspozycja profili zależy od feedu aplikacji; model z efektami losowymi: oszacowanie z `lme4` (GPBoost nie podał błędów std.).

## Figura C: czy wynik się trzyma?

**Podpis.** Średni efekt bio w punktach procentowych (kółko: model dla wszystkich swipe'ów; romb: porównanie w obrębie jednej osoby oceniającej, przeliczone na p.p. przy ryzyku bazowym z M2) w modelu podstawowym i w sprawdzeniach odporności. Pas: ±1,5 p.p., orientacyjny odpowiednik marginesu praktycznego zera z reguły werdyktu. W połowie próby (tylko swipe'y z pewną wersją profilu) efekt jest słabszy: 0,9 p.p. (95%: −0,4 do 2,2), przedział obejmuje zero.

**Tekst alternatywny.** 11 wierszy; kółka leżą głównie na prawo od pasa wokół zera, z przedziałami po dodatniej stronie. Przedział obejmuje zero w: tylko swipe'y z pewną wersją profilu; tylko mężczyźni oceniają.

**Tytuły-wnioski:**

1. Wynik jest podobny w większości sprawdzeń, ale słabszy w połowie próby.
2. W większości sprawdzeń bio wiąże się z o ok. 2 p.p. częstszymi prawymi swipe'ami; słabszy efekt w połowie próby i u mężczyzn.
3. Związek bio z prawym swipe'em utrzymuje się w 9 z 11 sprawdzeń.

**Ograniczenia.** Związek, nie przyczyna (dane obserwacyjne z jednej aplikacji); brak zdjęć profilowych w danych; ekspozycja profili zależy od feedu aplikacji; model z efektami losowymi: oszacowanie z `lme4` (GPBoost nie podał błędów std.).
