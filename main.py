import csv
import os
import re
import tempfile


def split_csv(input_file, lines_per_file=5000):
    base_dir = os.path.dirname(os.path.abspath(input_file))
    file_base = os.path.splitext(os.path.basename(input_file))[0]

    with open(input_file, "r", newline="") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)

        file_count = 1
        rows = []

        for i, row in enumerate(reader, 1):
            rows.append(row)
            if i % lines_per_file == 0:
                out_path = os.path.join(base_dir, f"{file_base}_part_{file_count}.csv")
                with open(out_path, "w", newline="") as out_file:
                    writer = csv.writer(out_file)
                    writer.writerow(header)
                    writer.writerows(rows)
                file_count += 1
                rows = []

        # Write any remaining rows
        if rows:
            out_path = os.path.join(base_dir, f"{file_base}_part_{file_count}.csv")
            with open(out_path, "w", newline="") as out_file:
                writer = csv.writer(out_file)
                writer.writerow(header)
                writer.writerows(rows)

    print(f"Done! CSV split into {file_count} parts.")


def remove_split_files(folder_path):
    pattern = re.compile(r"_part_\d+\.csv$")

    deleted_files = []

    for filename in os.listdir(folder_path):
        if pattern.search(filename):
            file_path = os.path.join(folder_path, filename)
            try:
                os.remove(file_path)
                deleted_files.append(filename)
            except Exception as e:
                print(f"Error deleting {filename}: {e}")

    print(f"Deleted {len(deleted_files)} files.")
    if deleted_files:
        print("Files removed:")
        for f in deleted_files:
            print(f"  - {f}")


def remove_after_timestamp_inplace(csv_path):
    """
    Edits the given CSV file in-place, removing everything after ',timestamp:' in each line.
    """
    # Create a temporary file in the same directory
    dir_name = os.path.dirname(csv_path)
    temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".csv")
    os.close(temp_fd)  # Close file descriptor as we'll use `open`

    with open(csv_path, "r", newline="") as infile, open(
        temp_path, "w", newline=""
    ) as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            # Join the row to a string to search for ',timestamp:'
            joined_row = ",".join(row)
            if ",timestamp:" in joined_row:
                cleaned = joined_row.split(",timestamp:")[0]
                new_row = cleaned.split(",")
            else:
                new_row = row
            writer.writerow(new_row)

    # Replace the original file with the cleaned version
    os.replace(temp_path, csv_path)
    print(f"Cleaned in-place: {csv_path}")


# Example usage
split_csv("CSV/ranks.csv")
remove_split_files("CSV/")
# remove_after_timestamp_inplace("CSV/ranks.csv")
