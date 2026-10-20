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
  align: left,
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

#show figure.where(kind: table): set figure.caption(position: top)
#let tabfig(body, cap, placement: auto) = figure(body, caption: cap, kind: table, supplement: [Tab.], placement: placement)
// Keeps a bold subheading together with its list on one page
#let keep(body) = block(breakable: false, width: 100%, body)

// Entity-relationship diagram drawn from data/tables_metadata.json (no data involved).
// Fixed geometry: three columns of 5.4cm on an 18.1cm text width; rows 0.34cm, headers 0.6cm.
#let er-rh = 0.34cm
#let er-hh = 0.6cm
#let er-w = 5.4cm
#let er-key(t) = text(fill: c-purple-ink, weight: "bold", size: 5.8pt, t)
#let er-note(t) = text(fill: c-gray, size: 5.8pt, t)
#let erbox(title, count, rows, accent) = block(
  width: er-w, fill: white, radius: 5pt, stroke: 0.5pt + c-hair, clip: true, spacing: 0pt,
  {
    set block(spacing: 0pt)
    block(width: 100%, height: er-hh, fill: accent, inset: (x: 6pt), align(horizon, text(
      fill: white,
      size: 7.5pt,
    )[#text(weight: "bold", title) #h(1fr) #count]))
    for (name, tag) in rows {
      block(width: 100%, height: er-rh, inset: (x: 6pt), align(horizon, text(size: 6.5pt)[#raw(name) #h(1fr) #tag]))
    }
    block(height: 0.1cm)
  },
)
#let at(x, y, body) = place(top + left, dx: x, dy: y, body)
#let seg(x1, y1, x2, y2, s) = at(0cm, 0cm, line(start: (x1, y1), end: (x2, y2), stroke: s))
#let arrow-r(x, y, paint) = at(x, y, polygon(fill: paint, (0pt, 0pt), (-4pt, -2.2pt), (-4pt, 2.2pt)))
#let arrow-l(x, y, paint) = at(x, y, polygon(fill: paint, (0pt, 0pt), (4pt, -2.2pt), (4pt, 2.2pt)))
#let pk = er-key[PK]
#let fk-u = er-key[FK → users]
#let fk-l = er-key[FK → listings]
#let t-day = er-note[dzień]

#let erd = block(width: 100%, height: 8.6cm, {
  let solid = 0.7pt + c-purple
  let dashed = (paint: c-gray, thickness: 0.7pt, dash: "dashed")
  // Left bus: swipes, matches, profile_history -> users.user_key (key consistency checked in EDA)
  let bx = 5.875cm
  seg(bx, 0.77cm, bx, 5.97cm, solid)
  for y in (0.77cm, 1.45cm, 3.87cm, 4.21cm, 5.97cm) { seg(5.4cm, y, bx, y, solid) }
  seg(bx, 0.77cm, 6.35cm, 0.77cm, solid)
  arrow-r(6.35cm, 0.77cm, c-purple)
  // Right bus: chats, listings -> users.user_key (by column name only, not checked)
  let rx = 12.225cm
  seg(rx, 0.77cm, rx, 5.21cm, dashed)
  for y in (1.11cm, 1.45cm, 1.79cm, 5.21cm) { seg(rx, y, 12.7cm, y, dashed) }
  seg(11.75cm, 0.77cm, rx, 0.77cm, dashed)
  arrow-l(11.75cm, 0.77cm, c-gray)

  at(0cm, 0cm, erbox("swipes", "116 414", (
    ("user_key", fk-u),
    ("target_type", er-note[profile / listing]),
    ("target_user_key", fk-u),
    ("target_listing_key", fk-l),
    ("direction", er-note[left / right]),
    ("day", t-day),
  ), c-blue))
  at(0cm, 3.1cm, erbox("matches", "733", (
    ("user_a_key", fk-u),
    ("user_b_key", fk-u),
    ("day", t-day),
  ), c-blue))
  at(0cm, 5.2cm, erbox("profile_history", "4508 wersji", (
    ("user_key", fk-u),
    ("version", er-note[1 = utworzenie]),
    ("change_type", er-note[created / updated]),
    ("day", t-day),
    ("changed_fields", er-note[lista pól]),
    ("+ 17 pól profilu", er-note[snapshot jak w users]),
  ), c-gray))
  at(6.35cm, 0cm, erbox("users", "2065", (
    ("user_key", pk),
    ("sex", er-note[F / M / O]),
    ("age_band", er-note[pasmo wieku]),
    ("city", none),
    ("daily_routine", er-note[styl życia]),
    ("lifestyle", er-note[styl życia]),
    ("work_from_home", er-note[styl życia]),
    ("cleanliness", er-note[styl życia]),
    ("noise_level", er-note[styl życia]),
    ("smoking", er-note[styl życia]),
    ("alcohol", er-note[styl życia]),
    ("interests", er-note[tagi (JSON)]),
    ("budget", none),
    ("room_type", none),
    ("search_goal", none),
    ("move_in_month_offset", none),
    ("bio", er-note[tekst]),
    ("bio_length", none),
  ), c-purple))
  at(12.7cm, 0cm, erbox("chats", "2742", (
    ("chat_key", pk),
    ("user_a_key", fk-u),
    ("user_b_key", fk-u),
    ("first_sender_key", fk-u),
    ("from_match", er-note[bool]),
    ("source_listing_key", fk-l),
    ("chat_created_day", t-day),
    ("first_message_day", t-day),
    ("hours_to_first_message", er-note[godziny]),
  ), c-pink.darken(15%)))
  at(12.7cm, 4.1cm, erbox("listings", "294", (
    ("listing_key", pk),
    ("owner_key", fk-u),
    ("city", none),
    ("district", none),
    ("listing_kind", er-note[room / entire]),
    ("occupants_count", none),
    ("rooms_offered", none),
    ("min_price", none),
    ("max_price", none),
    ("is_active", er-note[bool]),
    ("created_day", t-day),
  ), c-gray))
})

// Title: eyebrow with a purple dot, two-line headline, payoff line in the brand gradient
#block(below: 0.9em)[
  #text(size: 9pt, weight: "semibold", fill: c-purple-ink)[#box(baseline: -0.15em, circle(radius: 3pt, fill: c-purple)) #h(0.3em) Analiza Mediów Cyfrowych · kamień milowy M1]
  #v(0.2em)
  #set par(leading: 0.3em)
  #text(size: 20pt, weight: 800, tracking: -0.025em, fill: c-black)[Karta eksploracji danych] \
  #text(size: 20pt, weight: 800, tracking: -0.025em, fill: brand-gradient)[Co przewiduje prawy swipe w RentFriends?]
  #v(0.15em)
  #text(size: 9pt, weight: "medium")[Zespół: Dominik Czech, Michał Jankowski, Jakub Smolarczyk, 2026-10-20]
  #v(0.05em)
  #text(size: 9pt, weight: "medium")[Repozytorium: https://github.com/banacchini/digital-media-analysis]
]


#block(fill: c-tint, inset: 9pt, radius: 10pt, width: 100%, text(size: 8pt)[
  *Podstawa liczb:* zapisane wyniki notebooków (`EDA`, `users_overview`, `profile_history_overview`) i dokument techniczny (`docs/rentfriends_hipotezy_karta_eksploracji.md`). Liczby są *sprzed filtra Hyderabad (45 kont)* i sprzed wersjonowania profili, więc płeć, wiek i miasto pochodzą z bieżącej tabeli `users`.
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
  [CI efektu obejmuje 0 po kontroli kompletności profilu i popularności. H3b (treść bio) tylko przy wolnych zasobach.],
)
#text(size: 8pt)[Dawne ID (dokument techniczny, notebooki): H1 = H1, H2 = H2, H3 = *H5*. H3 jest dodatkowa, bo zakres części NLP jest niepewny.#footnote[Odrzuciliśmy dwie hipotezy wymagające kolejności zdarzeń w ciągu dnia (dopasowanie dwustronne, zgodność selektywności; dawne H3 i H4). Dane mają tylko `day`, a po filtrach zostaje 2308 par i 87 matchy.]]

= Źródła danych

Zanonimizowany eksport z RentFriends z losowymi identyfikatorami `user_key`. Nie używamy innych platform ani scrapingu.

- *Właściciel, warunki użycia, data otrzymania:* opisze je data statement (w przygotowaniu).
- *Struktura:* sześć tabel powiązanych kluczami użytkownika i ogłoszenia (@rys-erd); kolumny opisują @tab-users, @tab-hist i @tab-events.
- *Spójność kluczy:* `user_key` łączy `users`, `swipes` i `matches`; 100% swipe'ów na ogłoszenia łączy się z `listings`; zduplikowanych swipe'ów jest 0; match pokrywa się z wzajemnym prawym swipe'em w 99,95%.
- *Czas:* tylko numer dnia `day` (swipe'y: dni 1–113), bez godzin.

#figure(
  erd,
  kind: image,
  placement: auto,
  caption: [Schemat tabel i powiązań kluczy (wszystkie kolumny według `data/tables_metadata.json`; `profile_history` powtarza 17 pól profilu z `users`). W nagłówkach liczba wierszy: `swipes` = 95~144 na profile + 21~270 na ogłoszenia. Linia ciągła: spójność kluczy sprawdzona w EDA. Linia przerywana: powiązanie według nazw kolumn, niesprawdzone. Relacje z `listings` (FK → listings) nie są narysowane; swipe'y na ogłoszenia łączą się z `listings` w 100%. Liczności sprzed filtra Hyderabad.],
  supplement: [Rys.],
) <rys-erd>


= Zakres próby

- *Jednostka:* swipe A→B na profil, a dla matcha para {A, B}. Użytkownik występuje w wielu parach, więc foldy i bootstrap robimy po użytkownikach.
- *Próba główna* (bez progu aktywności i bez wykluczania kont skrajnych): 1583 swipujących z 2065 użytkowników, 95~144 swipe'ów, 7790 par z decyzją obu stron, 487 matchy. 246 matchy z jednym swipe'em jest poza modelem.
- *Wykluczenie:* 45 kont z Hyderabad (anomalia dla polskiej aplikacji) wraz z ich swipe'ami. Kategoria „inne” zostaje.
- *Wrażliwość:* próg ≥ 10 swipe'ów daje 7538 par i 470 matchy. Bez kont skrajnych (18 z samymi prawymi, 359 z samymi lewymi swipe'ami) zostaje 5527 par.
- *Jednorodność:* `student` ma 55% użytkowników, pasmo 18–20 54%, `search_goal` = LR 92%. Miasta: Wrocław 34%, „inne” 28%, Warszawa 15%.

= Wyniki wstępnej eksploracji

Opis bez wnioskowania. Dane wstępne: bieżąca płeć z `users`, surowe tagi, z Hyderabad.

*Struktura tabel* (@tab-users, @tab-hist, @tab-events). Znaczenia kolumn pochodzą z notebooków `users_overview` i `profile_history_overview`, typy z `data/tables_metadata.json`, a braki z `users_overview` (sekcja 3).

#tabfig(
  table(
    columns: (3.9cm, 1fr, 1.9cm, 1fr),
    table.header([*Kolumny*], [*Znaczenie*], [*Braki*], [*Uwagi*]),
    [`user_key`], [pseudonimizowany identyfikator (UUID)], [0%], [unikalny w tabeli],
    [`sex`], [płeć: F / M / O], [0%], [`O` ma 73 osoby],
    [`age_band`], [pasmo wieku (18–20 … 36+), nie lata], [0,4%], [6 pasm],
    [`city`], [miasto; „inne” = pozostałe], [0%], [10 wartości, w tym Hyderabad (45 kont)],
    [`daily_routine`, `lifestyle`, `work_from_home`, `smoking`, `alcohol`], [kody stylu życia], [73,8–81,1%], [brak codebooka],
    [`cleanliness`, `noise_level`], [kody stylu życia], [1,0% / 1,2%], [brak codebooka; możliwa wartość domyślna],
    [`interests`], [lista tagów JSON (0–9)], [0%], [2,57% pustych list; 124 surowe ciągi],
    [`budget`], [miesięczny budżet], [86,0%], [wartości skrajne do sprawdzenia],
    [`room_type`, `search_goal`], [kody (`SN`/`SH`; `LR`/`HA`)], [78,6% / 0%], [znaczenie do potwierdzenia; LR 92%],
    [`move_in_month_offset`], [miesiące do przeprowadzki], [88,1%], [są wartości ujemne],
    [`bio`, `bio_length`], [opis i jego długość w znakach], [46,6% / 0%], [treść niewyświetlana; sufit 250],
  ),
  [Kolumny tabeli `users` (2065 profili, 18 kolumn), stan bieżący z eksportu.],
) <tab-users>

#tabfig(
  table(
    columns: (3.9cm, 1fr, 1fr),
    table.header([*Kolumny*], [*Znaczenie*], [*Uwagi*]),
    [`user_key`], [identyfikator jak w `users`], [2056 użytkowników; 9 z `users` bez historii],
    [`version`], [numer wersji użytkownika, 1 = utworzenie], [maks. 30],
    [`change_type`], [`created` (tylko wersja 1) lub `updated`], [2056 utworzeń, 2452 aktualizacji],
    [`day`], [numer dnia wersji; data początkowa nieznana], [dni 2–113],
    [`changed_fields`], [pola zmienione względem poprzedniej wersji], [nie odnotowuje `sex`; `city` 541 razy przy 303 zmianach],
    [17 pól profilu, w tym `bio`], [pełny snapshot profilu w danej wersji], [ostatnia wersja zgodna z `users` w 100% pól],
  ),
  [Kolumny tabeli `profile_history` (4508 wersji, 22 kolumny).],
) <tab-hist>

#tabfig(
  table(
    columns: (1.8cm, 6cm, 1fr),
    table.header([*Tabela*], [*Kolumny*], [*Znaczenie i uwagi*]),
    table.cell(rowspan: 4)[`swipes`], [`user_key`], [nadawca swipe'a],
    [`target_type`, `target_user_key`, `target_listing_key`], [cel: profil (odbiorca) albo ogłoszenie],
    [`direction`], [`left` / `right`; prawe: 20,49% swipe'ów na profile],
    [`day`], [numer dnia (1–113), bez godzin],
    table.cell(rowspan: 2)[`matches`], [`user_a_key`, `user_b_key`], [para; 487 z 733 matchy ma zapisane oba swipe'y],
    [`day`], [dzień matcha (4–113)],
    table.cell(rowspan: 4)[`chats`], [`chat_key`, `user_a_key`, `user_b_key`, `first_sender_key`], [rozmowa, para i osoba, która napisała pierwsza; bez treści],
    [`from_match`, `source_listing_key`], [źródło: match (269) albo ogłoszenie (163); 2310 bez obu],
    [`chat_created_day`, `first_message_day`], [dni (4–113)],
    [`hours_to_first_message`], [godziny do pierwszej wiadomości: jedyna miara czasu poniżej dnia],
    table.cell(rowspan: 4)[`listings`], [`listing_key`, `owner_key`], [ogłoszenie i jego właściciel],
    [`city`, `district`, `listing_kind`], [lokalizacja; `room` / `entire`],
    [`occupants_count`, `rooms_offered`, `min_price`, `max_price`, `is_active`], [`min_price`: mediana 1750, maks. 500~000 (do czyszczenia)],
    [`created_day`], [dzień utworzenia (12–113)],
  ),
  [Kolumny tabel zdarzeń i ogłoszeń. Typy: klucze UUID, dni jako liczby całkowite.],
) <tab-events>

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
    - *Rozmowy:* 2742, z czego 269 z matcha, 163 z ogłoszenia, a 2310 bez obu (do skonsultowania z dostawcą).
    - *Ten sam dzień:* 1220 z 7790 par (15,66%) zdecydowało tego samego dnia.
  ],
)

#keep[
*Aktywność* (@rys-akt)
- Mediana 26 swipe'ów na użytkownika (średnia 60,1; p95 ≈ 250; maks. 646). 231 kont (14,59%) ma mniej niż 5 swipe'ów.
- Selektywność (odsetek prawych): mediana 4,4%, średnia 17,4%.
- Duże różnice między użytkownikami uzasadniają efekty losowe i wrażliwość na konta skrajne.
]

*Styl życia i tagi, H1* (@rys-tagi, @rys-pola)

#block(fill: c-tint, inset: 8pt, radius: 8pt, width: 100%, stroke: (left: 2.5pt + c-purple))[
  *Styl życia jest zapisany w dwóch miejscach:* w 7 polach strukturalnych, które są w większości puste, i w tagach `interests`, które mieszają styl życia z hobby i statusem. Bez rozdzielenia tagów blok „zainteresowań” w H1 mierzyłby po części styl życia.
]

- *Pola strukturalne:* pięć pól stylu życia ma 74–81% braków. `cleanliness` i `noise_level` mają tylko 1,0% i 1,2% braków, ale dominująca kategoria ma 53,0% i 50,4%, co może być wartością domyślną. Kody nie mają codebooka.
- *Tagi `interests` to nie tylko zainteresowania:* wśród 10 najczęstszych tagów 6 opisuje styl życia (np. `non_smoker` 809, `likes_calm` 636, `night_owl` 569 użytkowników), 1 status (`student`, 1143), a tylko 2 to hobby (`cooking`, `movies_cinema`).
- *Ta sama cecha w dwóch miejscach:* tag `non_smoker` ma 809 użytkowników, a pole `smoking` jest puste u 1637 (79,3%). Podobne pary: `quiet_after_22`/`quiet_evenings` i `noise_level`, `loves_cleanliness` i `cleanliness`.
- *Skutek dla H1:* Jaccard tagów w 733 matchach (średnia 0,146, mediana 0,125) liczono na surowych tagach, więc obejmuje też styl życia i status. Przed modelem dzielimy tagi (D12), polu dajemy pierwszeństwo przed tagiem (D13) i ujednolicamy formaty.
- *Formaty tagów:* 124 surowe ciągi, w tym 54 formy emoji obok snake_case. 256 użytkowników ma oba formaty (159 z nich na limicie 9). 57% ma 9 tagów, 2,57% żadnego.

#let c-open = c-gray.lighten(60%)
#let tag-rows = (
  ("student", 1143, c-gray),
  ("non_smoker", 809, c-purple),
  ("likes_calm", 636, c-purple),
  ("extrovert", 598, c-purple),
  ("night_owl", 569, c-purple),
  ("values_privacy", 492, c-open),
  ("introvert", 470, c-purple),
  ("cooking", 455, c-blue),
  ("likes_pets", 452, c-purple),
  ("movies_cinema", 436, c-blue),
)
#let swatch(c, t) = box[#box(width: 7pt, height: 7pt, radius: 2pt, fill: c, baseline: 0.5pt) #h(1pt) #t]
#let chip(t, fill: c-tint, ink: c-purple-ink) = box(fill: fill, radius: 1em, inset: (x: 4pt, y: 1.5pt), text(fill: ink, size: 6.5pt, raw(t)))
#let stat(n, label) = block(width: 100%, fill: c-bg, radius: 6pt, inset: 6pt)[
  #text(size: 15pt, weight: 800, fill: c-black, n) \
  #text(size: 6.5pt, label)
]
#let card(body) = block(fill: white, radius: 8pt, stroke: 0.5pt + c-hair, inset: 8pt, width: 100%, height: 6.3cm, body)

#figure(
  kind: image,
  placement: auto,
  supplement: [Rys.],
  grid(
    columns: (1fr, 1fr),
    column-gutter: 10pt,
    card({
      set text(size: 7pt)
      set par(justify: false, leading: 0.5em)
      text(weight: "bold", fill: c-black)[10 najczęstszych tagów `interests`]
      linebreak()
      text(size: 6.5pt)[liczba użytkowników (n = 2065); kolor: proponowany podział]
      v(4pt)
      grid(
        columns: (2.3cm, 1fr),
        row-gutter: 4pt,
        column-gutter: 5pt,
        ..tag-rows
          .map(((t, n, c)) => (
            align(right + horizon, text(size: 6.5pt, raw(t))),
            align(horizon)[#box(width: 80% * n / 1143, height: 8pt, radius: 2pt, fill: c) #h(2pt) #text(size: 6.5pt)[#n]],
          ))
          .flatten(),
      )
      v(5pt)
      text(size: 6.5pt)[#swatch(c-purple)[styl życia (6)] #h(5pt) #swatch(c-gray)[status (1)] #h(5pt) #swatch(c-blue)[hobby (2)] #h(5pt) #swatch(c-open)[do ustalenia (1)]]
    }),
    card({
      set text(size: 7pt)
      set par(justify: false, leading: 0.5em)
      text(weight: "bold", fill: c-black)[Ta sama cecha w tagu i w polu]
      linebreak()
      text(size: 6.5pt)[tag `interests` #h(1fr) pole strukturalne (braki)]
      v(4pt)
      grid(
        columns: (1fr, auto, auto),
        row-gutter: 6pt,
        column-gutter: 5pt,
        align: (right + horizon, center + horizon, left + horizon),
        [#chip("non_smoker") #chip("smoker") #chip("vapes")], text(fill: c-purple, size: 9pt)[⟷], [#chip("smoking", fill: luma(235), ink: c-black) #text(size: 6.5pt)[79,3%]],
        [#chip("quiet_after_22") #chip("quiet_evenings")], text(fill: c-purple, size: 9pt)[⟷], [#chip("noise_level", fill: luma(235), ink: c-black) #text(size: 6.5pt)[1,2%]],
        [#chip("loves_cleanliness")], text(fill: c-purple, size: 9pt)[⟷], [#chip("cleanliness", fill: luma(235), ink: c-black) #text(size: 6.5pt)[1,0%]],
      )
      v(1fr)
      grid(
        columns: (1fr, 1fr),
        column-gutter: 6pt,
        stat[809][użytkowników z tagiem `non_smoker`],
        stat[1637][użytkowników z pustym polem `smoking` (79,3%)],
      )
    }),
  ),
  caption: [Styl życia w tagach `interests` i w polach strukturalnych. Lewy: 10 najczęstszych surowych tagów (`EDA`, „Analiza zainteresowań”). Kolor to wstępny podział według D12, D15 i dokumentu technicznego (`values_privacy` nieprzypisany); `cooking` i `movies_cinema` jako hobby to propozycja przed zamrożeniem codebooka. Prawy: pary tag–pole wskazane w dokumencie technicznym (H1, plan pomiaru) i braki pól z `users_overview`. Liczności tagów pozostałych par nie były liczone. Surowe tagi z duplikatami formatów, z Hyderabad.],
) <rys-tagi>

#keep[
*Demografia, H2* (@rys-plec, @rys-wiek)
- Ta sama vs różna płeć: kobiety 20,1% vs 9,2% (F→M 8,7%, CI 8,3–9,1%), mężczyźni 19,5% vs 28,9% (M→F 29,2%).
- Żadna komórka nie jest bliska zeru. Komórki z `O` są małe (O→O: 98 swipe'ów).
- Wiek: to samo vs różne pasmo daje 21,2% vs 20,0%, ale liczy się kierunek: 18–20 → 18–20 20,4%, 18–20 → 27–30 6,6%. 65% wyświetleń dotyczy profili 18–20.
]

#keep[
*Bio, H3*
- Bio ma 1102 z 2065 profili (53,4%). Mediana 81 znaków (IQR 33–153), sufit 250.
- P(prawy): 21,5% dla odbiorców z bio, 19,2% bez bio (bez kontroli; wykres: `EDA`, „Bio”).
]

#keep[
*Wersje profilu*
- 4508 wersji; ostatnia zgadza się z `users` w 100% pól.
- Płeć zmieniło 87 użytkowników (101 zmian, 65 do `O`), wiek 12, miasto 118. `changed_fields` pomija zmiany płci, więc porównujemy snapshoty.
- Swipe'y względem wersji: 54~597 (46,9%) z dnia pierwszej wersji, 61~118 (52,5%) z wcześniejszą wersją, 551 przed pierwszą, 148 bez historii. Liczone na 116~414 swipe'ach razem z ogłoszeniami. #recalc[dla 95~144 swipe'ów na profile]
]

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

#keep[
*Wersja profilu w dniu swipe'a.* Każdy swipe dostaje flagę źródła:
- `prior_version`: swipe po dniu pierwszej wersji, czyli ostatnia wersja sprzed dnia swipe'a;
- `first_version`: swipe z dnia pierwszej wersji lub wcześniejszy, czyli wersja v1;
- `users_current`: 9 użytkowników bez historii, czyli bieżący `users`.
]

#keep[
*Bloki zmiennych* (1–3 skalary na blok, D16)
- *Demografia:* płeć nadawcy × odbiorcy (`O` jako osobna kategoria), ta sama płeć, różnica pasm wieku ze znakiem i to samo pasmo (pasma 27+ połączone).
- *Styl życia:* zgodność 7 pól, gdy obie strony je wypełniły („brak danych” jako kategoria); konflikt kierunkowy tagów (np. `non_smoker` vs `smoker`/`vapes`); liczba wspólnych tagów. Pole ma pierwszeństwo przed tagiem, a tag uzupełnia braki.
- *Zainteresowania:* tagi hobby po ujednoliceniu i deduplikacji, czyli Jaccard i liczba tagów. `student` to status; zwierzęta i `extrovert`/`introvert` należą do stylu życia.
- *Bio (H3a):* pusty/niepusty, długość liczona z tekstu.
]

#keep[
*Model i testy*
- Regresja logistyczna dla `y_right`; match w modelu drugorzędnym (7790 par).
- Estymator: regresja logistyczna z krzyżowymi efektami losowymi (wyraz wolny nadawcy i odbiorcy) dla H2 i H3. Dla H1 pooled logit z błędami klastrowanymi dwukierunkowo (nadawca, odbiorca), oceniany w foldach po użytkownikach. Jeśli GLMM nie osiągnie zbieżności, H2 i H3 liczymy pooled logitem z klastrowaniem dwukierunkowym, a H3 raportujemy bez twierdzenia o kontroli popularności.
- Kontrole: `same_city` (trzy poziomy: to samo miasto / inne / nieznane dla „inne”). Popularność i hojność jako efekty losowe odbiorcy i nadawcy w GLMM.
- Walidacja w foldach po użytkownikach; metryki logloss, AUC, AUC-PR.
- *H1:* ΔlogLoss i ΔAUC po dodaniu bloku, w obu kolejnościach, z CI z bootstrapu po użytkownikach i baseline'em z tasowania bloku. Analiza per pole jest drugorzędna.
- *H2:* iloraz szans z CI. *H3:* efekt bio z kontrolą liczby tagów i kompletności profilu.
]

#keep[
*Instrument AI*
- Normalizacja tagów (124 surowe ciągi, w tym 54 formy emoji → kanoniczne snake_case): agent generuje mapowanie, człowiek je przegląda i poprawia. Miara: odsetek mapowań poprawionych przez człowieka, z listą korekt.
- Podział tagów (styl życia / status / hobby / do ustalenia): agent proponuje etykiety, człowiek etykietuje niezależnie, bez wglądu w propozycje agenta. Miara: κ Cohena agent–człowiek z 95% CI (bootstrap po tagach), uzupełniona o odsetek zgodności i macierz pomyłek.
- Propozycje agenta zapisujemy przed zamrożeniem codebooka. Wersję końcową ustala człowiek, a rozbieżności są raportowane, nie ukrywane.
- Ewentualne NLP w H3: gold standard z ręcznie oznaczonej próbki, lokalnie. Rozmiar próbki i adnotatorzy są nieustaleni.
]

#keep[
*Analizy wrażliwości*
+ Próg ≥ 10 swipe'ów i bez kont skrajnych.
+ Tylko swipe'y z `prior_version`; cechy z bieżącego `users`.
+ Z kontami Hyderabad.
+ Bez kategorii „brak danych” oraz bez `cleanliness`/`noise_level`.
+ Dla matcha: z 246 matchami z jednym swipe'em.
]

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

#tabfig(
  table(
    columns: (2.7cm, 1fr, 1fr),
    table.header([*Osoba i rola*], [*M2: raport z metodologią i pierwszymi wynikami*], [*M3: plakat, notatka, prezentacja i obrony*]),
    [Dominik Czech \ lead badawczy],
    [pytanie, hipotezy i spójność wniosku; próbny fit estymatora (GLMM); *analiza H2* (iloraz szans z CI)],
    [główny wynik i wniosek na plakacie; notatka dla odbiorcy spoza zespołu; *wrażliwość 5* (match z 246 matchami z jednym swipe'em)],
    [Michał Jankowski \ inżynier danych],
    [data statement, zgodność z RODO i regulaminami, filtr Hyderabad; cechy as-of i flagi wersji profilu; przeliczenie liczb na 95~144 swipe'ach; reguła foldów dla par],
    [*analiza H3* (bio); *wrażliwość 2 i 3* (`prior_version`; z Hyderabad); sekcja o danych i ograniczeniach na plakacie],
    [Jakub Smolarczyk \ inżynier pipelinu],
    [codebook, normalizacja i podział tagów, gold standard, κ agent–człowiek, analiza błędów; *analiza H1* (ΔlogLoss, ΔAUC, bootstrap po użytkownikach, tasowanie bloku)],
    [*wrażliwość 1 i 4* (próg ≥ 10 i bez kont skrajnych; bez „brak danych” oraz bez `cleanliness`/`noise_level`); wizualizacje H1 z CI],
  ),
  [Podział zadań na M2 i M3. Analizy wrażliwości numerowane jak w sekcji 5.],
  placement: none,
) <tab-podzial>

#keep[
Pytań do dostawcy nie da się zadać przed kartą, więc otwarte kwestie opisujemy scenariuszami:

#table(
  columns: (0.75fr, 1.25fr),
  table.header([*Kwestia*], [*Jeśli…, to…*]),
  [Działanie feedu (filtry, ranking, widoczność lajka)], [Jeśli feed filtruje płeć lub wiek, H2 opisuje ustawienia filtrów, a efekty są zaniżone. Jeśli jest losowy, opisuje preferencje w obserwowanej puli.],
  [Widoczność tagów i bio na karcie], [Jeśli są niewidoczne, brak efektu w H1 lub H3 nie oznacza braku znaczenia, a hipoteza staje się nietestowalna.],
  [246 matchy z jednym swipe'em; rozmowy bez matcha (2310)], [Jeśli braki są losowe, model na 487 matchach jest reprezentatywny. Jeśli nie, zawężamy wniosek o matchu i sprawdzamy wrażliwość.],
  [Kody pól stylu życia; domyślne `cleanliness`/`noise_level`], [Jeśli to wartości domyślne, wyłączamy te pola. Bez codebooka używamy tylko zgodności równości.],
  [Znaczenie `O`, zmiany płci], [Jeśli `O` to artefakt, wyniki dla `O` podajemy tylko opisowo.],
  [Dzień zerowy; swipe'y z dnia pierwszej wersji i wcześniejsze], [Jeśli v1 powstaje przy rejestracji, przypisanie v1 jest poprawne. Jeśli nie, opieramy się na wrażliwości dla `prior_version`.],
)
]

= Dane osobowe i ujawnienie użycia AI

#keep[
*Dane osobowe*
- Bio przetwarzamy tylko zagregowanie, bez wyświetlania treści.
- Przesiew regułami w wersjach bio: cyfry w 9,27% wersji, `@` lub link w 1 wersji, ciągów 9+ cyfr brak. Pełny audyt przed użyciem tekstu.
- NLP tylko lokalnie, bez zewnętrznych API. Dane nie trafiają do repozytorium, a raport pokazuje tylko agregaty.
]

#keep[
*Użycie AI*
- Kartę przygotował agent Claude Code według decyzji zespołu (`docs/prompts/m1-generation-plan.md`). Review zespołu: Dominik Czech 20.10.2026 3:42.
- Wcześniejsze użycie AI opisuje `docs/ai-disclosure.md`, a logi sesji leżą w `logs/ai/`.
]
