#!/usr/bin/env python3
#
# Copyright (c) 2024 YunoHost Contributors
#
# This file is part of YunoHost (see https://yunohost.org)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import json
import sys
from pathlib import Path
import textwrap
import re
from collections import OrderedDict


def autofix_i18n_placeholders(reference_file: Path, locale_files: list[Path]) -> None:
    reference = json.load(reference_file.open())

    fatal_errors: list[str] = []

    def _autofix_i18n_placeholders(locale_file: Path) -> None:
        """
        This tries for magically fix mismatch between en.json format and other.json format
        e.g. an i18n string with:
            source:   "Lorem ipsum {some_var}"
            fr:       "Lorem ipsum {une_variable}"
        (ie the keyword in {} was translated but shouldnt have been)
        """
        this_locale = json.load(locale_file.open())
        fixed_stuff = False

        # We iterate over all keys/string in en.json
        for key, string in reference.items():
            # Ignore check if there's no translation yet for this key
            if key not in this_locale:
                continue

            # Then we check that every "{stuff}" (for python's .format())
            # should also be in the translated string, otherwise the .format
            # will trigger an exception!
            subkeys_in_ref = [k[0] for k in re.findall(r"{(\w+)(:\w)?}", string)]
            subkeys_in_this_locale = [
                k[0] for k in re.findall(r"{(\w+)(:\w)?}", this_locale[key])
            ]

            if set(subkeys_in_ref) != set(subkeys_in_this_locale) and (
                len(subkeys_in_ref) == len(subkeys_in_this_locale)
            ):
                for i, subkey in enumerate(subkeys_in_ref):
                    this_locale[key] = this_locale[key].replace(
                        "{%s}" % subkeys_in_this_locale[i], "{%s}" % subkey
                    )
                    fixed_stuff = True

            # Validate that now it's okay ?
            subkeys_in_ref = [k[0] for k in re.findall(r"{(\w+)(:\w)?}", string)]
            subkeys_in_this_locale = [
                k[0] for k in re.findall(r"{(\w+)(:\w)?}", this_locale[key])
            ]
            if any(k not in subkeys_in_ref for k in subkeys_in_this_locale):
                errmsg = textwrap.dedent(f"""\
                    ==========================
                    Format inconsistency for string {key} in {locale_file}:
                    {reference_file.name} -> {string.encode("utf-8")}
                    {locale_file.name} -> {this_locale[key].encode("utf-8")}
                    Please fix it manually !
                    """)
                print(errmsg)
                fatal_errors.append(locale_file.name)

        if fixed_stuff:
            with locale_file.open("w") as locale_io:
                json.dump(
                    this_locale,
                    locale_io,
                    indent=4,
                    ensure_ascii=False,
                )
                locale_io.write("\n")

    for locale_file in locale_files:
        _autofix_i18n_placeholders(locale_file)

    if fatal_errors:
        print(f"Errors found in files {', '.join(fatal_errors)}.")
        sys.exit(1)


def autofix_orthotypography_and_standardized_words(locale_dir: Path) -> None:
    def reformat(lang: str, transformations: dict[str, str]) -> None:
        locale_file = locale_dir / f"{lang}.json"
        json_raw = locale_file.read_text()
        for pattern, replace in transformations.items():
            json_raw = re.compile(pattern).sub(replace, json_raw)
        locale_file.write_text(json_raw)

    ######################################################

    godamn_spaces_of_hell = [
        "\u00a0",
        "\u2000",
        "\u2001",
        "\u2002",
        "\u2003",
        "\u2004",
        "\u2005",
        "\u2006",
        "\u2007",
        "\u2008",
        "\u2009",
        "\u200a",
        # "\u202f",
        # "\u202F",
        "\u3000",
    ]
    transformations_space = {s: " " for s in godamn_spaces_of_hell}

    transformations_misc = {
        r"\.\.\.": "…",
        "https ://": "https://",
    }

    transformations = transformations_space | transformations_misc

    reformat("en", transformations)

    ######################################################

    transformations_fr = {
        "courriel": "email",
        "e-mail": "email",
        "Courriel": "Email",
        "E-mail": "Email",
        "« ": "'",
        "«": "'",
        " »": "'",
        "»": "'",
        "’": "'",
        # r"$(\w{1,2})'|( \w{1,2})'": r"\1\2’",
    }
    reformat("fr", transformations | transformations_fr)


def remove_stale_translated_strings(reference_file: Path, locale_files: list[Path]) -> None:
    reference = json.load(reference_file.open())

    for file in locale_files:
        this_locale = json.load(file.open(), object_pairs_hook=OrderedDict)
        this_locale_fixed = {k: v for k, v in this_locale.items() if k in reference}
        with file.open("w") as locale_io:
            json.dump(
                this_locale_fixed,
                locale_io,
                indent=4,
                ensure_ascii=False,
            )
            locale_io.write("\n")



def main() -> None:
    project_dir: Path = Path(__file__).resolve().parent.parent
    locale_dir = project_dir / "locales"

    reference_locale = locale_dir / "en.json"
    locales = list(locale_dir.glob("*.json"))
    locales.remove(reference_locale)

    autofix_orthotypography_and_standardized_words(locale_dir)
    remove_stale_translated_strings(reference_locale, locales)
    autofix_i18n_placeholders(reference_locale, locales)


if __name__ == "__main__":
    main()
