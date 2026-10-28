# How this repository was made (Tajikistan)

This file is written by the build on 2026-10-28, the day the source data was retrieved. Everything below is enough to rebuild this repository hash for hash.

## Sources

| Source | Address | Retrieved | Requests | Licence |
| --- | --- | --- | ---: | --- |
| Majlisi namoyandagon (parlament.tj), via Internet Archive | <http://parlament.tj/konstitutsiyai-jt/> | 2026-10-28 | 1 | Official legislative text (public domain as an official act); Internet Archive capture |

Every response is cached by the sha256 of its URL, and the table above lists every source with its retrieval date. Lexifina keeps its fetch scripts privately; `tools/parse.py` reads only the cache and writes `corpus.json`, so the same cache always gives the same corpus.

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

## Commands, in order

```sh
# fill the cache from the sources listed above (network; Lexifina's fetch scripts are kept privately)
python -X utf8 tools/parse.py                  # cache -> corpus.json (no network)
python -X utf8 tools/build.py <folder> --repo <empty folder> --docs-date 2026-10-28
python -X utf8 tools/check_repo.py <repo> --corpus <folder>/corpus.json --write
python -X utf8 tools/build.py <folder> --repo <another empty folder> --docs-date 2026-10-28 --compare <repo>
```

In the main Lexifina repository these files live as follows:
- `fetch.py`, `parse.py` and `repo/`: in `scripts/tajikistan-law/`.
- `build.py`, `check_repo.py` (`check.py` there) and `on.py`: in `scripts/gitlaw_common/`, with the corpus format in `SCHEMA.md`.

## Exact inputs

- `corpus.json` sha256 `ccf26555f4f9a884b779c874e526d7be32deb5dd825ca006e5dbe88a8b740d9b` (95815 bytes)
- Script blob hashes (`git hash-object`):

| Script | Blob |
| --- | --- |
| build.py | `2bfc4ac9df193a7be844556d7f69cdb9d93ec3f2` |
| check.py | `cd346c7ff9996d450240e3bab52bcae03b2bc865` |
| on.py | `644a6c0857fbcc72562032b58d57aa113fee0641` |
| fetch.py | `(missing)` |
| parse.py | `a7ccb06a52c5f49212d7a1a89a9717bf674f4f3a` |

- Tools:
  - Python 3.14.0
  - git version 2.52.0.windows.1
  - curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP

## Checks

1 versions of 1 acts read back from git on the day each took effect and on the day before: 0 mismatches. Trailers: 0 commits whose trailers git cannot parse. Health: 0 merge commits on main, 0 commit dates that go backwards, 0 commits dated after the build.

Not yet run for this build.

These results are from the check run on the build before this one, from the same corpus.

## Decisions made by hand

- Tajik is the official language; the Tajik text is built. Russian texts exist (adlia.tj) but anonymous access shows only 1,500 characters.
- All .tj sites time out from the build machine, so the official pages are read from Internet Archive id_ captures, pinned by timestamp.
- Constitution: the oldest text available is the 1999+2003 edition published by the Majlisi namoyandagon; it is the first version (first_law null), dated 2003-06-22, the referendum day the source names for the edition.
- The 1994 original and the 1999 edition were not found online at an official source; they are named in earlier_laws.
- Belarusian ў in the publisher text is normalised to Tajik ӯ.

## What AI did and did not do

The fetch, parse and check scripts were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above, through code that anyone can rerun.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: no model wrote or transformed legal text; Claude Opus 5.5 wrote the scripts.
