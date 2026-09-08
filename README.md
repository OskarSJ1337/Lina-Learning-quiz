# Lina – självtest

En svensk skrivbordsapp för Windows med 30 förståelse- och tillämpningsfrågor baserade på projektets tre PDF-filer. Fyra alternativ, grön/röd återkoppling, förklaring, sidhänvisning, Nästa-knapp och poängräknare. Frågor och svar blandas vid varje test. Missade frågor kan repeteras.

## Starta

Dubbelklicka på `dist/Lina-Sjalvtest.exe`. Ingen Python-installation, internetanslutning eller API-nyckel behövs. EXE-filen kan flyttas till en annan Windows-dator; frågebanken är inbyggd.

## Gränssnitt

Startsidan har **Starta quiz** för alla frågor samt ett separat alternativ för varje PDF. Antalet frågor visas vid varje val. **Nytt test** behåller vald grupp, även efter repetition av missade frågor. Under testet visas frågan, fyra svar och antal rätt. Efter svaret visas återkoppling, förklaring, en kort källhänvisning och **Nästa**. Texten är större och har tydligare kontrast.

PDF-import visas inte längre i gränssnittet. Alla 82 frågor ingår. Sidhänvisningar räknas från PDF-filens första sida.

## Utveckling

Python 3.13 användes för bygget. Tkinter ingår i standardinstallationen för Windows.

```powershell
python -m pip install -r requirements.txt
python app.py
python -m unittest -v
python build_exe.py
```

`questions.json` innehåller frågorna. `create_bank.py` återskapar den filen från de formulerade frågorna. `test_app.py` kontrollerar blandning, facit, låsta svar, poäng och repetition.

## Dela appen

Skicka endast `dist/Lina-Sjalvtest.exe` (cirka 11 MB) till mottagaren. Appen ?r byggd f?r 64-bitars Windows och beh?ver inte installeras. De 82 fr?gorna ing?r; PDF-filer beh?vs bara f?r att importera fler fr?gor. Bygget beh?ller PDF-import och anv?nder optimerad Python-kod utan oanv?nda OpenSSL-bibliotek. Den f?rdiga EXE-filen har testats fr?n en separat tillf?llig mapp, inklusive r?tt/fel, resultat och import av samtliga tre PDF-filer.

Fr?gebanken omfattar nu 82 fr?gor. De 40 tillagda fr?gorna i `additional_questions.py` t?cker bland annat urval, bortfall, enk?ter, m?tningskvalitet, statistik, analys, teorifunktioner och etiska avv?gningar. Alla har fyra alternativ, f?rklaring och h?nvisning till PDF-sida.

Efter granskning av ämnestäckning, överlapp och källtext tillkom 12 frågor om samtycke, indirekt identifiering, tredje person, dubbla roller, dataminimering, barn, falsifierbarhet, teoretiserande, intressekonflikter, rättelser och etiska ramverk.

Läsinställningar: Verdana med minst 14 punkters text, A−/A+ för större text, kortare stycken och tydligare kontrast i dag- och nattläge. Frågehjälpen använder enklare språk. Inställningarna gäller under den öppna sessionen.
