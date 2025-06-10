import os
import csv
import requests


def download_file(url: str, save_path: str) -> None:
    """
    Downloads a file from a given URL and saves it to the specified path.

    :param url: The URL of the file to download.
    :param save_path: The path where the file should be saved.
    """
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful
    with open(save_path, "wb") as file:
        file.write(response.content)
    print(f"Downloaded {url} to {save_path}")


def download_files(urls: list[str], folder: str) -> None:
    """
    Downloads a list of files from URLs and saves them in the specified folder.

    :param urls: A list of URLs of the files to download.
    :param folder: The folder where the files will be saved.
    """
    # Create the folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)

    for url in urls:
        file_name = url.split("/")[-1]  # Get the file name from the URL
        save_path = os.path.join(folder, file_name)  # Path to save the file
        download_file(url, save_path)


def validate_csv(file_path: str) -> bool:
    try:
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row_num, row in enumerate(reader, start=1):
                # Just check if the row can be read; no assumptions about structure
                if not row:  # Empty rows might be problematic
                    print(f"Warning: Empty row at line {row_num}.")
                    continue
                # You could add a simple check like the following, depending on your needs:
                # if len(row) < 1:  # e.g., if the row has no data at all, consider it an issue
                #     raise ValueError(f"Row {row_num} seems to be empty or malformed.")

        print("CSV file is valid (no corruption detected).")
        return True

    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return False

    except csv.Error as e:
        print(f"Error: CSV file is malformed at line {e.args[0]} - {e.args[1]}")
        return False

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False


# Function to recursively search a directory and return files with the given extension
def walk_directory_and_extract_given_file_extension(
    system_path: str, extension: str
) -> list[str]:
    matched_files = []  # List to store matched files
    for root, _, files in os.walk(system_path):  # Traverse directories recursively
        for file in files:  # Loop through each file
            if file.endswith(extension):  # Check for matching extension
                full_path = os.path.abspath(
                    os.path.join(root, file)
                )  # Get absolute path
                matched_files.append(full_path)  # Add to result list
    return matched_files  # Return list of matched files


# Function to remove a file from the filesystem
def remove_system_file(system_path: str) -> None:
    os.remove(system_path)  # Delete the file


if __name__ == "__main__":
    # List of URLs to the CSV files
    urls = [
        "https://www.50-a.org/data/nypd/officers.csv",
        "https://www.50-a.org/data/nypd/ranks.csv",
        "https://www.50-a.org/data/nypd/discipline.csv",
        "https://www.50-a.org/data/nypd/documents.csv",
        "https://www.50-a.org/data/nypd/awards.csv",
    ]

    # Folder to save the downloaded files
    folder = "CSV"

    # Download the files
    download_files(urls, folder)

    # Get all the CSV files.
    csv_files = walk_directory_and_extract_given_file_extension(
        "./CSV", ".csv"
    )  # Find all PDFs

    for csv_file in csv_files:  # Loop through each PDF file
        if not validate_csv(csv_file):  # If PDF is invalid
            remove_system_file(csv_file)  # Delete corrupt PDF
