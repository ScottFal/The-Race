import json


def openJsonFile(filePath):
    try:
        with open(filePath, 'r', encoding='utf-8') as jsonFile:
            data = json.load(jsonFile)
        return data
    except FileNotFoundError:
        print(f"File '{filePath}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file '{filePath}'.")
        return None


def writeToJsonFile(filePath, data):
    try:
        with open(filePath, 'w') as jsonFile:
            json.dump(data, jsonFile, indent=2)
    except json.JSONDecodeError:
        print(f"Error encoding JSON data to file '{filePath}'.")
