# Tajikistan: law history in git

The law of Tajikistan as a git history: one file per provision, one commit per law on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; picking a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `tj/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `konstitutsiya/` | Konstitutsiyai (Sarqonuni) Jumhurii Tojikiston (the Constitution, in Tajik) | 1 | One version: the edition with the amendments of the referendums of 26 September 1999 and 22 June 2003 |

**Important limits**

- The text is the 1999 and 2003 edition of the Constitution **as the Majlisi namoyandagon published it in 2017**. Tajikistan amended the Constitution again by referendum on 22 May 2016. Those 2016 amendments are **not** in this text, so it is not the Constitution in force today. A later version is added when an official text of the current edition is found.
- There is one version only ("oldest version available"). It is dated 22 June 2003, the referendum day the source names for the edition, and it is credited to its publisher, not to a law. The 1994 original and the 1999 edition are named in the record but their texts are not in it.
- The language is Tajik (Cyrillic), the official language. The Belarusian letter "ў" that the publisher mixes in is normalised to the Tajik "ӯ".
- Other Tajik codes and laws are not in this record yet.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did article 100 say on a date? | `python tools/on.py 2010-01-01 konstitutsiya art-100` |
| Who wrote each paragraph of article 8? | `git blame konstitutsiya/art-008.md` |
| Every change to a provision | `git log -p --word-diff konstitutsiya/art-008.md` |

## Dates

Each commit is dated at noon, Asia/Dushanbe, on the day the change took effect. The record's first version has no earlier version to compare with.

## How it is checked

- The text was compared article by article with a second official copy (the Majlisi milli, majmilli.tj). The two copies are the same edition; they differ only in spelling slips (for example "Кӯҳистони" and "Куҳистони", "мӯҳлат" and "муҳлат") and in the formatting of numbered lists, and this record keeps the Majlisi namoyandagon text.
- Every version is read back from git and must match `corpus.json`. Results are in `REPRODUCE.md`.
- Health checks: no merge commits, commit dates never go backwards, nothing dated in the future, and every commit's trailers parse.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist. For the first version it is the publisher. The committer is always Lexifina.
