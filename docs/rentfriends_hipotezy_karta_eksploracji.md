# RentFriends — materiał do Karty Eksploracji Danych (M1)

**Status:** dane jeszcze niedostępne, więc dokument zawiera plan i założenia, a nie wyniki EDA.

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

z aplikacji RentFriends otrzymamy zanonimizowane dane (**profile użytkowników**: zainteresowania, styl życia, płeć, wiek, opis z bio; **akcje użytkowników**: swipe’y profili i ogłoszeń mieszkań, matche, informacja o rozpoczęciu rozmowy na czacie, bez treści wiadomości; użytkownicy oznaczeni losowymi ID).

### 2.1 Zakładany schemat

Dane będą pochodzić z dumpu z bazy danych PostgreSQL, zakładamy pliki csv połączone relacyjnie za pomocą ID.

| Tabela | Zawartość | Uwagi |
|---|---|---|
| `profiles` | losowe ID, zainteresowania, styl życia (pola strukturalne), płeć, wiek, bio (tekst) | brak zdjęć; prawdopodobnie snapshot z momentu eksportu |
| `swipes_profiles` | nadawca, odbiorca, kierunek (lewo/prawo) | **nie wiemy czy otrzymamy znaczniki czasu** |
| `swipes_listings` | użytkownik, ogłoszenie, kierunek | atrybuty ogłoszeń niewymienione |
| `matches` | para użytkowników | definicja matcha: oba prawe swipe'y ` |
| `chat_started` | para, informacja o rozpoczęciu rozmowy | bez treści wiadomości |

### 2.2 Pytania decydujące o wykonalności (czekamy na otrzymanie danych) - planowane EDA + pytania do dostawcy

1. Czy swipe'y mają znaczniki czasu? Jeśli tak, w jakiej rozdzielczości?
2. Jak działa feed: ranking, filtry użytkownika (płeć, wiek, palenie, lokalizacja), losowość? Czy B widzi, że A go polubił, przed swoją decyzją? (krytyczne dla H1–H3) - czekamy na kontakt z przedstawicielem.
3. Czy profile (**w tym bio**) mają historię edycji, czy tylko stan z momentu eksportu? (krytyczne dla H5).
4. Jakie pola stylu życia są w profilu, jakie mają kategorie i czy mają wartości domyślne? Czy są to cechy własne, czy preferencje względem współlokatora?
5. Jaki jest zakres czasowy danych i liczba użytkowników, swipe'ów, matchy i rozpoczętych rozmów?
6. Czy ID są spójne między tabelami? Czy boty i konta testowe zostały usunięte?
7. Czy swipe'y na ogłoszenia można powiązać z cechami ogłoszeń (cena, lokalizacja)?
8. Czy istnieje mechanizm "Superlajka" (bezpośredniego wysłania wiadomości, bez wymogu istnienia matcha).

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
| G2 | `POTENCJALNE` **Snapshot profilu:** cechy z momentu eksportu, swipe'y z przeszłości; edycje po swipe'ach to błąd datowania | sprawdzić historię edycji; opisać jako ograniczenie |
| G3 | `POTENCJALNE` **Brak timestampów** : uniemożliwia okna czasowe i walidację czasową | warunkowa wykonalność H3 i H4 |
| G4 | **Rzadkość matchy i mała moc** | policzyć zdarzenia i userów przed ustaleniem liczby zmiennych; AUC-PR, regularyzacja |
| G5 | **Brak zdjęć:** mocny sygnał na aplikacjach typu Tinder; mierzymy najwyżej popularność | efekty losowe odbiorcy; w tekście "popularność"|
| G6 | **Homogeniczna próba** (prawdopodobnie głównie studenci): wąski wiek, podobny styl życia, jedno lub kilka miast | zbadać rozkłady; ostrożne uogólnianie; standaryzowane efekty |
| G7 | **Braki i wartości domyślne** w polach strukturalnych | analiza kompletności, osobna kategoria braku |
| G8 | **Wielość porównań** (wiele definicji podobieństwa) | z góry zapisany plan; jedna główna definicja na zmienną |
| G9 | **Match ≠ decyzja o wspólnym wynajmie** | sformułować wnioski jako dotyczące matcha i zaangażowania |
| G10 | **Boty, konta nietypowe** (swipe'ują wszystko w prawo/lewo) | flagowanie, analiza z wykluczeniem i bez |
| G11 | **Anonimizacja:** losowe ID ograniczają łączenie z innymi źródłami; ryzyko reidentyfikacji z bio | przetwarzanie lokalne, bez próby identyfikacji |

---

## 4. Hipotezy

### H1. Zgodność stylu życia przewiduje match silniej niż zgodność wieku i zainteresowań

**One-liner:** wolę mieszkać z kimś o podobnym stylu życia (np. nie imprezuje) niż z kimś, kto byłby idealnym znajomym, ale irytowałyby mnie jego nawyki.

**Źródła danych:** `profiles` (styl życia, zainteresowania, wiek, płeć), `swipes_profiles`, `matches`.

**Zakres próby:**
- Pary {A,B}, w których obie strony zdecydowały i mają wypełnione pola używane w analizie.
- Wykluczenie kont oznaczonych jako boty (G10).
- Progi minimalnej aktywności: `[DO UZUPEŁNIENIA po EDA]`.
- Liczba par, userów i matchy: `[DO UZUPEŁNIENIA]`.

**Plan pomiaru:**
- Zmienna objaśniana: y_match (główna), y_right kierunkowo (wtórna).
- Bloki zmiennych: demografia (`|Δwiek|`, `same_gender`), zainteresowania (Jaccard, IDF-Jaccard, liczba tagów), styl życia (zgodność per pole, kierunkowa).
- Model bazowy: demografia + zainteresowania. Model rozszerzony: + styl życia. Dodatkowo odwrócona kolejność (styl życia → + demografia + zainteresowania).
- Wszystko z efektami losowymi nadawcy i odbiorcy (G6).
- **Kryterium:** H1 potwierdzona, jeśli przyrost ΔlogLoss/ΔAUC po dodaniu stylu życia jest większy niż po dodaniu wieku i zainteresowań, a przedział ufności różnicy nie obejmuje zera.
- **Wynik negatywny:** styl życia nie wyjaśnia matcha ponad wiek i zainteresowania. Interpretacja "dopasowanie oparte na popularności" wymaga potwierdzenia przez efekty losowe, a nie samym brakiem efektu.

**Ograniczenia danych:** G1, G2, G6, G7; grube pola stylu życia (mała rozdzielczość pomiaru vs wiele tagów zainteresowań); wąski rozstrzał wieku (mała wariancja zmiennej, więc słaby efekt mechanicznie); asymetria cech (niepalący nie akceptuje palącego, odwrotnie niekoniecznie).

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
- Liczność komórek (płeć nadawcy × płeć odbiorcy) i par różnopłciowych: `[DO UZUPEŁNIENIA]`. Jeśli jest ich bardzo mało, test traci sens (G1).

**Plan pomiaru:**
- Zmienna objaśniana: y_right (główna, kierunkowa), y_match (wtórna).
- Stratyfikacja: P(prawy swipe | ta sama płeć) vs P(prawy swipe | różna płeć), osobno według płci nadawcy, z przedziałami ufności.
- Model z interakcją `płeć_A × płeć_B`; `|Δwiek|`, `Δwiek` ze znakiem); bloki stylu życia i zainteresowań z H1.
- "Warunek wstępny" - model dwuetapowy: (1) czy para przechodzi bramkę demograficzną, (2) czy w obrębie warstwy działają pozostałe cechy. Próg "bliskie zeru" dla P(prawy | różna płeć) ustalamy przed analizą `[DO UZUPEŁNIENIA]`.
- **Wynik negatywny:** demografia nie dominuje; styl życia wyjaśnia matcha równie dobrze lub lepiej, więc parametry wpływają na dopasowanie, a nie tylko na strukturę zbioru.

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
- Swipe'y, dla których nadawca ma historię ≥ n_min wcześniejszych swipe'ów (próg `[DO UZUPEŁNIENIA po EDA]`).
- Pary, w których obie strony zdecydowały.
- Liczność po zastosowaniu progu (wpływ selekcji): `[DO UZUPEŁNIENIA]`.

**Plan pomiaru:**
- Preferencje użytkownika estymowane wyłącznie z jego swipe'ów **sprzed** danej decyzji (rozwijane okno)
- Dopasowanie `fit_A→B` i `fit_B→A`, każde z historii własnej strony i z czasu przed jej swipe'em.
- Zestaw modeli: tylko `fit_A`, tylko `fit_B`, `fit_A + fit_B`, `fit_A × fit_B` z interakcją; min i |różnica| (suma jest kolinearna z nimi)
- Baseline niezależności: P(match) = P(A prawo) · P(B prawo).
- Walidacja czasowa.
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
- Swipe'y A→B z minimalną historią ≥ n_min swipe'ów po obu stronach `[DO UZUPEŁNIENIA]`.
- Wykluczenie lub osobna analiza kont o selektywności ≈ 0 lub ≈ 1 (boty, G10).

**Plan pomiaru:**
- Selektywność `s` = odsetek prawych swipe'ów w oknie przed zdarzeniem. Intensywność `n` = liczba swipe'ów w oknie.
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
- Odsetek niepustych bio i rozkład długości: `[DO UZUPEŁNIENIA]`. Od tego zależy moc testu.

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
| 1 | Liczba userów, swipe'ów, matchy, rozmów | `[DO UZUPEŁNIENIA]` | jeśli matchy < ok. 10× liczba zmiennych modelu, ograniczyć liczbę zmiennych |
| 2 | Zakres czasowy, obecność timestampów | `[DO UZUPEŁNIENIA]` | brak timestampów → H3 i H4 przeformułować lub odrzucić |
| 3 | Rozkład wieku (zakres, mediana, IQR) | `[DO UZUPEŁNIENIA]` | wąski zakres → ostrożna interpretacja H1/H2 dla wieku |
| 4 | Rozkład płci i macierz nadawca × odbiorca swipe'ów | `[DO UZUPEŁNIENIA]` | brak par różnopłciowych → H2 niewykonalna w proponowanej formie |
| 5 | Kompletność i rozkład pól stylu życia, wartości domyślne | `[DO UZUPEŁNIENIA]` | duże braki → analiza podzbioru lub uzupełnienie z bio |
| 6 | Liczba tagów zainteresowań i rozkład Jaccarda | `[DO UZUPEŁNIENIA]` | kontrola liczby tagów w modelu |
| 7 | Odsetek niepustych bio i rozkład długości | `[DO UZUPEŁNIENIA]` | niski odsetek → H5b ograniczyć do podpróby |
| 8 | Rozkład aktywności na usera, odsetek prawych swipe'ów, wykrycie botów | `[DO UZUPEŁNIENIA]` | flagowanie kont skrajnych |
| 9 | Odsetek swipe'ów dających match i rozmowę po matchu | `[DO UZUPEŁNIENIA]` | wybór zmiennej głównej (match vs chat) |
| 10 | Odpowiedzi dostawcy na pytania z sekcji 2.2 | `[DO UZUPEŁNIENIA]` | wpływ na wykonalność H1–H5 |

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
