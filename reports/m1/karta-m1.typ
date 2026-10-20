// Karta eksploracji danych (M1), RentFriends.
// Build (from the repo root; fonts are bundled in reports/assets/fonts):
//   typst compile --font-path reports/assets/fonts reports/m1/karta-m1.typ
//   or: uvx --from typst python -c "import typst; typst.compile('reports/m1/karta-m1.typ', output='reports/m1/karta-m1.pdf', font_paths=['reports/assets/fonts'])"
// Numbers come only from saved notebook outputs and docs/rentfriends_hipotezy_karta_eksploracji.md
// (the "technical document"). Reviewer notes: reports/m1/uwagi-dla-recenzenta.md.
// Visual style: STYLEGUIDE.md (one-pager rules, section 8). Figures are kept as rendered in the notebooks.

// Brand tokens (STYLEGUIDE.md, section 2)
#let c-black = rgb("#0F0F0F")
#let c-bg = rgb("#F4F2EE")
#let c-gray = rgb("#595959")
#let c-blue = rgb("#234CE0")
#let c-purple = rgb("#A247E3")
#let c-purple-ink = rgb("#8B34C4")
#let c-pink = rgb("#E95BD2")
#let c-tint = c-purple.transparentize(88%)
#let c-hair = c-gray.transparentize(80%)
#let brand-gradient = gradient.linear(c-blue, c-purple, c-pink)

#set document(title: "Karta eksploracji danych (M1): RentFriends")
#set page(
  paper: "a4",
  margin: (x: 1.45cm, top: 1.3cm, bottom: 1.5cm),
  fill: c-bg,
  footer: context {
    set text(size: 7.5pt, fill: c-gray)
    line(length: 100%, stroke: 0.5pt + c-hair)
    v(-0.4em)
    grid(
      columns: (1fr, auto),
      [Analiza Mediów Cyfrowych · analiza studencka, nie publikacja RentFriends],
      counter(page).display("1 / 1", both: true),
    )
  },
)
#set text(font: ("Plus Jakarta Sans", "DejaVu Sans"), lang: "pl", size: 8.7pt, fill: c-gray, spacing: 135%)
#show raw: set text(font: "DejaVu Sans Mono", size: 0.92em, fill: c-black)
#show strong: set text(fill: c-black)
#set strong(delta: 300)
#set par(justify: true, leading: 0.72em, spacing: 1.1em)
#set heading(numbering: "1.")
#show heading: set text(fill: c-black, weight: 800, tracking: -0.02em)
#show heading.where(level: 1): set text(size: 12pt)
#show heading: set block(above: 1.1em, below: 0.55em)
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.75em)[
  #text(fill: c-purple-ink)[#counter(heading).display(it.numbering)]#h(0.4em)#it.body
]
#set list(spacing: 0.7em, marker: text(fill: c-purple, size: 0.8em, baseline: -0.1em)[●], body-indent: 0.5em)
#show list: set block(above: 0.7em, below: 1.1em)
#set footnote.entry(separator: line(length: 30%, stroke: 0.5pt + c-hair))
#show footnote.entry: set text(size: 7.5pt)

// Tables: white card with a hairline frame, purple-tinted header, horizontal hairlines only
#set table(
  inset: (x: 5pt, y: 4pt),
  stroke: (x, y) => (top: if y > 0 { 0.5pt + c-hair }),
  fill: (x, y) => if y == 0 { c-tint } else { white },
)
#show table.cell.where(y: 0): set text(fill: c-black, weight: "bold")
#show table: set text(size: 8pt)
#show table: set par(justify: false)
#show table: it => block(radius: 8pt, clip: true, stroke: 0.5pt + c-hair, it)

#set figure(gap: 0.45em)
#show figure: set block(above: 1em, below: 1em)
#show figure.caption: set text(size: 7.5pt)
#show figure.caption: set align(left)
#show figure.caption: set par(justify: true)
#set figure.caption(separator: [. ])

// Review markers: pill chips
#let mark(body) = box(
  fill: c-tint,
  radius: 1em,
  inset: (x: 4pt, y: 0pt),
  outset: (y: 1.6pt),
  text(fill: c-purple-ink, weight: "bold", size: 0.82em, body),
)
#let tbc = mark[DO POTWIERDZENIA]
#let recalc(what) = mark[DO PRZELICZENIA#if what != [] [ #what]]
#let pre = text(style: "italic")[wstępne: bieżąca płeć z `users`, surowe tagi, z Hyderabad]

// Notebook charts sit on a white rounded card (they have white backgrounds)
#let fig(path, cap, w: 100%) = figure(
  block(fill: white, radius: 8pt, inset: 4pt, stroke: 0.5pt + c-hair, image(path, width: w)),
  caption: cap,
  supplement: [Rys.],
)

// Title: eyebrow with a purple dot, two-line headline, payoff line in the brand gradient
#block(below: 0.9em)[
  #text(size: 9pt, weight: "semibold", fill: c-purple-ink)[#box(baseline: -0.15em, circle(radius: 3pt, fill: c-purple)) #h(0.3em) Analiza Mediów Cyfrowych · kamień milowy M1]
  #v(0.2em)
  #set par(leading: 0.3em)
  #text(size: 20pt, weight: 800, tracking: -0.025em, fill: c-black)[Karta eksploracji danych] \
  #text(size: 20pt, weight: 800, tracking: -0.025em, fill: brand-gradient)[Co przewiduje prawy swipe w RentFriends?]
  #v(0.15em)
  #text(size: 9pt, weight: "medium")[Zespół: #tbc · wersja robocza do review, 2026-10-20]
]


#block(fill: c-tint, inset: 9pt, radius: 10pt, width: 100%, text(size: 8pt)[
  *Podstawa liczb:* zapisane wyniki notebooków (`EDA`, `users_overview`, `profile_history_overview`) i dokument techniczny (`docs/rentfriends_hipotezy_karta_eksploracji.md`). Liczby są *sprzed filtra Hyderabad (45 kont)* i sprzed wersjonowania profili (D7, D10), więc płeć, wiek i miasto pochodzą z bieżącej tabeli `users`. #recalc[po filtrze Hyderabad] \
  #tbc oznacza założenie lub brak danych w artefaktach.
])

= Pytanie badawcze i hipotezy

*Wspólnego najmu nie obserwujemy.* Dane kończą się na rozpoczęciu rozmowy, a match nie jest decyzją o najmie. Badamy więc decyzje w aplikacji.

*Pytanie:* które cechy pary (A, B) są związane z prawym swipe'em A→B? W szczególności: czy zgodność stylu życia przewiduje go silniej niż zgodność wieku i zainteresowań?

- *Zmienna główna:* `y_right`, czyli swipe kierunkowy A→B na profil.
- *Zmienna drugorzędna:* match, tylko dla par z zapisanymi swipe'ami obu stron.
- *Rozmowy:* tylko opisowo.

#table(
  columns: (auto, 1fr, 1fr),
  table.header([*ID*], [*Hipoteza*], [*Co ją obali*]),
  [H1], [Zgodność stylu życia przewiduje `y_right` (i match) silniej niż zgodność wieku i zainteresowań.],
  [Blok stylu życia nie daje większego przyrostu niż wiek i zainteresowania w obu kolejnościach, CI różnicy obejmuje 0 albo blok nie odróżnia się od tasowania.],
  [H2], [Płeć i wiek są związane z `y_right`. Szacujemy wielkość efektu: iloraz szans (ta sama vs różna płeć) według płci nadawcy, z CI.],
  [CI ilorazu szans obejmuje 1. Macierz z @rys-plec widzieliśmy przed sformułowaniem H2, więc ta część jest eksploracyjna.],
  [H3#super[dod.]], [Staranność bio odbiorcy (pusty/niepusty, długość; H3a) przewiduje `y_right` ponad pola strukturalne i liczbę tagów.],
  [CI efektu obejmuje 0 po kontroli kompletności profilu i popularności. H3b (treść bio) tylko przy wolnych zasobach #tbc.],
)
#text(size: 8pt)[Dawne ID (dokument techniczny, notebooki): H1 = H1, H2 = H2, H3 = *H5*. H3 jest dodatkowa, bo zakres części NLP jest niepewny.#footnote[Odrzuciliśmy dwie hipotezy wymagające kolejności zdarzeń w ciągu dnia (dopasowanie dwustronne, zgodność selektywności; dawne H3 i H4). Dane mają tylko `day`, a po filtrach zostaje 2308 par i 87 matchy.]]

= Źródła danych

Zanonimizowany eksport z RentFriends z losowymi identyfikatorami `user_key`. Nie używamy innych platform ani scrapingu.

- *Właściciel, warunki użycia, data otrzymania:* #tbc (data statement w przygotowaniu).
- *Spójność kluczy:* `user_key` łączy `users`, `swipes` i `matches`; 100% swipe'ów na ogłoszenia łączy się z `listings`; zduplikowanych swipe'ów jest 0; match pokrywa się z wzajemnym prawym swipe'em w 99,95%.
- *Czas:* tylko numer dnia `day` (swipe'y: dni 1–113), bez godzin.

#table(
  columns: (auto, 1fr, auto),
  table.header([*Tabela*], [*Zawartość*], [*Liczność*]),
  [`users`], [płeć (F/M/O), `age_band`, miasto, 7 pól stylu życia, tagi `interests`, bio], [2065 profili],
  [`swipes`], [nadawca, cel (profil/ogłoszenie), kierunek, `day`], [95~144 na profile, 21~270 na ogłoszenia],
  [`matches`], [para, `day`], [733],
  [`chats`], [para, `from_match`, ogłoszenie źródłowe, dni; bez treści], [2742],
  [`listings`], [miasto, typ, cena, `created_day`], [294],
  [`profile_history`], [pełne snapshoty profilu w każdej wersji], [4508 wersji, 2056 użytk.],
)

= Zakres próby

- *Jednostka:* swipe A→B na profil, a dla matcha para {A, B}. Użytkownik występuje w wielu parach, więc foldy i bootstrap robimy po użytkownikach.
- *Próba główna* (bez progu aktywności i bez wykluczania kont skrajnych, D6): 1583 swipujących z 2065 użytkowników, 95~144 swipe'ów, 7790 par z decyzją obu stron, 487 matchy. 246 matchy z jednym swipe'em jest poza modelem.
- *Wykluczenie:* 45 kont z Hyderabad (anomalia dla polskiej aplikacji) wraz z ich swipe'ami. Kategoria „inne” zostaje. #recalc[]
- *Wrażliwość:* próg ≥ 10 swipe'ów daje 7538 par i 470 matchy. Bez kont skrajnych (18 z samymi prawymi, 359 z samymi lewymi swipe'ami) zostaje 5527 par.
- *Jednorodność:* `student` ma 55% użytkowników, pasmo 18–20 54%, `search_goal` = LR 92%. Miasta: Wrocław 34%, „inne” 28%, Warszawa 15%.

= Wyniki wstępnej eksploracji

Opis bez wnioskowania. Dane wstępne: bieżąca płeć z `users`, surowe tagi, z Hyderabad.

#grid(
  columns: (0.95fr, 1.05fr),
  column-gutter: 12pt,
  table(
    columns: (1fr, auto, auto),
    table.header([*Lejek*], [*Liczba*], [*Odsetek*]),
    [Swipe'y na profile], [95~144], [100%],
    [Prawe swipe'y], [19~495], [20,49% swipe'ów],
    [Matche], [733], [7,52% prawych],
    [Matche z rozmową], [269], [36,70% matchy],
  ),
  [
    - *Matche:* 487 z oboma swipe'ami, 246 (33,6%) z jednym.
    - *Rozmowy:* 2742, z czego 269 z matcha, 163 z ogłoszenia, a 2310 bez obu (możliwy „Superlajk”).
    - *Ten sam dzień:* 1220 z 7790 par (15,66%) zdecydowało tego samego dnia.
  ],
)

*Aktywność* (@rys-akt)
- Mediana 26 swipe'ów na użytkownika (średnia 60,1; p95 ≈ 250; maks. 646). 231 kont (14,59%) ma mniej niż 5 swipe'ów.
- Selektywność (odsetek prawych): mediana 4,4%, średnia 17,4%.
- Duże różnice między użytkownikami uzasadniają efekty losowe i wrażliwość na konta skrajne.

*Styl życia i tagi, H1* (@rys-pola)
- Pięć pól stylu życia ma 74–81% braków.
- `cleanliness` i `noise_level` mają tylko 1,0% i 1,2% braków, ale dominująca kategoria ma 53,0% i 50,4%. To może być wartość domyślna. Kody nie mają codebooka.
- Tagi: 124 surowe ciągi, w tym 54 formy emoji obok snake_case. 256 użytkowników ma oba formaty (159 z nich na limicie 9). 57% ma 9 tagów, 2,57% żadnego.
- Jaccard w 733 matchach: średnia 0,146, mediana 0,125. Liczony na surowych tagach i bez porównania z parami bez matcha (wykresy: `users_overview`, sekcja 6).

*Demografia, H2* (@rys-plec, @rys-wiek)
- Ta sama vs różna płeć: kobiety 20,1% vs 9,2% (F→M 8,7%, CI 8,3–9,1%), mężczyźni 19,5% vs 28,9% (M→F 29,2%).
- Żadna komórka nie jest bliska zeru. Komórki z `O` są małe (O→O: 98 swipe'ów).
- Wiek: to samo vs różne pasmo daje 21,2% vs 20,0%, ale liczy się kierunek: 18–20 → 18–20 20,4%, 18–20 → 27–30 6,6%. 65% wyświetleń dotyczy profili 18–20.

*Bio, H3*
- Bio ma 1102 z 2065 profili (53,4%). Mediana 81 znaków (IQR 33–153), sufit 250.
- P(prawy): 21,5% dla odbiorców z bio, 19,2% bez bio (bez kontroli; wykres: `EDA`, „Bio”).

*Wersje profilu*
- 4508 wersji; ostatnia zgadza się z `users` w 100% pól.
- Płeć zmieniło 87 użytkowników (101 zmian, 65 do `O`), wiek 12, miasto 118. `changed_fields` pomija zmiany płci, więc porównujemy snapshoty.
- Swipe'y względem wersji: 54~597 (46,9%) z dnia pierwszej wersji, 61~118 (52,5%) z wcześniejszą wersją, 551 przed pierwszą, 148 bez historii. Liczone na 116~414 swipe'ach razem z ogłoszeniami. #recalc[dla 95~144 swipe'ów na profile]

#grid(
  columns: (1fr, 1fr),
  column-gutter: 10pt,
  [#fig("figures/R3_aktywnosc_selektywnosc.png")[Liczba swipe'ów na użytkownika (lewy) i selektywność, czyli odsetek prawych swipe'ów (prawy); 1583 użytkowników. Podstawa: swipe'y na profile, `EDA`, „Aktywność użytkowników”. Z Hyderabad. Słupki przy 0 i 1 to konta skrajne (D6).] <rys-akt>],
  [#fig("figures/R2_kompletnosc_pol.png")[Braki w polach strukturalnych `users` (lewy) i liczba wypełnionych pól na użytkownika (prawy); n = 2065. Podstawa: `EDA`, „Pola stylu życia”. Niskie braki `cleanliness` i `noise_level` mogą wynikać z wartości domyślnych. Wykres obejmuje też pola spoza stylu życia.] <rys-pola>],
)
#grid(
  columns: (0.8fr, 1.2fr),
  column-gutter: 10pt,
  [#fig("figures/R1_akceptacja_plec.png")[P(prawy swipe) według płci nadawcy→odbiorcy z 95% CI Wilsona; 95~144 swipe'ów. Podstawa: `EDA`, „H2: przedziały ufności”. CI niezgrupowane po użytkowniku, więc zaniżone. `O` interpretujemy ostrożnie. #pre.] <rys-plec>],
  [#fig("figures/R4_wiek_ekspozycja_akceptacja.png")[Wyświetlenia (lewy) i odsetek prawych swipe'ów (prawy) według pasma wieku nadawcy (wiersze) i odbiorcy (kolumny); 94~566 swipe'ów z `age_band`. Podstawa: `EDA`, „ekspozycji oraz stopnia akceptacji”. Komórki 27+ są małe; w analizie łączymy je (D9). Z Hyderabad.] <rys-wiek>],
)

= Plan pomiaru zjawiska

*Wersja profilu w dniu swipe'a (as-of, D7).* Każdy swipe dostaje flagę źródła:
- `prior_version`: swipe po dniu pierwszej wersji, czyli ostatnia wersja sprzed dnia swipe'a;
- `first_version`: swipe z dnia pierwszej wersji lub wcześniejszy, czyli wersja v1;
- `users_current`: 9 użytkowników bez historii, czyli bieżący `users`.

*Bloki zmiennych* (1–3 skalary na blok, D16)
- *Demografia:* płeć nadawcy × odbiorcy (`O` jako osobna kategoria), ta sama płeć, różnica pasm wieku ze znakiem i to samo pasmo (pasma 27+ połączone).
- *Styl życia:* zgodność 7 pól, gdy obie strony je wypełniły („brak danych” jako kategoria); konflikt kierunkowy tagów (np. `non_smoker` vs `smoker`/`vapes`); liczba wspólnych tagów. Pole ma pierwszeństwo przed tagiem, a tag uzupełnia braki.
- *Zainteresowania:* tagi hobby po ujednoliceniu i deduplikacji #tbc, czyli Jaccard i liczba tagów. `student` to status; zwierzęta i `extrovert`/`introvert` należą do stylu życia.
- *Bio (H3a):* pusty/niepusty, długość liczona z tekstu.

*Model i testy*
- Regresja logistyczna dla `y_right`; match w modelu drugorzędnym (7790 par).
- Estymator #tbc: krzyżowe efekty losowe nadawcy i odbiorcy albo błędy klastrowane.
- Kontrole: `same_city`, a popularność i hojność przez efekty losowe #tbc.
- Walidacja w foldach po użytkownikach; metryki logloss, AUC, AUC-PR.
- *H1:* ΔlogLoss i ΔAUC po dodaniu bloku, w obu kolejnościach, z CI z bootstrapu po użytkownikach i baseline'em z tasowania bloku. Analiza per pole jest drugorzędna.
- *H2:* iloraz szans z CI. *H3:* efekt bio z kontrolą liczby tagów i kompletności profilu.

*Instrument AI*
- Agent AI proponuje ujednolicenie tagów (54 formy emoji → kanoniczne) i ich podział, a człowiek ustala wersję końcową.
- Walidacja: zgodność agenta z człowiekiem (miara #tbc). Propozycje agenta zapisujemy przed zamrożeniem codebooka.
- Ewentualne NLP w H3: gold standard z ręcznie oznaczonej próbki, lokalnie. Rozmiar próbki i adnotatorzy są nieustaleni.

*Analizy wrażliwości*
+ Próg ≥ 10 swipe'ów i bez kont skrajnych.
+ Tylko swipe'y z `prior_version`; cechy z bieżącego `users`.
+ Z kontami Hyderabad.
+ Bez kategorii „brak danych” oraz bez `cleanliness`/`noise_level`.
+ Dla matcha: z 246 matchami z jednym swipe'em.

= Ograniczenia danych i możliwe źródła błędu

- *Match ≠ najem.* Wnioski dotyczą decyzji w aplikacji. Badamy związki, nie przyczyny.
- *Ekspozycja:* widzimy tylko pary pokazane przez feed. Filtry i ranking mogą zawężać wariancję, np. płci.
- *Czas tylko w dniach:* dla 46,9% swipe'ów wersja v1 jest przybliżeniem; 551 swipe'ów jest sprzed pierwszej wersji, a dzień zerowy jest nieznany.
- *Pomiar stylu życia:* dużo braków, brak codebooka, możliwe wartości domyślne. Bloki mają różną rozdzielczość i są skorelowane, więc porównujemy je w obu kolejnościach.
- *Tagi:* sufit 9 tagów i duplikaty formatów zniekształcają podobieństwo; Jaccard zależy od liczby tagów.
- *Płeć `O`:* powstaje głównie przez zmianę płci, ma małe komórki i niejasne znaczenie.
- *Brak zdjęć:* popularność modelujemy efektem losowym, ale nie znamy jej źródła.
- *Jednorodna próba* (studenci, 18–20, kilka miast) ogranicza uogólnienie.
- *Wielość porównań:* jedna główna definicja zmiennej na blok, ustalona przed modelowaniem.

= Wykonalność w skali kursu

- *Liczności:* `y_right` ma 95~144 obserwacji, a match 487 zdarzeń. Reguła 10 zdarzeń na zmienną pozwala na ok. 47 zmiennych (dokument techniczny, próg ≥ 10). Planujemy 1–3 skalary na blok.
- *Rdzeń:* H1 i H2 na `y_right`. H3a to jeden blok więcej w tym samym modelu; H3b tylko przy wolnym czasie.
- *Przed modelowaniem:* ujednolicenie tagów, cechy as-of, filtr Hyderabad.
- *Podział zadań na M2 i M3:* #tbc

Pytań do dostawcy nie da się zadać przed kartą, więc otwarte kwestie opisujemy scenariuszami:

#table(
  columns: (0.75fr, 1.25fr),
  table.header([*Kwestia*], [*Jeśli…, to…*]),
  [Działanie feedu (filtry, ranking, widoczność lajka)], [Jeśli feed filtruje płeć lub wiek, H2 opisuje ustawienia filtrów, a efekty są zaniżone. Jeśli jest losowy, opisuje preferencje w obserwowanej puli.],
  [Widoczność tagów i bio na karcie], [Jeśli są niewidoczne, brak efektu w H1 lub H3 nie oznacza braku znaczenia, a hipoteza staje się nietestowalna.],
  [246 matchy z jednym swipe'em; Superlajk (2310 rozmów)], [Jeśli braki są losowe, model na 487 matchach jest reprezentatywny. Jeśli nie, zawężamy wniosek o matchu i sprawdzamy wrażliwość.],
  [Kody pól stylu życia; domyślne `cleanliness`/`noise_level`], [Jeśli to wartości domyślne, wyłączamy te pola. Bez codebooka używamy tylko zgodności równości.],
  [Znaczenie `O`, zmiany płci], [Jeśli `O` to artefakt, wyniki dla `O` podajemy tylko opisowo.],
  [Dzień zerowy; swipe'y z dnia pierwszej wersji i wcześniejsze], [Jeśli v1 powstaje przy rejestracji, przypisanie v1 jest poprawne. Jeśli nie, opieramy się na wrażliwości dla `prior_version`.],
)

= Dane osobowe i ujawnienie użycia AI

*Dane osobowe*
- Bio przetwarzamy tylko zagregowanie, bez wyświetlania treści.
- Przesiew regułami w wersjach bio: cyfry w 9,27% wersji, `@` lub link w 1 wersji, ciągów 9+ cyfr brak. Pełny audyt przed użyciem tekstu.
- NLP tylko lokalnie, bez zewnętrznych API. Dane nie trafiają do repozytorium, a raport pokazuje tylko agregaty.

*Użycie AI*
- Kartę przygotował agent Claude Code według decyzji zespołu (`docs/prompts/m1-generation-plan.md`). Review zespołu: #tbc
- Wcześniejsze użycie AI opisuje `docs/ai-disclosure.md`, a logi sesji leżą w `logs/ai/`.
