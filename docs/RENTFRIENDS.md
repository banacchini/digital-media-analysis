# RentFriends: baza wiedzy projektu

**Kurs:** Analiza Mediów Cyfrowych
**Temat:** RentFriends, aplikacja typu tinder do dopasowywania współlokatorów
**Status dokumentu:** wersja robocza, aktualizowana wraz z postępem prac
**Data ostatniej aktualizacji:** 2026-10-12
**Zakres:** ustalenia dotyczące samego projektu. Zasady kursu nie są tu powtarzane.

---

## 1. Pytanie badawcze

**Pytanie wyjściowe:** Jakie parametry wpływają na decyzję o wspólnym wynajęciu mieszkania?

**Ocena:** pytanie jest zbyt szerokie, żeby je zweryfikować. Wymaga zawężenia do jednej rodziny cech i mierzalnego proxy. Sama decyzja o wspólnym wynajęciu nie jest obserwowalna w danych aplikacji.

**Przykład zawężonej hipotezy (roboczy, nieprzyjęty):**
> Zgodność deklarowanego stylu życia (np. palenie, zwierzęta, godziny snu, czystość w bio) zwiększa prawdopodobieństwo wzajemnego matcha bardziej niż zgodność wieku i zainteresowań, przy kontroli płci.

**Pomysł na rozszerzenie (do decyzji zespołu):** czy wpływ zgodności stylu życia zależy od ciasnoty lokalnego rynku mieszkaniowego. Wymaga danych kontekstowych (patrz sekcja 7).

---

## 2. Dane

### 2.1 Dane dostarczone przez RentFriends (zanonimizowane)

- **Profile:** zainteresowania, styl życia, płeć, wiek, opis z bio.
- **Akcje użytkowników:**
  - swipe na inne profile (w prawo / w lewo),
  - swipe na ogłoszenia mieszkań (w prawo / w lewo),
  - matche,
  - pierwszy kontakt na czacie (z kim użytkownik zaczął pisać).

### 2.2 Co jest nieznane

- Czy ogłoszenia mają atrybuty (cena, lokalizacja, metraż), czy tylko identyfikatory.
- Czy identyfikatory użytkowników są spójne między tabelami profili i akcji. Bez tego nie da się połączyć par ani swipe'ów z profilami.
- Zawartość bio pod kątem danych bezpośrednich (imiona, numery telefonów, linki do social media).

### 2.3 Jednostka analizy

**Para użytkowników (A, B).**
- Swipe jest zdarzeniem skierowanym A→B.
- Match to wzajemny swipe w prawo (A→B i B→A).
- Lejek: swipe → match → czat.

### 2.4 Proxy zmiennej wynikowej

Decyzja o wspólnym wynajęciu nie jest obserwowana. Dostępne proxy:

1. **Match** (wzajemny swipe w prawo na profilach). Sygnał dopasowania między osobami, ale nie chęci wspólnego wynajęcia.
2. **Współzainteresowanie tym samym ogłoszeniem** (oboje swipnęli w prawo to samo ogłoszenie). Bliższe pytaniu o wspólne mieszkanie. Warto sprawdzić, czy wyniki dla obu proxy są podobne.

**Ograniczenie do zapisania w karcie:** żadne proxy nie jest równoważne decyzji o wspólnym wynajęciu.

---

## 3. Plan metodologiczny (wstępny)

- **Eksploracja (do wykonania):** liczba użytkowników, profili, swipe'ów na profile i na ogłoszenia, matchów i czatów; rozkład swipe'ów na użytkownika; odsetek matchów według pary płci i przedziału różnicy wieku; braki (puste bio, niekompletne pola); liczba unikalnych ogłoszeń i liczba osób swipujących każde z nich.
- **Dane zależne:** ten sam użytkownik występuje w wielu parach. Podział train/test po użytkownikach albo błędy standardowe klastrowane po użytkownikach.
- **Model:** regresja logistyczna dla matcha z cechami podobieństwa (np. Jaccard dla zainteresowań, różnica wieku, wskaźnik tej samej płci, wynik zgodności stylu życia). Kierunek swipe'ów modelowany osobno.
- **Test z kontrolą:** rozkład zerowy przez losowe tasowanie par. Efekt nieodróżnialny od rozkładu zerowego jest wynikiem negatywnym, który jest pełnoprawnym rezultatem.
- **Miara jakości:** nie F1 modelu. Miarą jest zakres i pewność wniosku.

---

## 4. Ryzyka do przygotowania na red teaming

- **Selekcja:** do aplikacji trafiają aktywni użytkownicy, więc wyniki nie generalizują się na wszystkich szukających współlokatorów.
- **Homofilia a preferencje:** wysoki efekt podobieństwa może wynikać z tego, że użytkownicy swipują osoby podobne demograficznie, a nie z dopasowania stylu życia.
- **Asymetria:** A może swipować w prawo, a B nie.
- **Dane osobowe w bio:** sprawdzić i opisać w data statement. Jeśli bio nie jest oczyszczone, rozważyć użycie wyłącznie cech strukturalnych.
- **Spójność kluczy anonimizacji:** potwierdzić przed analizą.

---

## 5. Alternatywne źródła danych (ocena legalności)

Żadna z poniższych platform nie została ocenona jako legalne źródło do scrapingu. Ocena opiera się na informacjach znalezionych w wyszukiwaniu, nie na pełnej analizie regulaminów ani prawa.

| Platforma | Kraj | Ustalenia | Status |
|---|---|---|---|
| Facebook (grupy współlokatorskie) | globalnie | Warunki Meta zakazują zautomatyzowanego zbierania bez zgody. Posty zawierają dane osób trzecich (RODO). Dostęp badawczy z DSA art. 40 dotyczy tylko bardzo dużych platform i idzie przez koordynatora (w Polsce UKE). | Odrzucone jako źródło do scrapingu |
| SpareRoom | UK | Regulamin zabrania „harvestowania" informacji i nieautoryzowanych integracji. Kontakty za logowaniem. Na Apify istnieją gotowe scrapery, ale nie zmieniają statusu prawnego. | Scraping odradzany; możliwe zapytanie do platformy |
| Erasmus Play | PL/międzynarodowy | Wyniki wyszukiwania to strony SEO bez opisu danych i regulaminu. | Nieocenione, do sprawdzenia |
| Ideal Flatmate | UK | Brak publicznego regulaminu. Jedyna droga do wyjaśnienia legalności to zapytanie mailowe. Źródło historyczne (2017), aktualność serwisu nieznana. | Do wyjaśnienia mailowego |
| WG-Gesucht | DE/AT | Udostępnia agregowane dane badawcze na zapytanie (pr@wg-gesucht.de). Brak surowych danych, pojedynczych ogłoszeń i danych osobowych. | Ścieżka możliwa (dane zagregowane) |
| Badi, Roommates.com, Roomster, Flatmates.com.au | ES/US/AU | Nie sprawdzono. | Nieocenione |
| OLX, Gratka, Otodom, pokoje.pl | PL | Nie sprawdzono regulaminów. Prawdopodobnie zakazy scrapingu. | Nieocenione, do sprawdzenia |

**Kontekst prawny (wskazówki, nie stanowisko prawne):**
- Holenderski organ ochrony danych (AP, wytyczne z 1 maja 2024) stwierdził, że scraping przez podmioty prywatne jest prawie zawsze niezgodny z RODO.
- BGH, I ZR 224/12 (2014): samo złamanie zakazu screen scrapingu w AGB nie jest automatycznie nieuczciwą konkurencją. Orzeczenie niemieckie, nie stosuje się wprost w Polsce.
- Stanowisko UODO nie zostało sprawdzone.

**Wniosek:** legalna ścieżka to zgoda platformy, zapytanie o dane zagregowane albo własna ankieta z dobrowolną zgodą. Decyzję o ścieżce podejmuje zespół, najlepiej po konsultacji z prowadzącym lub działem prawnym uczelni.

---

## 6. Dane zagregowane z WG-Gesucht (informacja)

**Co oferują:** agregowane dane o cenach ofert, podaży i popycie na WG, strukturze WG (wielkość, typ), ofertach czasowych i bezterminowych oraz szeregi czasowe dla miast.

**Zakres geograficzny:** Niemcy i Austria, m.in. Berlin i Wiedeń. Brak Polski.

**Czego nie zawierają:** swipe'ów, matchów, czatów, danych na poziomie par ani pojedynczych ogłoszeń.

**Jak wystąpić:** mail na pr@wg-gesucht.de z opisem pytania badawczego, potrzebnych cech, okresu i poziomu regionalnego.

**Możliwe rozszerzenia projektu (do decyzji):**
1. **Moderator na poziomie miasta:** wskaźniki rynkowe z WG-Gesucht jako kontekst dla efektu zgodności stylu życia. Ograniczenia: mała liczba miast, ryzyko błędu ekologicznego, inny kraj.
2. **Porównanie struktury ofert:** typy lokali z WG-Gesucht (pokój w WG, kawalerka, całe mieszkanie) jako odniesienie dla ogłoszeń w RentFriends, jeśli mają podobny podział.
3. **Porównanie PL vs DE na poziomie rynku:** tło do dyskusji, nie dowód o zachowaniach.

---

## 7. Literatura do weryfikacji

Podane przez asystenta, nie zweryfikowane w tej sesji:
- Hitsch, Hortaçsu & Ariely (2010), „Matching and Sorting in Online Dating", *American Economic Review*. Wzorzec metodologiczny (swipe'y i matche).
- Fisman, Iyengar, Kamenica & Simonson (2006). Preferencje w speed datingu.
- Literatura o wyborze współlokatorów i platformach typu SpareRoom (do wyszukania w Google Scholar): *roommate matching*, *flatmate search*, *shared housing preferences*, *online roommate platform*.

---

## 8. Stan prac i otwarte kwestie

- **M1 (karta eksploracji danych):** w przygotowaniu. Karta wymaga aktualizacji: dane z aplikacji są dostępne, więc wcześniejsze założenie o ich braku jest nieaktualne.
- **Pytanie badawcze:** do zawężenia do jednej tezy z mierzalnym wynikiem.
- **Proxy:** wybór między matchem a współzainteresowaniem ogłoszeniem, lub sprawdzenie obu.
- **Klucze anonimizacji:** do potwierdzenia u źródła.
- **Bio:** audyt danych osobowych przed analizą.
- **Zapytania mailowe:** Ideal Flatmate (legalność), WG-Gesucht (dane zagregowane), ewentualnie RentFriends (dostęp i warunki).
- **Data statement:** do przygotowania przez Inżyniera danych.

---

## 9. Dziennik pochodzenia informacji (bookkeeping)

### 9.1 Źródła internetowe konsultowane

| Data dostępu | Źródło | Do czego użyte |
|---|---|---|
| 2026-10-12 | https://www.wg-gesucht.de/de/presse/forschung-kooperationen | Zakres i warunki danych badawczych WG-Gesucht |
| 2026-10-12 | https://www.spareroom.co.uk/content/default/terms-uk | Fragment regulaminu SpareRoom (zakaz harvestowania, nieautoryzowane integracje) |
| 2026-10-12 | https://apify.com/studio-amba/spareroom-scraper | Informacja o istnieniu gotowych scraperów SpareRoom (bez oceny prawnej) |
| 2026-10-12 | https://www.flib.nl/en/?p=19015 | Wytyczne holenderskiego AP dot. scrapingu |
| 2026-10-12 | https://www.otto-schmidt.de/... (BGH I ZR 224/12) | Orzeczenie dot. screen scrapingu, kontekst niemiecki |
| 2026-10-12 | https://antyweb.pl/jak-znalezc-wspolokatora-ideal-flatmate | Opis Ideal Flatmate (artykuł z 2017 r.) |
| 2026-10-12 | https://erasmusplay.com (wyniki wyszukiwania) | Strony SEO bez danych o regulaminie |

Uwaga: część wyników wyszukiwania to strony agregujące lub SEO. Ich treść wymaga weryfikacji u źródła przed cytowaniem w raporcie.

### 9.2 Udział narzędzi AI

- Asystent AI (Claude, sesje w październiku 2026) został użyty do: wstępnego przeglądu pytania badawczego, sugestii metodologicznych, wyszukiwania i wstępnej oceny alternatywnych platform, przygotowania niniejszego dokumentu.
- Wszystkie sugestie metodologiczne, cytowania literatury i ustalenia prawne wymagają weryfikacji przez zespół przed użyciem w raporcie.
- Literatura podana przez asystenta nie została zweryfikowana w źródle.
- Zgodnie z wymaganiami kursu udział AI należy ujawnić w raporcie.

### 9.3 Zmiany w ustaleniach (korekty)

- Wcześniej zakładano, że dane z RentFriends nie będą dostępne. Po przekazaniu informacji o danych dostępnych w aplikacji założenie zostało zaktualizowane.
- Ideal Flatmate początkowo zaklasyfikowano jako platformę polską/UE. Po uzupełnieniu informacji, że działa w UK, wpis został poprawiony.

---

*Dokument przygotowany na podstawie roboczych ustaleń. Nie stanowi opinii prawnej.*
