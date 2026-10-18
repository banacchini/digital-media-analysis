from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd


def find_project_root(
    start_path: Path, anchors=(".git", "requirements.txt", "pyproject.toml")
) -> Path:
    """Dynamicznie szuka katalogu głównego projektu, idąc w górę drzewa katalogów."""
    for parent in [start_path] + list(start_path.parents):
        if any((parent / anchor).exists() for anchor in anchors):
            return parent
    return start_path.anchor


def inspect_all_parquet_files(source_subdir="data/processed"):
    # 1. Dynamiczne lokalizowanie katalogu głównego projektu
    script_path = Path(__file__).resolve()
    project_root = find_project_root(script_path)

    # 2. Definiowanie ścieżek
    parquet_dir = project_root / source_subdir
    report_filepath = parquet_dir / "metadata.txt"

    if not parquet_dir.exists():
        print(f"Błąd: Folder nie istnieje w lokalizacji: {parquet_dir}")
        return

    # 3. Dynamiczne pobranie wszystkich plików Parquet
    parquet_files = sorted([p for p in parquet_dir.glob("*") if p.suffix in (".parquet", ".pq")])

    if not parquet_files:
        print(f"Nie znaleziono plików Parquet w folderze: {parquet_dir}")
        return

    # 4. Przekierowanie wszystkich funkcji print() bezpośrednio do pliku tekstowego
    print(f"Rozpoczynam analizę. Raport zostanie zapisany w: {report_filepath}")

    with (
        open(report_filepath, "w", encoding="utf-8") as report_file,
        redirect_stdout(report_file),
    ):
        # Pętla przetwarzająca każdy znaleziony plik
        for file_path in parquet_files:
            try:
                print(f"File: {file_path.name}")
                print("-" * 40)

                # Odczyt pliku Parquet
                df = pd.read_parquet(file_path)

                # Pobranie wymiarów i kolumn
                rows, columns = df.shape
                column_names = list(df.columns)

                # Wyświetlenie wyników (zostaną zapisane w pliku)
                print(f"  Columns ({len(column_names)}): {column_names}")
                print(df.dtypes)
                print("=" * 60)

            except Exception as e:
                print(f"  Błąd podczas analizy pliku {file_path.name}: {e}")
                print("=" * 60)

    print("Analiza zakończona pomyślnie.")


if __name__ == "__main__":
    # Uruchomienie skryptu
    inspect_all_parquet_files()
