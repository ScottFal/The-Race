import math
from datetime import datetime, timedelta
import disnake
import pytz
from disnake import ApplicationCommandInteraction
from disnake.ext import commands, tasks
import requests
from src.utils.commonUtils import requestLimit, jsonFile, dailyPostTimer, discordChannel, platforms, regions, riotApKey, discordToken
from src.utils.dataUtils import checkForNewPatchNotes, numberOfSummoners, update, crownData, mvpData
from src.utils.jsonUtils import openJsonFile, writeToJsonFile

bot = commands.InteractionBot()

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
        interval = math.floor(60 * numberOfSummoners(5) / (requestLimit * 0.7))

        updateRaceImage.change_interval(seconds=interval)

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
        summonerList = [summoner.lower() for summoner in jsonData['summoners']]

        if summonerFullName.lower() in summonerList:
            await inter.send(f'{summonerFullName} is already added')

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
