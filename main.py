import os  # For interacting with the file system
import csv  # For reading and writing CSV files
import requests  # For downloading files over HTTP
import re  # For regular expression operations
import tempfile  # For creating temporary files
from typing import List  # For type hinting lists


def download_file(file_url: str, destination_path: str) -> None:
    """
    Downloads a single file from the specified URL and saves it locally.

    :param file_url: The URL to download the file from.
    :param destination_path: The local path to save the downloaded file.
    """
    response = requests.get(file_url)  # Send a GET request to the URL
    response.raise_for_status()  # Raise error if download fails
    with open(
        destination_path, "wb"
    ) as destination_file:  # Open file in binary write mode
        destination_file.write(response.content)  # Write content to file
    print(f"Downloaded {file_url} to {destination_path}")  # Confirm download


def download_files(file_urls: List[str], destination_folder: str) -> None:
    """
    Downloads multiple files and saves them into a specific folder.

    :param file_urls: List of URLs to download.
    :param destination_folder: The folder to save the files in.
    """
    os.makedirs(destination_folder, exist_ok=True)  # Create folder if it doesn't exist

    for file_url in file_urls:
        file_name: str = file_url.split("/")[-1]  # Extract file name from URL
        destination_path: str = os.path.join(
            destination_folder, file_name
        )  # Full destination path
        download_file(file_url, destination_path)  # Download each file


def validate_csv(csv_file_path: str) -> bool:
    """
    Validates a CSV file to check for basic corruption or malformed rows.

    :param csv_file_path: Path to the CSV file to validate.
    :return: True if valid, False otherwise.
    """
    try:
        with open(csv_file_path, newline="", encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)  # Create CSV reader object
            for row_number, row_data in enumerate(csv_reader, start=1):
                if not row_data:  # Warn if an empty row is found
                    print(f"Warning: Empty row found at line {row_number}.")
                    continue  # Continue checking next rows
        print("CSV file is valid (no corruption detected).")
        return True  # Return True if no issues

    except FileNotFoundError:
        print(f"Error: File not found - {csv_file_path}")
        return False

    except csv.Error as error:
        print(f"Error reading CSV: {error}")
        return False

    except Exception as unknown_error:
        print(f"Unexpected error: {str(unknown_error)}")
        return False


def walk_directory_and_extract_given_file_extension(
    directory_path: str, file_extension: str
) -> List[str]:
    """
    Recursively searches a directory and returns a list of files matching a specific extension.

    :param directory_path: Root directory to begin search.
    :param file_extension: File extension to match (e.g., '.csv').
    :return: List of full file paths with the given extension.
    """
    matching_file_paths: List[str] = []  # Store matched files

    for current_folder, _, file_names in os.walk(directory_path):
        for file_name in file_names:
            if file_name.endswith(file_extension):  # Check file extension
                full_path: str = os.path.abspath(
                    os.path.join(current_folder, file_name)
                )
                matching_file_paths.append(full_path)  # Add full path to list

    return matching_file_paths


def remove_system_file(file_path: str) -> None:
    """
    Deletes a file from the file system.

    :param file_path: The path of the file to remove.
    """
    os.remove(file_path)
    print(f"Removed file: {file_path}")


def split_csv(input_csv_path: str, lines_per_split_file: int = 10000) -> None:
    """
    Splits a CSV file into smaller chunks, each with a specified number of lines.

    :param input_csv_path: Path to the input CSV file.
    :param lines_per_split_file: Number of lines per output file.
    """
    input_directory: str = os.path.dirname(
        os.path.abspath(input_csv_path)
    )  # Folder of the input file
    input_filename_without_extension: str = os.path.splitext(
        os.path.basename(input_csv_path)
    )[0]

    with open(input_csv_path, "r", newline="") as input_csv:
        csv_reader = csv.reader(input_csv)
        header_row: List[str] = next(csv_reader)  # Store header

        file_index: int = 1  # Index for naming split files
        row_buffer: List[List[str]] = []  # Temporary storage for rows

        for line_index, row_data in enumerate(csv_reader, start=1):
            row_buffer.append(row_data)

            if line_index % lines_per_split_file == 0:
                output_file_path: str = os.path.join(
                    input_directory,
                    f"{input_filename_without_extension}_part_{file_index}.csv",
                )
                with open(output_file_path, "w", newline="") as output_file:
                    csv_writer = csv.writer(output_file)
                    csv_writer.writerow(header_row)  # Write header
                    csv_writer.writerows(row_buffer)  # Write data
                file_index += 1
                row_buffer = []  # Reset buffer

        # Write remaining rows
        if row_buffer:
            output_file_path = os.path.join(
                input_directory,
                f"{input_filename_without_extension}_part_{file_index}.csv",
            )
            with open(output_file_path, "w", newline="") as output_file:
                csv_writer = csv.writer(output_file)
                csv_writer.writerow(header_row)
                csv_writer.writerows(row_buffer)

    print(f"CSV split completed. Total parts: {file_index}")


def remove_split_files(folder_path: str) -> None:
    """
    Removes previously split CSV files (those with pattern *_part_#.csv).

    :param folder_path: Directory to scan and remove files from.
    """
    split_file_pattern = re.compile(
        r"_part_\d+\.csv$"
    )  # Pattern to identify split files
    deleted_file_names: List[str] = []  # Track which files are deleted

    for file_name in os.listdir(folder_path):
        if split_file_pattern.search(file_name):
            full_file_path = os.path.join(folder_path, file_name)
            try:
                os.remove(full_file_path)
                deleted_file_names.append(file_name)
            except Exception as deletion_error:
                print(f"Error deleting {file_name}: {deletion_error}")

    print(f"Deleted {len(deleted_file_names)} split files.")
    if deleted_file_names:
        print("Removed files:")
        for deleted_file in deleted_file_names:
            print(f"  - {deleted_file}")


def remove_after_timestamp_inplace(csv_file_path: str) -> None:
    """
    Edits a CSV file in place, removing anything after ',timestamp:' in each line.

    :param csv_file_path: The path to the CSV file to clean.
    """
    parent_directory: str = os.path.dirname(csv_file_path)
    temp_file_descriptor, temp_file_path = tempfile.mkstemp(
        dir=parent_directory, suffix=".csv"
    )
    os.close(temp_file_descriptor)  # Close the OS-level file descriptor

    with open(csv_file_path, "r", newline="") as original_file, open(
        temp_file_path, "w", newline=""
    ) as cleaned_file:
        csv_reader = csv.reader(original_file)
        csv_writer = csv.writer(cleaned_file)

        for row in csv_reader:
            row_as_string: str = ",".join(row)
            if ",timestamp:" in row_as_string:
                cleaned_row_string: str = row_as_string.split(",timestamp:")[0]
                cleaned_row: List[str] = cleaned_row_string.split(",")
                csv_writer.writerow(cleaned_row)
            else:
                csv_writer.writerow(row)

    os.replace(temp_file_path, csv_file_path)  # Replace original file with cleaned one
    print(f"Timestamp cleanup done: {csv_file_path}")


if __name__ == "__main__":
    # List of URLs pointing to CSV files
    csv_file_urls: List[str] = [
        "https://www.50-a.org/data/nypd/officers.csv",
        "https://www.50-a.org/data/nypd/ranks.csv",
        "https://www.50-a.org/data/nypd/discipline.csv",
        "https://www.50-a.org/data/nypd/documents.csv",
        "https://www.50-a.org/data/nypd/awards.csv",
        "https://www.50-a.org/data/nypd/training.csv",
    ]

    # Directory to store downloaded CSVs
    local_csv_directory: str = "CSV/"

    # Step 1: Download all CSVs
    download_files(csv_file_urls, local_csv_directory)

    # Step 2: Find all CSVs in the folder
    all_csv_file_paths: List[str] = walk_directory_and_extract_given_file_extension(
        local_csv_directory, ".csv"
    )

    # Step 3: Process each file
    for csv_file_path in all_csv_file_paths:
        if not validate_csv(csv_file_path):  # Validate CSV format
            remove_system_file(csv_file_path)  # Remove if corrupted
            continue  # Skip further steps for this file

        remove_after_timestamp_inplace(csv_file_path)  # Clean timestamp metadata
        remove_split_files(local_csv_directory)  # Remove previously split files
        split_csv(csv_file_path)  # Split into smaller chunks
