## utils/file_utils.py
import pandas as pd
from pathlib import Path
import os
from typing import List, Dict, Any
import shutil

def ensure_directory(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def read_csv_safe(file_path: Path, default_columns: List[str] = None) -> pd.DataFrame:
    """Safely read CSV file, create if doesn't exist"""
    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            # Check if file is empty or has no columns
            if df.empty and default_columns:
                df = pd.DataFrame(columns=default_columns)
                df.to_csv(file_path, index=False)
            return df
        except pd.errors.EmptyDataError:
            # Handle completely empty files
            if default_columns:
                df = pd.DataFrame(columns=default_columns)
                ensure_directory(file_path.parent)
                df.to_csv(file_path, index=False)
                return df
            return pd.DataFrame()
    else:
        # Create empty DataFrame with default columns
        if default_columns:
            df = pd.DataFrame(columns=default_columns)
            ensure_directory(file_path.parent)
            df.to_csv(file_path, index=False)
            return df
        return pd.DataFrame()

def append_to_csv(file_path: Path, data: Dict[str, Any]) -> None:
    """Append data to CSV file"""
    ensure_directory(file_path.parent)
    df = pd.DataFrame([data])
    
    if file_path.exists():
        df.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df.to_csv(file_path, index=False)

def update_csv_row(file_path: Path, condition_col: str, condition_val: Any, updates: Dict[str, Any]) -> bool:
    """Update specific row in CSV file"""
    if not file_path.exists():
        return False
    
    df = pd.read_csv(file_path)
    mask = df[condition_col] == condition_val
    
    if not mask.any():
        return False
    
    for col, val in updates.items():
        df.loc[mask, col] = val
    
    df.to_csv(file_path, index=False)
    return True

def backup_file(file_path: Path, backup_dir: Path = None) -> None:
    """Create backup of file"""
    if not file_path.exists():
        return
    
    if backup_dir is None:
        backup_dir = file_path.parent / "backups"
    
    ensure_directory(backup_dir)
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name
    
    shutil.copy2(file_path, backup_path)