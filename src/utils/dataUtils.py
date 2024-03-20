import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import os
import numpy as np
import time
import requests
from PIL import ImageFont
from PIL import Image, ImageDraw
from table2ascii import table2ascii as t2a, PresetStyle

from src.utils.commonUtils import jsonFile, statisticsForMvp, Summoner, riotApKey, Rank
from src.utils.drawUtils import generateImage
from src.utils.jsonUtils import openJsonFile, writeToJsonFile


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
        highEloPlayersPlatforms = []
        highEloPlayersData = {}

        # Collect unique platforms of summoners in high elo
        for summoner in summoners:
            if summoner.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                platform = summoner.platform
                if platform not in highEloPlayersPlatforms:
                    highEloPlayersPlatforms.append(platform)

        # Fetch high elo player data for each unique platform
        for platform in highEloPlayersPlatforms:
            mastersUrl = f"https://{platform.lower()}.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
            grandMastersUrl = f"https://{platform.lower()}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"
            challengerUrl = f"https://{platform.lower()}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key=RGAPI-f42c18f5-4234-48aa-b354-c977e092238d"

            combinedHighEloPlayers = []
            for url in [mastersUrl, grandMastersUrl, challengerUrl]:
                response = requests.get(url)
                if response.status_code == 200:
                    players = response.json().get("entries", [])
                    combinedHighEloPlayers.extend(players)
                else:
                    print(f"Failed to fetch data from {url}. Status code:", response.status_code)

            sortedHighEloPlayers = sorted(combinedHighEloPlayers, key=lambda x: (-x["leaguePoints"], -x["wins"]))

            highEloPlayersData[platform] = sortedHighEloPlayers

        # Assign ranks to summoners based on fetched data for their respective platforms
        for summoner in summoners:
            if summoner.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                platform = summoner.platform
                for index, player in enumerate(highEloPlayersData[platform], start=1):
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


def update(force, daily):
    list = fetchAllSummonerData(force, daily)

    print(f"\r{datetime.now().strftime('%I:%M:%S %p %d/%m/%Y')}", end="", flush=True)

    if list[1] or force:
        generateImage(list[0], daily)
    return list[1]


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


def numberOfSummoners(wiggleRoom):
    jsonFata = openJsonFile(jsonFile)
    count = len(jsonFata['summoners']) + wiggleRoom
    return count
