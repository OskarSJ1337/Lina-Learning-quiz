# Linas självstudie quiz på Mac

Detta paket innehåller Python-versionen och byggfilerna, inte en färdig fristående .app. Mac-versionen är ännu inte provkörd på macOS.

## Köra med Python

Installera Python 3.13 för macOS från https://www.python.org/downloads/macos/ (med Tkinter). Öppna Terminal i paketets mapp och kör `python3 app.py`, eller `bash "Starta Mac.command"`. PDF-filer behövs inte och quizet använder inget nätverk.

## Bygga en fristående app att skicka

På en Mac med Python och Tkinter: öppna Terminal i paketets mapp och kör:

```sh
bash "Bygg Mac.command"
```

Byggsteget hämtar PyInstaller från nätet och skapar en lokal byggmiljö. Resultatet finns i `dist`: `Linas självstudie quiz.app` och en ZIP-fil som bevarar appens struktur. Mottagaren behöver ingen Python-installation. Bygget använder Mac-datorns Python-arkitektur: arm64 för Apple Silicon eller x86_64 för Intel. Bygg på respektive arkitektur för separata versioner; ett bygge är inte automatiskt universellt.

Appen är inte signerad med Developer ID eller notariserad av Apple. macOS kan därför varna eller blockera den nedladdade appen. För vanlig offentlig distribution behöver den signeras och notariseras på Mac.

## Bygga med GitHub Actions

1. Pusha `.github/workflows/build-mac.yml`, `build_mac.py`, `app.py`, `questions.json` och `test_app.py` till repot. Workflow-filen måste finnas på repots standardgren (vanligtvis main) för att knappen för manuell körning ska visas.
2. Öppna repot på GitHub → Actions → Bygg Mac-app → Run workflow → välj gren → Run workflow.
3. Flödet bygger separat på Apple Silicon (arm64) och Intel (x86_64). Det testar frågebanken och kör den paketerade appens självtest.
4. Öppna den avslutade körningen. Under Artifacts finns `Linas-quiz-Mac-arm64` och `Linas-quiz-Mac-x86_64`. Packa upp den hämtade artifact-filen. Inuti finns ZIP-filen med själva appen; skicka den vidare. Mottagaren packar upp den till en .app.

Jobben körs bara när du startar dem manuellt. Inga secrets eller Apple-konton krävs för detta osignerade bygge. Byggresultaten sparas i 14 dagar. macOS-byggtid kan förbruka Actions-kvot i privata repon; kontrollera kontots plan och budget. Ett grönt bygge ersätter inte en visuell kontroll på mottagarens Mac. Flödet har ännu inte körts på GitHub från denna arbetsmiljö.
