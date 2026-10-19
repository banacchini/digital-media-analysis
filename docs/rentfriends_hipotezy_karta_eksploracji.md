# RentFriends — materiał do Karty Eksploracji Danych (M1)

**Status:** dane otrzymane; wstępna EDA wykonana (`notebooks/EDA.ipynb`, wersja z wynikami: `notebooks/EDA-rendered.ipynb`). Sekcje 2, 4 i 5 uzupełniono liczbami z EDA. Pytania do dostawcy (feed, Superlajk, wartości domyślne, brakujące swipe'y matchy) pozostają otwarte. Liczby są opisowe (bez wnioskowania statystycznego). Audyt 2026-10-20 wobec `profile_history` i notebooków `users_overview` / `profile_history_overview`: zmiany opisano w sekcji 7.

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
| `users` | **2065** profili: `user_key`, `sex` (F/M/O), `age_band`, `city`, pola stylu życia (`daily_routine`, `lifestyle`, `work_from_home`, `cleanliness`, `noise_level`, `smoking`, `alcohol`), `room_type`, `budget`, `move_in_month_offset`, `search_goal`, `interests` (lista tagów), `bio`, `bio_length` | wiek tylko jako przedział, nie w latach; pełna lista kolumn na diagramie ERD w notebooku; `interests`: 124 surowe ciągi, patrz G14 (audyt 2026-10-20) |
| `swipes` | `user_key`, `target_type` (`profile` / listing), `target_user_key`, `direction` (left/right), `day` | **jedyna informacja czasowa to `day` (int32)**, bez godzin; swipe'y na profile: **95 144** |
| `matches` | `user_a_key`, `user_b_key`, `day` | **733** matche, bez braków (0% NaN); match = wzajemne prawe swipe'y |
| `chats` | para użytkowników, `from_match`, `source_listing_key`, dni utworzenia i pierwszej wiadomości | bez treści wiadomości; łącznie **2742** rozmowy, z matcha **269**, z ogłoszenia (bez matcha) 163, pozostałe 2310 |
| `listings` | **294** ogłoszenia: miasto, dzielnica, `listing_kind` (room/entire), liczba mieszkańców, pokoje, `min_price`/`max_price`, `created_day` | swipe'y na ogłoszenia: **21 270**, wszystkie łączą się z `listings` |
| `profile_history` | pełne snapshoty profilu w każdej wersji (w tym bio) oraz `changed_fields` (pola zmienione względem poprzedniej wersji) | **4508 wersji**, 2056 userów (9 userów z `users` bez historii); wersja 1 = utworzenie; **552 zmiany bio u 362 userów**; ostatnia wersja zgodna z `users` w 100% pól; `day` od 2 do 113. `changed_fields` niepełne dla `sex` i `city` (G17) (audyt 2026-10-20) |

### 2.2 Pytania decydujące o wykonalności (stan po EDA)

1. Czy swipe'y mają znaczniki czasu? Jeśli tak, w jakiej rozdzielczości? **Odpowiedź (EDA): tylko dzień (`day`), bez godzin.** Wśród 7790 par z decyzją obu stron 15,66% (1220) zdecydowało tego samego dnia, więc kolejności nie da się ustalić; pozostałe 84,34% da się uporządkować.
2. Jak działa feed: ranking, filtry użytkownika (płeć, wiek, palenie, lokalizacja), losowość? Czy B widzi, że A go polubił, przed swoją decyzją? (krytyczne dla H1–H3) - **bez odpowiedzi, dane tego nie rozstrzygają; czekamy na kontakt z przedstawicielem.**
3. Czy profile (**w tym bio**) mają historię edycji, czy tylko stan z momentu eksportu? (krytyczne dla H5). **Częściowo (audyt 2026-10-20): `profile_history` zawiera pełne snapshoty profilu dla 4508 wersji (2056 userów), w tym bio; 552 zmiany bio u 362 userów. Treść bio w wersjach istnieje, ale nie była analizowana w całości (w EDA nie wyświetlano tekstu). Zakres: dni 2-113; dzień zerowy nieznany.**
4. Jakie pola stylu życia są w profilu, jakie mają kategorie i czy mają wartości domyślne? Czy są to cechy własne, czy preferencje względem współlokatora? **Częściowo. Są osobne pola strukturalne (sekcja 2.1) oraz tagi stylu życia w `interests` (np. `non_smoker`, `night_owl`, `likes_calm`; 124 unikalne tagi, maks. 9 na użytkownika). Pola `daily_routine`, `lifestyle`, `work_from_home`, `smoking`, `alcohol` mają 74-81% braków; `cleanliness` i `noise_level` tylko 1,0% i 1,2%, a najczęstsza kategoria to odpowiednio 53% i 50%, co może wskazywać na wartość domyślną (do potwierdzenia z dostawcą). Czy to cechy własne czy preferencje, nie wiadomo.** Audyt 2026-10-20: słownika tagów nie ma w repo; surowe ciągi zawierają dwa formaty tego samego typu (snake_case i emoji/etykieta), 256 userów ma oba, a 57% ma 9 tagów (sufit). Historia nie rozstrzyga, czy `cleanliness` i `noise_level` to wartość domyślna: rozkład przy utworzeniu profilu (FT 52,4%) jest taki sam jak w całej populacji, a zmian jest mało (49 i 54 aktualizacje). Pytanie do dostawcy.
5. Jaki jest zakres czasowy danych i liczba użytkowników, swipe'ów, matchy i rozpoczętych rozmów? **2065 użytkowników (1583 z co najmniej jednym swipe'em na profil), 95 144 swipe'y na profile i 21 270 na ogłoszenia, 733 matche, 2742 rozmowy (269 z matcha). Zakres czasowy: dni 1-113 (swipe'y), matche i rozmowy od dnia 4.**
6. Czy ID są spójne między tabelami? Czy boty i konta testowe zostały usunięte? **ID łączą się między `users`, `swipes` i `matches` (płeć i wiek przypisano do swipe'ów na profile z bieżącego `users`, a nie z dnia swipe'a (patrz pyt. 9); po `age_band` odpadło 578 z 95 144). Boty nie zostały usunięte: 18 kont (1,14% swipujących) ma 100% prawych swipe'ów przy ≥ 10 swipe'ach.**
7. Czy swipe'y na ogłoszenia można powiązać z cechami ogłoszeń (cena, lokalizacja)? **Tak: 100% swipe'ów na ogłoszenia łączy się z `listings` (257 z 294 ogłoszeń ma swipe'y; 16,2% prawych; to samo miasto 16,3% vs inne 14,8%). `min_price` ma wartości skrajne (mediana 1750, maks. 500 000), więc wymaga czyszczenia.**
8. Czy istnieje mechanizm "Superlajka" (bezpośredniego wysłania wiadomości, bez wymogu istnienia matcha). **Dane to sugerują: tylko 9,8% rozmów (269 z 2742) pochodzi z matcha, 163 z ogłoszenia, a 2310 rozmów nie ma ani matcha, ani ogłoszenia. Mechanizm trzeba potwierdzić z dostawcą. Konsekwencja: rozmowa nie jest zdarzeniem wyłącznie po matchu, więc `y_chat | match` obejmuje tylko 269 rozmów.**
9. Czy cechy użytkownika (płeć, wiek, miasto) zmieniają się w czasie i czy swipe'y są przypisane do właściwej wersji profilu? **(Audyt 2026-10-20.)** Tak: płeć zmieniło 87 userów (4,2%), wiek 12, miasto 118. Z 101 zmian płci 65 prowadzi do `O`. Przy przypisaniu według wersji obowiązującej w dniu swipe'a wartości różnią się od bieżących dla: płci aktora (1,8% swipe'ów z wcześniejszą wersją), płci odbiorcy (0,78%), wieku aktora (1,33%) i miasta aktora (3,88%). Dla 54 597 swipe'ów (46,9%) dzień swipe'a jest dniem pierwszej wersji profilu, więc nie da się rozstrzygnąć, czy swipe był przed zmianą. 551 swipe'ów jest przed pierwszą wersją i do wyjaśnienia z dostawcą. Konsekwencja: cechy pary wziąć z wersji obowiązującej w dniu decyzji, a bieżącą wersję traktować jako analizę wrażliwości.

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
- **Wersja cech (audyt 2026-10-20):** płeć, wiek, miasto i pola stylu życia pary bierzemy z wersji profilu obowiązującej w dniu decyzji (`profile_history`, z dokładnością do dnia, G2). Dla swipe'ów bez wcześniejszej wersji używamy pierwszej wersji i oznaczamy je. Wersja z `users` jest analizą wrażliwości.

### 3.3 Model i walidacja

Aby potwierdzić że wniosek hipotezy jest oparty na danych, zbudujemy prosty model regresji logistycznej.

- **Model główny:** regresja logistyczna z **efektami losowymi nadawcy i odbiorcy**- model szacuje prawdopodobieństwo swipe'a lub matcha na podstawie cech pary. Efekty losowe pozwolą nam wprowadzić poprawki na popularność i hojność użytkowników.
- **Metryki:** logloss, AUC, AUC-PR (zdarzenia rzadkie). Porównywanie bloków zmiennych przez ΔlogLoss/ΔAUC po dodaniu bloku (testy AB).
- **Podział danych:** walidacja krzyżowa grupowana po użytkownikach. Jeśli są timestampy, dodatkowo podział czasowy - uczymy się na starszych danych, sprawdzamy na nowszych.
- **Raportowanie:** Wielkości efektów i przedziały ufności. Definicje zmiennych i metryk ustalone przed analizą, żeby nie dobierać danych pod wynik.

### 3.4 Ograniczenia wspólne dla wszystkich hipotez

| ID | Ograniczenie / źródło błędu | Sposób postępowania |
|---|---|---|
| G1 | **Ekspozycja:** widzimy tylko pary pokazane przez feed. Filtry i ranking zawężają wariancję zmiennych, co zaniża efekty | ustalić z dostawcą działanie feedu; raportować rozkład zmiennych w obserwowanych parach |
| G2 | **Snapshot profilu:** `users` to stan z momentu eksportu, swipe'y z przeszłości; edycje po swipe'ach to błąd datowania. `profile_history` (4508 wersji, 2056 userów) pozwala odtworzyć profil w dniu decyzji, ale tylko z dokładnością do dnia: 54 597 swipe'ów (46,9%) jest z dnia pierwszej wersji, a 551 jest przed nią (audyt 2026-10-20) | cechy z wersji obowiązującej w dniu swipe'a, pierwsza wersja jako oznaczone przybliżenie; `users` jako wrażliwość; opisać jako ograniczenie |
| G3 | **Brak timestampów (potwierdzone):** jest tylko `day`; 15,66% par z decyzją obu stron to ten sam dzień. Uniemożliwia okna na poziomie zdarzeń i walidację czasową w dokładnej formie | H3 i H4 przeformułować do agregacji dziennej; swipe'y z tego samego dnia traktować jako remis (bez użycia do estymacji preferencji) |
| G4 | **Rzadkość matchy i mała moc** | policzyć zdarzenia i userów przed ustaleniem liczby zmiennych; AUC-PR, regularyzacja |
| G5 | **Brak zdjęć:** mocny sygnał na aplikacjach typu Tinder; mierzymy najwyżej popularność | efekty losowe odbiorcy; w tekście "popularność"|
| G6 | **Homogeniczna próba** (audyt 2026-10-20): tag `student` ma 55% userów (sugeruje studentów); wiek 18-20 to 54% userów; `search_goal` = LR u 92%; miasta: Wrocław 34%, „inne” 28%, Warszawa 15%; 45 userów ma miasto Hyderabad (2,2%), co nie pasuje do polskiej aplikacji i wymaga sprawdzenia | zbadać rozkłady; ostrożne uogólnianie; wrażliwość na podpróbę (np. bez Hyderabad i bez „inne”); standaryzowane efekty |
| G7 | **Braki i wartości domyślne** w polach strukturalnych (puste `interests`: 2,57%; puste bio: 46,6%) | analiza kompletności, osobna kategoria braku |
| G8 | **Wielość porównań** (wiele definicji podobieństwa) | z góry zapisany plan; jedna główna definicja na zmienną |
| G9 | **Match ≠ decyzja o wspólnym wynajmie** | sformułować wnioski jako dotyczące matcha i zaangażowania |
| G10 | **Boty, konta nietypowe** (swipe'ują wszystko w prawo/lewo): 18 kont 100% prawo (≥ 10 swipe'ów), 359 kont 0% prawo (22,68% swipujących) | flagowanie, analiza z wykluczeniem i bez |
| G12 | **Dane osobowe w bio** (audyt nieukończony; w poprzedniej wersji karty odwołanie do G12 nie miało wpisu, audyt 2026-10-20): w wersjach bio cyfry występują w 9,27%, `@` lub link w 1 wersji (0,02%), ciąg 9+ cyfr nie występuje. To tylko przesiew regułami, bez wyświetlania treści | pełny audyt przed użyciem tekstu bio; przetwarzanie lokalnie, bez zewnętrznych API; w raporcie tylko wyniki zagregowane |
| G13 | **Wiek tylko jako `age_band`** (18-20, 21-23, 24-26, 27-30, 31-35, 36+); 65% wyświetlanych profili to 18-20; komórki 27+ są bardzo małe (np. 31-35 → 31-35: 46 swipe'ów) | zamiast ciągłej różnicy wieku używać różnicy numerów przedziałów lub zgodności przedziału; łączyć rzadkie przedziały |
| G14 | **Styl życia częściowo w polach strukturalnych (74-81% braków w większości), częściowo w tagach `interests`** (maks. 9 tagów, mediana = 9; 57% userów na suficie). **Słownika tagów nie ma w repo.** 124 surowe ciągi zawierają m.in. 54 formy emoji/etykiety obok odpowiedników snake_case (np. `🎓 Student` i `student`); 256 userów ma oba formaty, a 159 z nich wykorzystuje tym limit 9 (audyt 2026-10-20) | ujednolicić format tagów (mapowanie do zweryfikowania) przed Jaccardem; w H1 rozdzielić tagi stylu życia i pola strukturalne (sekcja 4, H1); Jaccard wrażliwy na sufit i duplikaty |
| G15 | **Matche bez kompletu swipe'ów:** dla 246 z 733 matchy (33,6%) w `swipes` jest tylko jeden swipe na profil, drugi nie jest zapisany (mechanizm nieznany) | modele par z decyzją obu stron mają dostęp tylko do 487 matchy; sprawdzić z dostawcą; analiza wrażliwości |
| G16 | **Zmiany cech użytkownika w czasie** (audyt 2026-10-20): płeć zmieniło 87 userów (101 zmian, z czego 65 na `O`), wiek 12, miasto 118 | cechy pary z wersji obowiązującej w dniu decyzji (sekcja 3.2); wyjaśnić z dostawcą, co oznacza `O` i czy zmiany są własne, czy błędne |
| G17 | **`changed_fields` niepełne:** `sex` nigdy nie jest wymienione (101 zmian w snapshotach); `city` wymienione 541 razy przy 303 zmianach w snapshotach; `move_in` zgodne w 99,4% (= `move_in_month_offset`); `bio` zgodne w 100% (audyt 2026-10-20) | nie używać listy zmian jako źródła dla płci i miasta; porównywać snapshoty; listę zmian bio można używać |
| G18 | **Niespójność `bio_length` z długością tekstu:** zgodne w 97,7% profili (`users`) i 97,4% wersji (`profile_history`) (audyt 2026-10-20) | ustalić definicję długości; w H5a liczyć długość z tekstu i raportować różnicę |
| G11 | **Anonimizacja:** losowe ID ograniczają łączenie z innymi źródłami; ryzyko reidentyfikacji z bio | przetwarzanie lokalne, bez próby identyfikacji |

---

## 4. Hipotezy

### H1. Zgodność stylu życia przewiduje match silniej niż zgodność wieku i zainteresowań

**One-liner:** wolę mieszkać z kimś o podobnym stylu życia (np. nie imprezuje) niż z kimś, kto byłby idealnym znajomym, ale irytowałyby mnie jego nawyki.

**Źródła danych:** `users` (styl życia, zainteresowania, wiek, płeć), `swipes`, `matches`. (Audyt 2026-10-20: wcześniej `profiles` i `swipes_profiles`, czyli nazwy tabel, które nie istnieją.)

**Zakres próby:**
- Pary {A,B}, w których obie strony zdecydowały i mają wypełnione pola używane w analizie.
- Wykluczenie kont oznaczonych jako boty (G10).
- Progi minimalnej aktywności: propozycja na podstawie rozkładu aktywności (mediana 26, średnia 60, p25 = 9, p95 ≈ 250 swipe'ów): ≥ 10 swipe'ów na użytkownika (odpada ok. 1/4 swipujących), do zatwierdzenia przed modelowaniem. Konta z < 5 swipe'ami to 14,59% swipujących.
- Liczba par, userów i matchy: 7790 par z decyzją obu stron, w tym 487 matchy (6,3% takich par; pozostałe 246 z 733 matchy ma zapisany tylko jeden swipe, G15), 1583 swipujących użytkowników z 2065. Po filtrze ≥ 10 swipe'ów obu stron: 7538 par i 470 matchy (5533 pary bez kont skrajnych). Reguła 10 matchy na zmienną pozwala na ok. 47 zmiennych w modelu na parach (73 przy użyciu wszystkich 733 matchy).

**Plan pomiaru:**
- Zmienna objaśniana: y_match (główna), y_right kierunkowo (wtórna).
- Przed policzeniem Jaccarda (audyt 2026-10-20): ujednolicić format tagów (G14); rozdzielić tagi stylu życia od zainteresowań; ustalić, czy tagi dublujące pola strukturalne (`non_smoker`/`smoker`/`vapes` ↔ `smoking`, `quiet_after_22`/`quiet_evenings` ↔ `noise_level`, `loves_cleanliness` ↔ `cleanliness`) są tą samą zmienną. Dopiero wtedy zdefiniować bloki.
- Bloki zmiennych: demografia (`|Δwiek|`, `same_gender`), zainteresowania (Jaccard, IDF-Jaccard, liczba tagów), styl życia (zgodność per pole, kierunkowa).
- Model bazowy: demografia + zainteresowania. Model rozszerzony: + styl życia. Dodatkowo odwrócona kolejność (styl życia → + demografia + zainteresowania).
- Wszystko z efektami losowymi nadawcy i odbiorcy (G6).
- **Kryterium:** H1 potwierdzona, jeśli przyrost ΔlogLoss/ΔAUC po dodaniu stylu życia jest większy niż po dodaniu wieku i zainteresowań, a przedział ufności różnicy nie obejmuje zera.
- **Wynik negatywny:** styl życia nie wyjaśnia matcha ponad wiek i zainteresowania. Interpretacja "dopasowanie oparte na popularności" wymaga potwierdzenia przez efekty losowe, a nie samym brakiem efektu.

**Wstępne obserwacje z EDA:** akceptacja jest podobna dla tej samej i różnej grupy wiekowej (21,2% vs 20,0%), ale silnie zależy od kierunku: 18-20 → 18-20 20,4%, a 18-20 → 27+ ok. 7%. Jaccard zainteresowań wśród 733 matchy: średnia 0,146, mediana 0,125, 16,37% par bez wspólnego tagu; brak jeszcze rozkładu dla par niezmatchowanych, więc nie wiadomo, czy to więcej niż przypadek. Jaccard liczono na surowych tagach z duplikatami formatów (G14), więc wartości trzeba powtórzyć po ujednoliceniu.

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

**Źródła danych:** `users` (płeć, wiek), `swipes`, `matches`, `profile_history` (płeć i wiek w dniu swipe'a, G2, G16).

**Zakres próby:**
- Swipe'y skierowane A→B, z podziałem na płeć nadawcy i odbiorcy. Płeć z wersji obowiązującej w dniu swipe'a (G2, G16). Wersja bieżąca daje inną płeć dla 1,8% swipe'ów aktora i 0,78% odbiorców z wcześniejszą wersją (audyt 2026-10-20).
- Liczność komórek (swipe'y nadawca × odbiorca): F→F 30 878, F→M 16 677, F→O 1307, M→F 24 003, M→M 17 446, M→O 1130, O→F 2178, O→M 1427, O→O 98. Par różnopłciowych (płeć nadawcy ≠ odbiorcy): 46 722 swipe'y (9847 prawych, 21,08%), więc kryterium wykonalności (≥ 1000) jest spełnione. Komórki z płcią `O` są małe (≤ 2178).

**Plan pomiaru:**
- Zmienna objaśniana: y_right (główna, kierunkowa), y_match (wtórna).
- Stratyfikacja: P(prawy swipe | ta sama płeć) vs P(prawy swipe | różna płeć), osobno według płci nadawcy, z przedziałami ufności.
- Model z interakcją `płeć_A × płeć_B`, `|Δwiek|`, `Δwiek` (ze znakiem); bloki stylu życia i zainteresowań z H1.
- "Warunek wstępny" - model dwuetapowy: (1) czy para przechodzi bramkę demograficzną, (2) czy w obrębie warstwy działają pozostałe cechy. Próg "bliskie zeru" dla P(prawy | różna płeć) jest decyzją zespołu, którą należy zapisać przed analizą. Punkt odniesienia z EDA: najniższa komórka F→M ma 8,7% (95% CI Wilsona 8,3-9,1%), a żadna komórka nie ma CI przy zerze (przedziały nie uwzględniają klastrowania po użytkowniku, więc są zaniżone).
- **Wynik negatywny:** demografia nie dominuje; styl życia wyjaśnia matcha równie dobrze lub lepiej, więc parametry wpływają na dopasowanie, a nie tylko na strukturę zbioru.

**Wstępne obserwacje z EDA (P(prawy)):** F→F 20,1%, F→M 8,7%, F→O 14,9%; M→F 29,2%, M→M 19,5%, M→O 22,6%; O→F 28,7%, O→M 22,4%, O→O 26,5%. Kobiety rzadziej akceptują mężczyzn niż kobiety, ale prawdopodobieństwo nie jest bliskie zeru, więc dane nie wyglądają na twardą bramkę (opis bez kontroli innych cech i popularności). Liczono na płci z bieżącego `users`; po przejściu na wersję z dnia swipe'a trzeba to powtórzyć (różnica dotyczy 0,8–1,8% swipe'ów, wpływ do sprawdzenia). Kategoria `O` powstaje głównie przez zmianę płci (G16), więc wynik dla `O` wymaga ostrożności.

**Ograniczenia danych:** G1 (filtry płci w appce mogą narzucać `same_gender` bez wariancji), G6, G16; mało liczne grupy mniejszościowe płciowo (np. pary męsko-męskie, osoby niebinarne); możliwe konta par lub grup (jeśli występują).

**Możliwe źródła błędu:**
- Korelacja płci z innymi cechami (palenie, czystość, zainteresowania): ryzyko konfundowania.
- Silne nakładanie się z H1 (te same zmienne), co grozi dublowaniem testów; proponuje się wspólny model blokowy (sekcja 6).
- Selekcja ekspozycji: jeśli feed już filtruje płeć, wynik odzwierciedla ustawienia, a nie preferencje.

---

### H3. Match determinuje zgodność dwustronna (minimum), a nie jednostronna

**One-liner:** to, że widzę idealnego (według mnie) współlokatora, nie znaczy, że on mnie za takiego uważa.

**Źródła danych:** `users`, `swipes` (**wymagane timestampy**, G3; jest tylko `day`), `matches`, `profile_history` (wersje profilu w dniu decyzji z dokładnością do dnia, G2).

**Zakres próby:**
- Swipe'y, dla których nadawca ma historię ≥ n_min wcześniejszych swipe'ów (propozycja: ≥ 10, jak w H1, do zatwierdzenia). Swipe'y z taką historią z wcześniejszych dni: 45 315 z 95 144.
- Pary, w których obie strony zdecydowały: 7790, z czego 6570 (84,34%) w różne dni (odstęp 1 dzień: 1210, 2-3 dni: 1152, 4-7: 1418, 8-14: 1182, 15-30: 1257, > 30: 351). 1220 par (15,66%) zdecydowało tego samego dnia i nie nadaje się do okna czasowego.
- Liczność po progu n_min = 10 i wymogu różnych dni: 2308 par i tylko **87 matchy** (1894 pary bez kont skrajnych); dla n_min = 5: 2512 par i 98 matchy; dla n_min = 30: 1614 par i 48 matchy. Selekcja jest silna (zostają aktywni), a przy 87 matchach reguła 10 matchy na zmienną pozwala na ok. 8 zmiennych, więc H3 jest wykonalna tylko w bardzo uproszczonej formie.

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

**Źródła danych:** `swipes` (**timestampy lub przynajmniej kolejność zdarzeń**; jest tylko `day`), `users`, `matches`, `profile_history` (G2).

**Zakres próby:**
- Swipe'y A→B z minimalną historią ≥ n_min swipe'ów po obu stronach (propozycja n_min = 10, do zatwierdzenia). Liczności jak w H3: 2308 par i 87 matchy po wymogu historii z wcześniejszych dni; po wykluczeniu kont skrajnych 1894 pary. W H4 swipe'y z tego samego dnia też są wyłączone z estymacji `s`.
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
- Dryf selektywności z wiekiem konta (efekt nowości) i survivor bias (selektywni odpadają szybciej albo wolniej, jeśli osoby, które znalazły parę, odinstalowują aplikację).


---

### H5. Treść i staranność bio niosą informację o dopasowaniu ponad pola strukturalne

**One-liner:** ludzie czytają bio i oceniają, czy ktoś "pasuje do klimatu", a samo staranne bio podnosi szansę na prawy swipe niezależnie od treści.

**Źródła danych:** `users` (bio, pola strukturalne), `swipes`, `matches`, `profile_history` (bio w wersjach, 552 zmiany).

**Zakres próby:**
- Profile z niepustym bio (dla H5b pary, w których oba bio są niepuste).
- Niepuste bio: 1102 z 2065 profili (53,4%). Długość niepustego bio (znaki): mediana 81, IQR 33-153, maks. 250 (górny limit pola, rozkład ucięty). Par z decyzją obu stron z oboma bio niepustymi: 3535 z 7790, w tym 250 matchy (350 z 733 matchy ma oba bio niepuste). Swipe'y na profile z bio (H5a): 52 371 z 95 144; prawe swipe'y 21,5% (z bio) vs 19,2% (bez bio), różnica opisowa, bez kontroli popularności i kompletności profilu.
- `profile_history` (audyt 2026-10-20): 552 zmiany bio u 362 userów. W wersjach 42,1% to puste bio, a mediana długości niepustych wynosi 96 znaków (w `users`, liczonym na profilach, 53,4% niepustych i mediana 81; to inne jednostki). Histogram ma wyraźne skupienie na 250 znakach, co potwierdza górny limit pola. Bio obowiązujące w dniu swipe'a da się odtworzyć z dokładnością do dnia (G2); liczba swipe'ów po zmianie bio mierzy edycje po swipe'ach (G3).

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
| 2 | Zakres czasowy, obecność timestampów | Tylko `day` (int32), brak godzin; 15,66% par decyzji wzajemnych tego samego dnia; zakres dni 1-113 (112 różnych dni ze swipe'ami) | brak timestampów → H3 i H4 przeformułować lub odrzucić |
| 3 | Rozkład wieku (zakres, mediana, IQR) | Tylko `age_band`: 18-20 to 65% wyświetlanych profili (61 689 z 94 566; w `users` 54% userów, to inna jednostka), 21-23 19%, pozostałe ≤ 9%; mediana/IQR nie dotyczy | wąski zakres → ostrożna interpretacja H1/H2 dla wieku |
| 4 | Rozkład płci i macierz nadawca × odbiorca swipe'ów | Macierz 3×3 w sekcji H2: 46 722 swipe'y różnopłciowe, 21,08% prawych (F→M 8,7%, M→F 29,2%); płeć `O` rzadka | brak par różnopłciowych → H2 niewykonalna w proponowanej formie |
| 5 | Kompletność i rozkład pól stylu życia, wartości domyślne | `daily_routine`, `lifestyle`, `work_from_home`, `smoking`, `alcohol`: 74-81% braków; `cleanliness`, `noise_level`: ok. 1% braków, dominująca kategoria 53% i 50% (możliwy default); mediana 4 z 12 pól strukturalnych wypełnionych | duże braki → analiza podzbioru lub uzupełnienie z bio |
| 6 | Liczba tagów zainteresowań i rozkład Jaccarda | Puste: 2,57%; mediana 9 tagów (sufit 9), średnia 7,2; 124 unikalne tagi; Jaccard na 733 matchach: średnia 0,146, mediana 0,125, 16,37% zer (brak baseline'u dla par losowych) | kontrola liczby tagów w modelu |
| 7 | Odsetek niepustych bio i rozkład długości | 1102 z 2065 (53,4%) niepustych; mediana długości 81 znaków, IQR 33-153, maks. 250 | niski odsetek → H5b ograniczyć do podpróby (3535 par z oboma bio) |
| 8 | Rozkład aktywności na usera, odsetek prawych swipe'ów, wykrycie botów | Mediana 26 swipe'ów (średnia 60,1; p95 ≈ 250; maks. 646); selektywność: mediana 4,4%, średnia 17,4%; 18 kont 100% prawo (1,14%), 359 kont 0% prawo (22,68%), 231 kont z < 5 swipe'ami (14,59%) | flagowanie kont skrajnych |
| 9 | Odsetek swipe'ów dających match i rozmowę po matchu | 20,49% swipe'ów to prawy; 733 matche = 0,77% swipe'ów (487 z zapisanymi obydwoma swipe'ami); 36,70% matchy ma rozmowę (269); rozmów spoza matchy: 2473 | wybór zmiennej głównej (match vs chat) |
| 10 | Odpowiedzi dostawcy na pytania z sekcji 2.2 | Odpowiedzi częściowe z danych (sekcja 2.2); pytania o feed i Superlajk czekają na dostawcę | wpływ na wykonalność H1–H5 |
| 11 | Zgodność wersji profilu z `users`, wiarygodność `changed_fields` (audyt 2026-10-20) | ostatnia wersja = `users` w 100% pól; `changed_fields` niepełne dla `sex` (nigdy) i `city` (541 vs 303); bio zgodne w 100%; płeć zmieniło 87 userów, wiek 12, miasto 118 | cechy pary z wersji z dnia decyzji; nie ufać `changed_fields` dla płci i miasta |
| 12 | Swipe'y względem pierwszej wersji profilu (audyt 2026-10-20) | 54 597 swipe'ów (46,9%) z dnia pierwszej wersji; 61 118 (52,5%) z wcześniejszą wersją; 551 przed pierwszą wersją; 148 od userów bez historii | cechy as-of tylko dla swipe'ów z wcześniejszą wersją; pozostałe oznaczyć; zapytać dostawcę o dzień utworzenia |

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
4. Przed modelowaniem (audyt 2026-10-20): ujednolicić format tagów (G14) i wersjonować cechy użytkownika według dnia swipe'a (G2, G16). Bez tego H1 i H2 opierają się na zduplikowanych tagach i na bieżącej płci.

---

## 7. Dziennik audytu (2026-10-20)

**Podstawa:** `profile_history` (4508 wersji), `users` (2065), `swipes` (116 414) oraz notebooki `users_overview` i `profile_history_overview`. Liczby policzono na danych lokalnych; treść bio nie była wyświetlana.

**Zmiany w karcie:** sekcja 2.1 (wiersz `profile_history`, `users`), 2.2 (pyt. 3, 4, 6, nowy pyt. 9), 3.2 (wersja cech), 3.4 (G2, G6, G12 nowy, G14, G16–G18 nowe), sekcja 4 (nazwy tabel we wszystkich hipotezach, H1 przed Jaccardem, H2 płeć z dnia swipe'a, H5 statystyki bio w wersjach, literówki), sekcja 5 (wiersz 3, wiersze 11–12), sekcja 6 (pkt 4).

### Problemy w hipotezach

| ID | Hipoteza | Problem | Status |
|---|---|---|---|
| P1 | H1–H5 | Nazwy tabel `profiles` i `swipes_profiles` nie istnieją (tabele: `users`, `swipes`) | poprawione (sekcja 4) |
| P2 | H5 | Odwołanie do G12, którego w tabeli nie było | poprawione (G12 dodany) |
| P3 | H1 | G14 zakłada „słownik 124 tagów”; słownika nie ma, a 124 to surowe ciągi z duplikatami formatów (256 userów ma oba) | otwarte: ujednolicić format |
| P4 | H1 | Wstępny Jaccard (średnia 0,146) liczony na surowych tagach z duplikatami | otwarte: powtórzyć po P3 |
| P5 | H1 | Tagi stylu życia i zainteresowań nie są rozdzielone; część tagów dubluje pola strukturalne | otwarte: decyzja przed modelem |
| P6 | H1, H5 | Kody pól stylu życia bez kodebooka; historia nie rozstrzyga, czy `cleanliness`/`noise_level` to wartość domyślna | otwarte: pytanie do dostawcy |
| P7 | H2, H3, H4 | Płeć, wiek i miasto z bieżącego `users`, a nie z dnia swipe'a (płeć zmieniło 87 userów); różnice 0,8–3,9% swipe'ów | otwarte: przejście na wersję z dnia decyzji |
| P8 | H2 | Kategoria `O` powstaje głównie przez zmianę płci (65 z 101 zmian), więc może być artefaktem | otwarte: pytanie do dostawcy |
| P9 | H2 | Sekcja 2.2 pyt. 6 twierdziła, że płeć i wiek przypisano do swipe'ów; to był bieżący stan | poprawione (pyt. 6 i nowy pyt. 9) |
| P10 | H3, H4 | Wersje profilu tylko z dokładnością do dnia: 46,9% swipe'ów z dnia pierwszej wersji, 551 przed nią | otwarte: pytanie o dzień utworzenia i zapis zmian |
| P11 | H3, H4 | Okno „z przeszłości” nie pokazuje, co użytkownik widział przed decyzją (G3) | ograniczenie, opisane w G2/G3 |
| P12 | H5 | Statystyki bio w H5 liczone na `users` (profile), a nie na wersjach; różne jednostki | poprawione (opis w H5) |
| P13 | H5 | G2 mówił, że pokrycie historii nie jest sprawdzone; sprawdzone: bio zgodne w 100% z `changed_fields` | poprawione (G2, G17) |
| P14 | H5 | `bio_length` różni się od długości tekstu w 2,3–2,6% profili i wersji (G18) | otwarte: ustalić definicję |
| P15 | H5 | Audyt danych osobowych w bio nieukończony; flagi regex to tylko przesiew | otwarte (G12) |
| P16 | H1, H2, H5 | G6 nieprecyzyjne („jedno lub kilka miast”); Hyderabad (45 userów) to anomalia | poprawione (G6); anomalia otwarta |
| P17 | H2, H5 | `changed_fields` niepełne dla płci i miasta, co grozi błędnym wnioskiem przy szukaniu zmian | poprawione (G17) |
| P18 | H2 | Wstępne P(prawy) liczone na bieżącej płci | otwarte: powtórzyć |
| P19 | H1–H5 | Literówki i błędy składni: „survivor bias*”, „apliakcję”, „pare”, „hojnosć”, niedomknięty nawias w H2 | poprawione |
| P20 | sekcja 5 | Wiek: 65% (wyświetlane profile) i 54% (`users`) to różne jednostki | poprawione (opis w wierszu 3) |

---

---
