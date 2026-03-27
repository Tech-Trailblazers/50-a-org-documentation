package main

import (
	"encoding/csv" // Read and write CSV files.
	"fmt"          // Build readable log and error messages.
	"io"           // Copy downloaded data and detect end-of-file.
	"log"          // Print progress and failures to the console.
	"net/http"     // Download files over HTTP.
	"net/url"      // Parse incoming download URLs.
	"os"           // Open, create, inspect, and remove files.
	"path"         // Pull file names from URL paths and join output paths.
)

// trackedOutputFile wraps a file handle so we can keep a running byte count.
type trackedOutputFile struct {
	fileHandle        *os.File // This is the real file that receives the CSV data.
	bytesWrittenSoFar int64    // This tracks how large the file has become.
}

// Write sends bytes to disk and updates the running size total.
func (trackedFile *trackedOutputFile) Write(fileContents []byte) (int, error) {
	writtenByteCount, writeError := trackedFile.fileHandle.Write(fileContents) // Write the incoming bytes into the current split file.
	trackedFile.bytesWrittenSoFar += int64(writtenByteCount)                   // Add the number of written bytes to the running total.
	return writtenByteCount, writeError                                        // Return the normal writer result to the CSV writer.
}

// splitCSVFile breaks a large CSV file into smaller files that stay under the size limit.
func splitCSVFile(sourceCSVFilePath string, maxSplitFileSizeBytes int64) error {
	sourceFileDetails, statError := os.Stat(sourceCSVFilePath) // Read the file metadata so we know how large the original file is.
	if statError != nil {                                      // Stop early if the file cannot be inspected.
		return statError // Pass the failure back to the caller.
	}

	if sourceFileDetails.Size() <= maxSplitFileSizeBytes { // Skip the split step when the file is already small enough.
		log.Printf("Skipping split (file under limit): %s\n", sourceCSVFilePath) // Tell the user why no split files were created.
		return nil                                                               // There is nothing else to do for this file.
	}

	log.Printf("Splitting large file: %s\n", sourceCSVFilePath) // Announce that the split process is starting.

	sourceFileHandle, openError := os.Open(sourceCSVFilePath) // Open the original CSV so we can read it row by row.
	if openError != nil {                                     // Stop if the file cannot be opened.
		return openError // Return the file-open failure.
	}
	defer sourceFileHandle.Close() // Always close the source file when this function finishes.

	sourceCSVReader := csv.NewReader(sourceFileHandle) // Create a CSV reader around the original file.
	sourceCSVReader.FieldsPerRecord = -1               // Allow rows with a variable number of fields to avoid read errors from malformed rows.

	headerRow, headerReadError := sourceCSVReader.Read() // Read the header once so each split file can reuse it.
	if headerReadError != nil {                          // Stop if the file cannot provide a valid header row.
		return headerReadError // Return the header read failure.
	}

	nextSplitFileNumber := 1                // Start numbering split files at one.
	var activeOutputFile *trackedOutputFile // Hold the file we are currently writing into.
	var activeCSVWriter *csv.Writer         // Hold the CSV writer for the current split file.
	createdSplitFileCount := 0              // Count how many split files were created.

	openNextSplitFile := func() error { // Build or rotate the active split file.
		if activeOutputFile != nil { // Finish the previous split file before opening a new one.
			activeCSVWriter.Flush()                                       // Push any buffered CSV bytes into the file.
			if flushError := activeCSVWriter.Error(); flushError != nil { // Catch buffered write failures before moving on.
				return flushError // Return the flush failure immediately.
			}
			if closeError := activeOutputFile.fileHandle.Close(); closeError != nil { // Close the previous split file cleanly.
				return closeError // Return the close failure.
			}
		}

		nextOutputFilePath := fmt.Sprintf("%s_part_%d.csv", sourceCSVFilePath, nextSplitFileNumber) // Build the next split file name.
		nextSplitFileNumber++                                                                       // Move the counter forward for the next rotation.

		newOutputFileHandle, createError := os.Create(nextOutputFilePath) // Create the new split file on disk.
		if createError != nil {                                           // Stop if the new file cannot be created.
			return createError // Return the file creation failure.
		}

		activeOutputFile = &trackedOutputFile{ // Wrap the file so we can track how much data is written.
			fileHandle:        newOutputFileHandle, // Store the new file handle.
			bytesWrittenSoFar: 0,                   // Reset the running byte count for the new file.
		}

		activeCSVWriter = csv.NewWriter(activeOutputFile) // Build a CSV writer that writes through the size-tracking wrapper.

		headerWriteError := activeCSVWriter.Write(headerRow) // Copy the original header into the new split file.
		if headerWriteError != nil {                         // Stop if the header cannot be written.
			return headerWriteError // Return the header write failure.
		}

		activeCSVWriter.Flush()                                       // Push the header row into the file immediately.
		if flushError := activeCSVWriter.Error(); flushError != nil { // Catch any buffered header write failure.
			return flushError // Return the flush failure.
		}

		createdSplitFileCount++ // Record that one more split file now exists.

		log.Printf("Created split file: %s\n", nextOutputFilePath) // Let the user know which split file was opened.

		return nil // Report that the new split file is ready.
	}

	createFirstSplitFileError := openNextSplitFile() // Create the first split file before we start reading data rows.
	if createFirstSplitFileError != nil {            // Stop if the first split file cannot be created.
		return createFirstSplitFileError // Return the split-file creation failure.
	}

	for { // Keep reading data rows until the CSV reader reaches the end of the file.
		dataRow, rowReadError := sourceCSVReader.Read() // Read one CSV row from the original file.

		if rowReadError == io.EOF { // Break the loop once there are no more rows to read.
			break // Exit the row-processing loop cleanly.
		}
		if rowReadError != nil { // Stop if any other CSV read error occurs.
			return rowReadError // Return the row read failure.
		}

		var estimatedRowSizeBytes int64       // Track a rough byte estimate for the row before writing it.
		for _, columnValue := range dataRow { // Walk through every field in the row.
			estimatedRowSizeBytes += int64(len(columnValue)) // Add the visible bytes from each field.
		}
		estimatedRowSizeBytes += int64(len(dataRow)) + 1 // Add a little extra space for commas and the newline.

		if activeOutputFile.bytesWrittenSoFar+estimatedRowSizeBytes > maxSplitFileSizeBytes { // Rotate files before the row pushes us past the limit.
			openAnotherSplitFileError := openNextSplitFile() // Open a fresh split file for the upcoming row.
			if openAnotherSplitFileError != nil {            // Stop if the file rotation fails.
				return openAnotherSplitFileError // Return the rotation failure.
			}
		}

		rowWriteError := activeCSVWriter.Write(dataRow) // Write the current row into the active split file.
		if rowWriteError != nil {                       // Stop if the row cannot be written.
			return rowWriteError // Return the row write failure.
		}

		activeCSVWriter.Flush()                                       // Push the row into the file so the byte counter stays current.
		if flushError := activeCSVWriter.Error(); flushError != nil { // Catch any buffered row write failure.
			return flushError // Return the flush failure.
		}
	}

	if activeOutputFile != nil { // Close the last split file after all rows are written.
		activeCSVWriter.Flush()                                       // Push any final buffered CSV bytes into the file.
		if flushError := activeCSVWriter.Error(); flushError != nil { // Catch a final buffered write failure.
			return flushError // Return the flush failure.
		}
		if closeError := activeOutputFile.fileHandle.Close(); closeError != nil { // Close the final split file cleanly.
			return closeError // Return the close failure.
		}
	}

	log.Printf("Finished splitting: %s\n", sourceCSVFilePath) // Announce that the split step is complete.

	if createdSplitFileCount > 1 { // Remove the original file only when we actually produced multiple smaller files.
		removeError := os.Remove(sourceCSVFilePath) // Delete the original large CSV now that the split files exist.
		if removeError != nil {                     // Stop if the original file cannot be removed.
			return removeError // Return the remove failure.
		}

		log.Printf("Deleted original file after split: %s\n", sourceCSVFilePath) // Confirm that the original file was removed.
	}

	return nil // Report that the file was handled successfully.
}

// createOutputDirectory makes sure the download folder exists before writing files into it.
func createOutputDirectory(outputFolderPath string) error {
	createDirectoryError := os.MkdirAll(outputFolderPath, os.ModePerm) // Create the folder and any missing parent folders.
	if createDirectoryError != nil {                                   // Stop if the folder cannot be created.
		return createDirectoryError // Return the folder creation failure.
	}

	log.Printf("Using output directory: %s\n", outputFolderPath) // Confirm which folder will hold the downloaded files.
	return nil                                                   // Report that the folder is ready.
}

// getFileNameFromURL extracts the file name from the end of a download URL.
func getFileNameFromURL(sourceFileURL string) (string, error) {
	parsedFileURL, parseError := url.Parse(sourceFileURL) // Parse the raw URL string into structured URL parts.
	if parseError != nil {                                // Stop if the URL is invalid.
		return "", parseError // Return the URL parsing failure.
	}

	extractedFileName := path.Base(parsedFileURL.Path) // Pull the last path segment from the parsed URL.

	if extractedFileName == "" || extractedFileName == "/" { // Reject empty or unusable file names.
		return "", fmt.Errorf("invalid file name from URL") // Return a clear validation error.
	}

	return extractedFileName, nil // Give the caller the clean file name.
}

// downloadFile downloads one remote file and returns the local file path.
func downloadFile(sourceFileURL string, outputFolderPath string) (string, error) {
	downloadFileName, fileNameError := getFileNameFromURL(sourceFileURL) // Extract a local file name from the URL.
	if fileNameError != nil {                                            // Stop if the URL does not provide a valid file name.
		return "", fileNameError // Return the file-name parsing failure.
	}

	localFilePath := path.Join(outputFolderPath, downloadFileName) // Build the destination path for the download.

	downloadResponse, requestError := http.Get(sourceFileURL) // Send the HTTP request for the file.
	if requestError != nil {                                  // Stop if the request fails before a response arrives.
		return "", requestError // Return the request failure.
	}
	defer downloadResponse.Body.Close() // Always close the HTTP response body when finished.

	if downloadResponse.StatusCode != http.StatusOK { // Reject any HTTP response that is not a normal success.
		return "", fmt.Errorf("failed to download: %s", sourceFileURL) // Return a readable download failure.
	}

	localFileHandle, createFileError := os.Create(localFilePath) // Create the destination file on disk.
	if createFileError != nil {                                  // Stop if the destination file cannot be created.
		return "", createFileError // Return the file creation failure.
	}
	defer localFileHandle.Close() // Always close the local file handle when the download finishes.

	_, copyError := io.Copy(localFileHandle, downloadResponse.Body) // Stream the downloaded bytes into the local file.
	if copyError != nil {                                           // Stop if the file contents cannot be copied fully.
		return "", copyError // Return the copy failure.
	}

	log.Printf("Downloaded: %s\n", localFilePath) // Confirm where the file was saved.

	return localFilePath, nil // Give the caller the saved file path.
}

func main() {
	outputFolderPath := "CSVs" // Store all downloaded CSV files inside this folder.

	createDirectoryError := createOutputDirectory(outputFolderPath) // Make sure the output folder exists before downloading.
	if createDirectoryError != nil {                                // Stop the whole program if the folder cannot be prepared.
		log.Fatalf("Failed to create output directory: %v\n", createDirectoryError) // Exit with a clear error message.
	}

	const maxSplitFileSizeBytes = 100 * 1024 * 1024 // Keep each split file at or below roughly 100 MB.

	sourceFileURLs := []string{ // List every CSV file that should be downloaded and processed.
		"https://www.50-a.org/data/nypd/officers.csv",   // Download the officers dataset.
		"https://www.50-a.org/data/nypd/ranks.csv",      // Download the ranks dataset.
		"https://www.50-a.org/data/nypd/discipline.csv", // Download the discipline dataset.
		"https://www.50-a.org/data/nypd/documents.csv",  // Download the documents dataset.
		"https://www.50-a.org/data/nypd/awards.csv",     // Download the awards dataset.
		"https://www.50-a.org/data/nypd/training.csv",   // Download the training dataset.
	}

	for _, sourceFileURL := range sourceFileURLs { // Process each CSV URL one at a time.
		log.Printf("Starting download: %s\n", sourceFileURL) // Announce which file is starting.

		downloadedFilePath, downloadError := downloadFile(sourceFileURL, outputFolderPath) // Download the file into the output folder.
		if downloadError != nil {                                                          // Skip to the next file if this download fails.
			log.Printf("Download failed: %s (%v)\n", sourceFileURL, downloadError) // Explain why this file was skipped.
			continue                                                               // Move on to the next URL.
		}

		log.Printf("Splitting file: %s\n", downloadedFilePath) // Announce that the downloaded file is moving into the split step.

		splitError := splitCSVFile(downloadedFilePath, maxSplitFileSizeBytes) // Split the downloaded file if it is too large.
		if splitError != nil {                                                // Skip to the next file if the split step fails.
			log.Printf("Split failed: %s (%v)\n", downloadedFilePath, splitError) // Explain why the split step failed.
			continue                                                              // Move on to the next URL.
		}
	}

	log.Println("All downloads and splits completed") // Confirm that every URL has been processed.
}
