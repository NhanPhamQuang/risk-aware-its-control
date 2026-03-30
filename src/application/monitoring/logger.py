import csv

def log(data):
    with open("outputs/logs/log.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerow(data)
