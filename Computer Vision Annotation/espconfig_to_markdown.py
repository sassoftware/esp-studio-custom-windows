"""
This script can be used to populate the Usage section of a README.md file

It automatically inserts a table between `<!--start_of_usage-->` and `<!--end_of_usage-->`
"""

# pip install tabulate
import re
import pandas as pd
import annotation

espconfig = annotation._espconfig_  # pylint: disable=protected-access

ESP_DATA_TYPES = [
    "int32",
    "int64",
    "double",
    "string",
    "date",
    "stamp",
    "money",
    "blob",
    "rstring",
    "array(i32)",
    "array(i64)",
    "array(dbl)",
]


def create_markdown_table(df):
    """Create a Markdown table from a DataFrame."""
    df = df.rename(
        columns={
            "name": "Name",
            "desc": "Description",
            "optional": "Required or Optional",
            "default": "Default",
        }
    )

    df["Name"] = "`" + df["Name"] + "`"

    if "Default" not in df.columns:
        last_bracket = r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)$"
        df["_temp_bracket_content"] = df["Description"].str.extract(last_bracket)[0]

        def format_data_types(row):
            content = row["_temp_bracket_content"]
            esp_type = row["esp_type"]

            if pd.isna(content):
                # Use esp_type if no parentheses found
                if pd.notna(esp_type):
                    return f"`{esp_type}`"
                return "`unknown`"

            data_types = []
            for word in content.split():
                if word in ESP_DATA_TYPES:
                    data_types.append(word)

            if len(data_types) == 0:
                return "`unknown`"
            elif len(data_types) == 1:
                return f"`{data_types[0]}`"
            elif len(data_types) == 2:
                return f"`{data_types[0]}` or `{data_types[1]}`"
            else:
                # Handle case with more than 2 data types
                formatted_types = [f"`{dt}`" for dt in data_types[:-1]]
                return f"{', '.join(formatted_types)}, or `{data_types[-1]}`"

        df["Type"] = df.apply(format_data_types, axis=1)
        df.drop(columns=["_temp_bracket_content"], inplace=True)

        df["Description"] = df["Description"].str.replace(last_bracket, "", regex=True)

    if "Default" in df.columns:
        df["Default"] = "`" + df["Default"] + "`"

    if "Required or Optional" in df.columns:
        df["Required or Optional"] = df["Required or Optional"].apply(
            lambda x: "Optional" if x else "Required"
        )

    # Ordering
    if "Default" not in df.columns:
        if "Required or Optional" in df.columns:
            df = df[["Name", "Description", "Type", "Required or Optional"]]
        else:
            df = df[["Name", "Description", "Type"]]
    else:
        df = df[["Name", "Description", "Default"]]

    markdown_table = df.to_markdown(index=False)
    return markdown_table


def main():
    """Populate the Usage section of the README.md file"""
    usage = "<!--start_of_usage-->\n"
    usage += "### Input Variables\n"
    usage += espconfig["inputVariables"]["desc"] + "\n\n"
    usage += create_markdown_table(pd.DataFrame(espconfig["inputVariables"]["fields"]))

    usage += "\n\n### Output Variables\n"
    usage += espconfig["outputVariables"]["desc"] + "\n\n"
    usage += create_markdown_table(pd.DataFrame(espconfig["outputVariables"]["fields"]))

    usage += "\n\n### Initialization\n"
    usage += espconfig["initialization"]["desc"] + "\n\n"
    usage += create_markdown_table(pd.DataFrame(espconfig["initialization"]["fields"]))

    usage += "\n\n<!--end_of_usage-->"

    with open("README.md", "r", encoding="utf-8") as readme:
        new_readme, modifications = re.subn(
            "<!--start_of_usage-->.*<!--end_of_usage-->",
            usage,
            readme.read(),
            flags=re.DOTALL,
        )
    if modifications == 0:
        print("No modifications made to README.md")
    else:
        print("Modified README.md")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)


if __name__ == "__main__":
    main()
