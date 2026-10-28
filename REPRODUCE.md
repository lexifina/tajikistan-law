# How this repository was made (Tajikistan)

This file is written by the build on 2026-10-28, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| Majlisi namoyandagon (parlament.tj), via Internet Archive | <http://parlament.tj/konstitutsiyai-jt/> | 2026-10-28 | Official legislative text (public domain as an official act); Internet Archive capture |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `konstitutsiya` | Конститутсияи (Сарқонуни) Ҷумҳурии Тоҷикистон | 1 | 2003-06-22 to 2003-06-22 |

The build made 1 commits:

| Commits | Kind |
| ---: | --- |
| 1 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `future`: laws not yet in force on 2026-10-28.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 2 laws in the record.
- 1 tags.

## Dates

Each commit is dated at noon (Asia/Dushanbe) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: Constitutional amendments adopted by national referendum; this build dates the edition by the referendum day the source names. http://parlament.tj/konstitutsiyai-jt/

## How the history is built

`tools/build.py` turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/SCHEMA.md`.

- Corpus: sha256 `174246e68863297aa376529b6b0dd371e1b6a42ab6ec0dc1e32d763b46e11bfd` (95925 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `a4faa25af85facb64b956b372f6b528aafdd7ec1`, `check.py` `3e59cb6f05eccb94a9ec14431a7f6781221e83ef`, `on.py` `644a6c0857fbcc72562032b58d57aa113fee0641`.
- Python 3.12.10; git version 2.46.0.windows.1.

## Checks

Not yet run for this build.

No second build of this corpus has been compared yet.

## Decisions made by hand

- Tajik is the official language; the Tajik text is built. Russian texts exist (adlia.tj) but anonymous access shows only 1,500 characters.
- Constitution: the oldest text available is the 1999+2003 edition published by the Majlisi namoyandagon; it is the first version (first_law null), dated 2003-06-22, the referendum day the source names for the edition.
- The 1994 original and the 1999 edition were not found online at an official source; they are named in earlier_laws.
- Belarusian ў in the publisher text is normalised to Tajik ӯ.

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: no model wrote or transformed legal text; Claude Opus 5.5 wrote the scripts.
