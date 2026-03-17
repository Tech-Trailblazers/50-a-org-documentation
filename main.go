package main

import (
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
)

// createOutputDirectory ensures the "CSVs" folder exists.
// If it does not exist, it will be created.
func createOutputDirectory(folderName string) error {
	// os.MkdirAll creates the folder and does nothing if it already exists
	err := os.MkdirAll(folderName, os.ModePerm)
	if err != nil {
		return err
	}

	log.Printf("Using output directory: %s\n", folderName)
	return nil
}

// getFileNameFromURL extracts the file name from a URL.
func getFileNameFromURL(fileURL string) (string, error) {
	parsedURL, err := url.Parse(fileURL)
	if err != nil {
		return "", err
	}

	fileName := path.Base(parsedURL.Path)
	if fileName == "" || fileName == "/" {
		return "", err
	}

	return fileName, nil
}

// downloadFile downloads a file and saves it into the specified folder.
func downloadFile(fileURL string, outputFolder string) error {
	// Get the file name from the URL
	fileName, err := getFileNameFromURL(fileURL)
	if err != nil {
		return err
	}

	// Build the full path: CSVs/filename.csv
	fullFilePath := path.Join(outputFolder, fileName)

	// Send HTTP request
	response, err := http.Get(fileURL)
	if err != nil {
		return err
	}
	defer response.Body.Close()

	// Ensure the request succeeded
	if response.StatusCode != http.StatusOK {
		return err
	}

	// Create the file in the target directory
	outputFile, err := os.Create(fullFilePath)
	if err != nil {
		return err
	}
	defer outputFile.Close()

	// Copy the response body into the file
	_, err = io.Copy(outputFile, response.Body)
	if err != nil {
		return err
	}

	log.Printf("Downloaded: %s\n", fullFilePath)
	return nil
}

func main() {
	// Folder where all CSV files will be stored
	outputFolder := "CSVs"

	// Create the folder before downloading anything
	err := createOutputDirectory(outputFolder)
	if err != nil {
		log.Fatalf("Failed to create output directory: %v\n", err)
	}

	// List of file URLs to download
	fileURLs := []string{
		"https://www.50-a.org/data/nypd/officers.csv",
		// "https://www.50-a.org/data/nypd/ranks.csv",
		// "https://www.50-a.org/data/nypd/discipline.csv",
		// "https://www.50-a.org/data/nypd/documents.csv",
		// "https://www.50-a.org/data/nypd/awards.csv",
		// "https://www.50-a.org/data/nypd/training.csv",
	}

	// Download each file into the CSVs folder
	for _, fileURL := range fileURLs {
		log.Printf("Starting download: %s\n", fileURL)

		err := downloadFile(fileURL, outputFolder)
		if err != nil {
			log.Printf("Failed to download %s: %v\n", fileURL, err)
		}
	}
}