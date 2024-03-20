from datetime import datetime, timedelta
from io import BytesIO
import os
import requests
from PIL import ImageFont
from PIL import Image, ImageDraw

from src.utils.commonUtils import version, Rank


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
