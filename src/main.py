import json
import math
from datetime import datetime, timedelta
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import os
import disnake
import numpy as np
import pytz
from disnake import ApplicationCommandInteraction
from disnake.ext import commands, tasks
import time
import requests
from PIL import ImageFont
from PIL import Image, ImageDraw
from table2ascii import table2ascii as t2a, PresetStyle
from dotenv import load_dotenv

load_dotenv()
riotApKey = os.getenv("RIOT_API_KEY")
discordToken = os.getenv("DISCORD_TOKEN")
discordChannel = int(os.getenv("DISCORD_CHANNEL"))
requestLimit = int(os.getenv("REQUESTS"))
dailyPostTimer = int(os.getenv("DAILY"))

jsonFile = "data.json"

platforms = ["BR1", "EUN1", "EUW1", "JP1", "KR", "LA1", "LA2", "NA1", "OC1", "TR1", "RU", "PH2", "SG2", "TH2", "TW2", "VN2"]
regions = ["AMERICAS", "EUROPE", "ASIA", "SEA"]
version = requests.get('https://ddragon.leagueoflegends.com/api/versions.json').json()[0]

statisticsForMvp = {
    "killParticipation": 1,
    "kda": 1.2,
    "totalDamageDealtToChampions": 1,
    "damageDealtToBuildings": 0.7,
    "totalDamageTaken": 0.7,
    "goldPerMinute": 1,
    "visionScore": 1
}

bot = commands.InteractionBot()


class Rank:
    tierOrder = {
        'IRON': 1,
        'BRONZE': 2,
        'SILVER': 3,
        'GOLD': 4,
        'PLATINUM': 5,
        'EMERALD': 6,
        'DIAMOND': 7,
        'MASTER': 8,
        'GRANDMASTER': 9,
        'CHALLENGER': 10
    }

    rankOrder = {'IV': 1, 'III': 2, 'II': 3, 'I': 4}

    iconPath = {
        'IRON': 'Imgs/Ranks/Iron.png',
        'BRONZE': 'Imgs/Ranks/Bronze.png',
        'SILVER': 'Imgs/Ranks/Silver.png',
        'GOLD': 'Imgs/Ranks/Gold.png',
        'PLATINUM': 'Imgs/Ranks/Platinum.png',
        'EMERALD': 'Imgs/Ranks/Emerald.png',
        'DIAMOND': 'Imgs/Ranks/Diamond.png',
        'MASTER': 'Imgs/Ranks/Master.png',
        'GRANDMASTER': 'Imgs/Ranks/Grandmaster.png',
        'CHALLENGER': 'Imgs/Ranks/Challenger.png'
    }

    def rankToNumber(rank):
        if isinstance(rank, int):
            return str(f"#{rank}")

        rank_map = {'I': '1', 'II': '2', 'III': '3', 'IV': '4'}
        if rank in rank_map:
            return rank_map[rank]
        else:
            return None

    def calculateScore(tier, rank, leaguepoints):
        tierPoints = (Rank.tierOrder[tier] - 1) * 400
        rankPoints = (Rank.rankOrder[rank] - 1) * 100

        if tier == "MASTER":
            tierPoints -= 300
        if tier == "GRANDMASTER":
            tierPoints -= 700
        if tier == "CHALLENGER":
            tierPoints -= 1100

        totalPoints = tierPoints + rankPoints + leaguepoints
        return totalPoints


class Summoner:

    def __init__(self):
        self.rank = None
        self.tier = None
        self.leaguePoints = None
        self.series = None
        self.seriesWins = None
        self.seriesLosses = None

        self.wins = None
        self.losses = None
        self.hotStreak = None
        self.MvpScoreTotal = None
        self.hasCrown = None

        self.fullName = None
        self.name = None
        self.tagline = None
        self.id = None
        self.puuid = None
        self.Platform = None
        self.region = None

        self.score = None
        self.previousScore = None
        self.leaderboardPosition = None
        self.previousLeaderboardPosition = None
        self.gamesPlayed = None
        self.previousGamesPlayed = None
        self.dailyScore = None
        self.dailyLeaderboardPosition = None
        self.dailyGamesPlayed = None

        self.deltaScore = 0
        self.deltaDailyScore = 0
        self.deltaDailyLeaderboardPosition = 0
        self.deltaLeaderboardPosition = 0
        self.deltaGamesPlayed = 0
        self.deltaDailyGamesPlayed = 0

        self.game1Kills = None
        self.game1Deaths = None
        self.game1Assists = None
        self.game1Win = None
        self.game1Mvp = None
        self.game1Mvp = None
        self.game1MvpScore = None
        self.game1Remake = None
        self.game1Champion = None
        self.game1GameLength = None
        self.game1DamageDealtToChampions = None

        self.game2Kills = None
        self.game2Deaths = None
        self.game2Assists = None
        self.game2Win = None
        self.game2Mvp = None
        self.game2MvpScore = None
        self.game2Remake = None
        self.game2Champion = None
        self.game2GameLength = None
        self.game2DamageDealtToChampions = None

        self.game3Kills = None
        self.game3Deaths = None
        self.game3Assists = None
        self.game3Win = None
        self.game3Mvp = None
        self.game3MvpScore = None
        self.game3Remake = None
        self.game3Champion = None
        self.game3GameLength = None
        self.game3DamageDealtToChampions = None

        self.game4Kills = None
        self.game4Deaths = None
        self.game4Assists = None
        self.game4Win = None
        self.game4Mvp = None
        self.game4MvpScore = None
        self.game4Remake = None
        self.game4Champion = None
        self.game4GameLength = None
        self.game4DamageDealtToChampions = None

        self.game5Kills = None
        self.game5Deaths = None
        self.game5Assists = None
        self.game5Win = None
        self.game5Mvp = None
        self.game5MvpScore = None
        self.game5Remake = None
        self.game5Champion = None
        self.game5GameLength = None
        self.game5DamageDealtToChampions = None


def checkForNewPatchNotes(jsonFilePath, forceUpdate):
    # Function to download image from URL
    def downloadImage(imageUrl, saveDir):
        response = requests.get(imageUrl)
        if response.status_code == 200:
            # Create the directory if it doesn't exist
            os.makedirs(saveDir, exist_ok=True)

            # Parse the URL to remove query parameters
            parsedUrl = urlparse(imageUrl)
            cleanedFilename = os.path.basename(unquote(parsedUrl.path))

            # Split the filename and extension
            filenameParts = cleanedFilename.split('.')
            if len(filenameParts) > 1:
                # Use the last part as the file extension
                fileExtension = filenameParts[-1]
                # Construct the full path to save the image with correct extension
                savePath = os.path.join(saveDir, f"patch_image.{fileExtension}")
                # Save the image
                with open(savePath, 'wb') as f:
                    f.write(response.content)
                return True, savePath
            else:
                print("Failed to extract file extension from image URL.")
                return False, None
        else:
            print("Failed to download image.")
            return False, None

    # Load latest patch version from JSON file
    with open(jsonFilePath, "r") as f:
        latestPatchData = json.load(f)
        latestPatch = latestPatchData.get("latestPatch")

    # URL of the League of Legends patch notes page
    url = "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/"

    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the first element with class="style__List-sc-106zuld-2 cGSeTq"
    firstElement = soup.find(class_="style__List-sc-106zuld-2 cGSeTq")

    if firstElement:
        # Find the <h2> element with the specified data-testid and class attributes
        patchTitle = firstElement.find("h2", {"data-testid": "articlelist:article-0:title", "class": "style__Title-sc-1h41bzo-8 hvOSAW"})

        if patchTitle:
            # Extract the URL from the href attribute of the <a> tag enclosing the title
            patchUrl = patchTitle.find_parent("a")["href"]
            fullUrl = "https://www.leagueoflegends.com" + patchUrl

            # Extract patch number from title
            newPatch = patchTitle.text.split()[1]

            timeElement = soup.find("time")
            datetimeStr = timeElement["datetime"]
            datetimeObjDate = datetime.strptime(datetimeStr[:10], "%Y-%m-%d").date()
            dateNow = datetime.now().date()
            # dateNow = datetime(2024, 2, 20).date()

            daysDifference = abs((datetimeObjDate - dateNow).days)
            daysAgo = daysDifference - 1
            nextPatchDate = datetimeObjDate + timedelta(weeks=2)
            daysUntilNextPatch = (nextPatchDate - dateNow).days
            daysUntilNextPatch += 1  # Add 1 to include the current day

            # Check if the new patch is newer than the one stored in JSON
            if (float(newPatch) > float(latestPatch)) or forceUpdate:
                # Send a GET request to the patch notes URL
                patchResponse = requests.get(fullUrl)
                patchSoup = BeautifulSoup(patchResponse.content, "html.parser")

                # Search for the image by filename
                imageTags = patchSoup.find_all("img", src=lambda src: src and "highlights" in src.lower())
                if imageTags:
                    # Assuming the first image found is the correct one
                    imageUrl = imageTags[0]["src"]
                    # Download the image
                    imgDownloaded, imgPath = downloadImage(imageUrl, "imgs/patch highlights")
                    if imgDownloaded:
                        # Update latest patch in JSON file
                        latestPatchData["latestPatch"] = newPatch
                        with open(jsonFilePath, "w") as f:
                            json.dump(latestPatchData, f, indent=2)
                            # print("Updated latest patch to:", newPatch)
                        return True, newPatch, daysAgo, daysUntilNextPatch, fullUrl, imgPath  # Return True, updated patch version, and image path

    return False, None, daysAgo, daysUntilNextPatch, None, None  # Return False if there's no update or encountered an error


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


def drawChampionImage(canvas, x, y, champ, win, remake, mvp):
    champName = "Fiddlesticks" if champ == "FiddleSticks" else champ
    imgPath = f"Imgs/Champ icons/{champName}.png"

    # Check if the image is already downloaded
    if os.path.exists(imgPath):
        img = Image.open(imgPath).convert("RGBA")
    else:
        # Download the image from the internet
        response = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champName}.png")
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        # Save the image for future use
        os.makedirs(os.path.dirname(imgPath), exist_ok=True)
        img.save(imgPath)

    # Crop the edges 5%
    width, height = img.size
    left = int(width * 0.05)
    top = int(height * 0.05)
    right = int(width * 0.95)
    bottom = int(height * 0.95)
    img = img.crop((left, top, right, bottom))

    # Make the image round
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
    img.putalpha(mask)

    # Add a stroke around the circle
    draw = ImageDraw.Draw(img)
    if remake:
        strokeColor = (40, 40, 48)
    else:
        if win:
            if mvp:
                mvp = Image.open("Imgs/mvp win.png").convert("RGBA")
                canvas.paste(mvp, (x + 80, y + 80), mvp)
                strokeColor = (255, 255, 0)
            else:
                strokeColor = (0, 255, 0)
        else:
            # if mvp:
            #     mvp = Image.open("Imgs/mvp loss.png").convert("RGBA")
            #     canvas.paste(mvp, (x + 80, y + 80), mvp)
            strokeColor = (255, 0, 0)

    strokeWidth = 4
    draw.ellipse((0, 0, img.size[0], img.size[1]), outline=strokeColor, width=strokeWidth)

    # Resize the image to 100x100
    img = img.resize((100, 100))

    # Paste the image onto the canvas at the specified coordinates
    canvas.paste(img, (x, y), img)


def drawURLImage(canvas, url, x, y, w=0, opacity=1.0, cropTop=None, cropBottom=None, makeRound=False):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    img = img.convert("RGBA")

    # Crop the top and bottom of the image
    if cropTop is not None and cropBottom is not None:
        height = img.size[1]
        top = int(height * cropTop)
        bottom = int(height * (1 - cropBottom))
        img = img.crop((0, top, img.size[0], bottom))

    if w != 0:
        # Resize the image
        newWidth = w
        widthPercent = (newWidth / float(img.size[0]))
        newHeight = int((float(img.size[1]) * float(widthPercent)))
        img = img.resize((newWidth, newHeight))

    if makeRound:
        # Create a circular mask
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)

        # Apply the mask to the image
        img.putalpha(mask)

    if opacity != 1:
        img.putalpha(int(255 * opacity))

    canvas.paste(img, (x, y), img)


def drawFileImage(canvas, file, x, y, w=0, opacity=1.0, cropTop=None, cropBottom=None):
    img = Image.open(file)
    img = img.convert("RGBA")

    if cropTop != None and cropBottom != None:
        # Crop the top and bottom of the image
        height = img.size[1]
        top = int(height * cropTop)
        bottom = int(height * (1 - cropBottom))
        img = img.crop((0, top, img.size[0], bottom))

    if w != 0:
        # Resize the image
        newWidth = w
        widthPercent = (newWidth / float(img.size[0]))
        newHeight = int((float(img.size[1]) * float(widthPercent)))
        img = img.resize((newWidth, newHeight))

    if opacity != 1:
        img.putalpha(int(255 * opacity))

    canvas.paste(img, (x, y), img)


def drawTextCentered(canvas, text, x, y, font, colour=((255, 255, 255))):
    # Get the size of the text using the provided font
    draw = ImageDraw.Draw(canvas)
    textBbox = draw.textbbox((x, y), text, font=font)

    # Calculate the x and y positions to center the text
    centerX = x - (textBbox[2] - textBbox[0]) / 2
    centerY = y - (textBbox[3] - textBbox[1]) / 2

    # Draw the text at the center position with the specified opacity
    draw.text((centerX, centerY), text, colour, font=font)


def formatTime(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds}s"


def formatDamage(damage):
    return "{:,}".format(damage)


def numberOfSummoners(wiggleRoom):
    jsonFata = openJsonFile(jsonFile)
    count = len(jsonFata['summoners']) + wiggleRoom
    return count


def calculateZScore(value, multiplier, mean, std):
    if mean is None or std is None or std == 0:
        return 0
    return ((value - mean) / std) * multiplier


def calculateMeanAndStd(data, matchId, stat):
    values = []
    for participant in data["matchData"][matchId]["info"]['participants']:
        if 'challenges' in participant and stat in participant['challenges']:
            values.append(participant['challenges'][stat])
        elif stat in participant:
            values.append(participant[stat])
    if not values:
        return None, None

    return np.mean(values), np.std(values)


def crownData():
    summoners = []
    jsonData = openJsonFile(jsonFile)

    for summonerName in jsonData["summoners"]:
        allMatchesIds = []
        summoner = Summoner()

        summoner.fullName = summonerName
        summoner.puuid = jsonData["summoners"][summonerName]["puuid"]
        summoner.region = jsonData["summoners"][summonerName]["region"]
        summoner.platform = jsonData["summoners"][summonerName]["platform"]

        riotApiData = requests.get(f'https://{summoner.region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner.puuid}/ids?queue=420&start=0&count=5&api_key={riotApKey}').json()
        for i, matchId in enumerate(riotApiData):
            allMatchesIds.append(matchId)
            if matchId in jsonData["matchData"]:
                # print(f"Found {matchId} in json")
                fetchMatchData(i, summoner, jsonData, matchId)
            else:
                # print(f'Fetching {matchId}')
                success = False
                matchData = None
                while not success:
                    response = requests.get(f'https://{summoner.region}.api.riotgames.com/lol/match/v5/matches/{matchId}?api_key={riotApKey}')
                    if response.status_code == 200:
                        matchData = response.json()
                        success = True
                    else:
                        print("No match data, trying again in 125 seconds")
                        time.sleep(125)

                jsonData["matchData"][matchId] = matchData

                fetchMatchData(i, summoner, jsonData, matchId)

        summoner.MvpScoreTotal = summoner.game1MvpScore + summoner.game2MvpScore + summoner.game3MvpScore + summoner.game4MvpScore + summoner.game5MvpScore
        summoners.append(summoner)

    summoners.sort(key=lambda s: s.MvpScoreTotal, reverse=True)

    tableData = []
    for index, summoner in enumerate(summoners, start=1):
        row = [
            summoner.fullName,
            index,
            round(summoner.MvpScoreTotal, 2),
            f"{round(summoner.game1MvpScore, 2)}*" if summoner.game1Mvp else round(summoner.game1MvpScore, 2),
            f"{round(summoner.game2MvpScore, 2)}*" if summoner.game2Mvp else round(summoner.game2MvpScore, 2),
            f"{round(summoner.game3MvpScore, 2)}*" if summoner.game3Mvp else round(summoner.game3MvpScore, 2),
            f"{round(summoner.game4MvpScore, 2)}*" if summoner.game4Mvp else round(summoner.game4MvpScore, 2),
            f"{round(summoner.game5MvpScore, 2)}*" if summoner.game5Mvp else round(summoner.game5MvpScore, 2),
        ]
        tableData.append(row)

    # Create the table with the populated data
    table = t2a(
        header=["Summoner", "Rank", "Total score", "Game 1 Score", "Game 2 Score", "game 3 Score", "Game 4 Score", "Game 5 Score"],
        body=tableData,
        style=PresetStyle.ascii_simple,
        cell_padding=1
    )

    with open("crown data.txt", "w", encoding="utf-8") as file:
        file.write(table)


def mvpData(matchId):
    data = openJsonFile(jsonFile)
    gameData = []

    # Calculate mean and std
    meanStdDict = {stat: calculateMeanAndStd(data, matchId, stat) for stat in statisticsForMvp}

    for participant in data["matchData"][matchId]["info"]['participants']:
        playerChamp = participant['championName']
        playerName = participant['riotIdGameName']
        playerTeam = participant['win']
        zScores = {}
        originalValues = {}
        for stat, (mean, std) in meanStdDict.items():
            if stat in participant['challenges']:
                originalValue = participant['challenges'][stat]
                multiplier = statisticsForMvp[stat]
                zScore = round(calculateZScore(originalValue, multiplier, mean, std), 2)
            elif stat in participant:
                originalValue = participant[stat]
                multiplier = statisticsForMvp[stat]
                zScore = round(calculateZScore(originalValue, multiplier, mean, std), 2)
            else:
                originalValue = 0  # or any default value you prefer if the statistic is missing
                zScore = 0

            # Use a tuple instead of a lambda function
            zScores[stat] = (zScore, originalValue)
            originalValues[stat] = originalValue

        totalZScore = round(sum(z[0] for z in zScores.values()), 2)

        playerData = {
            "Summoner": playerName,
            "Champion": playerChamp,
            "Win": playerTeam,
            "Total Score": totalZScore,
            "Z-Scores": zScores,
            "Original Values": originalValues,
        }
        gameData.append(playerData)

    # Sort the gameData list by Total Score in descending order
    gameData.sort(key=lambda x: x["Total Score"], reverse=True)

    # Add Rank to each player's data
    for rank, playerData in enumerate(gameData, start=1):
        playerData["Rank"] = rank

    # Dynamically generate the table header based on statisticsForMvp
    header = ["Summoner", "Champion", "Win", "Rank", "Total Score"]
    for stat, multiplier in statisticsForMvp.items():
        header.append(f"{stat} ({multiplier})")

    table = t2a(
        header=header,
        body=[
            [
                row["Summoner"],
                row["Champion"],
                row["Win"],
                row["Rank"],
                row["Total Score"],
                *(f"{round(row['Z-Scores'][stat][0], 2)} ({round(row['Z-Scores'][stat][1], 2)})" for stat in statisticsForMvp)
            ]
            for row in gameData
        ],
        style=PresetStyle.ascii_simple,
        cell_padding=1
    )

    with open("mvp data.txt", "w", encoding="utf-8") as file:
        file.write(table)


def fetchMatchData(i, summoner, data, matchId):
    mvpPuuid = None
    maxZScore = float('-inf')

    summoner.__setattr__(f'game{i + 1}GameLength', data["matchData"][matchId]["info"]["gameDuration"])

    # Calculate mean and std for each statistic
    meanStdDict = {stat: calculateMeanAndStd(data, matchId, stat) for stat in statisticsForMvp}

    for participant in data["matchData"][matchId]["info"]['participants']:
        playerPuuid = participant['puuid']
        zScores = {}
        for stat, (mean, std) in meanStdDict.items():
            if stat in participant['challenges']:
                originalValue = participant['challenges'][stat]
            elif stat in participant:
                originalValue = participant[stat]
            else:
                originalValue = 0  # or any default value you prefer if the statistic is missing

            # Calculate the Z-score using the multiplier from statisticsForMvp
            zScores[stat] = calculateZScore(originalValue, statisticsForMvp[stat], mean, std)

        totalZScore = sum(zScores.values())
        if participant['puuid'] == summoner.puuid:
            summoner.__setattr__(f'game{i + 1}MvpScore', totalZScore)

        # MVP
        if totalZScore > maxZScore:
            maxZScore = totalZScore
            mvpPuuid = playerPuuid

        if participant['puuid'] == summoner.puuid:
            summoner.__setattr__(f'game{i + 1}Champion', participant['championName'])
            summoner.__setattr__(f'game{i + 1}Kills', participant['kills'])
            summoner.__setattr__(f'game{i + 1}Deaths', participant['deaths'])
            summoner.__setattr__(f'game{i + 1}Assists', participant['assists'])
            summoner.__setattr__(f'game{i + 1}DamageDealtToChampions', participant['totalDamageDealtToChampions'])
            summoner.__setattr__(f'game{i + 1}Win', participant['win'])
            summoner.__setattr__(f'game{i + 1}Remake', participant['gameEndedInEarlySurrender'])

        # FIX NAME CHANGE
        if i == 0 and participant['puuid'] == summoner.puuid:
            gameName = participant['riotIdGameName'] + '#' + participant['riotIdTagline']
            savedName = summoner.fullName

            if gameName != savedName and gameName != "#":
                summoner.fullName = gameName
                summoner.tagline = participant['riotIdTagline']
                summoner.name = participant['riotIdGameName']
                print(f"{savedName} has changed their name to {gameName}")
                data["summoners"][gameName] = data["summoners"].pop(savedName)
                writeToJsonFile("data.json", data)

    # Print MVP
    # print(f"MVP: {mvpPuuid}")

    if mvpPuuid == summoner.puuid:
        summoner.__setattr__(f'game{i + 1}Mvp', True)
    else:
        summoner.__setattr__(f'game{i + 1}Mvp', False)


def fetchAllSummonerData(force, daily):
    summoners = []
    summonersList = []
    jsonData = openJsonFile(jsonFile)

    # assign ids, ranks, score
    for summonerName in jsonData["summoners"]:

        summoner = Summoner()

        summoner.fullName = summonerName
        summoner.name = summonerName.split("#")[0]
        summoner.tagline = summonerName.split("#")[1]
        summoner.id = jsonData["summoners"][summonerName]["id"]
        summoner.puuid = jsonData["summoners"][summonerName]["puuid"]
        summoner.platform = jsonData["summoners"][summonerName]["platform"]
        summoner.region = jsonData["summoners"][summonerName]["region"]
        # print(f'Fetching {summoner.fullName} rank data')
        try:
            riotApiData = requests.get(f'https://{summoner.platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner.id}?api_key={riotApKey}').json()

            for data in riotApiData:
                if data['queueType'] == 'RANKED_SOLO_5x5':
                    summoner.tier = data['tier']
                    summoner.rank = data['rank']
                    summoner.leaguePoints = data['leaguePoints']
                    summoner.wins = data['wins']
                    summoner.losses = data['losses']
                    summoner.hotStreak = data['hotStreak']

                    if 'miniSeries' in data:
                        summoner.series = True
                        summoner.seriesWins = data['miniSeries']['wins']
                        summoner.seriesLosses = data['miniSeries']['losses']
                    else:
                        summoner.series = False

            summoner.previousScore = jsonData["summoners"][summonerName]["score"]
            summoner.score = Rank.calculateScore(summoner.tier, summoner.rank, summoner.leaguePoints)
            summoner.deltaScore = summoner.score - summoner.previousScore
            summoner.previousLeaderboardPosition = jsonData["summoners"][summonerName]["leaderboardPosition"]
            summoner.gamesPlayed = summoner.wins + summoner.losses
            summoner.previousGamesPlayed = jsonData["summoners"][summonerName]["gamesPlayed"]
            summoner.deltaGamesPlayed = summoner.gamesPlayed - summoner.previousGamesPlayed

            if daily:
                summoner.dailyScore = jsonData["summoners"][summonerName]['dailyScore']
                summoner.deltaDailyScore = summoner.score - summoner.dailyScore
                summoner.dailyGamesPlayed = jsonData["summoners"][summonerName]['dailyGamesPlayed']
                summoner.deltaGamesPlayed = summoner.gamesPlayed - summoner.dailyGamesPlayed
                summoner.dailyLeaderboardPosition = jsonData["summoners"][summonerName]['dailyLeaderboardPosition']

            summoners.append(summoner)

        except Exception:
            # print(f"{summoner.fullName} is unranked")
            pass

    summoners.sort(key=lambda s: (Rank.tierOrder[s.tier], Rank.rankOrder[s.rank], s.leaguePoints, int(s.wins / (s.wins + s.losses) * 100)), reverse=True)

    for i, summoner in enumerate(summoners):
        summoner.leaderboardPosition = i + 1
        summoner.deltaLeaderboardPosition = summoner.previousLeaderboardPosition - summoner.leaderboardPosition
        jsonData["summoners"][summoner.fullName]['score'] = summoner.score
        jsonData["summoners"][summoner.fullName]['leaderboardPosition'] = summoner.leaderboardPosition
        jsonData["summoners"][summoner.fullName]['gamesPlayed'] = summoner.gamesPlayed
        if daily:
            jsonData["summoners"][summoner.fullName]['dailyScore'] = summoner.score
            jsonData["summoners"][summoner.fullName]['dailyLeaderboardPosition'] = summoner.leaderboardPosition
            jsonData["summoners"][summoner.fullName]['dailyGamesPlayed'] = summoner.gamesPlayed
            summoner.deltaDailyLeaderboardPosition = summoner.dailyLeaderboardPosition - summoner.leaderboardPosition

    updated = False
    for summoner in summoners:
        if daily:
            if summoner.deltaDailyScore != 0 or summoner.deltaDailyLeaderboardPosition != 0 or summoner.deltaDailyGamesPlayed != 0:
                updated = True
        else:
            if summoner.deltaScore != 0 or summoner.deltaLeaderboardPosition != 0 or summoner.deltaGamesPlayed != 0 or force:
                updated = True

    if updated or force:
        allMatchesIds = []
        highEloPlayers = None
        sortedHighEloPlayers = []

        # high elo players
        for summoner in summoners:
            if summoner.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                mastersUrl = "https://euw1.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
                grandMastersUrl = "https://euw1.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
                challengerUrl = "https://euw1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
                combinedHighEloPlayers = []
                for url in [mastersUrl, grandMastersUrl, challengerUrl]:
                    response = requests.get(url)
                    if response.status_code == 200:
                        players = response.json().get("entries", [])
                        combinedHighEloPlayers.extend(players)
                    else:
                        print(f"Failed to fetch data from {url}. Status code:", response.status_code)

                sortedHighEloPlayers = sorted(combinedHighEloPlayers, key=lambda x: (-x["leaguePoints"], x["summonerName"]))
                highEloPlayers = True
                break
            else:
                highEloPlayers = False

        if highEloPlayers:
            for summoner in summoners:
                if summoner.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                    for index, player in enumerate(sortedHighEloPlayers, start=1):
                        if player["summonerId"] == summoner.id:
                            summoner.rank = index
                            break

        for summoner in summoners:
            # solo 420 flex 440
            riotApiData = requests.get(f'https://{summoner.region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner.puuid}/ids?queue=420&start=0&count=5&api_key={riotApKey}').json()
            for i, matchId in enumerate(riotApiData):
                allMatchesIds.append(matchId)
                if matchId in jsonData["matchData"]:
                    # print(f"Found {matchId} in json")
                    fetchMatchData(i, summoner, jsonData, matchId)
                else:
                    # print(f'Fetching {matchId}')
                    success = False
                    matchData = None
                    while not success:
                        response = requests.get(f'https://{summoner.region}.api.riotgames.com/lol/match/v5/matches/{matchId}?api_key={riotApKey}')
                        if response.status_code == 200:
                            matchData = response.json()
                            success = True
                        else:
                            print("No match data, trying again in 125 seconds")
                            time.sleep(125)

                    jsonData["matchData"][matchId] = matchData

                    fetchMatchData(i, summoner, jsonData, matchId)

            summonersList.append(summoner)

        # give crown to the best recent 5 games
        for summoner in summoners:
            summoner.MvpScoreTotal = summoner.game1MvpScore + summoner.game2MvpScore + summoner.game3MvpScore + summoner.game4MvpScore + summoner.game5MvpScore
            # print(f"{summoner.name}, Total: {summoner.MvpScoreTotal}, Game 1: {summoner.game1MvpScore}, Game 2: {summoner.game2MvpScore}, Game 3: {summoner.game3MvpScore}, Game 4: {summoner.game4MvpScore}, Game 5: {summoner.game5MvpScore}")

        playerWithHighestScore = max(summoners, key=lambda x: x.MvpScoreTotal)
        playerWithHighestScore.hasCrown = True

        # clean up matchData
        keysToDelete = []
        for matchId in jsonData["matchData"].keys():
            if matchId not in allMatchesIds:
                # print(f'Deleting {matchId}')
                keysToDelete.append(matchId)

        # Now delete the keys outside of the loop
        for matchId in keysToDelete:
            del jsonData["matchData"][matchId]

        # Save the updated data back to the JSON file
        writeToJsonFile("data.json", jsonData)

    return summonersList, updated


def generateImage(summones, daily):
    # Calculate the size of the canvas based on the number of summonerss
    canvasWidth = 1820
    canvasHeight = (140 * len(summones) - 20 + 100)
    if daily:
        canvasHeight = (140 * len(summones) - 20 + 340)

    # Create image of rank list on top of background
    canvas = Image.new('RGBA', (canvasWidth, canvasHeight), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)

    # Load tier icons
    icons = {
        tier: Image.open(Rank.iconPath[tier]).resize((80, 80), resample=Image.BICUBIC)
        for tier in Rank.iconPath
    }

    hotStreakIcon = Image.open('Imgs/Fire emoji.png').resize((30, 30), resample=Image.BICUBIC)
    coldStreakIcon = Image.open('Imgs/Skull emoji.png').resize((30, 30), resample=Image.BICUBIC)

    # Define box parameters
    boxWidth = 1820
    boxHeight = 120
    borderRadius = 60

    # Define the new box colors
    firstPlaceColor = (212, 175, 55)  # gold
    secondPlaceColor = (192, 192, 192)  # silver
    thirdPlaceColor = (183, 119, 41)  # bronze

    # Write summoners info and tier icons to image
    fontTitle = ImageFont.truetype("ARIAL.TTF", 120)
    fontLeaderboardRank = ImageFont.truetype("ARIAL.TTF", 70)
    fontName = ImageFont.truetype("ARIAL.TTF", 40)
    fontTagline = ImageFont.truetype("ARIAL.TTF", 16)
    fontTier = ImageFont.truetype("ARIAL.TTF", 32)
    fontLp = ImageFont.truetype("ARIAL.TTF", 24)
    fontKda = ImageFont.truetype('ARIAL.TTF', 25)

    y = 0
    if daily:
        dateStr = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%y")
        drawTextCentered(canvas, f"Daily - {dateStr}", 910, 120, fontTitle)
        y = 240
    for i, summoner in enumerate(summones):
        # Determine the box color based on summoner rank
        if i == 0:
            boxColor = firstPlaceColor
        elif i == 1:
            boxColor = secondPlaceColor
        elif i == 2:
            boxColor = thirdPlaceColor
        else:
            boxColor = (49, 49, 60, 255)  # default box color

        # Draw box background
        x = 0
        boxPos = (x, y, x + boxWidth, y + boxHeight)
        circleColor = (40, 40, 48, 255)
        draw.rounded_rectangle(boxPos, borderRadius, boxColor, None)
        draw.ellipse((x + 120, y + 10, x + 230, y + 110), fill=circleColor)
        draw.ellipse((x + 10, y + 10, x + 110, y + 110), fill=circleColor)

        # Draw tier icon
        tierIcon = icons[summoner.tier]
        canvas.paste(tierIcon, (x + 135, y + 20), tierIcon)

        # draw deltaLeaguePoints
        if daily:
            if summoner.deltaDailyScore != 0:
                draw.ellipse((x + 610, y + 10, x + 710, y + 110), fill=circleColor)

                if summoner.deltaDailyScore > 0:
                    textBbox = fontName.getbbox(f"+{summoner.deltaDailyScore}")
                    textWidth = textBbox[2] - textBbox[0]
                    xCentered = x + 660 - textWidth // 2
                    draw.text((xCentered, y + 40), f"+{summoner.deltaDailyScore}", (50, 200, 50), font=fontName)
                else:
                    textBbox = fontName.getbbox(f"{summoner.deltaDailyScore}")
                    textWidth = textBbox[2] - textBbox[0]
                    xCentered = x + 660 - textWidth // 2
                    draw.text((xCentered, y + 40), f"{summoner.deltaDailyScore}", (200, 50, 50), font=fontName)

            if summoner.deltaDailyScore == 0 and summoner.deltaDailyGamesPlayed != 0:
                draw.ellipse((x + 610, y + 10, x + 710, y + 110), fill=circleColor)
                textBbox = fontName.getbbox('-0')
                textWidth = textBbox[2] - textBbox[0]
                xCentered = x + 660 - textWidth // 2
                draw.text((xCentered, y + 40), '-0', (200, 50, 50), font=fontName)
        else:
            if summoner.deltaScore != 0:
                draw.ellipse((x + 610, y + 10, x + 710, y + 110), fill=circleColor)

                if summoner.deltaScore > 0:
                    textBbox = fontName.getbbox(f"+{summoner.deltaScore}")
                    textWidth = textBbox[2] - textBbox[0]
                    xCentered = x + 660 - textWidth // 2
                    draw.text((xCentered, y + 40), f"+{summoner.deltaScore}", (50, 200, 50), font=fontName)
                else:
                    textBbox = fontName.getbbox(f"{summoner.deltaScore}")
                    textWidth = textBbox[2] - textBbox[0]
                    xCentered = x + 660 - textWidth // 2
                    draw.text((xCentered, y + 40), f"{summoner.deltaScore}", (200, 50, 50), font=fontName)

            if summoner.deltaScore == 0 and summoner.deltaGamesPlayed != 0:
                draw.ellipse((x + 610, y + 10, x + 710, y + 110), fill=circleColor)
                textBbox = fontName.getbbox('-0')
                textWidth = textBbox[2] - textBbox[0]
                xCentered = x + 660 - textWidth // 2
                draw.text((xCentered, y + 40), '-0', (200, 50, 50), font=fontName)

        # promos
        # if summoner.series:
        #     draw.ellipse((x + 500, y + 10, x + 600, y + 110), fill=circleColor)
        #     textBbox = fontName.getbbox(f"{summoner.seriesWins}-{summoner.seriesLosses}")
        #     textWidth = textBbox[2] - textBbox[0]
        #     xCentered = x + 550 - textWidth // 2
        #     draw.text((xCentered, y + 40), f"{summoner.seriesWins}-{summoner.seriesLosses}", (255, 255, 255), font=fontName)

        # leaderboard Position
        if daily:
            if summoner.deltaDailyLeaderboardPosition != 0:
                draw.ellipse((x + 490, y + 10, x + 590, y + 110), fill=circleColor)

                if summoner.deltaDailyLeaderboardPosition > 0:
                    triangleCoordsUp = [(x + 530, y + 70), (x + 540, y + 50), (x + 550, y + 70)]
                    draw.polygon(triangleCoordsUp, fill=(50, 200, 50), outline=(0, 0, 0))
                else:
                    triangleCoordsDown = [(x + 530, y + 50), (x + 540, y + 70), (x + 550, y + 50)]
                    draw.polygon(triangleCoordsDown, fill=(200, 50, 50), outline=(0, 0, 0))
        else:

            if summoner.deltaLeaderboardPosition != 0:
                draw.ellipse((x + 490, y + 10, x + 590, y + 110), fill=circleColor)

                if summoner.deltaLeaderboardPosition > 0:
                    triangleCoordsUp = [(x + 530, y + 70), (x + 540, y + 50), (x + 550, y + 70)]
                    draw.polygon(triangleCoordsUp, fill=(50, 200, 50), outline=(0, 0, 0))
                else:
                    triangleCoordsDown = [(x + 530, y + 50), (x + 540, y + 70), (x + 550, y + 50)]
                    draw.polygon(triangleCoordsDown, fill=(200, 50, 50), outline=(0, 0, 0))

        draw.rounded_rectangle((x + 110 + + 620, y + 10, x + 110 + + 820, y + 110), borderRadius, circleColor, None)
        drawChampionImage(canvas, 730, y + 10, summoner.game1Champion, summoner.game1Win, summoner.game1Remake, summoner.game1Mvp)
        draw.text((835, y + 30), f"{summoner.game1Kills}/{summoner.game1Deaths}/{summoner.game1Assists}", (255, 255, 255), fontKda)
        draw.text((835, y + 60), formatDamage(summoner.game1DamageDealtToChampions), (255, 255, 255), fontKda)
        # draw.text((835, y + 90), formatDamage(round(summoner.game1MvpScore, 2)), (255, 255, 255), fontKda)

        draw.rounded_rectangle((x + 110 + + 840, y + 10, x + 110 + + 1040, y + 110), borderRadius, circleColor, None)
        drawChampionImage(canvas, 950, y + 10, summoner.game2Champion, summoner.game2Win, summoner.game2Remake, summoner.game2Mvp)
        draw.text((1055, y + 30), f"{summoner.game2Kills}/{summoner.game2Deaths}/{summoner.game2Assists}", (255, 255, 255), fontKda)
        draw.text((1055, y + 60), formatDamage(summoner.game2DamageDealtToChampions), (255, 255, 255), fontKda)
        # draw.text((1055, y + 90), formatDamage(round(summoner.game2MvpScore, 2)), (255, 255, 255), fontKda)

        draw.rounded_rectangle((x + 110 + + 1060, y + 10, x + 110 + + 1260, y + 110), borderRadius, circleColor, None)
        drawChampionImage(canvas, 1170, y + 10, summoner.game3Champion, summoner.game3Win, summoner.game3Remake, summoner.game3Mvp)
        draw.text((1275, y + 30), f"{summoner.game3Kills}/{summoner.game3Deaths}/{summoner.game3Assists}", (255, 255, 255), fontKda)
        draw.text((1275, y + 60), formatDamage(summoner.game3DamageDealtToChampions), (255, 255, 255), fontKda)
        # draw.text((1275, y + 90), formatDamage(round(summoner.game3MvpScore, 2)), (255, 255, 255), fontKda)

        draw.rounded_rectangle((x + 110 + + 1280, y + 10, x + 110 + + 1480, y + 110), borderRadius, circleColor, None)
        drawChampionImage(canvas, 1390, y + 10, summoner.game4Champion, summoner.game4Win, summoner.game4Remake, summoner.game4Mvp)
        draw.text((1495, y + 30), f"{summoner.game4Kills}/{summoner.game4Deaths}/{summoner.game4Assists}", (255, 255, 255), fontKda)
        draw.text((1495, y + 60), formatDamage(summoner.game4DamageDealtToChampions), (255, 255, 255), fontKda)
        # draw.text((1495, y + 90), formatDamage(round(summoner.game4MvpScore, 2)), (255, 255, 255), fontKda)

        draw.rounded_rectangle((x + 110 + + 1500, y + 10, x + 110 + + 1700, y + 110), borderRadius, circleColor, None)
        drawChampionImage(canvas, 1610, y + 10, summoner.game5Champion, summoner.game5Win, summoner.game5Remake, summoner.game5Mvp)
        draw.text((1715, y + 30), f"{summoner.game5Kills}/{summoner.game5Deaths}/{summoner.game5Assists}", (255, 255, 255), fontKda)
        draw.text((1715, y + 60), formatDamage(summoner.game5DamageDealtToChampions), (255, 255, 255), fontKda)
        # draw.text((1715, y + 90), formatDamage(round(summoner.game5MvpScore, 2)), (255, 255, 255), fontKda)

        # Calculate the length of the summoner.name
        nameLength = draw.textlength(summoner.name, font=fontName)

        # Draw summoner name with fontName
        draw.text((x + 240, y + 10), summoner.name, (255, 255, 255), font=fontName)

        # Draw summoner tagline with fontLp after the summoner.name
        draw.text((x + 240 + nameLength + 5, y + 31), f"#{summoner.tagline}", (255, 255, 255), font=fontTagline)

        # Draw hot streak
        if summoner.hotStreak:
            taglineLength = draw.textlength(f"#{summoner.tagline}", font=fontTagline)

            canvas.paste(hotStreakIcon, (x + 245 + int(nameLength + taglineLength), y + 17), hotStreakIcon)

        lossesInARow = 0
        for i in range(5):
            if not summoner.__dict__.get(f'game{i + 1}Remake'):
                if not summoner.__dict__.get(f'game{i + 1}Win'):
                    lossesInARow += 1
                else:
                    break

        # crown
        if summoner.hasCrown:
            crown = Image.open("Imgs/crown.png").convert("RGBA")
            canvas.paste(crown, (x + 157, y + 17), crown)

        # Draw loss streak
        if lossesInARow >= 3:
            taglineLength = draw.textlength(f"#{summoner.tagline}", font=fontTagline)
            canvas.paste(coldStreakIcon, (x + 245 + int(nameLength + taglineLength), y + 17), coldStreakIcon)

        # Draw summoner tier and rank
        draw.text((x + 240, y + 54), f"{summoner.tier} {Rank.rankToNumber(summoner.rank)}", (255, 255, 255), font=fontTier)
        draw.text((x + 240, y + 90), f"{summoner.leaguePoints} LP {summoner.wins}/{summoner.losses} {round(summoner.wins / (summoner.wins + summoner.losses) * 100, 1)}%", (255, 255, 255), font=fontLp)
        # draw.text((x + 1720, y + 20), , (255, 255, 255), font=fontLeaderboardRank)
        drawTextCentered(canvas, f"{summoner.leaderboardPosition}", x + 60, y + 50, fontLeaderboardRank)

        # Increment y position for next summoners
        y += boxHeight + 20

        drawTextCentered(canvas, "SLASH COMMANDS: /add, /remove, /mvp, /crown, /list, /patch /chall", 910, y + 10, fontTier)

    # Save image to file and show it
    if daily:
        canvas.save('Daily Rank list.png')
    else:
        canvas.save('Rank list.png')
    # canvas.show()


def update(force, daily):
    interval = math.floor(60 * numberOfSummoners(5) / (requestLimit * 0.7))

    updateRaceImage.change_interval(seconds=interval)

    list = fetchAllSummonerData(force, daily)

    print(f"\r{datetime.now().strftime('%I:%M:%S %p %d/%m/%Y')}", end="", flush=True)

    if list[1] or force:
        generateImage(list[0], daily)
    return list[1]


if __name__ == "__main__":

    @bot.event
    async def on_ready():
        print('Logged in as {0.user} at {1}'.format(bot, datetime.now().strftime('%I:%M:%S %p %d/%m/%Y')))
        print("")
        if not updateRaceImage.is_running():
            updateRaceImage.start()
            updatePatchNotes.start()


    @tasks.loop(minutes=120)
    async def updatePatchNotes():
        updateAvailable, updatedPatch, daysAgo, daysTillNext, fullUrl, imagePath = checkForNewPatchNotes("data.json", False)
        if daysAgo > 12:
            updatePatchNotes.change_interval(minutes=15)

        if updateAvailable:
            channel = bot.get_channel(discordChannel)
            # print("There is a new patch available. Patch version:", updatedPatch, fullUrl, "Image saved at:", imagePath)
            with open(imagePath, 'rb') as f:
                image = disnake.File(f)

                await channel.send(f'Patch {updatedPatch}\n'
                                   f'{"tomorrow" if daysAgo == -1 else "today" if daysAgo == 0 else "yesterday" if daysAgo == 1 else f"{daysAgo} days ago"}\n'
                                   f'{"" if daysAgo < 1 or daysTillNext == 13 or daysTillNext == 0 else f"next patch in: {daysTillNext} days"}\n'
                                   f'{fullUrl}', file=image)


    @tasks.loop(seconds=60)
    async def updateRaceImage():
        json_data = openJsonFile(jsonFile)
        lastRunTime = json_data['runtime']
        # Set the timezone to Europe/London
        timezone = pytz.timezone('Europe/London')
        currentTime = datetime.now(tz=timezone)
        dateStr = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%y")

        dailyTime = currentTime.replace(hour=dailyPostTimer, minute=0, second=0, microsecond=0).timestamp()

        # If it's past 9pm and last run time is before 9pm today, update the image
        if currentTime.timestamp() > dailyTime > lastRunTime:
            json_data['runtime'] = dailyTime
            writeToJsonFile("data.json", json_data)
            if update(False, True):
                channel = bot.get_channel(discordChannel)

                with open("Daily Rank list.png", 'rb') as f:
                    image = disnake.File(f)

                await channel.send(f'Daily - {dateStr}', file=image)
        else:
            if update(False, False):
                channel = bot.get_channel(discordChannel)

                with open("Rank list.png", 'rb') as f:
                    image = disnake.File(f)

                await channel.send(file=image)


    @bot.slash_command(description="Full list of summoners")
    async def list(inter: ApplicationCommandInteraction):
        await inter.response.defer()
        jsonData = openJsonFile(jsonFile)
        summonerList = []
        for summoner in jsonData['summoners']:
            summonerList.append(summoner)
        await inter.send("\n".join(summonerList))


    @bot.slash_command(description="lp needed for challenger and grandmaster")
    async def chall(inter: ApplicationCommandInteraction, platform: str = commands.Param(choices=platforms)):
        await inter.response.defer()

        mastersUrl = f"https://{platform}.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
        grandMastersUrl = f"https://{platform}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
        challengerUrl = f"https://{platform}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
        combinedHighEloPlayers = []
        for url in [mastersUrl, grandMastersUrl, challengerUrl]:
            response = requests.get(url)
            if response.status_code == 200:
                players = response.json().get("entries", [])
                combinedHighEloPlayers.extend(players)
            else:
                print(f"Failed to fetch data from {url}. Status code:", response.status_code)

        sortedHighEloPlayers = sorted(combinedHighEloPlayers, key=lambda x: (-x["leaguePoints"], x["summonerName"]))

        challenger_lp_needed = sortedHighEloPlayers[299]["leaguePoints"] + 1 if len(sortedHighEloPlayers) > 299 else None
        grandmaster_lp_needed = sortedHighEloPlayers[999]["leaguePoints"] + 1 if len(sortedHighEloPlayers) > 999 else None

        await inter.send(f"{platform}\nLP needed for Challenger: {challenger_lp_needed}\nLP needed for Grandmaster: {grandmaster_lp_needed}")


    @bot.slash_command(description="Patch notes")
    async def patch(inter: ApplicationCommandInteraction):
        await inter.response.defer()
        update_available, updated_patch, days_ago, days_till_next, full_url, image_path = checkForNewPatchNotes("data.json", True)
        if update_available:
            # print("There is a new patch available. Patch version:", updated_patch, full_url, "Image saved at:", image_path)
            with open(image_path, 'rb') as f:
                image = disnake.File(f)
                await inter.send(f'Patch {updated_patch}\n'
                                 f'{"tomorrow" if days_ago == -1 else "today" if days_ago == 0 else "yesterday" if days_ago == 1 else f"{days_ago} days ago"}\n'
                                 f'{"" if days_ago < 1 or days_till_next == 13 or days_till_next == 0 else f"next patch in: {days_till_next} days"}\n'
                                 f'{full_url}', file=image)


    @bot.slash_command(description="breakdown of mvp score for a given game")
    async def mvp(inter: ApplicationCommandInteraction, name: str, tagline: str, region: str = commands.Param(choices=regions), game: int = commands.Param(choices=[1, 2, 3, 4, 5])):
        await inter.response.defer()
        response = requests.get(
            f'https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tagline}?api_key={riotApKey}'
        )
        if response.status_code == 200:
            apiData1 = response.json()
            summonerPuuid = apiData1['puuid']
            summonerName = apiData1['gameName']
            summonerTagline = apiData1['tagLine']
            riotApiData = requests.get(f'https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{summonerPuuid}/ids?queue=420&start=0&count=5&api_key={riotApKey}').json()

            matchId = riotApiData[game - 1]
            mvpData(matchId)

            with open("mvp data.txt", 'rb') as f:
                dataFile = disnake.File(f)
            await inter.send(f'Mvp scores for: {summonerName}#{summonerTagline}, game: {game}', file=dataFile)
        else:
            summonerFullName = f"{name}#{tagline}"
            await inter.send(f'Invalid summoner: {summonerFullName}')


    @bot.slash_command(description="Mvp scores for all summoners")
    async def crown(inter: ApplicationCommandInteraction):
        await inter.response.defer()
        crownData()
        with open("crown data.txt", 'rb') as f:
            dataFile = disnake.File(f)
        await inter.send(f'Mvp scores', file=dataFile)


    @bot.slash_command(description="Add summoner to the list")
    async def add(inter: ApplicationCommandInteraction, name: str, tagline: str, platform: str = commands.Param(choices=platforms), region: str = commands.Param(choices=regions)):
        await inter.response.defer()
        jsonData = openJsonFile(jsonFile)
        if "#" in tagline:
            tagline = tagline.replace("#", "")

        summonerFullName = f"{name}#{tagline}"
        summonerList = []
        for summoner in jsonData['summoners']:
            summonerList.append(summoner)

        if summonerFullName.lower() in summonerList:
            await inter.send(f'{name} is already added')

        else:
            response = requests.get(
                f'https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tagline}?api_key={riotApKey}'
            )
            if response.status_code == 200:
                apiData1 = response.json()
                summonerFullName = apiData1['gameName'] + '#' + apiData1['tagLine']
                summonerPuuid = apiData1['puuid']

                response = requests.get(
                    f'https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{summonerPuuid}?api_key={riotApKey}'
                )
                apiData2 = response.json()

                data = jsonData

                data["summoners"][summonerFullName] = {
                    "id": apiData2['id'],
                    "puuid": summonerPuuid,
                    "profileIconId": 123,
                    "platform": platform,
                    "region": region,
                    "score": 0,
                    "dailyScore": 0,
                    "leaderboardPosition": 100,
                    "dailyLeaderboardPosition": 100,
                    "gamesPlayed": 0,
                    "dailyGamesPlayed": 0
                }

                writeToJsonFile("data.json", data)
                await inter.send(f'{summonerFullName} added')
            else:
                await inter.send(f'Invalid summoner: {summonerFullName}')


    @bot.slash_command(description="Remove summoner from the list")
    async def remove(inter: ApplicationCommandInteraction, name: str, tagline: str):
        await inter.response.defer()
        jsonData = openJsonFile(jsonFile)
        if "#" in tagline:
            tagline = tagline.replace("#", "")

        summonerFullName = f"{name}#{tagline}"
        summonerList = [summoner.lower() for summoner in jsonData['summoners']]

        if summonerFullName.lower() not in summonerList:
            await inter.send(f"{summonerFullName} has not been added")
        else:
            # Find the matching summoner in the original case
            originalCaseSummoner = next(
                summoner for summoner in jsonData['summoners']
                if summoner.lower() == summonerFullName.lower())
            del jsonData['summoners'][originalCaseSummoner]
            writeToJsonFile("data.json", jsonData)
            await inter.send(f"{originalCaseSummoner} removed")


    bot.run(discordToken)
