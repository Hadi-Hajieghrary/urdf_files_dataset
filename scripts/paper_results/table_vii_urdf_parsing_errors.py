from pathlib import Path
import subprocess
import os
import re
import pandas as pd
from helper_functions import _get_subdirectories, _get_files_with


def _find_issue_and_description_rosparser(output_string, issue_word):
    issue_indices = [m.start() for m in re.finditer(issue_word, output_string.lower())]
    issues = set()
    for idx in issue_indices:
        issue = output_string[idx:output_string.find("\n",idx)]
        issue = str(issue.lower().replace(f"{issue_word}:","")).lstrip()
        issues.add(issue)
    return issues


def check_urdf(filename):
    res = subprocess.run(f'check_urdf {filename}', shell=True, capture_output=True, text=True)
    if res.returncode == 0: # success
        return res.stdout
    else:
        warnings = _find_issue_and_description_rosparser(res.stderr, 'warning')
        errors = _find_issue_and_description_rosparser(res.stderr, 'error')
        return errors, warnings


def capture_issues(df, issue, cur_issue, urdf_file):
    issue_count = df.loc[df[issue] == cur_issue, 'count']
    dirs = str(urdf_file).split(os.path.sep)
    file = os.path.basename(urdf_file)
    source = dirs[dirs.index('urdf_files')+1] # in case urdf_files is not found, we assume the source is the root dir
    if issue_count.size == 0:
        err_info = pd.Series({issue: cur_issue, "count": 1, "urdf file": [file], "source": [source]})
        df = pd.concat([df, err_info.to_frame().T], ignore_index=True)
    else:
        issue_count = issue_count.iloc[0] + 1 # increment count of current error
        err_source = df.loc[df[issue] == cur_issue, 'source']
        err_source.iloc[0].append(source)
        err_urdf_file = df.loc[df[issue] == cur_issue, 'urdf file']
        err_urdf_file.iloc[0].append(file)

        df.loc[df[issue] == cur_issue, 'count'] = issue_count
        df.loc[df[issue] == cur_issue, 'source'] = err_source
        df.loc[df[issue] == cur_issue, 'urdf file'] = err_urdf_file   
    return df        

dir = "urdf_files"
subdirs = _get_subdirectories(dir)
root_dir = os.getcwd()

df_errors = pd.DataFrame(columns=["errors","count","urdf file","source"])
df_warnings = pd.DataFrame(columns=["warnings","count","urdf file","source"])
n_urdfs_with_errors = 0
n_urdfs_with_warnings = 0

for d in subdirs:
    urdf_files = _get_files_with(d, "*.urdf")
    for urdf_file in urdf_files:
        output = check_urdf(str(urdf_file))
        if 'Success' not in output:
            errors = output[0]
            warnings = output[1]
            for err in errors:
                df_errors = capture_issues(df_errors, "errors", err, urdf_file)
            for warn in warnings:
                df_warnings = capture_issues(df_warnings, "warnings", warn, urdf_file)
            if len(list(errors)) > 0:
                n_urdfs_with_errors += 1
            if len(list(warnings)) > 0:
                n_urdfs_with_warnings += 1

defined_error_categories = {"Issue with joint limits":"limit", 
                                "No link elements found in URDF file":"no link element",
                                "Non-unique link": "not unique",
                                "No name given for robot": "no name",
                                "Parent link not found": "parent link",
                                "XML parsing failed": "parsing the xml"}
defined_errors = list(defined_error_categories.values())

quanitified_errors = pd.DataFrame(index=[list(defined_error_categories.keys())],columns=["n_urdfs","sources"])
quanitified_errors = quanitified_errors.fillna(0)

for index, row in df_errors.iterrows():
    for error, category in list(defined_error_categories.items()):
     if category in row['errors']:
        quanitified_errors.loc[error,"n_urdfs"] += row['count']
        quanitified_errors.loc[error,"sources"] = str(row['source'])


quanitified_errors.to_csv("table_vii_parsing_errors.csv")
df_errors.to_csv("ros_parsing_errors.csv", index=False)
df_warnings.to_csv("ros_parsing_warnings.csv", index=False)

print(f"total number of urdf files with errors: {n_urdfs_with_errors}")
print(f"total number of urdf files with warnings: {n_urdfs_with_warnings}")

