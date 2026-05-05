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

## Dzien 2 - Srodowisko i zaleznosci
- [ ] Utworzyc virtualenv i zainstalowac biblioteki: `streamlit`, `langchain`, `chromadb`, `ollama`.
- [ ] Przygotowac plik `.env.example` z konfiguracja modelu i sciezek.
- [ ] Sprawdzic lokalne uruchomienie "hello app" w Streamlit.

## Dzien 3 - Ingestion dokumentow
- [ ] Zaimplementowac loader PDF/TXT z katalogu `data/`.
- [ ] Dodac chunking (size + overlap) i normalizacje tekstu.
- [ ] Dodac prosty skrypt CLI `ingest`, ktory raportuje liczbe przetworzonych plikow.

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
