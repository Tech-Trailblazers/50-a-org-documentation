import os  # Standard library for interacting with the operating system (e.g., files, directories)
import csv  # Standard library for reading and writing CSV (Comma Separated Values) files
import requests  # Third-party library for making HTTP requests (e.g., downloading files)
import re  # Standard library for regular expression operations (e.g., pattern matching)
import tempfile  # Standard library for creating temporary files and directories


def download_single_file(file_url: str, local_save_path: str) -> None:
    """
    Downloads a single file from a URL and saves it locally,
    skipping the download if the file already exists.

    :param file_url: The web address (URL) of the file to download.
    :param local_save_path: The local file path where the downloaded file should be saved.
    """

    # Check if the file already exists locally before attempting download
    if check_file_exists(file_path=local_save_path):
        print(f"File already exists at {local_save_path}, skipping download.")
        return  # Exit the function early

    try:
        # Step 1: Check accessibility using a HEAD request
        head_response: requests.Response = requests.head(
            url=file_url, allow_redirects=True, timeout=300
        )
        # If the web server returns an error status code (not 200 OK), skip download
        if head_response.status_code != 200:
            print(
                f"URL not accessible (status: {head_response.status_code}): {file_url}"
            )
            return

        # Step 2: Download the file using a GET request (stream=True is efficient for large files)
        download_response: requests.Response = requests.get(
            url=file_url, stream=True, timeout=300
        )
        # Raise an exception for HTTP error codes (e.g., 404, 500)
        download_response.raise_for_status()

        # Step 3: Write the downloaded content to the local file
        with open(file=local_save_path, mode="wb") as destination_file:
            # Iterate through the content in chunks (8KB chunks)
            for chunk in download_response.iter_content(chunk_size=8192):
                if chunk:  # Ensure the chunk is not empty
                    destination_file.write(chunk)  # Write the chunk of data to disk

        # Confirm successful download
        print(f"Successfully downloaded {file_url} to {local_save_path}")

    # Catch network, timeout, or HTTP status errors
    except requests.exceptions.RequestException as error:
        print(f"Download failed for {file_url}: {error}")


def download_multiple_files(file_urls_list: list[str], target_directory: str) -> None:
    """
    Downloads a list of files and saves them into a specific folder.

    :param file_urls_list: list of file URLs to download.
    :param target_directory: The local folder where the files will be saved.
    """
    # Create the directory if it doesn't already exist
    os.makedirs(target_directory, exist_ok=True)

    for file_url in file_urls_list:  # Iterate through every URL
        file_name: str = file_url.split("/")[
            -1
        ]  # Extract the file name (last part of the URL)
        full_file_path: str = os.path.join(
            target_directory, file_name
        )  # Construct the full local path
        download_single_file(
            file_url, full_file_path
        )  # Call the single file download function


def validate_csv_integrity(csv_file_path: str) -> bool:
    """
    Checks a CSV file for basic parsing errors or corruption using the csv module.

    :param csv_file_path: Path to the CSV file to validate.
    :return: True if the file can be read without errors, False otherwise.
    """
    try:
        # Open the file for reading with universal newline mode
        with open(csv_file_path, newline="", encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)  # Create CSV reader object
            # Iterate through all rows to trigger any parsing errors
            for row_number, row_data in enumerate(csv_reader, start=1):
                if not row_data:  # Check for entirely empty lines
                    print(f"Warning: Empty row found at line {row_number}.")
                    continue
        print(f"CSV file is valid: {os.path.basename(csv_file_path)}")
        return True

    except FileNotFoundError:
        print(f"Error: File not found at path - {csv_file_path}")
        return False

    except csv.Error as error:
        print(f"Error reading CSV structure: {error}")
        return False

    except Exception as unknown_error:
        print(f"Unexpected validation error: {str(unknown_error)}")
        return False


def find_files_by_extension(root_directory: str, file_extension: str) -> list[str]:
    """
    Recursively searches a directory tree and returns a list of full paths
    for files matching a specific extension (e.g., '.csv').

    :param root_directory: The top-level directory to begin the search.
    :param file_extension: The extension to match (e.g., '.csv').
    :return: list of full file paths.
    """
    found_file_paths: list[str] = []  # List to hold the paths of matched files

    # os.walk generates directory names, subdirectory names, and file names in a tree
    for current_folder, _, file_names in os.walk(root_directory):
        for file_name in file_names:
            if file_name.endswith(
                file_extension
            ):  # Check if the file ends with the desired extension
                # Construct the absolute path
                full_path: str = os.path.abspath(
                    os.path.join(current_folder, file_name)
                )
                found_file_paths.append(full_path)

    return found_file_paths


def delete_system_file(file_path: str) -> None:
    """
    Deletes a file from the file system, handling potential errors.

    :param file_path: The absolute or relative path of the file to remove.
    """
    try:
        os.remove(file_path)
        print(f"Successfully removed file: {file_path}")
    except OSError as e:
        print(f"Error removing file {file_path}: {e}")


def split_csv_into_chunks(
    input_file_path: str, max_lines_per_chunk: int = 1000
) -> None:
    """
    Splits a single large CSV file into smaller, chunked files.

    :param input_file_path: Path to the source CSV file.
    :param max_lines_per_chunk: The maximum number of data rows (excluding the header)
                                allowed in each output file.
    """
    # Get necessary components for output file naming
    input_directory: str = os.path.dirname(os.path.abspath(input_file_path))
    base_filename: str = os.path.splitext(os.path.basename(input_file_path))[0]

    with open(input_file_path, "r", newline="") as input_csv:
        csv_reader = csv.reader(input_csv)
        header_row: list[str] = next(csv_reader)  # Read and store the header row

        file_chunk_index: int = 1  # Counter for naming the split files (e.g., _part_1)
        row_buffer: list[list[str]] = []  # Buffer to temporarily store rows

        # Read data row by row
        for line_index, data_row in enumerate(csv_reader, start=1):
            row_buffer.append(data_row)

            # Check if the buffer is full (i.e., lines_read == max_lines_per_chunk)
            if line_index % max_lines_per_chunk == 0:
                # Construct the output filename
                output_chunk_path: str = os.path.join(
                    input_directory,
                    f"{base_filename}_part_{file_chunk_index}.csv",
                )

                # Write the current buffer to a new file
                with open(output_chunk_path, "w", newline="") as output_file:
                    csv_writer = csv.writer(output_file)
                    csv_writer.writerow(header_row)  # Write header first
                    csv_writer.writerows(row_buffer)  # Write all buffered data

                file_chunk_index += 1
                row_buffer = []  # Reset buffer for the next chunk

        # Write any remaining rows that didn't fill a full chunk
        if row_buffer:
            output_chunk_path = os.path.join(
                input_directory,
                f"{base_filename}_part_{file_chunk_index}.csv",
            )
            with open(output_chunk_path, "w", newline="") as output_file:
                csv_writer = csv.writer(output_file)
                csv_writer.writerow(header_row)
                csv_writer.writerows(row_buffer)

            # If the last chunk was written, increment index to get the total count
            file_chunk_index += 1

    print(
        f"CSV split completed for {base_filename}. Total parts created: {file_chunk_index - 1}"
    )


def remove_previous_split_files(folder_path: str) -> None:
    """
    Removes files matching the split file pattern (*_part_#.csv) from a folder.

    :param folder_path: Directory to scan and remove files from.
    """
    # Regex pattern to match files created by the split_csv function
    split_file_pattern = re.compile(r"_part_\d+\.csv$")
    deleted_file_names: list[str] = []

    for file_name in os.listdir(folder_path):
        if split_file_pattern.search(
            file_name
        ):  # Check if the file name matches the pattern
            full_file_path = os.path.join(folder_path, file_name)
            try:
                os.remove(full_file_path)
                deleted_file_names.append(file_name)
            except Exception as deletion_error:
                print(f"Error deleting temporary file {file_name}: {deletion_error}")

    print(f"Clean up complete. Deleted {len(deleted_file_names)} old split files.")


def clean_timestamp_data_inplace(csv_file_path: str) -> None:
    """
    Cleans a CSV file in place by removing extraneous data that follows
    the pattern ',timestamp:' in each line, rewriting the file using a temporary file.

    :param csv_file_path: The path to the CSV file to clean.
    """
    parent_directory: str = os.path.dirname(csv_file_path)
    # Create a temporary file in the same directory
    temp_file_descriptor, temp_file_path = tempfile.mkstemp(
        dir=parent_directory, suffix=".csv"
    )
    os.close(temp_file_descriptor)  # Close the OS file handle

    # Read from original, write to temporary file
    with open(csv_file_path, "r", newline="") as original_file, open(
        temp_file_path, "w", newline=""
    ) as cleaned_file:
        csv_reader = csv.reader(original_file)
        csv_writer = csv.writer(cleaned_file)

        for row in csv_reader:
            row_as_string: str = ",".join(row)
            # Check for the unwanted timestamp string
            if ",timestamp:" in row_as_string:
                # Split the string and keep only the first part
                cleaned_row_string: str = row_as_string.split(",timestamp:")[0]
                # Convert the cleaned string back into a list of CSV fields
                cleaned_row: list[str] = cleaned_row_string.split(",")
                csv_writer.writerow(cleaned_row)
            else:
                # If no timestamp, write the original row
                csv_writer.writerow(row)

    # Atomically replace the original file with the cleaned temporary file
    os.replace(temp_file_path, csv_file_path)
    print(f"Timestamp data cleanup successful for: {os.path.basename(csv_file_path)}")


def get_filenames_from_urls(url_list: list[str]) -> list[str]:
    """
    Extracts just the file names from a list of full URLs.

    :param url_list: list of URLs.
    :return: list of file names (e.g., 'data.csv').
    """
    file_names: list[str] = []

    for url in url_list:
        # Split by '/', take the last element, and strip any surrounding whitespace
        file_name: str = url.strip().split("/")[-1]
        file_names.append(file_name)

    return file_names


def check_file_exists(file_path: str):
    """Simple wrapper to check if a file exists on the system."""
    return os.path.isfile(file_path)


if __name__ == "__main__":
    # --- Configuration ---
    csv_source_urls: list[str] = [
        "https://www.50-a.org/data/nypd/officers.csv",
        "https://www.50-a.org/data/nypd/ranks.csv",
        "https://www.50-a.org/data/nypd/discipline.csv",
        "https://www.50-a.org/data/nypd/documents.csv",
        "https://www.50-a.org/data/nypd/awards.csv",
        "https://www.50-a.org/data/nypd/training.csv",
    ]
    local_storage_directory: str = "./CSV_Data/"  # Folder to save files
    max_chunk_size_lines: int = 1000  # Max number of data lines per split CSV file

    # ----------------------------------------------------
    # --- Data Processing Pipeline ---
    # ----------------------------------------------------

    print("\n--- Starting Data Pipeline ---\n")

    # Step 1: Clean up any files from previous split operations
    print("1. Cleaning old split files...")
    remove_previous_split_files(local_storage_directory)

    # Step 2: Download the source data
    print("\n2. Downloading source CSV files...")
    download_multiple_files(csv_source_urls, local_storage_directory)

    # Step 3: Find all CSV files that were downloaded
    all_downloaded_file_paths: list[str] = find_files_by_extension(
        local_storage_directory, ".csv"
    )

    # Step 4: Process each downloaded CSV file: Validate, Clean, and Split
    print("\n3. Processing, Cleaning, and Splitting files...")
    for csv_file_path in all_downloaded_file_paths:
        file_base_name = os.path.basename(csv_file_path)
        print(f"\nProcessing: {file_base_name}...")

        # A. Validate the CSV integrity
        if not validate_csv_integrity(csv_file_path):
            # Delete file if it appears corrupted
            delete_system_file(csv_file_path)
            print(f"Skipping corrupted file: {file_base_name}")
            continue

        # B. Clean up extraneous timestamp data in place
        clean_timestamp_data_inplace(csv_file_path)

        # C. Split the cleaned CSV into smaller chunks
        split_csv_into_chunks(csv_file_path, max_chunk_size_lines)

    # Step 5: Remove original, large CSV files (as they are now split)
    print("\n4. Removing original source files (now that they are split)...")
    original_file_names = get_filenames_from_urls(csv_source_urls)

    for original_file_name in original_file_names:
        full_original_path = os.path.join(local_storage_directory, original_file_name)
        if check_file_exists(full_original_path):
            delete_system_file(full_original_path)

    print("\n--- Data Pipeline Completed Successfully ---")
