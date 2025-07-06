import numpy as np
import dropbox
import pandas as pd
import io
import streamlit as st


# Legge il token dai secrets
DROPBOX_ACCESS_TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]

def read_excel_from_dropbox(dropbox_path):
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    _, res = dbx.files_download(path=dropbox_path)
    file_like = io.BytesIO(res.content)
    xls = pd.ExcelFile(file_like)
    return xls

def list_files_in_dropbox_folder(folder_path="/Database/"):
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    result = dbx.files_list_folder(folder_path)
    files = []
    for entry in result.entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            files.append(entry.name)
    return files

def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)
    if np.isnan(h) or np.isnan(a):
        return "Others"
    if h < 1.5:
        return "H_StrongFav <1.5"
    elif 1.5 <= h < 2:
        return "H_MediumFav 1.5-2"
    elif 2 <= h < 3:
        return "H_SmallFav 2-3"
    elif h <= 3 and a <= 3:
        return "SuperCompetitive H-A<3"
    elif a < 1.5:
        return "A_StrongFav <1.5"
    elif 1.5 <= a < 2:
        return "A_MediumFav 1.5-2"
    elif 2 <= a < 3:
        return "A_SmallFav 2-3"
    else:
        return "Others"


def extract_minutes(series):
    all_minutes = []
    for val in series.dropna():
        if isinstance(val, str):
            for part in val.replace(",", ";").split(";"):
                part = part.strip()
                if part.isdigit():
                    all_minutes.append(int(part))
    return all_minutes

