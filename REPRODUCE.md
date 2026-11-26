# How this repository was made (Tajikistan)

This file is written by the build on 2026-11-26, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| Majlisi namoyandagon (parlament.tj), via Internet Archive | <http://parlament.tj/konstitutsiyai-jt/> | 2026-10-28 | Official legislative text (public domain as an official act); Internet Archive capture |
| Президенти Ҷумҳурии Тоҷикистон (president.tj) | <https://president.tj/> (API <https://api.president.tj/api/constitution_special>) | 2026-11-26 | Official text of the Constitution (an official act; not subject to copyright) |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `konstitutsiya` | Конститутсияи (Сарқонуни) Ҷумҳурии Тоҷикистон | 2 | 2003-06-22 to 2016-05-22 |

The build made 2 commits:

| Commits | Kind |
| ---: | --- |
| 1 | first version of an act |
| 1 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `future`: laws not yet in force on 2026-11-26.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 4 laws in the record.
- 3 tags.

## Dates

Each commit is dated at noon (Asia/Dushanbe) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: Constitutional amendments adopted by national referendum; this build dates the edition by the referendum day the source names. http://parlament.tj/konstitutsiyai-jt/

## How the history is built

`tools/build.py` turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/SCHEMA.md`.

- Corpus: sha256 `54ca9e00ce557419b2150d57d8e0979c6525484b30d8812b0a7bba5fa4750c59` (198962 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `3fa29d18e75f2ec35d37d87b5147fea1f2e4afdf`, `check.py` `3e59cb6f05eccb94a9ec14431a7f6781221e83ef`, `on.py` `644a6c0857fbcc72562032b58d57aa113fee0641`.
- Python 3.12.10; git version 2.46.0.windows.1.

## Checks

Not yet run for this build.

No second build of this corpus has been compared yet.

## Decisions made by hand

- Tajik is the official language; the Tajik text is built. Russian texts exist (adlia.tj) but anonymous access shows only 1,500 characters.
- Constitution: the oldest text available is the 1999+2003 edition published by the Majlisi namoyandagon; it is the first version (first_law null), dated 2003-06-22, the referendum day the source names for the edition.
- The 1994 original and the 1999 edition were not found online at an official source; they are named in earlier_laws.
- Belarusian ў in the publisher text is normalised to Tajik ӯ.
- Constitution, 2016 edition (2026-11-26): read from the President's site API (api.president.tj/api/constitution_special), which names the referendums of 1999, 2003 and 2016. Dated 2016-05-22, the referendum day (same rule as 2003); under Transitional provisions item 1 it took effect on official publication, a day not found at a reachable source (In-force-basis trailer). Units whose two editions differ only in line breaks, spaces, punctuation or letter case keep the 2003 text (57 units), so the referendum is credited only with word changes (55 units, incl. the new Transitional provisions). Spelling updates in the 2016 text (e.g. мӯҳлат → муҳлат, фавқулодда → фавқулода) stay as the source prints them.
- The 2016 commit was appended on top of the existing history (fast-forward), so it follows the 2026 documentation commits; its date and In-force trailer give its place in time.
- Layout: one folder per act (Tajik names, ASCII-folded: `konstitutsiya/`), one file per article (`art-NNN.md`), chapter headings `bob-NN.md`, `preamble.md`, `muqarraroti-intiqoli.md`; one commit per version at 12:00 Asia/Dushanbe on the in-force day, authored by the amending law (`<key>@parlament.invalid`), committer Lexifina.
- Not reachable from here on 2026-11-26: ncz.tj (National Center for Legislation, connection timeout), adlia.tj (FoxWeb "Broker Timed Out"), parlament.tj and majmilli.tj (timeout). No code or statute is held until one of them answers.

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: no model wrote or transformed legal text; Claude Opus 5.5 wrote the scripts.
