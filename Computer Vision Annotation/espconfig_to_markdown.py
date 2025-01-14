"""
This script can be used to populate the Usage section of a README.md file 
It automatically inserts a table between `<!--start_of_usage-->` and `<!--end_of_usage-->`
"""

# pip install tabulate
import re
import pandas as pd
import annotation

espconfig = annotation._espconfig_  # pylint: disable=protected-access


def create_markdown_table(df):
    """
    Create a Markdown table from a DataFrame.
    """
    df = df.rename(
        columns={
            "name": "Name",
            "desc": "Description",
            "optional": "Required or Optional",
            "default": "Default",
        }
    )
    if "Required or Optional" in df.columns:
        df["Required or Optional"] = df["Required or Optional"].apply(
            lambda x: "Optional" if x else "Required"
        )
    markdown_table = df.to_markdown(index=False)
    return markdown_table


def main():
    """
    Populate the Usage section of the README.md file
    """
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
