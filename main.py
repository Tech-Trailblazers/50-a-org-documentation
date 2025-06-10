import os
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

if __name__ == "__main__":
    # List of URLs to the CSV files
    urls = [
        "https://www.50-a.org/data/nypd/officers.csv",
        "https://www.50-a.org/data/nypd/ranks.csv"
    ]
    
    # Folder to save the downloaded files
    folder = "CSV"
    
    # Download the files
    download_files(urls, folder)
