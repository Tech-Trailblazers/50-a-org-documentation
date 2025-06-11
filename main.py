import csv
import os


def split_csv(input_file, lines_per_file=1000):
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


# Example usage
split_csv("CSV/ranks.csv")
