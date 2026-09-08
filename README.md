# Lina – självtest

En svensk skrivbordsapp för Windows med 30 förståelse- och tillämpningsfrågor baserade på projektets tre PDF-filer. Fyra alternativ, grön/röd återkoppling, förklaring, sidhänvisning, Nästa-knapp och poängräknare. Frågor och svar blandas vid varje test. Missade frågor kan repeteras.

## Starta

Dubbelklicka på `dist/Lina-Sjalvtest.exe`. Ingen Python-installation, internetanslutning eller API-nyckel behövs. EXE-filen kan flyttas till en annan Windows-dator; frågebanken är inbyggd.

## PDF-läge

Välj **Läs PDF-filer och skapa fler begreppsfrågor** och markera en eller flera PDF-filer. Texten läses lokalt med pypdf. Meningar med kända kursbegrepp blir luckfrågor med fyra alternativ. Originalmening, filnamn och PDF-sida visas efter svaret. Detta är regelbaserad generering, inte en språkmodell som kan skapa fria resonemangsfrågor från valfritt innehåll. Skannade dokument utan textlager kräver OCR; ingen OCR ingår. Importerade frågor används under den aktuella sessionen och sparas inte.

Den inbyggda frågebanken är separat formulerad utifrån PDF-materialet. Sidhänvisningar räknas från PDF-filens första sida, inte bokens tryckta sidnummer. Övningsfrågorna är inte ett officiellt facit och täcker inte hela kursen. Original-PDF:erna packas inte in i EXE-filen.

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

Skicka endast `dist/Lina-Sjalvtest.exe` (cirka 11 MB) till mottagaren. Appen ?r byggd f?r 64-bitars Windows och beh?ver inte installeras. De 70 fr?gorna ing?r; PDF-filer beh?vs bara f?r att importera fler fr?gor. Bygget beh?ller PDF-import och anv?nder optimerad Python-kod utan oanv?nda OpenSSL-bibliotek. Den f?rdiga EXE-filen har testats fr?n en separat tillf?llig mapp, inklusive r?tt/fel, resultat och import av samtliga tre PDF-filer.

Fr?gebanken omfattar nu 70 fr?gor. De 40 tillagda fr?gorna i `additional_questions.py` t?cker bland annat urval, bortfall, enk?ter, m?tningskvalitet, statistik, analys, teorifunktioner och etiska avv?gningar. Alla har fyra alternativ, f?rklaring och h?nvisning till PDF-sida.
