import discord
import re
import mysql.connector
from mysql.connector import Error
import subprocess
import time
import requests
import random
from discord.utils import get
import discord.utils
from datetime import datetime

client = discord.Client()

bible_kjv_text = {} 
async def log_message(log_entry):
    current_time_obj = datetime.now()
    current_time_string = current_time_obj.strftime("%b %d, %Y-%H:%M:%S.%f")
    print(current_time_string + " - " + log_entry, flush = True)
    
async def commit_sql(sql_query, params = None):
    try:
        connection = mysql.connector.connect(host='localhost', database='AuthorMaton', user='REDACTED', password='REDACTED')    
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        connection.commit()
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
                
async def select_sql(sql_query, params = None):
    try:
        connection = mysql.connector.connect(host='localhost', database='AuthorMaton', user='REDACTED', password='REDACTED')
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        records = cursor.fetchall()
        return records
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return None
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()

async def execute_sql(sql_query):
    try:
        connection = mysql.connector.connect(host='localhost', database='AuthorMaton', user='REDACTED', password='REDACTED')
        cursor = connection.cursor()
        result = cursor.execute(sql_query)
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
            
async def send_message(message, response):
    await log_message("Message sent back to server " + message.guild.name + " channel " + message.channel.name + " in response to user " + message.author.name + "\n\n" + response)
    message_chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
    for chunk in message_chunks:
        await message.channel.send(">>> " + chunk)
        time.sleep(1)

async def load_bible():
    global bible_kjv_text
    
    await log_message("Loading Bible...")
    
    bible_file = "/home/REDACTED/pg10.txt"
    
    verse_re = re.compile(r"(?P<chapter>\d+):(?P<verse>\d+) (?P<versetext>.+)", re.MULTILINE | re.S)
    book_re = re.compile(r"Book|Gospel|Epistle|^[A-Z][a-z]+$|The Song of Solomon")
    book_title_re = re.compile(r"Book of Moses:  Called (?P<booktitle1>[A-Za-z]+)|Book of the Prophet (?P<booktitle2>[A-Za-z]+)|Book of the (?P<booktitle3>[A-Za-z]+)|Book of (?P<booktitle4>[A-Za-z]+)")
    gospel_title_re = re.compile(r"Gospel According to Saint (?P<booktitle>[A-Za-z]+)")
    epistle_title_re = re.compile(r"Epistle of Paul the Apostle to (?:the){0,1} {0,1}(?P<booktitle1>[A-Za-z]+)|(?:Epistle|Epistle General) of (?P<booktitle2>.+)")
    other_title_re = re.compile(r"^(?P<booktitle>.+)$|Revelation")
    
    f = open(bible_file, 'r')
    new_chapter = False
    new_verse = False
    chapter = ""
    verse = ""
    current_book = "" 
    for line in f:
        new_verse = False
        book_line = False
        if not line.strip() or re.search(r"Otherwise called",line):
            continue
        m = book_re.search(line)
        
        if m:
            book_line = True
            chapter = 1
            verse = 1
            n1 = book_title_re.search(line)
            if n1:
                if n1.group('booktitle1'):
                    book_title = n1.group('booktitle1')
                elif n1.group('booktitle2'):
                    book_title = n1.group('booktitle2')
                elif n1.group('booktitle3'):
                    book_title = n1.group('booktitle3')
                elif n1.group('booktitle4'):
                    book_title = n1.group('booktitle4')
            n2 = gospel_title_re.search(line)
            if n2 and not n1:
                book_title = n2.group('booktitle')
            n5 = epistle_title_re.search(line)
            if n5 and not n1 and not n2:
                if n5.group('booktitle1'):
                    book_title = n5.group('booktitle1')
                elif n5.group('booktitle2'):
                    book_title = n5.group('booktitle2')

            n3 = re.search(r"^The Revelation", line)
            if n3 and not n1 and not n2 and not n5:
                book_title = "Revelation"
            n4 = other_title_re.search(line)
            if n4 and not n1 and not n2 and not n3 and not n5:
                book_title = n4.group('booktitle')
            n6 = re.search("Song of Solomon",line)
            if n6:
                book_title = "Song of Solomon"
            q1 = re.search(r"First", line)
            if q1 and "Moses" not in line:
                book_title = "1 " + book_title
            q2 = re.search(r"Second", line)
            if q2 and "Moses" not in line:
                book_title = "2 " + book_title
            q3 = re.search(r"Third", line)
            if q3 and "Moses" not in line:
               book_title = "3 "+  book_title
            book_title = book_title.strip()
            bible_kjv_text[book_title]  = {} 
            current_book = book_title
            await log_message("New book: " + book_title)
        m = verse_re.search(line)
        if m:
            new_verse = True
            chapter = m.group('chapter')
            verse = m.group('verse')
            verse_text = m.group('versetext')
            if verse == '1':
                bible_kjv_text[current_book][chapter] = {} 
            bible_kjv_text[current_book][chapter][verse] = verse_text.replace('\n',' ')
        if not new_verse and not book_line:
            bible_kjv_text[current_book][chapter][verse] = bible_kjv_text[current_book][chapter][verse] + line.replace('\n',' ')
            
            
    await log_message("Bible loaded.")

async def search_bible(term):
    global bible_kjv_text
    response = " "
    await log_message(term)
    for book in list(bible_kjv_text.keys()):
        for chapter in list(bible_kjv_text[book].keys()):
            for verse in list(bible_kjv_text[book][chapter].keys()):
                if re.search(term, bible_kjv_text[book][chapter][verse], re.IGNORECASE):
                    response = response + "**" + book + " " + chapter + ":" + verse + "** - " + bible_kjv_text[book][chapter][verse] + "\n"
    return response
    
@client.event
async def on_ready():
    global bible_kjv_text
    await load_bible()
    await log_message("Logged in!")


@client.event
async def on_message(message):
    global bible_kjv_text
    
    if message.author == client.user:
        return
    if message.author.bot:
        return
        
    if message.content.startswith('churchbot'):
        await log_message("Command recognized!")

        command_string = message.content.split(' ')
        command = command_string[1]
        parsed_string = message.content.replace("." + command + " ","")
        username = message.author.name
        server_name = message.guild.name 
        await log_message("recognized command: " + command)
        if command == 'lookup':
            parsed_string = parsed_string.replace('lookup ','').replace('churchbot ','')
            m = re.search(r"(?P<booktitle>\d{0,1}\s{0,1}[A-Za-z ]+?) (?P<chapter>\d+):{0,1}(?P<verse>\d+){0,1}-{0,1}(?P<endchapter>\d+){0,1}:{0,1}(?P<endverse>\d+){0,1}", parsed_string)
            if m:
                book = m.group('booktitle')
                book = re.sub(r"^ ","",book)
                chapter = m.group('chapter')
                verse = m.group('verse')
                endchapter = m.group('endchapter')
                endverse = m.group('endverse')
                if endchapter and endverse:
                    verse_text = " "
                    for count_chapter in list(bible_kjv_text[book].keys()):
                        for count_verse in list(bible_kjv_text[book][chapter].keys()):
                            if int(count_chapter) >= int(chapter) and int(count_chapter) <= int(endchapter):
                                if int(count_chapter) == chapter and count_verse >= int(verse):
                                    verse_text = verse_text + "**" + count_chapter + ":" + count_verse + "** - " + bible_kjv_text[book][count_chapter][count_verse] + "\n"
                                elif int(count_chapter) < int(endchapter):
                                    verse_text = verse_text + "**" + count_chapter + ":" + count_verse + "** - " + bible_kjv_text[book][count_chapter][count_verse] + "\n"
                                elif int(count_chapter) == int(endchapter) and int(count_verse) <= int(endverse):
                                    verse_text = verse_text + "**" + count_chapter + ":" + count_verse + "** - " + bible_kjv_text[book][count_chapter][count_verse] + "\n"
                elif not verse:
                    verse_text = " "
                    for key in bible_kjv_text[book][chapter].keys():
                        verse_text = verse_text + "**" + key + "** " + bible_kjv_text[book][chapter][key] + "\n"
                else:        
                    verse_text = bible_kjv_text[book][chapter][verse]
                await send_message(message, "**" + parsed_string.replace('churchbot ','') + "**\n\n" + verse_text)
            else:
                await send_message(message, "Not a valid reference.")
        elif command == 'randomverse':
            book = random.choice(list(bible_kjv_text.keys()))
            chapter = random.choice(list(bible_kjv_text[book].keys()))
            verse = random.choice(list(bible_kjv_text[book][str(chapter)].keys()))
            verse_text = bible_kjv_text[book][str(chapter)][str(verse)]
            response = "**RANDOM VERSE**\n\n" + verse_text + "\n" + "*" + book + " " + chapter + ":" + verse + ", KJV*\n"
            await send_message(message, response)
        elif command == 'searchbible':
            parsed_string = parsed_string.replace('searchbible ','').replace('churchbot ','')
            response = await search_bible(parsed_string)
            await send_message(message, response)
            
            
 
client.run('')