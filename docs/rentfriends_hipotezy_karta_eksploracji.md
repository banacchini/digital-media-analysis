# RentFriends — materiał do Karty Eksploracji Danych (M1)

**Status:** dane otrzymane; wstępna EDA wykonana (`notebooks/EDA.ipynb`, wersja z wynikami: `notebooks/EDA-rendered.ipynb`). Sekcje 2, 4 i 5 uzupełniono liczbami z EDA. Pozycje oznaczone `[DO UZUPEŁNIENIA]` nie zostały jeszcze policzone lub czekają na odpowiedź dostawcy. Liczby są opisowe (bez wnioskowania statystycznego).

---

## 1. Pytanie badawcze

**Główne:** Jakie parametry wpływają na decyzję o wspólnym wynajęciu mieszkania?

**Kontekst badań:** dane z aplikacji RentFriends obejmują decyzje na poziomie swipe'a, matcha i rozpoczęcia rozmowy. **Nie obserwujemy faktycznego wspólnego wynajęcia.** Pytanie jest więc badane na poziomie **wzajemnego zainteresowania** (match) i **zaangażowania** (rozpoczęcie czatu po matchu).

**Hipotezy:**

| ID | Hipoteza (skrót) |
|---|---|
| H1 | Zgodność stylu życia przewiduje match silniej niż zgodność wieku i zainteresowań |
| H2 | Dopasowanie demograficzne (płeć, wiek) jest warunkiem wstępnym, a nie preferencją |
| H3 | Match determinuje zgodność dwustronna (min. z obu stron), a nie jednostronna |
| H4 | Zgodność selektywności użytkowników przewiduje wzajemność lepiej niż cechy profilu |
| H5 | Treść i staranność bio niosą informację o dopasowaniu ponad pola strukturalne |

---

## 2. Dane

Z aplikacji RentFriends otrzymaliśmy zanonimizowane dane (**profile użytkowników**: zainteresowania, styl życia, płeć, wiek, opis z bio; **akcje użytkowników**: swipe’y profili i ogłoszeń mieszkań, matche, informacja o rozpoczęciu rozmowy na czacie, bez treści wiadomości; użytkownicy oznaczeni losowymi ID).

### 2.1 Faktyczny schemat (wg EDA)

Dane to przetworzone pliki parquet (`data/processed/`), połączone relacyjnie kluczami użytkowników (`user_key`). Schemat zweryfikowano w notebooku EDA (diagram ERD).

| Tabela | Zawartość | Uwagi |
|---|---|---|
| `users` | **2065** profili: `user_key`, `sex` (F/M/O), `age_band` (kategorie), `interests` (lista tagów), `bio`, `bio_length`, `budget`, `move_in_month_offset` i inne pola kategorialne | wiek tylko jako przedział, nie w latach; pełna lista kolumn na diagramie ERD w notebooku |
| `swipes` | `user_key`, `target_type` (`profile` / listing), `target_user_key`, `direction` (left/right), `day` | **jedyna informacja czasowa to `day` (int32)**, bez godzin; swipe'y na profile: **95 144** |
| `matches` | `user_a_key`, `user_b_key`, `day` | **733** matche, bez braków (0% NaN); match = wzajemne prawe swipe'y |
| `chats` | para użytkowników, flaga `from_match` | bez treści wiadomości; rozmowy po matchu: **269** |
| `listings` | ogłoszenia mieszkań | atrybuty i powiązanie ze swipe'ami nie były jeszcze analizowane w EDA |
| `profile_history` | historia zmian profilu, kolumna `changed_fields` | **552** odnotowane zmiany bio |

### 2.2 Pytania decydujące o wykonalności (stan po EDA)

1. Czy swipe'y mają znaczniki czasu? Jeśli tak, w jakiej rozdzielczości? **Odpowiedź (EDA): tylko dzień (`day`), bez godzin.** Wśród 7790 par z decyzją obu stron 15,66% (1220) zdecydowało tego samego dnia, więc kolejności nie da się ustalić; pozostałe 84,34% da się uporządkować.
2. Jak działa feed: ranking, filtry użytkownika (płeć, wiek, palenie, lokalizacja), losowość? Czy B widzi, że A go polubił, przed swoją decyzją? (krytyczne dla H1–H3) - **bez odpowiedzi, dane tego nie rozstrzygają; czekamy na kontakt z przedstawicielem.**
3. Czy profile (**w tym bio**) mają historię edycji, czy tylko stan z momentu eksportu? (krytyczne dla H5). **Częściowo: istnieje tabela `profile_history` z 552 zmianami bio.** Nie sprawdzono jeszcze, czy zawiera treść poprzednich wersji i jaki okres obejmuje.
4. Jakie pola stylu życia są w profilu, jakie mają kategorie i czy mają wartości domyślne? Czy są to cechy własne, czy preferencje względem współlokatora? **Częściowo: tagi stylu życia (np. `non_smoker`, `night_owl`, `likes_calm`, `values_privacy`) są w polu `interests` razem ze zwykłymi zainteresowaniami (124 unikalne tagi, maks. 9 na użytkownika), a nie w osobnych polach. Czy to cechy własne czy preferencje, nie wiadomo.**
5. Jaki jest zakres czasowy danych i liczba użytkowników, swipe'ów, matchy i rozpoczętych rozmów? **2065 użytkowników (1583 z co najmniej jednym swipe'em na profil), 95 144 swipe'y na profile, 733 matche, 269 rozmów po matchu. Zakres czasowy: dłuższy niż 30 dni (351 par ma odstęp > 30 dni); dokładny zakres `day` `[DO UZUPEŁNIENIA]`.**
6. Czy ID są spójne między tabelami? Czy boty i konta testowe zostały usunięte? **ID łączą się między `users`, `swipes` i `matches` (płeć i wiek przypisano do wszystkich swipe'ów na profile; po `age_band` odpadło 578 z 95 144). Boty nie zostały usunięte: 18 kont (1,14% swipujących) ma 100% prawych swipe'ów przy ≥ 10 swipe'ach.**
7. Czy swipe'y na ogłoszenia można powiązać z cechami ogłoszeń (cena, lokalizacja)? **Istnieje tabela `listings` i `target_type` w `swipes`; powiązanie i cechy ogłoszeń `[DO UZUPEŁNIENIA]`, EDA objęła tylko swipe'y na profile.**
8. Czy istnieje mechanizm "Superlajka" (bezpośredniego wysłania wiadomości, bez wymogu istnienia matcha). **Nie rozstrzygnięto. Flaga `from_match` w `chats` sugeruje, że istnieją rozmowy spoza matchy; ich liczby nie sprawdzono.**

---

## 3. Wspólne definicje i metodologia

### 3.1 Jednostki analizy

- **Swipe skierowany (A→B):** y_right ∈ {0,1}. Osoba A zareagowała na profil osoby B (0 - brak zainteresowania, 1 - potencjalny match).
- **Para {A,B}:** y_match = 1, gdy obaj dali prawy swipe. Rozważane tylko pary, w których obie strony już zdecydowały (unikamy cenzurowania).
- **Rozmowa po matchu:** y_chat | match. Wtórna zmienna wynikowa, bliższa realnemu zainteresowaniu niż sam match.

### 3.2 Cechy opisujące dopasowanie pary (wspólne dla wszystkich hipotez)

Dla każdej pary liczymy wskaźniki dopasowania:

- **Płeć:** zmienna `same_gender` (1 = ta sama płeć, 0 = różna).
- **Wiek:** zmienne `|Δ wiek|`, `Δ wiek` (ze znakiem), `|Δ wiek|^2`
- **Zainteresowania**: miara Jaccarda, sprawdzimy też wersję w której *rzadkie* wspólne zainteresowanie, liczy się bardziej niż popularne. Dodatkowo uwzględnimy liczbę zainteresowań obu osób.
- **Styl życia**: porównujemy każde pole osobno. Zwracamy uwagę na kierunek (np. niepalący A i palący B, to coś innego niż palący A i niepalący B).
- **Braki danych**: Jeśli ktoś nie wypełnił pola - traktujemy to jako osobną kategorię `brak danych`.

### 3.3 Model i walidacja

Aby potwierdzić że wniosek hipotezy jest oparty na danych, zbudujemy prosty model regresji logistycznej.

- **Model główny:** regresja logistyczna z **efektami losowymi nadawcy i odbiorcy**- model szacuje prawdopodobieństwo swipe'a lub matcha na podstawie cech pary. Efekty losowe pozwolą nam wprowadzić poprawki na popularność i hojnosć użytkowników.
- **Metryki:** logloss, AUC, AUC-PR (zdarzenia rzadkie). Porównywanie bloków zmiennych przez ΔlogLoss/ΔAUC po dodaniu bloku (testy AB).
- **Podział danych:** walidacja krzyżowa grupowana po użytkownikach. Jeśli są timestampy, dodatkowo podział czasowy - uczymy się na starszych danych, sprawdzamy na nowszych.
- **Raportowanie:** Wielkości efektów i przedziały ufności. Definicje zmiennych i metryk ustalone przed analizą, żeby nie dobierać danych pod wynik.

### 3.4 Ograniczenia wspólne dla wszystkich hipotez

| ID | Ograniczenie / źródło błędu | Sposób postępowania |
|---|---|---|
| G1 | **Ekspozycja:** widzimy tylko pary pokazane przez feed. Filtry i ranking zawężają wariancję zmiennych, co zaniża efekty | ustalić z dostawcą działanie feedu; raportować rozkład zmiennych w obserwowanych parach |
| G2 | **Snapshot profilu:** `users` to stan z momentu eksportu, swipe'y z przeszłości; edycje po swipe'ach to błąd datowania. Istnieje `profile_history` (552 zmiany bio), ale jej pokrycie nie jest sprawdzone | sprawdzić zawartość historii; opisać jako ograniczenie |
| G3 | **Brak timestampów (potwierdzone):** jest tylko `day`; 15,66% par z decyzją obu stron to ten sam dzień. Uniemożliwia okna na poziomie zdarzeń i walidację czasową w dokładnej formie | H3 i H4 przeformułować do agregacji dziennej; swipe'y z tego samego dnia traktować jako remis (bez użycia do estymacji preferencji) |
| G4 | **Rzadkość matchy i mała moc** | policzyć zdarzenia i userów przed ustaleniem liczby zmiennych; AUC-PR, regularyzacja |
| G5 | **Brak zdjęć:** mocny sygnał na aplikacjach typu Tinder; mierzymy najwyżej popularność | efekty losowe odbiorcy; w tekście "popularność"|
| G6 | **Homogeniczna próba** (prawdopodobnie głównie studenci): wąski wiek, podobny styl życia, jedno lub kilka miast | zbadać rozkłady; ostrożne uogólnianie; standaryzowane efekty |
| G7 | **Braki i wartości domyślne** w polach strukturalnych (puste `interests`: 2,57%; puste bio: 46,6%) | analiza kompletności, osobna kategoria braku |
| G8 | **Wielość porównań** (wiele definicji podobieństwa) | z góry zapisany plan; jedna główna definicja na zmienną |
| G9 | **Match ≠ decyzja o wspólnym wynajmie** | sformułować wnioski jako dotyczące matcha i zaangażowania |
| G10 | **Boty, konta nietypowe** (swipe'ują wszystko w prawo/lewo): 18 kont 100% prawo (≥ 10 swipe'ów), 359 kont 0% prawo (22,68% swipujących) | flagowanie, analiza z wykluczeniem i bez |
| G13 | **Wiek tylko jako `age_band`** (18-20, 21-23, 24-26, 27-30, 31-35, 36+); 65% wyświetlanych profili to 18-20; komórki 27+ są bardzo małe (np. 31-35 → 31-35: 46 swipe'ów) | zamiast ciągłej różnicy wieku używać różnicy numerów przedziałów lub zgodności przedziału; łączyć rzadkie przedziały |
| G14 | **Styl życia i zainteresowania w jednym polu `interests`** (maks. 9 tagów, sufit: mediana = 9) | wydzielić tagi stylu życia ze słownika (124 tagów) przed analizą H1; Jaccard wrażliwy na sufit |
| G11 | **Anonimizacja:** losowe ID ograniczają łączenie z innymi źródłami; ryzyko reidentyfikacji z bio | przetwarzanie lokalne, bez próby identyfikacji |

---

## 4. Hipotezy

### H1. Zgodność stylu życia przewiduje match silniej niż zgodność wieku i zainteresowań

**One-liner:** wolę mieszkać z kimś o podobnym stylu życia (np. nie imprezuje) niż z kimś, kto byłby idealnym znajomym, ale irytowałyby mnie jego nawyki.

**Źródła danych:** `profiles` (styl życia, zainteresowania, wiek, płeć), `swipes_profiles`, `matches`.

**Zakres próby:**
- Pary {A,B}, w których obie strony zdecydowały i mają wypełnione pola używane w analizie.
- Wykluczenie kont oznaczonych jako boty (G10).
- Progi minimalnej aktywności: propozycja na podstawie rozkładu aktywności (mediana 26, średnia 60, p25 = 9, p95 ≈ 250 swipe'ów): ≥ 10 swipe'ów na użytkownika (odpada ok. 1/4 swipujących), do zatwierdzenia przed modelowaniem. Konta z < 5 swipe'ami to 14,59% swipujących.
- Liczba par, userów i matchy: 7790 par z decyzją obu stron, 733 matche (ok. 9,4% takich par), 1583 swipujących użytkowników z 2065. Liczba par po filtrach `[DO UZUPEŁNIENIA]`. Reguła 10 matchy na zmienną pozwala na maks. ok. 73 zmienne w modelu, mniej w podzbiorach.

**Plan pomiaru:**
- Zmienna objaśniana: y_match (główna), y_right kierunkowo (wtórna).
- Bloki zmiennych: demografia (`|Δwiek|`, `same_gender`), zainteresowania (Jaccard, IDF-Jaccard, liczba tagów), styl życia (zgodność per pole, kierunkowa).
- Model bazowy: demografia + zainteresowania. Model rozszerzony: + styl życia. Dodatkowo odwrócona kolejność (styl życia → + demografia + zainteresowania).
- Wszystko z efektami losowymi nadawcy i odbiorcy (G6).
- **Kryterium:** H1 potwierdzona, jeśli przyrost ΔlogLoss/ΔAUC po dodaniu stylu życia jest większy niż po dodaniu wieku i zainteresowań, a przedział ufności różnicy nie obejmuje zera.
- **Wynik negatywny:** styl życia nie wyjaśnia matcha ponad wiek i zainteresowania. Interpretacja "dopasowanie oparte na popularności" wymaga potwierdzenia przez efekty losowe, a nie samym brakiem efektu.

**Wstępne obserwacje z EDA:** akceptacja jest podobna dla tej samej i różnej grupy wiekowej (21,2% vs 20,0%), ale silnie zależy od kierunku: 18-20 → 18-20 20,4%, a 18-20 → 27+ ok. 7%. Jaccard zainteresowań wśród 733 matchy: średnia 0,146, mediana 0,125, 16,37% par bez wspólnego tagu; brak jeszcze rozkładu dla par niezmatchowanych, więc nie wiadomo, czy to więcej niż przypadek.

**Ograniczenia danych:** G1, G2, G6, G7, G13, G14; grube pola stylu życia (mała rozdzielczość pomiaru vs wiele tagów zainteresowań); wąski rozstrzał wieku (mała wariancja zmiennej, więc słaby efekt mechanicznie); asymetria cech (niepalący nie akceptuje palącego, odwrotnie niekoniecznie).

**Możliwe źródła błędu:**
- Różna jakość pomiaru bloków, więc porównanie "który blok wyjaśnia więcej" zależy od rozdzielczości, nie tylko od realnego wpływu.
- Korelacje między blokami: ważność jest dzielona, dlatego wymagane obie kolejności dodawania.
- Arbitralne wagi indeksu stylu życia (stąd analiza per pole).
- Jaccard zależy od liczby tagów, a ta koreluje z aktywnością.
- Domyślne wartości w polach stylu życia sztucznie zawyżają podobieństwo.
- Filtry w appce usuwają wariancję zmiennej, która była filtrowana (G1).

---

### H2. Dopasowanie demograficzne jest warunkiem wstępnym, a nie preferencją

**One-liner:** dziewczyny czują się bezpieczniej z innymi dziewczynami, więc od razu odfiltrowują chłopaków.

**Źródła danych:** `profiles` (płeć, wiek), `swipes_profiles`, `matches`.

**Zakres próby:**
- Swipe'y skierowane A→B, z podziałem na płeć nadawcy i odbiorcy.
- Liczność komórek (swipe'y nadawca × odbiorca): F→F 30 878, F→M 16 677, F→O 1307, M→F 24 003, M→M 17 446, M→O 1130, O→F 2178, O→M 1427, O→O 98. Par różnopłciowych (płeć nadawcy ≠ odbiorcy): 46 722 swipe'y (9847 prawych, 21,08%), więc kryterium wykonalności (≥ 1000) jest spełnione. Komórki z płcią `O` są małe (≤ 2178).

**Plan pomiaru:**
- Zmienna objaśniana: y_right (główna, kierunkowa), y_match (wtórna).
- Stratyfikacja: P(prawy swipe | ta sama płeć) vs P(prawy swipe | różna płeć), osobno według płci nadawcy, z przedziałami ufności.
- Model z interakcją `płeć_A × płeć_B`; `|Δwiek|`, `Δwiek` ze znakiem); bloki stylu życia i zainteresowań z H1.
- "Warunek wstępny" - model dwuetapowy: (1) czy para przechodzi bramkę demograficzną, (2) czy w obrębie warstwy działają pozostałe cechy. Próg "bliskie zeru" dla P(prawy | różna płeć) ustalamy przed analizą `[DO UZUPEŁNIENIA]`. Wstępnie żadna komórka nie jest bliska zera.
- **Wynik negatywny:** demografia nie dominuje; styl życia wyjaśnia matcha równie dobrze lub lepiej, więc parametry wpływają na dopasowanie, a nie tylko na strukturę zbioru.

**Wstępne obserwacje z EDA (P(prawy)):** F→F 20,1%, F→M 8,7%, F→O 14,9%; M→F 29,2%, M→M 19,5%, M→O 22,6%; O→F 28,7%, O→M 22,4%, O→O 26,5%. Kobiety rzadziej akceptują mężczyzn niż kobiety, ale prawdopodobieństwo nie jest bliskie zeru, więc dane nie wyglądają na twardą bramkę (opis bez kontroli innych cech i popularności).

**Ograniczenia danych:** G1 (filtry płci w appce mogą narzucać `same_gender` bez wariancji), G6; mało liczne grupy mniejszościowe płciowo (np. pary męsko-męskie, osoby niebinarne); możliwe konta par lub grup (jeśli występują).

**Możliwe źródła błędu:**
- Korelacja płci z innymi cechami (palenie, czystość, zainteresowania): ryzyko konfundowania.
- Silne nakładanie się z H1 (te same zmienne), co grozi dublowaniem testów; proponuje się wspólny model blokowy (sekcja 6).
- Selekcja ekspozycji: jeśli feed już filtruje płeć, wynik odzwierciedla ustawienia, a nie preferencje.

---

### H3. Match determinuje zgodność dwustronna (minimum), a nie jednostronna

**One-liner:** to, że widzę idealnego (według mnie) współlokatora, nie znaczy, że on mnie za takiego uważa.

**Źródła danych:** `profiles`, `swipes_profiles` (**wymagane timestampy**, G3), `matches`.

**Zakres próby:**
- Swipe'y, dla których nadawca ma historię ≥ n_min wcześniejszych swipe'ów (próg propozycja: ≥ 10, jak w H1; `[DO UZUPEŁNIENIA]` po zatwierdzeniu).
- Pary, w których obie strony zdecydowały: 7790, z czego 6570 (84,34%) w różne dni (odstęp 1 dzień: 1210, 2-3 dni: 1152, 4-7: 1418, 8-14: 1182, 15-30: 1257, > 30: 351). 1220 par (15,66%) zdecydowało tego samego dnia i nie nadaje się do okna czasowego.
- Liczność po zastosowaniu progu (wpływ selekcji): `[DO UZUPEŁNIENIA]`.

**Plan pomiaru:**
- Preferencje użytkownika estymowane wyłącznie z jego swipe'ów **sprzed** danej decyzji (rozwijane okno)
- Dopasowanie `fit_A→B` i `fit_B→A`, każde z historii własnej strony i z czasu przed jej swipe'em.
- Zestaw modeli: tylko `fit_A`, tylko `fit_B`, `fit_A + fit_B`, `fit_A × fit_B` z interakcją; min i |różnica| (suma jest kolinearna z nimi)
- Baseline niezależności: P(match) = P(A prawo) · P(B prawo).
- Walidacja czasowa (na poziomie dni, G3).
- **Kryterium:** zgodność dwustronna wyjaśnia więcej niż jednostronna ponad baseline niezależności.
- **Wynik negatywny:** jednostronne dopasowanie przewiduje równie dobrze. Interpretację "decyduje popularność" trzeba poprzeć efektami losowymi odbiorcy, a nie tylko brakiem przewagi dwustronności.

**Ograniczenia danych:** G3 (bez timestampów hipoteza jest niewykonalna w tej formie), G1, G4; cold start (mało historii na początku); cenzurowanie (B mógł jeszcze nie zobaczyć A); niejasne, czy B widzi lajk A.

**Możliwe źródła błędu:**
- **Wyciek informacji z przyszłości:** użycie swipe'ów po decyzji lub swipe'a zwrotnego B→A przy liczeniu preferencji.
- Selekcja przez próg n_min (zostają aktywni użytkownicy).
- Preferencje wyuczone ze swipe'ów zawierają ukrytą popularność odbiorców.
- Kołowość: cechy użyte do estymacji preferencji i do oceny to te same zmienne.

---

### H4. Zgodność selektywności użytkowników przewiduje wzajemność lepiej niż cechy profilu

**One-liner:** osoba, która dużo odsiewa (np. nie chce nikogo, kto pije, pali, imprezuje), najlepiej dopasuje się do kogoś, kto też dużo odsiewa.

**Źródła danych:** `swipes_profiles` (**timestampy lub przynajmniej kolejność zdarzeń**), `profiles`, `matches`.

**Zakres próby:**
- Swipe'y A→B z minimalną historią ≥ n_min swipe'ów po obu stronach (propozycja n_min = 10, `[DO UZUPEŁNIENIA]` po zatwierdzeniu).
- Wykluczenie lub osobna analiza kont o selektywności ≈ 0 lub ≈ 1 (boty, G10). Rozkład selektywności jest bardzo skośny: mediana 4,4%, średnia 17,4%, p75 24,1%, p90 58,3%; 18 kont z 100% prawo, 359 z 0% prawo (≥ 10 swipe'ów). Przy tak dużej masie przy zerze wariancja zmiennej jest ograniczona.

**Plan pomiaru:**
- Selektywność `s` = odsetek prawych swipe'ów w oknie przed zdarzeniem (okno liczone w dniach, G3). Intensywność `n` = liczba swipe'ów w oknie.
- Zmienna objaśniana: **wzajemność** P(B prawo | A prawo) - odsetek osób, które polubił A, która polubiła go spowrotem.
- Model bazowy zawiera cechy profilu oraz selektywność obu stron. Dzięki temu uwzględniamy, że dwie osoby rzadko dające prawo mają niską szansę na match, bo po prostu rzadko lajkują. Następnie dodajemy zmienne mówiące, jak bardzo podobna jest selektywność i intensywność obu osób (różnica między nimi) i sprawdzamy, czy model przewiduje match lepiej.
- Porównanie bloku zachowania z blokiem profilu (ΔlogLoss/ΔAUC).
- **Wynik negatywny:** cechy zachowania nie dodają informacji ponad profil; wniosek: o dopasowaniu decyduje to, co użytkownik deklaruje, a nie jak się zachowuje.

**Ograniczenia danych:** G3, G1, G10; selektywność odzwierciedla też pulę wyświetlaną przez feed (cecha puli, nie tylko użytkownika); różny staż kont.

**Możliwe źródła błędu:**
- **Mechaniczność:** przy niezależności P(match) = pA·pB, więc dwóch selektywnych użytkowników ma najniższą szansę, a dwóch nieselektywnych najwyższą. Hipotezę trzeba testować jako nadwyżkę ponad ten baseline, inaczej pomylimy mechanikę z efektem.
- Endogeniczność: wcześniejsze matche wpływają na późniejszą selektywność (okno tylko z przeszłości ogranicza wyciek, ale nie usuwa tego mechanizmu).
- Szum estymaty `s` przy małych próbach (regresja do średniej).
- Dryf selektywności z wiekiem konta (efekt nowości) i survivor bias* (selektywni odpadają szybciej - lub wolniej - jeśli osoby znajdujące pare odinstalowują apliakcję).


---

### H5. Treść i staranność bio niosą informację o dopasowaniu ponad pola strukturalne

**One-liner:** ludzie czytają bio i oceniają, czy ktoś "pasuje do klimatu", a samo staranne bio podnosi szansę na prawy swipe niezależnie od treści.

**Źródła danych:** `profiles` (bio, pola strukturalne), `swipes_profiles`, `matches`.

**Zakres próby:**
- Profile z niepustym bio (dla H5b pary, w których oba bio są niepuste).
- Niepuste bio: 1102 z 2065 profili (53,4%). Rozkład długości `bio_length` jest zwizualizowany w notebooku, statystyki (mediana, IQR) `[DO UZUPEŁNIENIA]`. Liczba par z oboma bio niepustymi `[DO UZUPEŁNIENIA]`; od tego zależy moc H5b.
- Dostępna `profile_history` z 552 zmianami bio, więc część bio mogła się zmienić po swipe'ach (G2).

**Plan pomiaru:**
- **H5a (sygnał jakości):** długość (log słów), pusty/niepusty, liczba emoji, język, liczba pytań. Efekt główny bio odbiorcy na y_right, z kontrolą liczby tagów zainteresowań i kompletności profilu oraz z efektami losowymi popularności.
- **H5b (podobieństwo treści):** cosinus embeddingów wielojęzycznego modelu zdaniowego (wektory centrowane) i alternatywnie TF-IDF cosine. Do modelu trafia **skalar**, nie cały wektor. Baseline: rozkład cosinusa dla losowych par.
- Opcjonalnie: ekstrakcja sygnałów (imprezowanie, gotowanie, home office, intencja) regułami lub LLM-em, z walidacją na ręcznie oznaczonej próbce (100–200 bio, zgodność raportowana).
- ΔlogLoss/ΔAUC po dodaniu bloku bio do modelu z profilem (jak w H1).
- **Wynik negatywny:** bio nie dodaje informacji ponad pola strukturalne; wniosek: oceniane jest głównie to, co deklaratywne i ustrukturyzowane (z zastrzeżeniem widoczności bio, pytanie 4 z sekcji 2.2).

**Ograniczenia danych:** G3 (edycje bio po swipe'ach, np. "już znalazłem mieszkanie"); widoczność bio na karcie (jeśli niewidoczne, brak efektu nie znaczy braku wpływu); krótkie lub puste bio (niska moc); bio mieszane językowo; prywatność (G12): bio może zawierać dane osobowe mimo anonimizacji, więc przetwarzanie lokalnie, bez zewnętrznych API.

**Możliwe źródła błędu:**
- Długość bio koreluje z aktywnością i kompletnością profilu, więc H5a bez kontroli dubluje efekt popularności.
- Redundancja z polami strukturalnymi (bio powtarza palenie, zwierzęta), więc przyrost informacji bliski zeru może wynikać z duplikacji.
- Anizotropia embeddingów: cosinus zdominowany przez język, długość i styl.
- Przeuczenie przy wektorach wysokowymiarowych i małej liczbie matchy.
- Elastyczność metryki (wybór modelu embeddingów, ekstrakcji): zapisać z góry.
- Błędy ekstrakcji (LLM/reguły) mogą mieć strukturę zależną od stylu pisania.

---

## 5. Plan wstępnej eksploracji (po otrzymaniu danych)

| # | Wskaźnik do policzenia | Wynik | Reguła decyzyjna |
|---|---|---|---|
| 1 | Liczba userów, swipe'ów, matchy, rozmów | 2065 userów (1583 swipujących), 95 144 swipe'y na profile (19 495 prawych), 733 matche, 269 rozmów po matchu. Lejek: 20,49% prawych → 7,52% prawych kończy się matchem → 36,70% matchy z rozmową | jeśli matchy < ok. 10× liczba zmiennych modelu, ograniczyć liczbę zmiennych |
| 2 | Zakres czasowy, obecność timestampów | Tylko `day` (int32), brak godzin; 15,66% par decyzji wzajemnych tego samego dnia; dokładny zakres dni `[DO UZUPEŁNIENIA]` | brak timestampów → H3 i H4 przeformułować lub odrzucić |
| 3 | Rozkład wieku (zakres, mediana, IQR) | Tylko `age_band`: 18-20 to 65% wyświetlanych profili (61 689 z 94 566), 21-23 19%, pozostałe ≤ 9%; mediana/IQR nie dotyczy | wąski zakres → ostrożna interpretacja H1/H2 dla wieku |
| 4 | Rozkład płci i macierz nadawca × odbiorca swipe'ów | Macierz 3×3 w sekcji H2: 46 722 swipe'y różnopłciowe, 21,08% prawych (F→M 8,7%, M→F 29,2%); płeć `O` rzadka | brak par różnopłciowych → H2 niewykonalna w proponowanej formie |
| 5 | Kompletność i rozkład pól stylu życia, wartości domyślne | Pola stylu życia są tagami w `interests`; kompletność innych kolumn `users` zwizualizowana w notebooku, liczby `[DO UZUPEŁNIENIA]`; wartości domyślne niesprawdzone | duże braki → analiza podzbioru lub uzupełnienie z bio |
| 6 | Liczba tagów zainteresowań i rozkład Jaccarda | Puste: 2,57%; mediana 9 tagów (sufit 9), średnia 7,2; 124 unikalne tagi; Jaccard na 733 matchach: średnia 0,146, mediana 0,125, 16,37% zer (brak baseline'u dla par losowych) | kontrola liczby tagów w modelu |
| 7 | Odsetek niepustych bio i rozkład długości | 1102 z 2065 (53,4%) niepustych; histogram długości w notebooku | niski odsetek → H5b ograniczyć do podpróby |
| 8 | Rozkład aktywności na usera, odsetek prawych swipe'ów, wykrycie botów | Mediana 26 swipe'ów (średnia 60,1; p95 ≈ 250; maks. 646); selektywność: mediana 4,4%, średnia 17,4%; 18 kont 100% prawo (1,14%), 359 kont 0% prawo (22,68%), 231 kont z < 5 swipe'ami (14,59%) | flagowanie kont skrajnych |
| 9 | Odsetek swipe'ów dających match i rozmowę po matchu | 20,49% swipe'ów to prawy; 733 matche = 0,77% swipe'ów; 36,70% matchy ma rozmowę (269) | wybór zmiennej głównej (match vs chat) |
| 10 | Odpowiedzi dostawcy na pytania z sekcji 2.2 | Odpowiedzi częściowe z danych (sekcja 2.2); pytania o feed i Superlajk czekają na dostawcę | wpływ na wykonalność H1–H5 |

---

## 6. Wykonalność w skali kursu

| Hipoteza | Trudność | Warunek wykonalności | Priorytet |
|---|---|---|---|
| H1 | średnia | wariancja stylu życia i wieku w obserwowanych parach | rdzeń |
| H2 | niska/średnia | istnienie par różnopłciowych w danych (brak twardego filtra) | rdzeń |
| H5 | średnia | odsetek niepustych bio; zasób obliczeniowy na embeddingi | blok dodatkowy do modelu H1/H2 |
| H4 | średnio-wysoka | timestampy; baseline niezależności | warunkowo |
| H3 | wysoka | timestampy; wystarczająca historia swipe'ów | warunkowo |

**Proponowana organizacja pracy:**
1. **Wspólny model hierarchiczny** z blokami: demografia, styl życia, zainteresowania, bio, zachowanie. H1, H2 i H5 to różne porównania w obrębie tego samego pipeline'u, co ogranicza duplikację i problem wielokrotnych porównań.
2. H3 i H4 realizowane tylko przy spełnieniu warunku timestampów; w przeciwnym razie przeformułowane do wersji bez okien czasowych.
3. Jeśli po EDA liczba matchy okaże się mała, pozostawić H1/H2 oraz podzbiór H5 jako wykonalny rdzeń projektu.

---
