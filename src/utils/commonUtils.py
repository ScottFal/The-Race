import os
import requests
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
