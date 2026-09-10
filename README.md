# Linas självstudie quiz

En svensk quizapp för Vetenskaplig metodkurs Speciallärar- och specialpedagogprogrammet. Frågebanken innehåller 98 frågor från fyra PDF-filer, med fyra svarsalternativ, enkla förklaringar och källhänvisningar.

## Starta

### Webbversion

Webbversionen följer Windows-appens layout och färger och fungerar även på mobil.
Alla 98 frågor, källval, förenklingar, svarsförklaringar, nattläge, frågenavigering,
resultat och repetition av missade/obesvarade frågor ingår. Tangenterna 1–4 väljer svar.
Besökare har separata quiz i sina webbläsare. Omladdning startar om quizet; nattläget sparas lokalt.
Besvarade frågor behåller sina svar när man går tillbaka.

På servern finns sidan på <http://192.168.0.198/> och <http://192.168.0.198:30420/>.
Routerns regel **extern TCP-port 30420 → 192.168.0.198:80** ger åtkomst via
`http://DIN-PUBLIKA-IP:30420/`. Extern åtkomst behöver verifieras från exempelvis mobilnätet.

Driften använder Kubernetes i namnrymden `media`, Nginx och den befintliga Traefik-routern.
Quizets standardrutt har låg prioritet så befintliga domänspecifika rutter behålls.
Deploymenten återstartas automatiskt av Kubernetes. Endast webbens filer och frågebanken publiceras.
Argo CD-applikationen `lina-quiz` följer `main` i detta repo och synkar automatiskt
med prune och self-heal. Publicera webbändringar genom att committa och pusha till `main`.
Kustomize genererar versionsmärkta ConfigMaps så ändrade filer automatiskt startar en ny pod.
För att registrera applikationen från projektroten med rätt kubectl-konfiguration:

```sh
sh deploy/publish.sh
```

För lokal utveckling (Python 3, inga extra paket):

```sh
mkdir -p dist/web
cp web/index.html web/style.css web/quiz.js web/app.js questions.json dist/web/
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist/web
```

Öppna <http://localhost:8080/>. Quizlogiken testas med `node web/quiz.test.cjs`.

### Windows

Dubbelklicka på `dist/Lina-Sjalvtest.exe`. Appen körs lokalt på 64-bitars Windows utan installation, internet eller Python. Skicka bara EXE-filen; frågorna ingår och kursens PDF-filer behövs inte för att spela.

Startsidan har ett val för alla frågor och ett för varje källa. Åsberg (2001) har 16 frågor om bland annat metod, dataform, kunskapssyn och textens kritik av uppdelningen i kvalitativa och kvantitativa metoder. Författarens ståndpunkter anges i frågorna.

Förenkla frågan visar en lättare formulering. Dag- och nattläge finns. Det går att hoppa över frågor och gå tillbaka. Sidhänvisningar räknas från PDF-filens första sida.

## Utveckling

Python 3.13 med Tkinter används.

```powershell
python -m pip install -r requirements.txt
python create_bank.py
python -m unittest -v
python app.py
python build_exe.py
```

`aasberg_questions.json` innehåller den nya källans frågor, förenklingar och svarsförklaringar. `create_bank.py` sammanställer hela banken i `questions.json`, som bäddas in vid bygget. Källmaterial i PDF- och HTML-format samt byggfiler ignoreras av Git.
