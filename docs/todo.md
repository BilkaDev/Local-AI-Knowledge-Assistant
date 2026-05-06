# Plan prac dzien po dniu (portfolio AI integration)

Cel: dowiezc projekt Local-AI-Knowledge-Assistant do poziomu "gotowy na portfolio" z mocnym dowodem integracji AI i RAG.

## Dzien 1 - MVP i porzadek repo
- [x] Zdefiniowac MVP: chat + odpowiedz oparta o dokumenty + zrodla.
- [x] Uporzadkowac strukture folderow (`app/`, `rag/`, `data/`, `scripts/`, `tests/`).
- [x] Dodac `.gitignore` dla artefaktow lokalnych (venv, db, cache, logs).

### Debata zespolu IT (dialog decyzyjny)

- **PM:** Potrzebujemy MVP, ktore da sie pokazac rekruterowi w 2-3 minuty.
- **Backend:** Minimalny zakres to dzialajacy chat i stabilny przeplyw pytanie -> retrieval -> odpowiedz.
- **ML/RAG:** Odpowiedz musi byc oparta o dokumenty i zawsze pokazywac zrodla, inaczej nie udowodnimy RAG.
- **DevOps:** Struktura repo i `.gitignore` musza byc gotowe od razu, zeby kolejne dni nie produkowaly dlugu technicznego.
- **Decyzja koncowa:** Dzien 1 zamykamy dopiero, gdy mamy formalna definicje MVP, porzadek repo oraz `.gitignore`, a kazdy punkt ma kryteria akceptacji.

### Dzien 1 - Definition of Done (kryteria akceptacji)

- [x] **MVP jest jednoznacznie zdefiniowane**:
  - chat w UI (interfejs rozmowy),
  - odpowiedz oparta o tresc dokumentow (RAG),
  - odpowiedz zawiera co najmniej jedno zrodlo (plik/chunk).
- [x] **Struktura repo jest uporzadkowana**:
  - istnieja katalogi `app/`, `rag/`, `data/`, `scripts/`, `tests/`,
  - przeznaczenie katalogow jest opisane krotko w README.
- [x] **`.gitignore` obejmuje artefakty lokalne**:
  - srodowisko lokalne (`.venv/`, `venv/`),
  - dane runtime (`*.db`, cache, logi),
  - artefakty benchmarkow i pliki tymczasowe.

### Podsumowanie Dnia 1 (GO/NOGO na Dzien 2)

- Status MVP: [x] spelnione / [ ] brak
- Status struktury repo: [x] spelnione / [ ] brak
- Status `.gitignore`: [x] spelnione / [ ] brak
- Decyzja: [x] GO (start Dnia 2) / [ ] NOGO (uzupelnic braki)
- Uwagi koncowe: komplet Dnia 1 zamkniety; mozna startowac Dzien 2.

## Dzien 2 - Docker-first runtime i konfiguracja
- [x] Uruchomic bazowy stack przez `docker compose` (aplikacja gotowa do startu).
- [x] Przygotowac `.env.example` jako kontrakt konfiguracji kontenerow.
- [x] Wykonac smoke test "hello app" przez kontener Streamlit.
- [x] Potwierdzic health check i podstawowe logowanie kontenera.
- [x] Udokumentowac uruchomienie Docker-first oraz fallback diagnostyczny (`venv`) w README.

### Debata zespolu IT (Docker-first)

- **PM:** Priorytetem Dnia 2 jest reprodukowalny setup i jasne Definition of Done.
- **Backend:** Kontrakt `.env` musi byc jednoznaczny i stabilny pod kolejne dni.
- **ML/RAG:** Endpoint modelu i domyslne parametry musza byc gotowe pod Dzien 3.
- **DevOps:** Health check, porty i wolumeny sa wymagane do bezpiecznego startu.
- **Decyzja koncowa:** Runtime domyslny to Docker-first, a lokalny `venv` zostaje tylko jako fallback diagnostyczny.

### Podsumowanie Dnia 2 (GO/NOGO na Dzien 3)

- Status docker runtime: [x] spelnione / [ ] brak
- Status kontraktu `.env.example`: [x] spelnione / [ ] brak
- Status smoke test + health: [x] spelnione / [ ] brak
- Status notatki z debaty IT: [x] spelnione / [ ] brak
- Decyzja: [x] GO (start Dnia 3) / [ ] NOGO (uzupelnic braki)

## Dzien 3 - Ingestion dokumentow
- [x] Zaimplementowac loader PDF/TXT z katalogu `data/`.
- [x] Dodac chunking (size + overlap) i normalizacje tekstu.
- [x] Dodac prosty skrypt CLI `ingest`, ktory raportuje liczbe przetworzonych plikow.

### Debata zespolu IT (Dzien 3 - ingestion)

- **PM:** Priorytetem jest dowiezienie ingestion gotowego pod Dzien 4 bez rozszerzania scope.
- **Backend:** Potrzebny jest stabilny kontrakt CLI i raport z procesu ingest.
- **ML/RAG:** Chunking musi byc konfigurowalny (`size`, `overlap`), bo wplywa na jakosc retrieval.
- **DevOps:** Sciezki i uruchomienie musza pozostac zgodne z Docker-first.
- **Decyzja koncowa:** Realizujemy hybryde: loader-first + konfigurowalny chunking jeszcze w Dniu 3.

### Ustalone kryteria akceptacji Dnia 3

- [x] Loader obsluguje `.pdf` i `.txt` z `data/`.
- [x] Chunking dziala z parametrami konfigurowalnymi.
- [x] CLI `ingest` raportuje: liczbe plikow, chunkow i bledy.
- [x] Bledne pliki nie przerywaja calego przebiegu ingest.
- [x] Wynik ingest jest gotowy do przekazania do Dnia 4 (embeddings + ChromaDB).

Notatka szczegolowa z debaty: `docs/day3-it-debate.md`.

### Podsumowanie Dnia 3 (GO/NOGO na Dzien 4)

- Status loader + chunking: [x] spelnione / [ ] brak
- Status CLI ingest + raport: [x] spelnione / [ ] brak
- Status obslugi bledow ingest: [x] spelnione / [ ] brak
- Decyzja: [x] GO (start Dnia 4) / [ ] NOGO (uzupelnic braki)

## Dzien 4 - Embeddings i ChromaDB
- [ ] Wybrac embedding model i podlaczyc generowanie embeddingow.
- [ ] Zapisac chunki do ChromaDB z metadanymi (nazwa pliku, fragment, id).
- [ ] Zweryfikowac, ze kolekcja jest czytelna i gotowa do retrieval.

## Dzien 5 - Retrieval
- [ ] Dodac funkcje top-k podobnych fragmentow.
- [ ] Zwrocic rowniez metadane zrodlowe (plik, chunk id).
- [ ] Zalogowac czas retrieval i liczbe zwracanych chunkow.

## Dzien 6 - Integracja z Ollama
- [ ] Zbudowac prompt: kontekst + pytanie + zasady "nie zgaduj".
- [ ] Podlaczyc model Ollama i zwracac odpowiedz wraz ze zrodlami.
- [ ] Dodac fallback: komunikat gdy brak relewantnego kontekstu.

## Dzien 7 - Streamlit chat (MVP UI)
- [ ] Zrobic interfejs chatowy (historia rozmowy + `st.chat_input`).
- [ ] Pokazac zrodla pod kazda odpowiedzia.
- [ ] Dodac podstawowa obsluge bledow i loading state.

## Dzien 8 - Odswiezanie bazy wiedzy
- [ ] Dodac przycisk "Odswiez baze wiedzy".
- [ ] Podlaczyc trigger reindeksacji bez restartu aplikacji.
- [ ] Dodac komunikaty statusu: start, postep, sukces lub blad.

## Dzien 9 - Metryki (wymagane do portfolio)
- [ ] Mierzyc i zapisac: sredni czas odpowiedzi i p95.
- [ ] Raportowac liczbe dokumentow i chunkow w indeksie.
- [ ] Mierzyc osobno latency retrieval i latency generacji.

## Dzien 10 - Skutecznosc na zestawie pytan
- [ ] Przygotowac zestaw 10-20 pytan kontrolnych do dokumentow.
- [ ] Dodac oczekiwane odpowiedzi lub kryteria oceny.
- [ ] Policzyc skutecznosc i opisac wynik w README.

## Dzien 11 - Architektura i opis techniczny
- [ ] Dodac do README prosty diagram przeplywu RAG.
- [ ] Dopisac "Design decisions": dlaczego Streamlit, ChromaDB i Ollama.
- [ ] Dopisac ograniczenia i potencjalne usprawnienia.

## Dzien 12 - Evidence (materialy do rekrutacji)
- [ ] Zrobic 2-3 screenshoty interfejsu.
- [ ] Nagrac krotki GIF: dodanie dokumentu -> refresh -> pytanie -> odpowiedz.
- [ ] Dodac 3 konkretne przyklady Q&A ze zrodlami.

## Dzien 13 - Lessons Learned
- [ ] Opisac w README: wplyw chunking size/overlap na jakosc.
- [ ] Opisac jak ograniczales halucynacje.
- [ ] Opisac limity lokalnych modeli (predkosc, okno kontekstu, stabilnosc).

## Dzien 14 - Final polish i publikacja
- [ ] Dopracowac README: uruchomienie, architektura, metryki, evidence.
- [ ] Sprawdzic dzialanie przez `docker compose up`.
- [ ] Przygotowac finalny opis projektu do GitHub i LinkedIn.
