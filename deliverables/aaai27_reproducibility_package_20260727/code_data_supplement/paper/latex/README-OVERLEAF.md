# AlgoTutorGen AAAI anonymous-review source

This archive contains only the current English paper sources, the figures they
actually reference, the AAAI style files, and the reproducibility checklist.
Generated PDFs, Chinese reading copies, build caches, historical figures,
editable slide decks, experiment artifacts, and local-only files are excluded.

## Overleaf

1. Upload the ZIP as a new Overleaf project.
2. Set the compiler to pdfLaTeX.
3. Set `main.tex` as the main document to compile the paper.
4. Set `supplement.tex` as the main document to compile the supplement.
5. Set `reproducibility-checklist.tex` as the main document to compile the
   checklist if the submission site requests it separately.

Both `main.tex` and `supplement.tex` use BibTeX; Overleaf runs the required
pdfLaTeX/BibTeX passes automatically. The anonymous submission omits the project
page and all author and affiliation information; these should be added only to
an accepted final version.
