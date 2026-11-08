# Codebook: sygnały w bio (H3b-ii)

**Wersja:** 0.1 (szkic do pilotażu), 2026-11-08. **Status:** niezamrożony. Po pilotażu i zatwierdzeniu przez całą trójkę: wersja 1.0, zapisz tutaj hash SHA-256 pliku i datę. Po zamrożeniu nie zmieniamy definicji (poprawki tylko jako erratę z opisem wpływu na analizę).
**Hash v1.0:** _do uzupełnienia_

## 1. Cel i jednostka

Dla każdego bio oznaczasz **cztery niezależne sygnały binarne** (1 = obecny, 0 = nieobecny): `towarzyskie`, `spokoj`, `rytm`, `intencja`. Sygnały **nie wykluczają się**: jedno bio może mieć 0, 1, a nawet wszystkie cztery. Etykiety posłużą do (a) walidacji ekstrakcji lokalnym LLM-em i (b) sprawdzenia, czy treść bio wiąże się z prawym swipe'em.

## 2. Zasady ogólne

1. **Oceniasz wyłącznie tekst.** Nie wnioskuj z wieku, płci ani niczego spoza tekstu. Bio bierzesz tak, jak jest napisane: oznaczasz to, co tekst mówi, nie to, co by z niego wynikało.
2. **Jeden tekst, cztery decyzje**, każda osobno. Wszystkie cztery są wymagane.
3. **Własne cechy i oczekiwania liczą się razem** dla `towarzyskie` i `spokoj`: sygnał jest obecny, jeśli bio wyraża taki styl życia **u autora** albo **oczekuje go we wspólnym mieszkaniu** (np. „szukam spokojnej osoby"). Dla `rytm` liczą się tylko informacje o autorze. `intencja` dotyczy z definicji poszukiwania.
4. **Negacja odwraca sygnał:** „nie lubię imprez" to `towarzyskie` = 0 i `spokoj` = 1 (autor deklaruje preferencję ciszy), o ile reszta tekstu tego nie podważa.
5. **Tolerancja to nie preferencja:** „imprezy mi nie przeszkadzają", „mogę być z kimś głośniejszym" → 0 i kod `tolerancja`.
6. **Częstotliwość nie ma znaczenia:** „czasem", „okazjonalnie" nadal liczy się jako obecność. Ocenia się, czy tekst coś stwierdza, nie jak często.
7. **Emoji nie liczą się samodzielnie.** Same emoji (np. 🎉🍻) = 0 i kod `emoji`. Emoji mogą wzmocnić, ale nie zastąpić słów.
8. **Ironia i żarty:** jeśli dosłowny sens jest niejednoznaczny lub tekst sam siebie podważa → 0 i kod `ironia`.
9. **W razie wątpliwości: 0 i kod `?`.** Przez „wątpliwość" rozumiemy sytuację, w której dwie rozsądne osoby mogłyby ocenić inaczej. Nie wstawiaj 1 „na wszelki wypadek".
10. **Język:** polski, angielski i mieszany są równorzędne. Slang liczy się tak jak słownictwo standardowe. Tekst nieczytelny lub w innym języku, którego nie rozumiesz → 0 we wszystkich i kod `nieczytelne`.
11. **Pole `uwagi`:** tylko kody z sekcji 4, oddzielone przecinkami. **Nigdy nie cytuj bio w uwagach.**

## 3. Sygnały

### 3.1 `towarzyskie`: życie towarzyskie i imprezy

**Definicja.** Bio wyraża skłonność do aktywnego życia towarzyskiego i wspólnych aktywności: imprezy, wyjścia, spotkania ze znajomymi, goście w mieszkaniu, wspólne wieczory, albo samookreślenie jako towarzyski, otwarty na ludzi, dusza towarzystwa.
**1, gdy:** impreza/domówka/wyjście na miasto/koncert-festiwal-klub jako element stylu życia; goście lub spotkania w domu; „towarzyski/a", „ekstrawertyk"; chęć wspólnych kolacji, wieczorów filmowych ze współlokatorami.
**0, gdy:** hobby wykonywane solo (gotowanie, bieganie, czytanie); samo „chcę się dogadać ze współlokatorem" bez sygnału aktywności towarzyskiej; tolerancja; negacja; same emoji.
**Granica:** „lubię ludzi" bez żadnej aktywności → 0 i `?`.

### 3.2 `spokoj`: spokój, cisza, domatorstwo

**Definicja.** Bio wyraża spokojny styl życia lub potrzebę ciszy: domatorstwo, wieczory w domu, introwersja, wymóg braku imprez i hałasu, cisza nocna.
**1, gdy:** „spokojny/spokojna" jako cecha osoby lub mieszkania; „domator/ka", „introwertyk"; „cenię ciszę", „bez imprez", „cisza po 22"; negacja imprez jako deklaracja preferencji.
**0, gdy:** „chill", „na luzie", „luzak" bez kontekstu ciszy; **spokojna okolica/dzielnica** (to lokalizacja, nie tryb życia; kod `lokalizacja`); „relaksujące hobby" bez deklaracji stylu życia; tolerancja.

### 3.3 `rytm`: rytm pracy, nauki i dnia

**Definicja.** Bio podaje **konkretną informację o rytmie dnia autora**, która wpływa na wspólne mieszkanie, czyli kiedy i gdzie pracuje, uczy się, śpi albo bywa w domu.
**1, gdy:** praca zdalna/hybrydowa/home office; praca zmianowa lub nocna; godziny wyjść i powrotów („wracam późno", „wychodzę o 6"); „sowa", „skowronek", tryb nocny/poranny; okres intensywnej nauki w domu (sesja, egzaminy); informacja o tym, że rzadko lub często bywa w domu.
**0, gdy:** sam status lub zawód („student", „pracuję w IT", kierunek, uczelnia, firma); ogólne „zapracowany/a" bez informacji o czasie i miejscu; hobby.

### 3.4 `intencja`: kontekst poszukiwania

**Definicja.** Bio podaje **konkret dotyczący poszukiwania mieszkania lub współlokatora**: co, od kiedy, na jak długo, gdzie, za ile lub z kim.
**1, gdy** jest co najmniej jedno z: termin („od stycznia", „od 1.12"); okres („na rok", „na stałe", „na semestr"); typ lokalu lub liczba osób („pokój", „całe mieszkanie", „2-pokojowe"); lokalizacja („blisko centrum", „na Krzykach"); budżet („do 1500").
**0, gdy:** ogólne „szukam współlokatora/ki" lub „szukam fajnej osoby" bez żadnego z powyższych (kod `ogólne`); opis cech osoby szukanej bez kontekstu najmu.
**Uwaga:** lokalizacja zaznaczona jako **tylko** „spokojna okolica" liczy się jako lokalizacja (`intencja` = 1) i nie liczy się jako `spokoj`.

## 4. Kody w polu `uwagi`

`?` (wątpliwość), `tolerancja`, `ironia`, `emoji`, `lokalizacja`, `ogólne`, `nieczytelne`, `inny-język`, `negacja`. Kody oddzielasz przecinkami. Wolno użyć wielu kodów. Kodów nie wolno wzbogacać o cytaty.

## 5. Przykłady (**wymyślone, nie pochodzą z prawdziwych bio**)

| Tekst (wymyślony) | tow. | spok. | rytm | int. | Uzasadnienie |
|---|---|---|---|---|---|
| „Lubię wyjść ze znajomymi na miasto, czasem zrobię domówkę. Szukam pokoju od stycznia." | 1 | 0 | 0 | 1 | wyjścia i domówka; termin |
| „Spokojna osoba, wieczory najchętniej w domu z książką." | 0 | 1 | 0 | 0 | spokój i domatorstwo |
| „Nie przepadam za imprezami w mieszkaniu, cenię ciszę po 22." | 0 | 1 | 0 | 0 | negacja imprez, wymóg ciszy |
| „Pracuję zdalnie 4 dni w tygodniu, więc jestem często w domu." | 0 | 0 | 1 | 0 | rytm pracy i obecność w domu |
| „Student 3. roku informatyki, lubię wspinaczkę i gotowanie." | 0 | 0 | 0 | 0 | status i hobby solo |
| „Dorabiam na nocnej zmianie, wracam koło 6 rano." | 0 | 0 | 1 | 0 | praca nocna, godziny |
| „Imprezy mi nie przeszkadzają, ale sam rzadko chodzę." (`tolerancja`) | 0 | 0 | 0 | 0 | tolerancja ≠ preferencja |
| „Jestem duszą towarzystwa 😄 (czyli głównie śpię)." (`ironia`) | 0 | 0 | 0 | 0 | tekst sam się podważa |
| „🎉🍻🎶" (`emoji`) | 0 | 0 | 0 | 0 | same emoji |
| „Szukam mieszkania w spokojnej okolicy, najlepiej blisko centrum." (`lokalizacja`) | 0 | 0 | 0 | 1 | lokalizacja ≠ tryb życia |
| „Looking for a room from March, long term. I work remotely and prefer a quiet flat." | 0 | 1 | 1 | 1 | termin, okres; praca zdalna; wymóg ciszy |
| „Szukam współlokatora/ki." (`ogólne`) | 0 | 0 | 0 | 0 | brak konkretu |
| „Szukam osoby, z którą można czasem wyskoczyć na piwo i pogadać wieczorem." | 1 | 0 | 0 | 0 | oczekiwana aktywność towarzyska; brak konkretu najmu |
| „Budżet do 1500, wprowadzam się od 1 grudnia na rok." | 0 | 0 | 0 | 1 | budżet, termin, okres |
| „Introwertyk, ale lubię jak ktoś wpadnie na herbatę." | 1 | 1 | 0 | 0 | introwersja i gościnność: oba sygnały |
| „Sesja do lutego, wtedy siedzę w domu i się uczę." | 0 | 0 | 1 | 0 | okres nauki w domu |

## 6. Procedura

1. **Pilotaż (przed annotacją gold standardu).** 15 bio z ramki, **rozłącznych z 75 bio gold standardu**. Wszyscy trzej oznaczają niezależnie, potem omawiają niezgodności (pilotażowe bio wolno omawiać; gold nie). Popraw codebook, policz kappę pilotażową (informacyjnie, nie raportujemy jej jako wyniku gold standardu).
2. **Zamrożenie:** zatwierdzenie przez trzy osoby, wersja 1.0, hash, data. Każdy annotator potwierdza, że pracuje na tej wersji.
3. **Annotacja gold standardu** wg `label-studio-setup.md`: niezależnie, bez omawiania pozycji. Pytania o definicje do autora codebooku, bez cytowania bio.
4. **Rozstrzyganie sporów:** trzecia osoba (która tego bio nie etykietowała), po obejrzeniu obu etykiet. Zapisywane są etykiety surowe i konsensus.

## 7. Dla autora promptu LLM

Krótkie definicje operacyjne (do wklejenia do promptu; przykłady z sekcji 5 można wykorzystać, bo są wymyślone i nie pochodzą z gold standardu):

- `towarzyskie`: tekst wyraża skłonność do aktywności towarzyskich (imprezy, wyjścia, goście, spotkania, wspólne wieczory) albo samookreślenie jako towarzyski; własne lub oczekiwane. Tolerancja i negacja to 0.
- `spokoj`: tekst wyraża spokojny styl życia lub potrzebę ciszy (domatorstwo, introwersja, brak imprez/hałasu); własne lub oczekiwane. „Chill" i „spokojna okolica" to 0.
- `rytm`: tekst podaje konkretny rytm dnia autora (praca zdalna/zmianowa, godziny, sowa/skowronek, okres intensywnej nauki w domu). Sam status lub zawód to 0.
- `intencja`: tekst podaje co najmniej jeden konkret poszukiwania najmu (termin, okres, typ lokalu, lokalizacja, budżet). Ogólne „szukam współlokatora" to 0.
- Reguły ogólne: negacja odwraca, tolerancja = 0, same emoji = 0, ironia lub wątpliwość = 0, oceniaj wyłącznie tekst.

## 8. Dziennik zmian

- 0.1 (2026-11-08): szkic.
- 0.2 (2026-11-08): zespół potwierdził decyzje projektowe bez zmian w treści: (1) własne cechy i oczekiwania liczą się razem dla `towarzyskie` i `spokoj`; (2) `intencja` wymaga co najmniej jednego konkretu; (3) same emoji, tolerancja, ironia i wątpliwość = 0; (4) sygnały mogą współwystępować; (5) `rytm` jest jednym sygnałem. Następny krok: pilotaż na 15 bio spoza gold standardu.
